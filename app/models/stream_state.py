from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base, TimestampMixin


class StreamState(Base, TimestampMixin):
    __tablename__ = "stream_states"
    __table_args__ = (UniqueConstraint("streamer_id", name="uq_stream_state_streamer"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    guild_id: Mapped[int] = mapped_column(ForeignKey("guilds.id", ondelete="CASCADE"), index=True)
    streamer_id: Mapped[int] = mapped_column(
        ForeignKey("streamers.id", ondelete="CASCADE"), index=True
    )
    is_live: Mapped[bool] = mapped_column(default=False, nullable=False)
    stream_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    notification_message_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    streamer = relationship("Streamer", back_populates="state")

