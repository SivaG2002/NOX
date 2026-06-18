from datetime import UTC, datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base


class NotificationLog(Base):
    __tablename__ = "notification_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    guild_id: Mapped[int] = mapped_column(ForeignKey("guilds.id", ondelete="CASCADE"), index=True)
    streamer_id: Mapped[int | None] = mapped_column(
        ForeignKey("streamers.id", ondelete="SET NULL"), nullable=True, index=True
    )
    platform: Mapped[str] = mapped_column(String(20), nullable=False)
    event_type: Mapped[str] = mapped_column(String(40), index=True, nullable=False)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    notification_message_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    log_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), index=True, nullable=False
    )

    guild = relationship("Guild", back_populates="logs")
    streamer = relationship("Streamer", back_populates="logs")

