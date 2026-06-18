from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base, TimestampMixin


class Guild(Base, TimestampMixin):
    __tablename__ = "guilds"

    id: Mapped[int] = mapped_column(primary_key=True)
    guild_id: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)

    streamers = relationship("Streamer", back_populates="guild", cascade="all, delete-orphan")
    notification_settings = relationship(
        "NotificationSettings",
        back_populates="guild",
        cascade="all, delete-orphan",
        uselist=False,
    )
    embed_template = relationship(
        "EmbedTemplate",
        back_populates="guild",
        cascade="all, delete-orphan",
        uselist=False,
    )
    logs = relationship("NotificationLog", back_populates="guild", cascade="all, delete-orphan")

