from __future__ import annotations

import contextlib
import logging
from collections import Counter
from datetime import UTC, datetime, time
from typing import Any

import discord
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import AsyncSessionLocal
from app.models import (
    NotificationLog,
    TemporaryVoiceChannel,
    VoiceChannelSettings,
    VoiceChannelTrigger,
)
from app.services.guild_defaults import (
    get_guild_by_discord_id,
    get_or_create_voice_channel_settings,
)

logger = logging.getLogger(__name__)

VOICE_PLATFORM = "discord"
VOICE_EVENT_CREATED = "voice_channel_created"
VOICE_EVENT_DELETED = "voice_channel_deleted"
VOICE_EVENT_OWNER_CHANGED = "voice_owner_changed"
VOICE_EVENT_LOCKED = "voice_channel_locked"
VOICE_EVENT_UNLOCKED = "voice_channel_unlocked"
VOICE_EVENT_LIMIT_CHANGED = "voice_limit_changed"
VOICE_EVENT_RENAMED = "voice_channel_renamed"
VOICE_EVENT_PRIVACY_CHANGED = "voice_privacy_changed"
VOICE_EVENT_USER_ALLOWED = "voice_user_allowed"
VOICE_EVENT_USER_DENIED = "voice_user_denied"
VOICE_EVENT_MEMBER_KICKED = "voice_member_kicked"

VOICE_SIZE_PRESETS = {
    "solo": ("Solo", 1),
    "duo": ("Duo", 2),
    "trio": ("Trio", 3),
    "squad": ("Squad", 4),
    "party": ("Party", 5),
    "team": ("Team", 10),
    "custom": ("Custom", 4),
}

DEFAULT_NAMING_TEMPLATE = "{owner}'s Channel"


class VoiceChannelError(ValueError):
    pass


def clamp_user_limit(value: int | str | None) -> int:
    try:
        limit = int(value or 0)
    except (TypeError, ValueError):
        return 0
    return max(0, min(99, limit))


def clean_channel_name(name: str) -> str:
    cleaned = " ".join(name.replace("@everyone", "everyone").replace("@here", "here").split())
    return (cleaned or "Temporary Channel")[:100]


def render_channel_name(template: str, member: discord.Member) -> str:
    owner = member.display_name or member.name
    try:
        rendered = (template or DEFAULT_NAMING_TEMPLATE).format(
            owner=owner,
            username=member.name,
            display_name=member.display_name,
            guild=member.guild.name,
        )
    except (IndexError, KeyError, ValueError):
        rendered = DEFAULT_NAMING_TEMPLATE.format(owner=owner)
    return clean_channel_name(rendered)


def configured_create_channel_ids(settings: VoiceChannelSettings) -> set[str]:
    channel_ids: set[str] = set()
    if settings.create_channel_id:
        channel_ids.add(str(settings.create_channel_id))
    extra_channel_ids = settings.create_channel_ids or []
    if isinstance(extra_channel_ids, str):
        extra_channel_ids = [extra_channel_ids]
    for channel_id in extra_channel_ids:
        if channel_id:
            channel_ids.add(str(channel_id))
    return channel_ids


async def get_temporary_channel(
    db: AsyncSession, guild_pk: int, channel_id: str | int
) -> TemporaryVoiceChannel | None:
    result = await db.execute(
        select(TemporaryVoiceChannel).where(
            TemporaryVoiceChannel.guild_id == guild_pk,
            TemporaryVoiceChannel.channel_id == str(channel_id),
        )
    )
    return result.scalar_one_or_none()


async def list_active_temporary_channels(
    db: AsyncSession, guild_pk: int
) -> list[TemporaryVoiceChannel]:
    result = await db.execute(
        select(TemporaryVoiceChannel)
        .where(TemporaryVoiceChannel.guild_id == guild_pk)
        .order_by(desc(TemporaryVoiceChannel.created_at))
    )
    return list(result.scalars().all())


