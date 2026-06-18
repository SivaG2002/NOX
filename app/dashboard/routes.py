from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError
from sqlalchemy import desc, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.client import StreamNotificationBot
from app.core.security import get_or_create_csrf_token
from app.database.session import AsyncSessionLocal
from app.models import Guild, NotificationLog, StreamState, Streamer
from app.schemas.embed_template import EmbedTemplateUpdate
from app.schemas.streamer import StreamerCreate, normalize_streamer_name
from app.services.guild_defaults import (
    ensure_guild_defaults,
    get_guild_by_discord_id,
    get_or_create_embed_template,
    get_or_create_notification_settings,
)

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


def require_user(request: Request) -> dict | RedirectResponse:
    user = request.session.get("user")
    if not user:
        return RedirectResponse("/auth/login", status_code=status.HTTP_303_SEE_OTHER)
    return user


def flash(request: Request, message: str, category: str = "info") -> None:
    request.session.setdefault("flashes", []).append({"message": message, "category": category})


def pop_flashes(request: Request) -> list[dict]:
    flashes = request.session.get("flashes", [])
    request.session["flashes"] = []
    return flashes


def base_context(request: Request, **extra) -> dict:
    return {
        "request": request,
        "user": request.session.get("user"),
        "csrf_token": get_or_create_csrf_token(request),
        "flashes": pop_flashes(request),
        **extra,
    }


async def load_guild(request: Request, db: AsyncSession, guild_id: str) -> Guild:
    manageable_ids = {str(guild["id"]) for guild in request.session.get("guilds", [])}
    if str(guild_id) not in manageable_ids:
        raise HTTPException(status_code=403, detail="Missing Manage Server permission")
    guild = await get_guild_by_discord_id(db, guild_id)
    if not guild:
        raise HTTPException(status_code=404, detail="Guild not found")
    await ensure_guild_defaults(db, guild)
    await db.commit()
    await db.refresh(guild)
    return guild


async def discord_choices(request: Request, guild_id: str) -> tuple[list[dict], list[dict]]:
    bot: StreamNotificationBot | None = getattr(request.app.state, "discord_bot", None)
    if not bot or not bot.is_ready():
        return [], []
    return await bot.list_text_channels(guild_id), await bot.list_roles(guild_id)


@router.get("/")
async def root(request: Request):
    if request.session.get("user"):
        return RedirectResponse("/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    return RedirectResponse("/auth/login", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/dashboard")
async def dashboard(request: Request):
    user = require_user(request)
    if isinstance(user, RedirectResponse):
        return user
    async with AsyncSessionLocal() as db:
        ids = {str(guild["id"]) for guild in request.session.get("guilds", [])}
        result = await db.execute(select(Guild).where(Guild.guild_id.in_(ids)).order_by(Guild.name))
        guilds = list(result.scalars().all())
    
    return templates.TemplateResponse(
    request=request,
    name="dashboard.html",
    context=base_context(request, guilds=guilds),
)

@router.get("/dashboard/{guild_id}")
async def guild_overview(request: Request, guild_id: str):
    user = require_user(request)
    if isinstance(user, RedirectResponse):
        return user
    async with AsyncSessionLocal() as db:
        guild = await load_guild(request, db, guild_id)
        total_streamers = await db.scalar(
            select(func.count(Streamer.id)).where(Streamer.guild_id == guild.id)
        )
        active_notifications = await db.scalar(
            select(func.count(StreamState.id)).where(
                StreamState.guild_id == guild.id,
                StreamState.is_live.is_(True),
            )
        )
        recent_logs = await db.execute(
            select(NotificationLog)
            .where(NotificationLog.guild_id == guild.id)
            .order_by(desc(NotificationLog.timestamp))
            .limit(8)
        )
    return templates.TemplateResponse(
        "guilds/overview.html",
        base_context(
            request,
            guild=guild,
            total_streamers=total_streamers or 0,
            active_notifications=active_notifications or 0,
            recent_logs=list(recent_logs.scalars().all()),
            active_page="overview",
        ),
    )


