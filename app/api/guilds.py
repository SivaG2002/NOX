from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, manageable_guild_ids, require_guild_access
from app.bot.client import StreamNotificationBot
from app.database.session import get_db
from app.models import Guild
from app.schemas.guild import DiscordChannelOut, DiscordRoleOut, GuildOut
from app.services.guild_defaults import ensure_guild_defaults

router = APIRouter(prefix="/api/guilds", tags=["guilds"])


@router.get("", response_model=list[GuildOut])
async def list_guilds(
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
) -> list[Guild]:
    result = await db.execute(
        select(Guild).where(Guild.guild_id.in_(manageable_guild_ids(request))).order_by(Guild.name)
    )
    return list(result.scalars().all())


@router.get("/{guild_id}", response_model=GuildOut)
async def get_guild(guild: Guild = Depends(require_guild_access)) -> Guild:
    return guild


@router.get("/{guild_id}/channels", response_model=list[DiscordChannelOut])
async def list_channels(
    request: Request,
    guild: Guild = Depends(require_guild_access),
) -> list[dict[str, str]]:
    bot: StreamNotificationBot | None = getattr(request.app.state, "discord_bot", None)
    if not bot or not bot.is_ready():
        return []
    return await bot.list_text_channels(guild.guild_id)


@router.get("/{guild_id}/roles", response_model=list[DiscordRoleOut])
async def list_roles(
    request: Request,
    guild: Guild = Depends(require_guild_access),
) -> list[dict[str, str]]:
    bot: StreamNotificationBot | None = getattr(request.app.state, "discord_bot", None)
    if not bot or not bot.is_ready():
        return []
    return await bot.list_roles(guild.guild_id)


@router.post("/{guild_id}/defaults", response_model=GuildOut)
async def create_defaults(
    db: AsyncSession = Depends(get_db),
    guild: Guild = Depends(require_guild_access),
) -> Guild:
    await ensure_guild_defaults(db, guild)
    await db.commit()
    await db.refresh(guild)
    return guild

