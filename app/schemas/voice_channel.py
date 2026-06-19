from datetime import datetime

from pydantic import BaseModel, Field


class VoiceChannelSettingsUpdate(BaseModel):
    enabled: bool = False
    create_channel_id: str | None = None
    create_channel_ids: list[str] = Field(default_factory=list)
    category_id: str | None = None
    default_user_limit: int = Field(default=4, ge=0, le=99)
    naming_template: str = Field(default="{owner}'s Channel", min_length=1, max_length=100)
    auto_delete: bool = True


class VoiceChannelSettingsOut(BaseModel):
    id: int
    guild_id: int
    enabled: bool
    create_channel_id: str | None
    create_channel_ids: list[str] | None
    category_id: str | None
    default_user_limit: int
    naming_template: str
    auto_delete: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TemporaryVoiceChannelOut(BaseModel):
    id: int
    guild_id: int
    channel_id: str
    owner_id: str
    owner_name: str
    user_limit: int
    is_locked: bool
    is_private: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class VoiceChannelOwnerMetric(BaseModel):
    owner_id: str
    owner_name: str
    channels_created: int


class VoiceChannelMetricsOut(BaseModel):
    active_channels: int
    channels_created_today: int
    channels_deleted_today: int
    most_active_owners: list[VoiceChannelOwnerMetric]
