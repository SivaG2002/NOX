from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_guild_access, require_streamer_access
from app.database.session import get_db
from app.models import Guild, Streamer
from app.schemas.streamer import StreamerCreate, StreamerOut, StreamerUpdate, normalize_streamer_name

router = APIRouter(tags=["streamers"])


@router.get("/api/guilds/{guild_id}/streamers", response_model=list[StreamerOut])
async def list_streamers(
    guild: Guild = Depends(require_guild_access),
    db: AsyncSession = Depends(get_db),
) -> list[Streamer]:
    result = await db.execute(
        select(Streamer).where(Streamer.guild_id == guild.id).order_by(Streamer.platform, Streamer.streamer_name)
    )
    return list(result.scalars().all())


@router.post(
    "/api/guilds/{guild_id}/streamers",
    response_model=StreamerOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_streamer(
    payload: StreamerCreate,
    guild: Guild = Depends(require_guild_access),
    db: AsyncSession = Depends(get_db),
) -> Streamer:
    streamer = Streamer(
        guild_id=guild.id,
        platform=payload.platform,
        streamer_name=normalize_streamer_name(payload.platform, payload.streamer_name),
        enabled=payload.enabled,
    )
    db.add(streamer)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Streamer already exists for this guild") from exc
    await db.refresh(streamer)
    return streamer


@router.put("/api/streamers/{streamer_id}", response_model=StreamerOut)
async def update_streamer(
    payload: StreamerUpdate,
    streamer: Streamer = Depends(require_streamer_access),
    db: AsyncSession = Depends(get_db),
) -> Streamer:
    platform = payload.platform or streamer.platform
    if payload.platform is not None:
        streamer.platform = payload.platform
    if payload.streamer_name is not None:
        streamer.streamer_name = normalize_streamer_name(platform, payload.streamer_name)
    if payload.enabled is not None:
        streamer.enabled = payload.enabled
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Streamer already exists for this guild") from exc
    await db.refresh(streamer)
    return streamer


@router.delete("/api/streamers/{streamer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_streamer(
    streamer: Streamer = Depends(require_streamer_access),
    db: AsyncSession = Depends(get_db),
) -> None:
    await db.delete(streamer)
    await db.commit()

