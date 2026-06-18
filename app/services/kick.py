import logging
from datetime import datetime
from typing import Any

import httpx

from app.core.config import Settings
from app.services.stream_platform import StreamInfo, StreamPlatform, offline

logger = logging.getLogger(__name__)


class KickService(StreamPlatform):
    platform = "kick"

    def __init__(self, settings: Settings, client: httpx.AsyncClient) -> None:
        self.settings = settings
        self.client = client

    async def get_stream_info(self, streamer_name: str) -> StreamInfo:
        slug = streamer_name.strip().lstrip("@").lower()
        url = f"https://kick.com/{slug}"
        response = await self.client.get(f"{self.settings.kick_api_base.rstrip('/')}/channels/{slug}")
        if response.status_code == 404:
            return offline(self.platform, slug, url)
        response.raise_for_status()
        payload = response.json()
        livestream: dict[str, Any] | None = payload.get("livestream")
        if not livestream:
            return offline(self.platform, slug, url)

        category = livestream.get("categories")
        if isinstance(category, list) and category:
            game = category[0].get("name") or "Unknown"
        elif isinstance(category, dict):
            game = category.get("name") or "Unknown"
        else:
            game = livestream.get("category", {}).get("name", "Unknown")

        started_at = None
        raw_started_at = livestream.get("created_at") or livestream.get("start_time")
        if raw_started_at:
            started_at = datetime.fromisoformat(str(raw_started_at).replace("Z", "+00:00"))

        thumbnail = (
            livestream.get("thumbnail", {}).get("url")
            if isinstance(livestream.get("thumbnail"), dict)
            else livestream.get("thumbnail")
        )

        return StreamInfo(
            platform=self.platform,
            streamer_name=slug,
            is_live=True,
            title=livestream.get("session_title") or livestream.get("title") or "Live on Kick",
            game=game,
            url=url,
            viewers=livestream.get("viewer_count") or livestream.get("viewers"),
            started_at=started_at,
            thumbnail_url=thumbnail,
            preview_url=thumbnail,
            stream_id=str(livestream.get("id") or f"{slug}:{raw_started_at or 'live'}"),
        )

