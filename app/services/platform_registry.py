import httpx

from app.core.config import Settings, get_settings
from app.services.kick import KickService
from app.services.stream_platform import StreamPlatform
from app.services.twitch import TwitchService
from app.services.youtube import YouTubeService


class PlatformRegistry:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.client = httpx.AsyncClient(timeout=httpx.Timeout(15.0, connect=5.0))
        self._services: dict[str, StreamPlatform] = {
            "twitch": TwitchService(self.settings, self.client),
            "youtube": YouTubeService(self.settings, self.client),
            "kick": KickService(self.settings, self.client),
        }

    def get(self, platform: str) -> StreamPlatform:
        return self._services[platform]

    async def close(self) -> None:
        await self.client.aclose()

