from datetime import datetime

from pydantic import BaseModel


class GuildOut(BaseModel):
    id: int
    guild_id: str
    name: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DiscordChannelOut(BaseModel):
    id: str
    name: str


class DiscordRoleOut(BaseModel):
    id: str
    name: str

