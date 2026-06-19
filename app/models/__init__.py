from datetime import UTC, datetime

from sqlalchemy import DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )


from app.models.embed_template import EmbedTemplate  # noqa: E402
from app.models.guild import Guild  # noqa: E402
from app.models.notification_log import NotificationLog  # noqa: E402
from app.models.notification_settings import NotificationSettings  # noqa: E402
from app.models.stream_state import StreamState  # noqa: E402
from app.models.streamer import Streamer  # noqa: E402
from app.models.voice_channel import TemporaryVoiceChannel, VoiceChannelSettings  # noqa: E402

__all__ = [
    "Base",
    "EmbedTemplate",
    "Guild",
    "NotificationLog",
    "NotificationSettings",
    "StreamState",
    "Streamer",
    "TimestampMixin",
    "TemporaryVoiceChannel",
    "VoiceChannelSettings",
]
