from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class StreamInfo:
    platform: str
    streamer_name: str
    is_live: bool
    title: str = ""
    game: str = "Unknown"
    url: str = ""
    viewers: int | None = None
    started_at: datetime | None = None
    thumbnail_url: str | None = None
    preview_url: str | None = None
    stream_id: str | None = None


def offline(platform: str, streamer_name: str, url: str = "") -> StreamInfo:
    return StreamInfo(platform=platform, streamer_name=streamer_name, is_live=False, url=url)


class StreamPlatform(ABC):
    platform: str

    @abstractmethod
    async def get_stream_info(self, streamer_name: str) -> StreamInfo:
        raise NotImplementedError

    async def is_live(self, streamer_name: str) -> bool:
        return (await self.get_stream_info(streamer_name)).is_live

    async def get_thumbnail(self, streamer_name: str) -> str | None:
        return (await self.get_stream_info(streamer_name)).thumbnail_url

