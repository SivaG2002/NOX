from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import EmbedTemplate, Guild, NotificationSettings, VoiceChannelSettings


async def sync_manageable_guilds(db: AsyncSession, guilds: list[dict]) -> list[Guild]:
    synced: list[Guild] = []
    for guild_data in guilds:
        guild = await get_guild_by_discord_id(db, guild_data["id"])
        if guild:
            guild.name = guild_data["name"]
        else:
            guild = Guild(guild_id=guild_data["id"], name=guild_data["name"])
            db.add(guild)
        synced.append(guild)
    await db.flush()
    for guild in synced:
        await ensure_guild_defaults(db, guild)
    await db.commit()
    return synced


async def get_guild_by_discord_id(db: AsyncSession, guild_id: str) -> Guild | None:
    result = await db.execute(select(Guild).where(Guild.guild_id == str(guild_id)))
    return result.scalar_one_or_none()


async def ensure_guild_defaults(db: AsyncSession, guild: Guild) -> None:
    settings = await get_notification_settings(db, guild.id)
    template = await get_embed_template(db, guild.id)
    voice_settings = await get_voice_channel_settings(db, guild.id)
    if settings is None:
        db.add(NotificationSettings(guild_id=guild.id))
    if template is None:
        db.add(EmbedTemplate(guild_id=guild.id))
    if voice_settings is None:
        db.add(VoiceChannelSettings(guild_id=guild.id))
    await db.flush()


async def get_notification_settings(
    db: AsyncSession, guild_pk: int
) -> NotificationSettings | None:
    result = await db.execute(
        select(NotificationSettings).where(NotificationSettings.guild_id == guild_pk)
    )
    return result.scalar_one_or_none()


async def get_or_create_notification_settings(
    db: AsyncSession, guild_pk: int
) -> NotificationSettings:
    settings = await get_notification_settings(db, guild_pk)
    if settings is None:
        settings = NotificationSettings(guild_id=guild_pk)
        db.add(settings)
        await db.flush()
    return settings


async def get_embed_template(db: AsyncSession, guild_pk: int) -> EmbedTemplate | None:
    result = await db.execute(select(EmbedTemplate).where(EmbedTemplate.guild_id == guild_pk))
    return result.scalar_one_or_none()


async def get_or_create_embed_template(db: AsyncSession, guild_pk: int) -> EmbedTemplate:
    template = await get_embed_template(db, guild_pk)
    if template is None:
        template = EmbedTemplate(guild_id=guild_pk)
        db.add(template)
        await db.flush()
    return template


async def get_voice_channel_settings(
    db: AsyncSession, guild_pk: int
) -> VoiceChannelSettings | None:
    result = await db.execute(
        select(VoiceChannelSettings).where(VoiceChannelSettings.guild_id == guild_pk)
    )
    return result.scalar_one_or_none()


async def get_or_create_voice_channel_settings(
    db: AsyncSession, guild_pk: int
) -> VoiceChannelSettings:
    settings = await get_voice_channel_settings(db, guild_pk)
    if settings is None:
        settings = VoiceChannelSettings(guild_id=guild_pk)
        db.add(settings)
        await db.flush()
    return settings
