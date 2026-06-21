from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base, TimestampMixin


class EmbedTemplate(Base, TimestampMixin):
    __tablename__ = "embed_templates"

    id: Mapped[int] = mapped_column(primary_key=True)
    guild_id: Mapped[int] = mapped_column(
        ForeignKey("guilds.id", ondelete="CASCADE"), unique=True, index=True
    )
    title: Mapped[str] = mapped_column(String(256), default="\U0001f534 {streamer} is LIVE!")
    description: Mapped[str] = mapped_column(
        Text, default="Playing {game}\\n\\n{title}\\n\\nWatch Now: {url}"
    )
    color: Mapped[str] = mapped_column(String(16), default="#e53935", nullable=False)
    footer_text: Mapped[str | None] = mapped_column(String(256), nullable=True)
    author_text: Mapped[str | None] = mapped_column(String(256), nullable=True)
    show_thumbnail: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    show_preview: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    custom_thumbnail_url: Mapped[str | None] = mapped_column(String(512), nullable=True)

    guild = relationship("Guild", back_populates="embed_template")
