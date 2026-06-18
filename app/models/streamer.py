from sqlalchemy import Boolean, CheckConstraint, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base, TimestampMixin


class Streamer(Base, TimestampMixin):
    __tablename__ = "streamers"
    __table_args__ = (
        CheckConstraint("platform in ('twitch', 'youtube', 'kick')", name="ck_streamers_platform"),
        UniqueConstraint("guild_id", "platform", "streamer_name", name="uq_streamer_per_guild"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    guild_id: Mapped[int] = mapped_column(ForeignKey("guilds.id", ondelete="CASCADE"), index=True)
    platform: Mapped[str] = mapped_column(String(20), nullable=False)
    streamer_name: Mapped[str] = mapped_column(String(120), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    guild = relationship("Guild", back_populates="streamers")
    logs = relationship("NotificationLog", back_populates="streamer", cascade="all, delete-orphan")
    state = relationship(
        "StreamState", back_populates="streamer", cascade="all, delete-orphan", uselist=False
    )

