import asyncio
import logging
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.bot.client import StreamNotificationBot
from app.core.config import Settings, get_settings
from app.database.session import AsyncSessionLocal
from app.models import NotificationLog, StreamState, Streamer
from app.services.discord_notifications import build_mention, build_stream_embed
from app.services.guild_defaults import (
    get_or_create_embed_template,
    get_or_create_notification_settings,
)
from app.services.platform_registry import PlatformRegistry
from app.services.stream_platform import StreamInfo

logger = logging.getLogger(__name__)


class StreamMonitor:
    def __init__(
        self,
        bot: StreamNotificationBot,
        registry: PlatformRegistry | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.bot = bot
        self.settings = settings or get_settings()
        self.registry = registry or PlatformRegistry(self.settings)
        self._stop_event = asyncio.Event()
        self._run_lock = asyncio.Lock()

    async def run(self) -> None:
        logger.info("stream_monitor_started")
        while not self._stop_event.is_set():
            try:
                if self.bot.is_ready():
                    await self.check_once()
                else:
                    logger.info("stream_monitor_waiting_for_discord")
            except Exception:
                logger.exception("stream_monitor_tick_failed")
            try:
                await asyncio.wait_for(
                    self._stop_event.wait(),
                    timeout=max(10, self.settings.check_interval_seconds),
                )
            except TimeoutError:
                continue
        logger.info("stream_monitor_stopped")

    async def stop(self) -> None:
        self._stop_event.set()
        await self.registry.close()

    async def check_once(self) -> None:
        if self._run_lock.locked():
            logger.warning("stream_monitor_tick_skipped_already_running")
            return
        async with self._run_lock:
            streamer_ids = await self._enabled_streamer_ids()
            semaphore = asyncio.Semaphore(5)

            async def bounded_check(streamer_id: int) -> None:
                async with semaphore:
                    await self._check_streamer(streamer_id)

            await asyncio.gather(*(bounded_check(streamer_id) for streamer_id in streamer_ids))

    async def _enabled_streamer_ids(self) -> list[int]:
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Streamer.id).where(Streamer.enabled.is_(True)))
            return list(result.scalars().all())

    async def _check_streamer(self, streamer_id: int) -> None:
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(Streamer)
                    .where(Streamer.id == streamer_id)
                    .options(selectinload(Streamer.guild), selectinload(Streamer.state))
                )
                streamer = result.scalar_one_or_none()
                if streamer is None or not streamer.enabled:
                    return

                service = self.registry.get(streamer.platform)
                info = await service.get_stream_info(streamer.streamer_name)
                state = streamer.state
                if state is None:
                    state = StreamState(guild_id=streamer.guild_id, streamer_id=streamer.id)
                    db.add(state)
                    await db.flush()

                if info.is_live:
                    await self._handle_live_stream(db, streamer, state, info)
                elif state.is_live:
                    state.is_live = False
                    state.ended_at = datetime.now(UTC)
                    state.last_seen_at = datetime.now(UTC)
                    db.add(
                        NotificationLog(
                            guild_id=streamer.guild_id,
                            streamer_id=streamer.id,
                            platform=streamer.platform,
                            event_type="stream_ended",
                            message=f"{streamer.streamer_name} ended their stream.",
                            log_metadata={"stream_id": state.stream_id},
                        )
                    )
                await db.commit()
        except Exception as exc:
            logger.exception(
                "stream_check_failed",
                extra={"streamer_id": streamer_id, "error": str(exc)},
            )
            await self._write_error_log(streamer_id, str(exc))

    async def _handle_live_stream(self, db, streamer: Streamer, state: StreamState, info: StreamInfo):
        now = datetime.now(UTC)
        stream_id = info.stream_id or f"{info.platform}:{info.streamer_name}:{info.started_at or 'live'}"
        is_new_stream = not state.is_live or state.stream_id != stream_id
        state.is_live = True
        state.stream_id = stream_id
        state.started_at = info.started_at
        state.last_seen_at = now

        if not is_new_stream:
            return

        db.add(
            NotificationLog(
                guild_id=streamer.guild_id,
                streamer_id=streamer.id,
                platform=streamer.platform,
                event_type="stream_started",
                message=f"{streamer.streamer_name} started streaming.",
                log_metadata={"stream_id": stream_id, "title": info.title},
            )
        )
        message_id = await self._send_notification(db, streamer, info)
        state.notification_message_id = message_id
        db.add(
            NotificationLog(
                guild_id=streamer.guild_id,
                streamer_id=streamer.id,
                platform=streamer.platform,
                event_type="notification_sent",
                message=f"Sent notification for {streamer.streamer_name}.",
                notification_message_id=message_id,
                log_metadata={"stream_id": stream_id, "url": info.url},
            )
        )

    async def _send_notification(self, db, streamer: Streamer, info: StreamInfo) -> str:
        settings = await get_or_create_notification_settings(db, streamer.guild_id)
        template = await get_or_create_embed_template(db, streamer.guild_id)
        if not settings.channel_id:
            raise RuntimeError("Notification channel is not configured")
        if not self.bot.is_ready():
            raise RuntimeError("Discord bot is not ready")

        content, allow_everyone, allow_roles = build_mention(settings)
        embed = build_stream_embed(template, info)
        message = await self.bot.send_stream_embed(
            guild_id=streamer.guild.guild_id,
            channel_id=settings.channel_id,
            content=content,
            embed=embed,
            watch_url=info.url,
            allow_everyone=allow_everyone,
            allow_roles=allow_roles,
        )
        return str(message.id)

    async def _write_error_log(self, streamer_id: int, error: str) -> None:
        async with AsyncSessionLocal() as db:
            streamer = await db.get(Streamer, streamer_id)
            if streamer is None:
                return
            db.add(
                NotificationLog(
                    guild_id=streamer.guild_id,
                    streamer_id=streamer.id,
                    platform=streamer.platform,
                    event_type="error",
                    message=error,
                )
            )
            await db.commit()

