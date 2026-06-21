from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_guild_access
from app.database.session import get_db
from app.models import Guild, NotificationSettings
from app.schemas.notification_settings import NotificationSettingsOut, NotificationSettingsUpdate
from app.services.guild_defaults import get_or_create_notification_settings

router = APIRouter(tags=["notification-settings"])


@router.get(
    "/api/guilds/{guild_id}/notification-settings",
    response_model=NotificationSettingsOut,
)
async def get_settings(
    guild: Guild = Depends(require_guild_access),
    db: AsyncSession = Depends(get_db),
) -> NotificationSettings:
    settings = await get_or_create_notification_settings(db, guild.id)
    await db.commit()
    await db.refresh(settings)
    return settings


@router.put(
    "/api/guilds/{guild_id}/notification-settings",
    response_model=NotificationSettingsOut,
)
async def update_settings(
    payload: NotificationSettingsUpdate,
    guild: Guild = Depends(require_guild_access),
    db: AsyncSession = Depends(get_db),
) -> NotificationSettings:
    settings = await get_or_create_notification_settings(db, guild.id)
    settings.channel_id = payload.channel_id or None
    settings.role_id = payload.role_id or None
    settings.mention_everyone = payload.mention_everyone
    settings.mention_here = False if payload.mention_everyone else payload.mention_here
    settings.delete_notification_on_end = payload.delete_notification_on_end
    await db.commit()
    await db.refresh(settings)
    return settings
