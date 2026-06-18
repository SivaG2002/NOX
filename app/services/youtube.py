import logging
from datetime import datetime

import httpx

from app.core.config import Settings
from app.services.stream_platform import StreamInfo, StreamPlatform, offline

logger = logging.getLogger(__name__)


class YouTubeService(StreamPlatform):
    platform = "youtube"

    def __init__(self, settings: Settings, client: httpx.AsyncClient) -> None:
        self.settings = settings
        self.client = client
        self._channel_cache: dict[str, str] = {}

    async def _resolve_channel_id(self, channel_name: str) -> str | None:
        name = channel_name.strip()
        if name.startswith("UC") and len(name) >= 20:
            return name
        if name in self._channel_cache:
            return self._channel_cache[name]

        api_key = self.settings.youtube_api_key.get_secret_value()
        if not api_key:
            logger.warning("youtube_api_key_missing")
            return None

        response = await self.client.get(
            "https://www.googleapis.com/youtube/v3/search",
            params={
                "part": "snippet",
                "q": name,
                "type": "channel",
                "maxResults": 1,
                "key": api_key,
            },
        )
        response.raise_for_status()
        items = response.json().get("items", [])
        if not items:
            return None
        channel_id = items[0]["snippet"]["channelId"]
        self._channel_cache[name] = channel_id
        return channel_id

    async def get_stream_info(self, streamer_name: str) -> StreamInfo:
        channel_name = streamer_name.strip()
        channel_url = (
            f"https://www.youtube.com/channel/{channel_name}"
            if channel_name.startswith("UC")
            else f"https://www.youtube.com/@{channel_name.lstrip('@')}"
        )
        api_key = self.settings.youtube_api_key.get_secret_value()
        channel_id = await self._resolve_channel_id(channel_name)
        if not api_key or not channel_id:
            return offline(self.platform, channel_name, channel_url)

        live_response = await self.client.get(
            "https://www.googleapis.com/youtube/v3/search",
            params={
                "part": "snippet",
                "channelId": channel_id,
                "eventType": "live",
                "type": "video",
                "maxResults": 1,
                "key": api_key,
            },
        )
        live_response.raise_for_status()
        live_items = live_response.json().get("items", [])
        if not live_items:
            return offline(self.platform, channel_name, channel_url)

        video_id = live_items[0]["id"]["videoId"]
        details_response = await self.client.get(
            "https://www.googleapis.com/youtube/v3/videos",
            params={
                "part": "snippet,liveStreamingDetails",
                "id": video_id,
                "key": api_key,
            },
        )
        details_response.raise_for_status()
        details = details_response.json().get("items", [{}])[0]
        snippet = details.get("snippet", live_items[0].get("snippet", {}))
        live_details = details.get("liveStreamingDetails", {})
        started_at = None
        if live_details.get("actualStartTime"):
            started_at = datetime.fromisoformat(
                live_details["actualStartTime"].replace("Z", "+00:00")
            )
        thumbnails = snippet.get("thumbnails", {})
        thumbnail = (
            thumbnails.get("maxres", {})
            or thumbnails.get("high", {})
            or thumbnails.get("medium", {})
            or thumbnails.get("default", {})
        ).get("url")

        return StreamInfo(
            platform=self.platform,
            streamer_name=channel_name,
            is_live=True,
            title=snippet.get("title") or "Live on YouTube",
            game=snippet.get("categoryId") or "Live",
            url=f"https://www.youtube.com/watch?v={video_id}",
            viewers=int(live_details["concurrentViewers"])
            if live_details.get("concurrentViewers")
            else None,
            started_at=started_at,
            thumbnail_url=thumbnail,
            preview_url=thumbnail,
            stream_id=video_id,
        )

