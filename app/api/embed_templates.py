from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_guild_access
from app.database.session import get_db
from app.models import EmbedTemplate, Guild
from app.schemas.embed_template import EmbedTemplateOut, EmbedTemplateUpdate
from app.services.guild_defaults import get_or_create_embed_template

router = APIRouter(tags=["embed-templates"])


@router.get("/api/guilds/{guild_id}/embed-template", response_model=EmbedTemplateOut)
async def get_template(
    guild: Guild = Depends(require_guild_access),
    db: AsyncSession = Depends(get_db),
) -> EmbedTemplate:
    template = await get_or_create_embed_template(db, guild.id)
    await db.commit()
    await db.refresh(template)
    return template


@router.put("/api/guilds/{guild_id}/embed-template", response_model=EmbedTemplateOut)
async def update_template(
    payload: EmbedTemplateUpdate,
    guild: Guild = Depends(require_guild_access),
    db: AsyncSession = Depends(get_db),
) -> EmbedTemplate:
    template = await get_or_create_embed_template(db, guild.id)
    template.title = payload.title
    template.description = payload.description
    template.color = payload.color
    template.footer_text = payload.footer_text or None
    template.author_text = payload.author_text or None
    template.show_thumbnail = payload.show_thumbnail
    template.show_preview = payload.show_preview
    await db.commit()
    await db.refresh(template)
    return template

