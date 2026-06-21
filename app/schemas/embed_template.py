from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class EmbedTemplateUpdate(BaseModel):
    title: str = Field(default="\U0001f534 {streamer} is LIVE!", max_length=256)
    description: str = Field(
        default="Playing {game}\\n\\n{title}\\n\\nWatch Now: {url}", max_length=4000
    )
    color: str = "#e53935"
    footer_text: str | None = Field(default=None, max_length=256)
    author_text: str | None = Field(default=None, max_length=256)
    show_thumbnail: bool = True
    show_preview: bool = True

    @field_validator("color")
    @classmethod
    def validate_color(cls, value: str) -> str:
        value = value.strip()
        if not value.startswith("#"):
            value = f"#{value}"
        if len(value) != 7:
            raise ValueError("Color must be a 6-digit hex value")
        int(value[1:], 16)
        return value.lower()


class EmbedTemplateOut(BaseModel):
    id: int
    guild_id: int
    title: str
    description: str
    color: str
    footer_text: str | None
    author_text: str | None
    show_thumbnail: bool
    show_preview: bool
    custom_thumbnail_url: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