async def get_voice_channel_metrics(db: AsyncSession, guild_pk: int) -> dict[str, Any]:
    today_start = datetime.combine(datetime.now(UTC).date(), time.min, tzinfo=UTC)
    active_channels = len(await list_active_temporary_channels(db, guild_pk))
    result = await db.execute(
        select(NotificationLog).where(
            NotificationLog.guild_id == guild_pk,
            NotificationLog.platform == VOICE_PLATFORM,
            NotificationLog.event_type.in_([VOICE_EVENT_CREATED, VOICE_EVENT_DELETED]),
            NotificationLog.timestamp >= today_start,
        )
    )
    logs = list(result.scalars().all())
    created_logs = [log for log in logs if log.event_type == VOICE_EVENT_CREATED]
    owners: Counter[tuple[str, str]] = Counter()
    for log in created_logs:
        metadata = log.log_metadata or {}
        owner_id = str(metadata.get("owner_id") or "")
        owner_name = str(metadata.get("owner_name") or "Unknown")
        if owner_id:
            owners[(owner_id, owner_name)] += 1

    return {
        "active_channels": active_channels,
        "channels_created_today": len(created_logs),
        "channels_deleted_today": sum(1 for log in logs if log.event_type == VOICE_EVENT_DELETED),
        "most_active_owners": [
            {"owner_id": owner_id, "owner_name": owner_name, "channels_created": count}
            for (owner_id, owner_name), count in owners.most_common(5)
        ],
    }


async def log_voice_event(
    db: AsyncSession,
    *,
    guild_pk: int,
    event_type: str,
    message: str,
    metadata: dict[str, Any] | None = None,
) -> None:
    db.add(
        NotificationLog(
            guild_id=guild_pk,
            streamer_id=None,
            platform=VOICE_PLATFORM,
            event_type=event_type,
            message=message,
            log_metadata=metadata or {},
        )
    )


# VoiceChannelTrigger CRUD Operations


async def get_voice_channel_trigger(
    db: AsyncSession, guild_pk: int, trigger_id: int
) -> VoiceChannelTrigger | None:
    """Get a specific voice channel trigger by ID."""
    result = await db.execute(
        select(VoiceChannelTrigger).where(
            VoiceChannelTrigger.guild_id == guild_pk,
            VoiceChannelTrigger.id == trigger_id,
        )
    )
    return result.scalar_one_or_none()


async def get_voice_channel_trigger_by_channel(
    db: AsyncSession, guild_pk: int, channel_id: str
) -> VoiceChannelTrigger | None:
    """Get a voice channel trigger by trigger channel ID."""
    result = await db.execute(
        select(VoiceChannelTrigger).where(
            VoiceChannelTrigger.guild_id == guild_pk,
            VoiceChannelTrigger.trigger_channel_id == str(channel_id),
            VoiceChannelTrigger.enabled.is_(True),
        )
    )
    return result.scalar_one_or_none()


async def list_voice_channel_triggers(
    db: AsyncSession, guild_pk: int, enabled_only: bool = False
) -> list[VoiceChannelTrigger]:
    """List all voice channel triggers for a guild."""
    query = select(VoiceChannelTrigger).where(VoiceChannelTrigger.guild_id == guild_pk)
    if enabled_only:
        query = query.where(VoiceChannelTrigger.enabled.is_(True))
    query = query.order_by(VoiceChannelTrigger.trigger_channel_name)
    result = await db.execute(query)
    return list(result.scalars().all())


async def create_voice_channel_trigger(
    db: AsyncSession,
    *,
    guild_pk: int,
    trigger_channel_id: str,
    trigger_channel_name: str,
    category_id: str | None = None,
    user_limit: int = 4,
    size_preset: str = "custom",
    naming_template: str = DEFAULT_NAMING_TEMPLATE,
    enabled: bool = True,
) -> VoiceChannelTrigger:
    """Create a new voice channel trigger."""
    trigger = VoiceChannelTrigger(
        guild_id=guild_pk,
        trigger_channel_id=str(trigger_channel_id),
        trigger_channel_name=trigger_channel_name,
        category_id=category_id,
        user_limit=clamp_user_limit(user_limit),
        size_preset=size_preset,
        naming_template=naming_template or DEFAULT_NAMING_TEMPLATE,
        enabled=enabled,
    )
    db.add(trigger)
    return trigger


async def update_voice_channel_trigger(
    db: AsyncSession,
    guild_pk: int,
    trigger_id: int,
    *,
    trigger_channel_name: str | None = None,
    category_id: str | None = None,
    user_limit: int | None = None,
    size_preset: str | None = None,
    naming_template: str | None = None,
    enabled: bool | None = None,
) -> VoiceChannelTrigger | None:
    """Update an existing voice channel trigger."""
    trigger = await get_voice_channel_trigger(db, guild_pk, trigger_id)
    if not trigger:
        return None
    
    if trigger_channel_name is not None:
        trigger.trigger_channel_name = trigger_channel_name
    if category_id is not None:
        trigger.category_id = category_id
    if user_limit is not None:
        trigger.user_limit = clamp_user_limit(user_limit)
    if size_preset is not None:
        trigger.size_preset = size_preset
    if naming_template is not None:
        trigger.naming_template = naming_template or DEFAULT_NAMING_TEMPLATE
    if enabled is not None:
        trigger.enabled = enabled
    
    return trigger


