from datetime import UTC, datetime
from urllib.parse import urljoin, urlparse

import discord

from app.models import EmbedTemplate, NotificationSettings
from app.services.stream_platform import StreamInfo
from app.services.template_renderer import render_template

PLATFORM_ICONS = {
    "twitch": "https://www.google.com/s2/favicons?domain=twitch.tv&sz=64",
    "youtube": "https://www.google.com/s2/favicons?domain=youtube.com&sz=64",
    "kick": "https://www.google.com/s2/favicons?domain=kick.com&sz=64",
}


def stream_variables(info: StreamInfo) -> dict:
    return {
        "streamer": info.streamer_name,
        "title": info.title,
        "game": info.game,
        "platform": info.platform.title(),
        "url": info.url,
        "viewers": info.viewers if info.viewers is not None else "Unknown",
        "start_time": info.started_at or "",
    }


def parse_color(value: str | None) -> int:
    if not value:
        return 0xE53935
    return int(value.strip().lstrip("#"), 16)


def discord_timestamp(value: datetime | None) -> str:
    if value is None:
        return "Unknown"
    return f"<t:{int(value.timestamp())}:R>"


def public_image_url(url: str | None, base_url: str | None = None) -> str | None:
    if not url:
        return None
    if urlparse(url).scheme in {"http", "https"}:
        return url
    if not base_url:
        return url
    return urljoin(f"{base_url.rstrip('/')}/", url.lstrip("/"))


def build_mention(settings: NotificationSettings) -> tuple[str | None, bool, bool]:
    if settings.mention_everyone:
        return "@everyone", True, False
    if settings.mention_here:
        return "@here", True, False
    if settings.role_id:
        return f"<@&{settings.role_id}>", False, True
    return None, False, False


def build_stream_embed(
    template: EmbedTemplate,
    info: StreamInfo,
    *,
    base_url: str | None = None,
    custom_image_attachment_name: str | None = None,
) -> discord.Embed:
    variables = stream_variables(info)
    embed = discord.Embed(
        title=render_template(template.title, variables),
        description=render_template(template.description, variables),
        color=parse_color(template.color),
        url=info.url,
        timestamp=info.started_at or datetime.now(UTC),
    )
    platform_icon = PLATFORM_ICONS.get(info.platform)
    author_text = render_template(template.author_text, variables) if template.author_text else None
    embed.set_author(name=author_text or f"{info.platform.title()} Live", icon_url=platform_icon)
    if template.footer_text:
        embed.set_footer(text=render_template(template.footer_text, variables))
    custom_image_url = (
        f"attachment://{custom_image_attachment_name}"
        if template.custom_thumbnail_url and custom_image_attachment_name
        else public_image_url(template.custom_thumbnail_url, base_url)
    )
    if custom_image_url:
        if template.show_preview:
            embed.set_image(url=custom_image_url)
        elif template.show_thumbnail:
            embed.set_thumbnail(url=custom_image_url)
    else:
        if template.show_thumbnail and info.thumbnail_url:
            embed.set_thumbnail(url=info.thumbnail_url)
        if template.show_preview and info.preview_url:
            embed.set_image(url=info.preview_url)

    embed.add_field(name="Platform", value=info.platform.title(), inline=True)
    embed.add_field(
        name="Viewers",
        value=str(info.viewers if info.viewers is not None else "Unknown"),
        inline=True,
    )
    embed.add_field(name="Started At", value=discord_timestamp(info.started_at), inline=True)
    return embed
