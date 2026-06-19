from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_guild_access
from app.database.session import get_db
from app.models import Guild, TemporaryVoiceChannel, VoiceChannelSettings
from app.schemas.voice_channel import (
    TemporaryVoiceChannelOut,
    VoiceChannelMetricsOut,
    VoiceChannelSettingsOut,
    VoiceChannelSettingsUpdate,
)
from app.services.guild_defaults import get_or_create_voice_channel_settings
from app.services.temporary_voice_channels import (
    clamp_user_limit,
    get_voice_channel_metrics,
    list_active_temporary_channels,
)

router = APIRouter(tags=["voice-channels"])


@router.get(
    "/api/guilds/{guild_id}/voice-settings",
    response_model=VoiceChannelSettingsOut,
)
async def get_voice_settings(
    guild: Guild = Depends(require_guild_access),
    db: AsyncSession = Depends(get_db),
) -> VoiceChannelSettings:
    settings = await get_or_create_voice_channel_settings(db, guild.id)
    await db.commit()
    await db.refresh(settings)
    return settings


@router.put(
    "/api/guilds/{guild_id}/voice-settings",
    response_model=VoiceChannelSettingsOut,
)
async def update_voice_settings(
    payload: VoiceChannelSettingsUpdate,
    guild: Guild = Depends(require_guild_access),
    db: AsyncSession = Depends(get_db),
) -> VoiceChannelSettings:
    settings = await get_or_create_voice_channel_settings(db, guild.id)
    channel_ids = [str(channel_id) for channel_id in payload.create_channel_ids if channel_id]
    if payload.create_channel_id and str(payload.create_channel_id) not in channel_ids:
        channel_ids.insert(0, str(payload.create_channel_id))
    settings.enabled = payload.enabled
    settings.create_channel_id = channel_ids[0] if channel_ids else None
    settings.create_channel_ids = channel_ids
    settings.category_id = payload.category_id or None
    settings.default_user_limit = clamp_user_limit(payload.default_user_limit)
    settings.naming_template = payload.naming_template.strip()[:100] or "{owner}'s Channel"
    settings.auto_delete = payload.auto_delete
    await db.commit()
    await db.refresh(settings)
    return settings


@router.get(
    "/api/guilds/{guild_id}/temporary-voice-channels",
    response_model=list[TemporaryVoiceChannelOut],
)
async def list_temporary_voice_channels(
    guild: Guild = Depends(require_guild_access),
    db: AsyncSession = Depends(get_db),
) -> list[TemporaryVoiceChannel]:
    return await list_active_temporary_channels(db, guild.id)


@router.get(
    "/api/guilds/{guild_id}/voice-metrics",
    response_model=VoiceChannelMetricsOut,
)
async def voice_metrics(
    guild: Guild = Depends(require_guild_access),
    db: AsyncSession = Depends(get_db),
) -> dict:
    return await get_voice_channel_metrics(db, guild.id)
