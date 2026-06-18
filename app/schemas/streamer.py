from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.schemas.common import Platform


def normalize_streamer_name(platform: str, name: str) -> str:
    cleaned = name.strip()
    if platform in {"twitch", "kick"}:
        cleaned = cleaned.lstrip("@").lower()
    return cleaned


class StreamerBase(BaseModel):
    platform: Platform
    streamer_name: str = Field(min_length=1, max_length=120)
    enabled: bool = True

    @field_validator("streamer_name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        if "/" in value.strip():
            raise ValueError("Use the channel name, handle, or slug, not a full URL")
        return value.strip()


class StreamerCreate(StreamerBase):
    pass


class StreamerUpdate(BaseModel):
    platform: Platform | None = None
    streamer_name: str | None = Field(default=None, min_length=1, max_length=120)
    enabled: bool | None = None

    @field_validator("streamer_name")
    @classmethod
    def validate_optional_name(cls, value: str | None) -> str | None:
        if value is None:
            return value
        if "/" in value.strip():
            raise ValueError("Use the channel name, handle, or slug, not a full URL")
        return value.strip()


class StreamerOut(BaseModel):
    id: int
    guild_id: int
    platform: Platform
    streamer_name: str
    enabled: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