@router.get("/dashboard/{guild_id}/streamers")
async def streamers_page(request: Request, guild_id: str):
    user = require_user(request)
    if isinstance(user, RedirectResponse):
        return user
    async with AsyncSessionLocal() as db:
        guild = await load_guild(request, db, guild_id)
        result = await db.execute(
            select(Streamer)
            .where(Streamer.guild_id == guild.id)
            .order_by(Streamer.platform, Streamer.streamer_name)
        )
        streamers = list(result.scalars().all())
    return templates.TemplateResponse(
        "guilds/streamers.html",
        base_context(request, guild=guild, streamers=streamers, active_page="streamers"),
    )


@router.post("/dashboard/{guild_id}/streamers")
async def add_streamer(request: Request, guild_id: str):
    user = require_user(request)
    if isinstance(user, RedirectResponse):
        return user
    form = await request.form()
    async with AsyncSessionLocal() as db:
        guild = await load_guild(request, db, guild_id)
        try:
            payload = StreamerCreate(
                platform=str(form.get("platform")),
                streamer_name=str(form.get("streamer_name")),
                enabled=form.get("enabled") == "on",
            )
            db.add(
                Streamer(
                    guild_id=guild.id,
                    platform=payload.platform,
                    streamer_name=normalize_streamer_name(payload.platform, payload.streamer_name),
                    enabled=payload.enabled,
                )
            )
            await db.commit()
            flash(request, "Streamer saved.", "success")
        except (ValidationError, IntegrityError, ValueError) as exc:
            await db.rollback()
            flash(request, f"Could not save streamer: {exc}", "danger")
    return RedirectResponse(
        f"/dashboard/{guild_id}/streamers", status_code=status.HTTP_303_SEE_OTHER
    )


@router.post("/dashboard/{guild_id}/streamers/{streamer_id}/edit")
async def edit_streamer(request: Request, guild_id: str, streamer_id: int):
    user = require_user(request)
    if isinstance(user, RedirectResponse):
        return user
    form = await request.form()
    async with AsyncSessionLocal() as db:
        guild = await load_guild(request, db, guild_id)
        streamer = await db.get(Streamer, streamer_id)
        if streamer is None or streamer.guild_id != guild.id:
            raise HTTPException(status_code=404, detail="Streamer not found")
        platform = str(form.get("platform"))
        streamer.platform = platform
        streamer.streamer_name = normalize_streamer_name(platform, str(form.get("streamer_name")))
        streamer.enabled = form.get("enabled") == "on"
        try:
            await db.commit()
            flash(request, "Streamer updated.", "success")
        except IntegrityError as exc:
            await db.rollback()
            flash(request, f"Could not update streamer: {exc}", "danger")
    return RedirectResponse(
        f"/dashboard/{guild_id}/streamers", status_code=status.HTTP_303_SEE_OTHER
    )


@router.post("/dashboard/{guild_id}/streamers/{streamer_id}/delete")
async def delete_streamer(request: Request, guild_id: str, streamer_id: int):
    user = require_user(request)
    if isinstance(user, RedirectResponse):
        return user
    async with AsyncSessionLocal() as db:
        guild = await load_guild(request, db, guild_id)
        streamer = await db.get(Streamer, streamer_id)
        if streamer and streamer.guild_id == guild.id:
            await db.delete(streamer)
            await db.commit()
            flash(request, "Streamer deleted.", "success")
    return RedirectResponse(
        f"/dashboard/{guild_id}/streamers", status_code=status.HTTP_303_SEE_OTHER
    )


