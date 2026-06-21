from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base, TimestampMixin


class NotificationSettings(Base, TimestampMixin):
    __tablename__ = "notification_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    guild_id: Mapped[int] = mapped_column(
        ForeignKey("guilds.id", ondelete="CASCADE"), unique=True, index=True
    )
    channel_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    role_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    mention_everyone: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    mention_here: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    delete_notification_on_end: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )

    guild = relationship("Guild", back_populates="notification_settings")
