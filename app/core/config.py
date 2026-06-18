from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Discord Stream Notifier"
    app_env: str = "development"
    base_url: str = "http://localhost:8000"
    secret_key: SecretStr = Field(default=SecretStr("change-me"))
    database_url: str = "sqlite+aiosqlite:///./streambot.sqlite3"
    auto_create_tables: bool = True
    log_level: str = "INFO"
    check_interval_seconds: int = 60
    rate_limit_per_minute: int = 120
    session_cookie_name: str = "streamnotifier_session"

    discord_client_id: str = ""
    discord_client_secret: SecretStr = Field(default=SecretStr(""))
    discord_redirect_uri: str = "http://localhost:8000/auth/callback"
    discord_bot_token: SecretStr = Field(default=SecretStr(""))
    discord_api_base: str = "https://discord.com/api"
    discord_oauth_scopes: str = "identify guilds"

    twitch_client_id: str = ""
    twitch_client_secret: SecretStr = Field(default=SecretStr(""))
    youtube_api_key: SecretStr = Field(default=SecretStr(""))
    kick_api_base: str = "https://kick.com/api/v2"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()

