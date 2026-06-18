import logging
from datetime import UTC, datetime, timedelta

import httpx

from app.core.config import Settings
from app.services.stream_platform import StreamInfo, StreamPlatform, offline

logger = logging.getLogger(__name__)


class TwitchService(StreamPlatform):
    platform = "twitch"

    def __init__(self, settings: Settings, client: httpx.AsyncClient) -> None:
        self.settings = settings
        self.client = client
        self._access_token: str | None = None
        self._token_expires_at: datetime | None = None

    async def _get_access_token(self) -> str | None:
        if not self.settings.twitch_client_id or not self.settings.twitch_client_secret.get_secret_value():
            logger.warning("twitch_credentials_missing")
            return None
        if self._access_token and self._token_expires_at and self._token_expires_at > datetime.now(UTC):
            return self._access_token

        response = await self.client.post(
            "https://id.twitch.tv/oauth2/token",
            data={
                "client_id": self.settings.twitch_client_id,
                "client_secret": self.settings.twitch_client_secret.get_secret_value(),
                "grant_type": "client_credentials",
            },
        )
        response.raise_for_status()
        payload = response.json()
        self._access_token = payload["access_token"]
        self._token_expires_at = datetime.now(UTC) + timedelta(
            seconds=max(60, int(payload.get("expires_in", 3600)) - 60)
        )
        return self._access_token

    async def get_stream_info(self, streamer_name: str) -> StreamInfo:
        channel = streamer_name.strip().lstrip("@").lower()
        url = f"https://www.twitch.tv/{channel}"
        token = await self._get_access_token()
        if not token:
            return offline(self.platform, channel, url)

        response = await self.client.get(
            "https://api.twitch.tv/helix/streams",
            params={"user_login": channel},
            headers={
                "Client-ID": self.settings.twitch_client_id,
                "Authorization": f"Bearer {token}",
            },
        )
        response.raise_for_status()
        data = response.json().get("data", [])
        if not data:
            return offline(self.platform, channel, url)

        stream = data[0]
        started_at = None
        if stream.get("started_at"):
            started_at = datetime.fromisoformat(stream["started_at"].replace("Z", "+00:00"))
        thumbnail = stream.get("thumbnail_url")
        if thumbnail:
            thumbnail = thumbnail.replace("{width}", "640").replace("{height}", "360")

        return StreamInfo(
            platform=self.platform,
            streamer_name=channel,
            is_live=True,
            title=stream.get("title") or "Live on Twitch",
            game=stream.get("game_name") or "Unknown",
            url=url,
            viewers=stream.get("viewer_count"),
            started_at=started_at,
            thumbnail_url=thumbnail,
            preview_url=thumbnail,
            stream_id=stream.get("id"),
        )

