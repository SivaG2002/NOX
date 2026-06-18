# Discord Stream Notifier

Production-ready FastAPI and discord.py bot for Discord live stream notifications across Twitch, YouTube Live, and Kick.

## Features

- Discord OAuth2 dashboard login.
- Per-server streamers, notification channel, role mention, and embed template settings.
- Twitch Helix, YouTube Data API v3, and isolated Kick service integrations.
- Async scheduler that checks every 60 seconds, detects stream start/end, prevents duplicate notifications, and stores Discord notification message IDs.
- REST API routers for auth, guilds, streamers, notification settings, embed templates, and logs.
- PostgreSQL for production and SQLite for local development.
- Docker Compose deployment with Alembic migrations.

## Local Setup

1. Create and activate a Python 3.11 virtual environment.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
```

2. Copy the environment file and fill in secrets.

```powershell
Copy-Item .env.example .env
```

3. Create a Discord application:

- Add a bot token to `DISCORD_BOT_TOKEN`.
- Add OAuth2 redirect URL `http://localhost:8000/auth/callback`.
- Set `DISCORD_CLIENT_ID`, `DISCORD_CLIENT_SECRET`, and `DISCORD_REDIRECT_URI`.
- Invite the bot with `bot` scope and permissions to send messages, embed links, and use external emojis/buttons.

4. Add platform API credentials:

- Twitch: `TWITCH_CLIENT_ID` and `TWITCH_CLIENT_SECRET`.
- YouTube: `YOUTUBE_API_KEY`.
- Kick: `KICK_API_BASE` defaults to `https://kick.com/api/v2`. The Kick integration is isolated because Kick API availability and response shapes can change.

5. Run the app.

```powershell
uvicorn app.main:app --reload
```

Open `http://localhost:8000`.

## Docker

```powershell
Copy-Item .env.example .env
docker compose up --build
```

The Compose app runs Alembic migrations before starting Uvicorn. Keep one web worker for this deployment shape because the Discord gateway connection and scheduler run in the FastAPI process.

## API Overview

- `GET /auth/login`
- `GET /auth/callback`
- `GET /auth/logout`
- `GET /api/auth/me`
- `GET /api/guilds`
- `GET /api/guilds/{guild_id}`
- `GET /api/guilds/{guild_id}/channels`
- `GET /api/guilds/{guild_id}/roles`
- `GET /api/guilds/{guild_id}/streamers`
- `POST /api/guilds/{guild_id}/streamers`
- `PUT /api/streamers/{streamer_id}`
- `DELETE /api/streamers/{streamer_id}`
- `GET /api/guilds/{guild_id}/notification-settings`
- `PUT /api/guilds/{guild_id}/notification-settings`
- `GET /api/guilds/{guild_id}/embed-template`
- `PUT /api/guilds/{guild_id}/embed-template`
- `GET /api/guilds/{guild_id}/logs`

State-changing API requests must include the session CSRF token in the `x-csrf-token` header.

## Embed Variables

- `{streamer}`
- `{title}`
- `{game}`
- `{platform}`
- `{url}`
- `{viewers}`
- `{start_time}`

## Database

Run migrations manually:

```powershell
alembic upgrade head
```

Development defaults to SQLite with automatic table creation. Production should set `AUTO_CREATE_TABLES=false` and run Alembic migrations.

## Notes

- Discord OAuth only shows guilds where the logged-in user owns the server or has Manage Server permission.
- The dashboard channel and role selectors require the bot to be installed in the server and connected.
- Secrets are read from environment variables; do not commit `.env`.