@router.get("/dashboard/{guild_id}/settings")
async def notification_settings_page(request: Request, guild_id: str):
    user = require_user(request)
    if isinstance(user, RedirectResponse):
        return user
    async with AsyncSessionLocal() as db:
        guild = await load_guild(request, db, guild_id)
        settings = await get_or_create_notification_settings(db, guild.id)
        await db.commit()
        channels, roles = await discord_choices(request, guild.guild_id)
    return templates.TemplateResponse(
        "guilds/settings.html",
        base_context(
            request,
            guild=guild,
            settings=settings,
            channels=channels,
            roles=roles,
            active_page="settings",
        ),
    )


@router.post("/dashboard/{guild_id}/settings")
async def save_notification_settings(request: Request, guild_id: str):
    user = require_user(request)
    if isinstance(user, RedirectResponse):
        return user
    form = await request.form()
    async with AsyncSessionLocal() as db:
        guild = await load_guild(request, db, guild_id)
        settings = await get_or_create_notification_settings(db, guild.id)
        mention_mode = str(form.get("mention_mode") or "none")
        settings.channel_id = str(form.get("channel_id") or "") or None
        settings.role_id = str(form.get("role_id") or "") if mention_mode == "role" else None
        settings.mention_everyone = mention_mode == "everyone"
        settings.mention_here = mention_mode == "here"
        await db.commit()
        flash(request, "Notification settings saved.", "success")
    return RedirectResponse(f"/dashboard/{guild_id}/settings", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/dashboard/{guild_id}/embed")
async def embed_page(request: Request, guild_id: str):
    user = require_user(request)
    if isinstance(user, RedirectResponse):
        return user
    async with AsyncSessionLocal() as db:
        guild = await load_guild(request, db, guild_id)
        template = await get_or_create_embed_template(db, guild.id)
        await db.commit()
    return templates.TemplateResponse(
        "guilds/embed.html",
        base_context(request, guild=guild, template=template, active_page="embed"),
    )


@router.post("/dashboard/{guild_id}/embed")
async def save_embed(request: Request, guild_id: str):
    user = require_user(request)
    if isinstance(user, RedirectResponse):
        return user
    form = await request.form()
    async with AsyncSessionLocal() as db:
        guild = await load_guild(request, db, guild_id)
        try:
            payload = EmbedTemplateUpdate(
                title=str(form.get("title") or ""),
                description=str(form.get("description") or ""),
                color=str(form.get("color") or "#e53935"),
                footer_text=str(form.get("footer_text") or "") or None,
                author_text=str(form.get("author_text") or "") or None,
                show_thumbnail=form.get("show_thumbnail") == "on",
                show_preview=form.get("show_preview") == "on",
            )
            template = await get_or_create_embed_template(db, guild.id)
            template.title = payload.title
            template.description = payload.description
            template.color = payload.color
            template.footer_text = payload.footer_text
            template.author_text = payload.author_text
            template.show_thumbnail = payload.show_thumbnail
            template.show_preview = payload.show_preview
            await db.commit()
            flash(request, "Embed template saved.", "success")
        except (ValidationError, ValueError) as exc:
            await db.rollback()
            flash(request, f"Could not save embed template: {exc}", "danger")
    return RedirectResponse(f"/dashboard/{guild_id}/embed", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/dashboard/{guild_id}/logs")
async def logs_page(request: Request, guild_id: str, event_type: str | None = None):
    user = require_user(request)
    if isinstance(user, RedirectResponse):
        return user
    async with AsyncSessionLocal() as db:
        guild = await load_guild(request, db, guild_id)
        query = select(NotificationLog).where(NotificationLog.guild_id == guild.id)
        if event_type:
            query = query.where(NotificationLog.event_type == event_type)
        result = await db.execute(query.order_by(desc(NotificationLog.timestamp)).limit(100))
        logs = list(result.scalars().all())
    return templates.TemplateResponse(
        "guilds/logs.html",
        base_context(
            request,
            guild=guild,
            logs=logs,
            event_type=event_type,
            active_page="logs",
        ),
    )
