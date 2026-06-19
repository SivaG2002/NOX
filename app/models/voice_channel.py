from sqlalchemy import JSON, Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base, TimestampMixin


class VoiceChannelSettings(Base, TimestampMixin):
    __tablename__ = "voice_channel_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    guild_id: Mapped[int] = mapped_column(
        ForeignKey("guilds.id", ondelete="CASCADE"), unique=True, index=True
    )
    enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    create_channel_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    create_channel_ids: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    category_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    default_user_limit: Mapped[int] = mapped_column(Integer, default=4, nullable=False)
    naming_template: Mapped[str] = mapped_column(
        String(100), default="{owner}'s Channel", nullable=False
    )
    auto_delete: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    guild = relationship("Guild", back_populates="voice_channel_settings")


class TemporaryVoiceChannel(Base, TimestampMixin):
    __tablename__ = "temporary_voice_channels"

    id: Mapped[int] = mapped_column(primary_key=True)
    guild_id: Mapped[int] = mapped_column(ForeignKey("guilds.id", ondelete="CASCADE"), index=True)
    channel_id: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    owner_id: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    owner_name: Mapped[str] = mapped_column(String(120), nullable=False)
    user_limit: Mapped[int] = mapped_column(Integer, default=4, nullable=False)
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_private: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    guild = relationship("Guild", back_populates="temporary_voice_channels")
