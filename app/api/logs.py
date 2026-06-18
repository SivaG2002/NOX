from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_guild_access
from app.database.session import get_db
from app.models import Guild, NotificationLog
from app.schemas.notification_log import NotificationLogOut

router = APIRouter(tags=["logs"])


@router.get("/api/guilds/{guild_id}/logs", response_model=list[NotificationLogOut])
async def list_logs(
    guild: Guild = Depends(require_guild_access),
    db: AsyncSession = Depends(get_db),
    event_type: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
) -> list[NotificationLog]:
    query = select(NotificationLog).where(NotificationLog.guild_id == guild.id)
    if event_type:
        query = query.where(NotificationLog.event_type == event_type)
    query = query.order_by(desc(NotificationLog.timestamp)).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())