async def delete_voice_channel_trigger(
    db: AsyncSession, guild_pk: int, trigger_id: int
) -> bool:
    """Delete a voice channel trigger."""
    trigger = await get_voice_channel_trigger(db, guild_pk, trigger_id)
    if not trigger:
        return False
    
    await db.delete(trigger)
    return True


class TemporaryVoiceChannelService:
    def __init__(self) -> None:
        self._deleting_channel_ids: set[str] = set()

    async def handle_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ) -> None:
        if before.channel and before.channel == after.channel:
            return

        async with AsyncSessionLocal() as db:
            try:
                if after.channel and not member.bot:
                    await self.create_channel_for_join(db, member, after.channel)
                if before.channel:
                    await self.delete_channel_if_empty(db, before.channel)
                await db.commit()
            except Exception:
                await db.rollback()
                logger.exception(
                    "temporary_voice_channel_event_failed",
                    extra={"guild_id": str(member.guild.id), "member_id": str(member.id)},
                )

    async def handle_channel_delete(self, channel: discord.abc.GuildChannel) -> None:
        if not isinstance(channel, discord.VoiceChannel):
            return
        if str(channel.id) in self._deleting_channel_ids:
            return
        async with AsyncSessionLocal() as db:
            guild = await get_guild_by_discord_id(db, str(channel.guild.id))
            if guild is None:
                return
            record = await get_temporary_channel(db, guild.id, channel.id)
            if record is None:
                return
            await db.delete(record)
            await log_voice_event(
                db,
                guild_pk=guild.id,
                event_type=VOICE_EVENT_DELETED,
                message=f"Temporary voice channel {channel.name} was removed.",
                metadata={"channel_id": str(channel.id), "reason": "external_delete"},
            )
            await db.commit()

    async def create_channel_for_join(
        self,
        db: AsyncSession,
        member: discord.Member,
        source_channel: discord.abc.GuildChannel | discord.Thread,
    ) -> TemporaryVoiceChannel | None:
        if not isinstance(source_channel, discord.VoiceChannel):
            return None
        guild_record = await get_guild_by_discord_id(db, str(member.guild.id))
        if guild_record is None:
            return None
        
        # Check for a matching voice channel trigger
        trigger = await get_voice_channel_trigger_by_channel(db, guild_record.id, source_channel.id)
        if not trigger:
            return None

        user_limit = trigger.user_limit
        channel_name = render_channel_name(trigger.naming_template, member)
        category = (
            self._resolve_category(member.guild, trigger.category_id) or source_channel.category
        )
        overwrites = self._creation_overwrites(member)
        channel = await member.guild.create_voice_channel(
            name=channel_name,
            category=category,
            user_limit=user_limit,
            overwrites=overwrites,
            reason=f"Temporary voice channel for {member} ({member.id})",
        )
        try:
            await member.move_to(channel, reason="Moved to temporary voice channel")
        except discord.DiscordException:
            with contextlib.suppress(discord.DiscordException):
                await channel.delete(reason="Temporary voice channel move failed")
            raise

        record = TemporaryVoiceChannel(
            guild_id=guild_record.id,
            channel_id=str(channel.id),
            owner_id=str(member.id),
            owner_name=member.display_name or member.name,
            user_limit=user_limit,
            is_locked=False,
            is_private=True,
        )
        db.add(record)
        await log_voice_event(
            db,
            guild_pk=guild_record.id,
            event_type=VOICE_EVENT_CREATED,
            message=f"Created temporary voice channel {channel.name} for {record.owner_name}.",
            metadata={
                "channel_id": str(channel.id),
                "channel_name": channel.name,
                "owner_id": record.owner_id,
                "owner_name": record.owner_name,
                "user_limit": user_limit,
                "source_channel_id": str(source_channel.id),
                "trigger_id": trigger.id,
            },
        )
        logger.info(
            "temporary_voice_channel_created",
            extra={
                "guild_id": str(member.guild.id),
                "channel_id": str(channel.id),
                "owner_id": str(member.id),
            },
        )
        return record

    async def delete_channel_if_empty(
        self, db: AsyncSession, channel: discord.abc.GuildChannel | discord.Thread
    ) -> bool:
        if not isinstance(channel, discord.VoiceChannel):
            return False
        guild_record = await get_guild_by_discord_id(db, str(channel.guild.id))
        if guild_record is None:
            return False
        record = await get_temporary_channel(db, guild_record.id, channel.id)
        if record is None:
            return False
        settings = await get_or_create_voice_channel_settings(db, guild_record.id)
        if not settings.auto_delete or channel.members:
            return False

        self._deleting_channel_ids.add(str(channel.id))
        try:
            await channel.delete(reason="Temporary voice channel is empty")
        finally:
            self._deleting_channel_ids.discard(str(channel.id))
        await db.delete(record)
        await log_voice_event(
            db,
            guild_pk=guild_record.id,
            event_type=VOICE_EVENT_DELETED,
            message=f"Deleted empty temporary voice channel {channel.name}.",
            metadata={
                "channel_id": str(channel.id),
                "channel_name": channel.name,
                "owner_id": record.owner_id,
                "owner_name": record.owner_name,
                "reason": "empty",
            },
        )
        logger.info(
            "temporary_voice_channel_deleted",
            extra={"guild_id": str(channel.guild.id), "channel_id": str(channel.id)},
        )
        return True

    async def rename_channel(
        self, db: AsyncSession, member: discord.Member, name: str
    ) -> TemporaryVoiceChannel:
        record, channel = await self.require_owner(db, member)
        channel_name = clean_channel_name(name)
        await channel.edit(name=channel_name, reason=f"Temporary voice channel renamed by {member}")
        await log_voice_event(
            db,
            guild_pk=record.guild_id,
            event_type=VOICE_EVENT_RENAMED,
            message=f"{member.display_name} renamed a temporary voice channel to {channel_name}.",
            metadata={
                "channel_id": record.channel_id,
                "owner_id": record.owner_id,
                "name": channel_name,
            },
        )
        return record

    async def set_user_limit(
        self, db: AsyncSession, member: discord.Member, limit: int
    ) -> TemporaryVoiceChannel:
        record, channel = await self.require_owner(db, member)
        user_limit = clamp_user_limit(limit)
        await channel.edit(
            user_limit=user_limit, reason=f"Temporary voice channel limit changed by {member}"
        )
        record.user_limit = user_limit
        await log_voice_event(
            db,
            guild_pk=record.guild_id,
            event_type=VOICE_EVENT_LIMIT_CHANGED,
            message=(
                f"{member.display_name} changed a temporary voice channel limit to "
                f"{user_limit}."
            ),
            metadata={
                "channel_id": record.channel_id,
                "owner_id": record.owner_id,
                "user_limit": user_limit,
            },
        )
        return record

    async def set_locked(
        self, db: AsyncSession, member: discord.Member, locked: bool
    ) -> TemporaryVoiceChannel:
        record, channel = await self.require_owner(db, member)
        await self._apply_default_overwrite(
            channel,
            private=record.is_private,
            locked=locked,
            reason=f"Temporary voice channel {'locked' if locked else 'unlocked'} by {member}",
        )
        record.is_locked = locked
        await log_voice_event(
            db,
            guild_pk=record.guild_id,
            event_type=VOICE_EVENT_LOCKED if locked else VOICE_EVENT_UNLOCKED,
            message=(
                f"{member.display_name} {'locked' if locked else 'unlocked'} "
                "a temporary voice channel."
            ),
            metadata={"channel_id": record.channel_id, "owner_id": record.owner_id},
        )
        return record

    async def set_private(
        self, db: AsyncSession, member: discord.Member, private: bool
    ) -> TemporaryVoiceChannel:
        record, channel = await self.require_owner(db, member)
        await self._apply_default_overwrite(
            channel,
            private=private,
            locked=record.is_locked,
            reason=f"Temporary voice channel made {'private' if private else 'public'} by {member}",
        )
        record.is_private = private
        await log_voice_event(
            db,
            guild_pk=record.guild_id,
            event_type=VOICE_EVENT_PRIVACY_CHANGED,
            message=(
                f"{member.display_name} made a temporary voice channel "
                f"{'private' if private else 'public'}."
            ),
            metadata={
                "channel_id": record.channel_id,
                "owner_id": record.owner_id,
                "is_private": private,
            },
        )
        return record

    async def transfer_owner(
        self, db: AsyncSession, member: discord.Member, target: discord.Member
    ) -> TemporaryVoiceChannel:
        if target.bot:
            raise VoiceChannelError("Ownership cannot be transferred to a bot.")
        record, channel = await self.require_owner(db, member)
        if target == member:
            raise VoiceChannelError("You already own this channel.")
        if target not in channel.members:
            raise VoiceChannelError("Transfer ownership to someone in your voice channel.")

        await self._grant_owner_permissions(
            channel, target, reason="Temporary voice ownership transfer"
        )
        await self._remove_owner_permissions(channel, member, keep_access=True)
        old_owner_id = record.owner_id
        old_owner_name = record.owner_name
        record.owner_id = str(target.id)
        record.owner_name = target.display_name or target.name
        await log_voice_event(
            db,
            guild_pk=record.guild_id,
            event_type=VOICE_EVENT_OWNER_CHANGED,
            message=(
                f"{member.display_name} transferred a temporary voice channel to "
                f"{record.owner_name}."
            ),
            metadata={
                "channel_id": record.channel_id,
                "old_owner_id": old_owner_id,
                "old_owner_name": old_owner_name,
                "owner_id": record.owner_id,
                "owner_name": record.owner_name,
            },
        )
        return record

    async def claim_channel(
        self, db: AsyncSession, member: discord.Member
    ) -> TemporaryVoiceChannel:
        record, channel = await self.current_temp_channel(db, member)
        if any(str(channel_member.id) == record.owner_id for channel_member in channel.members):
            raise VoiceChannelError("The current owner is still in this channel.")
        old_owner_id = record.owner_id
        old_owner_name = record.owner_name
        old_owner = (
            channel.guild.get_member(int(record.owner_id)) if record.owner_id.isdigit() else None
        )
        if old_owner:
            await self._remove_owner_permissions(channel, old_owner, keep_access=False)
        await self._grant_owner_permissions(
            channel, member, reason="Temporary voice channel claimed"
        )
        record.owner_id = str(member.id)
        record.owner_name = member.display_name or member.name
        await log_voice_event(
            db,
            guild_pk=record.guild_id,
            event_type=VOICE_EVENT_OWNER_CHANGED,
            message=f"{member.display_name} claimed an abandoned temporary voice channel.",
            metadata={
                "channel_id": record.channel_id,
                "old_owner_id": old_owner_id,
                "old_owner_name": old_owner_name,
                "owner_id": record.owner_id,
                "owner_name": record.owner_name,
                "reason": "claim",
            },
        )
        return record

    async def allow_user(
        self, db: AsyncSession, member: discord.Member, target: discord.Member
    ) -> TemporaryVoiceChannel:
        record, channel = await self.require_owner(db, member)
        await channel.set_permissions(
            target,
            view_channel=True,
            connect=True,
            speak=True,
            reason=f"Temporary voice channel access allowed by {member}",
        )
        await log_voice_event(
            db,
            guild_pk=record.guild_id,
            event_type=VOICE_EVENT_USER_ALLOWED,
            message=(
                f"{member.display_name} allowed {target.display_name} into a "
                "temporary voice channel."
            ),
            metadata={
                "channel_id": record.channel_id,
                "owner_id": record.owner_id,
                "target_id": str(target.id),
                "target_name": target.display_name or target.name,
            },
        )
        return record

    async def deny_user(
        self, db: AsyncSession, member: discord.Member, target: discord.Member
    ) -> TemporaryVoiceChannel:
        record, channel = await self.require_owner(db, member)
        if str(target.id) == record.owner_id:
            raise VoiceChannelError("You cannot deny the channel owner.")
        await channel.set_permissions(
            target,
            view_channel=False,
            connect=False,
            reason=f"Temporary voice channel access denied by {member}",
        )
        await log_voice_event(
            db,
            guild_pk=record.guild_id,
            event_type=VOICE_EVENT_USER_DENIED,
            message=(
                f"{member.display_name} denied {target.display_name} from a "
                "temporary voice channel."
            ),
            metadata={
                "channel_id": record.channel_id,
                "owner_id": record.owner_id,
                "target_id": str(target.id),
                "target_name": target.display_name or target.name,
            },
        )
        return record

    async def kick_member(
        self, db: AsyncSession, member: discord.Member, target: discord.Member
    ) -> TemporaryVoiceChannel:
        record, channel = await self.require_owner(db, member)
        if str(target.id) == record.owner_id:
            raise VoiceChannelError("You cannot kick the channel owner.")
        if target.voice is None or target.voice.channel != channel:
            raise VoiceChannelError("That member is not in your voice channel.")
        await target.move_to(None, reason=f"Kicked from temporary voice channel by {member}")
        await log_voice_event(
            db,
            guild_pk=record.guild_id,
            event_type=VOICE_EVENT_MEMBER_KICKED,
            message=(
                f"{member.display_name} kicked {target.display_name} from a "
                "temporary voice channel."
            ),
            metadata={
                "channel_id": record.channel_id,
                "owner_id": record.owner_id,
                "target_id": str(target.id),
                "target_name": target.display_name or target.name,
            },
        )
        return record

    async def require_owner(
        self, db: AsyncSession, member: discord.Member
    ) -> tuple[TemporaryVoiceChannel, discord.VoiceChannel]:
        record, channel = await self.current_temp_channel(db, member)
        if record.owner_id != str(member.id):
            raise VoiceChannelError("Only the channel owner can use this command.")
        return record, channel

    async def current_temp_channel(
        self, db: AsyncSession, member: discord.Member
    ) -> tuple[TemporaryVoiceChannel, discord.VoiceChannel]:
        if member.voice is None or member.voice.channel is None:
            raise VoiceChannelError("Join one of your temporary voice channels first.")
        if not isinstance(member.voice.channel, discord.VoiceChannel):
            raise VoiceChannelError("This command can only be used in a voice channel.")
        guild_record = await get_guild_by_discord_id(db, str(member.guild.id))
        if guild_record is None:
            raise VoiceChannelError("This server is not registered in the dashboard.")
        record = await get_temporary_channel(db, guild_record.id, member.voice.channel.id)
        if record is None:
            raise VoiceChannelError("This is not a temporary voice channel.")
        return record, member.voice.channel

    def _creation_overwrites(
        self, member: discord.Member
    ) -> dict[discord.abc.Snowflake, discord.PermissionOverwrite]:
        overwrites: dict[discord.abc.Snowflake, discord.PermissionOverwrite] = {
            member.guild.default_role: discord.PermissionOverwrite(
                view_channel=False,
                connect=False,
            ),
            member: discord.PermissionOverwrite(
                view_channel=True,
                connect=True,
                speak=True,
                manage_channels=True,
                move_members=True,
            ),
        }
        bot_member = member.guild.me
        if bot_member is not None:
            overwrites[bot_member] = discord.PermissionOverwrite(
                view_channel=True,
                connect=True,
                speak=True,
                manage_channels=True,
                move_members=True,
            )
        return overwrites

    def _resolve_category(
        self, guild: discord.Guild, category_id: str | None
    ) -> discord.CategoryChannel | None:
        if not category_id:
            return None
        try:
            channel = guild.get_channel(int(category_id))
        except ValueError:
            return None
        return channel if isinstance(channel, discord.CategoryChannel) else None

    async def _apply_default_overwrite(
        self,
        channel: discord.VoiceChannel,
        *,
        private: bool,
        locked: bool,
        reason: str,
    ) -> None:
        overwrite = channel.overwrites_for(channel.guild.default_role)
        if private:
            overwrite.view_channel = False
            overwrite.connect = False
        else:
            overwrite.view_channel = None
            overwrite.connect = False if locked else None
        await channel.set_permissions(
            channel.guild.default_role,
            overwrite=None if overwrite.is_empty() else overwrite,
            reason=reason,
        )

    async def _grant_owner_permissions(
        self, channel: discord.VoiceChannel, member: discord.Member, *, reason: str
    ) -> None:
        overwrite = channel.overwrites_for(member)
        overwrite.view_channel = True
        overwrite.connect = True
        overwrite.speak = True
        overwrite.manage_channels = True
        overwrite.move_members = True
        await channel.set_permissions(member, overwrite=overwrite, reason=reason)

    async def _remove_owner_permissions(
        self, channel: discord.VoiceChannel, member: discord.Member, *, keep_access: bool
    ) -> None:
        overwrite = channel.overwrites_for(member)
        overwrite.manage_channels = None
        overwrite.move_members = None
        if keep_access:
            overwrite.view_channel = True
            overwrite.connect = True
            overwrite.speak = True
        await channel.set_permissions(
            member,
            overwrite=None if overwrite.is_empty() else overwrite,
            reason="Temporary voice ownership changed",
        )
