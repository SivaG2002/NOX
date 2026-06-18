from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.models import Guild, Streamer
from app.services.guild_defaults import get_guild_by_discord_id


def get_current_user(request: Request) -> dict:
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return user


def manageable_guild_ids(request: Request) -> set[str]:
    return {str(guild["id"]) for guild in request.session.get("guilds", [])}


async def require_guild_access(
    guild_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
) -> Guild:
    if str(guild_id) not in manageable_guild_ids(request):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Missing Manage Server")
    guild = await get_guild_by_discord_id(db, str(guild_id))
    if not guild:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Guild not found")
    return guild


async def require_streamer_access(
    streamer_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
) -> Streamer:
    result = await db.execute(
        select(Streamer)
        .join(Guild)
        .where(Streamer.id == streamer_id, Guild.guild_id.in_(manageable_guild_ids(request)))
    )
    streamer = result.scalar_one_or_none()
    if streamer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Streamer not found")
    return streamer

