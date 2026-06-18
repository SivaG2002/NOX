from fastapi import APIRouter

from app.api import auth, embed_templates, guilds, logs, notification_settings, streamers

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(guilds.router)
api_router.include_router(streamers.router)
api_router.include_router(notification_settings.router)
api_router.include_router(embed_templates.router)
api_router.include_router(logs.router)

