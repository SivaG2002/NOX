from datetime import datetime
from typing import Any

from pydantic import BaseModel


class NotificationLogOut(BaseModel):
    id: int
    guild_id: int
    streamer_id: int | None
    platform: str
    event_type: str
    message: str | None
    notification_message_id: str | None
    log_metadata: dict[str, Any] | None
    timestamp: datetime

    model_config = {"from_attributes": True}

