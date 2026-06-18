import secrets

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.security import get_or_create_csrf_token
from app.database.session import get_db
from app.services.discord_oauth import DiscordOAuthClient
from app.services.guild_defaults import sync_manageable_guilds

router = APIRouter(tags=["auth"])
settings = get_settings()


@router.get("/auth/login")
async def login(request: Request) -> RedirectResponse:
    if not settings.discord_client_id or not settings.discord_client_secret.get_secret_value():
        raise HTTPException(status_code=500, detail="Discord OAuth is not configured")
    state = secrets.token_urlsafe(32)
    request.session["oauth_state"] = state
    return RedirectResponse(DiscordOAuthClient(settings).authorization_url(state))


@router.get("/auth/callback")
async def callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    if not code or not state or state != request.session.get("oauth_state"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid OAuth state")

    client = DiscordOAuthClient(settings)
    try:
        token = await client.exchange_code(code)
        user = await client.fetch_user(token["access_token"])
        guilds = await client.fetch_manageable_guilds(token["access_token"])
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="Discord OAuth request failed") from exc

    await sync_manageable_guilds(db, guilds)
    request.session.clear()
    request.session["user"] = {
        "id": user["id"],
        "username": user.get("global_name") or user.get("username") or "Discord User",
        "avatar": user.get("avatar"),
    }
    request.session["guilds"] = guilds
    get_or_create_csrf_token(request)
    return RedirectResponse("/dashboard", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/auth/logout")
async def logout(request: Request) -> RedirectResponse:
    request.session.clear()
    return RedirectResponse("/auth/login", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/api/auth/me")
async def me(request: Request, user: dict = Depends(get_current_user)) -> dict:
    return {
        "user": user,
        "guilds": request.session.get("guilds", []),
        "csrf_token": get_or_create_csrf_token(request),
    }

