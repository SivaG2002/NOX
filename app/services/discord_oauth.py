from urllib.parse import urlencode

import httpx

from app.core.config import Settings, get_settings

MANAGE_GUILD_PERMISSION = 0x20


class DiscordOAuthClient:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def authorization_url(self, state: str) -> str:
        params = {
            "client_id": self.settings.discord_client_id,
            "redirect_uri": self.settings.discord_redirect_uri,
            "response_type": "code",
            "scope": self.settings.discord_oauth_scopes,
            "state": state,
            "prompt": "none",
        }
        return f"{self.settings.discord_api_base}/oauth2/authorize?{urlencode(params)}"

    async def exchange_code(self, code: str) -> dict:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                f"{self.settings.discord_api_base}/oauth2/token",
                data={
                    "client_id": self.settings.discord_client_id,
                    "client_secret": self.settings.discord_client_secret.get_secret_value(),
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": self.settings.discord_redirect_uri,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            response.raise_for_status()
            return response.json()

    async def fetch_user(self, access_token: str) -> dict:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                f"{self.settings.discord_api_base}/users/@me",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            response.raise_for_status()
            return response.json()

    async def fetch_manageable_guilds(self, access_token: str) -> list[dict]:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                f"{self.settings.discord_api_base}/users/@me/guilds",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            response.raise_for_status()
            guilds = response.json()

        manageable = []
        for guild in guilds:
            permissions = int(guild.get("permissions") or 0)
            if guild.get("owner") or permissions & MANAGE_GUILD_PERMISSION:
                manageable.append(
                    {
                        "id": guild["id"],
                        "name": guild["name"],
                        "icon": guild.get("icon"),
                    }
                )
        return manageable

