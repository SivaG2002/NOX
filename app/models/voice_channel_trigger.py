from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base, TimestampMixin


class VoiceChannelTrigger(Base, TimestampMixin):
    """Configuration for a trigger channel that creates temporary voice channels."""

    __tablename__ = "voice_channel_triggers"

    id: Mapped[int] = mapped_column(primary_key=True)
    guild_id: Mapped[int] = mapped_column(
        ForeignKey("guilds.id", ondelete="CASCADE"), index=True, nullable=False
    )
    trigger_channel_id: Mapped[str] = mapped_column(String(32), nullable=False)
    trigger_channel_name: Mapped[str] = mapped_column(String(120), nullable=False)
    category_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    user_limit: Mapped[int] = mapped_column(Integer, default=4, nullable=False)
    size_preset: Mapped[str] = mapped_column(String(20), default="custom", nullable=False)
    naming_template: Mapped[str] = mapped_column(
        String(100), default="{owner}'s Channel", nullable=False
    )
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    guild = relationship("Guild", back_populates="voice_channel_triggers")

    __table_args__ = (
        # Prevent duplicate triggers for the same channel in a guild
        # Note: SQLite doesn't support unique with nullable columns well,
        # so we handle this in application logic
    )
