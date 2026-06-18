from datetime import datetime

from pydantic import BaseModel


class NotificationSettingsUpdate(BaseModel):
    channel_id: str | None = None
    role_id: str | None = None
    mention_everyone: bool = False
    mention_here: bool = False


class NotificationSettingsOut(BaseModel):
    id: int
    guild_id: int
    channel_id: str | None
    role_id: str | None
    mention_everyone: bool
    mention_here: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

