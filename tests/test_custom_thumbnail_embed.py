from pathlib import Path

from app.models import EmbedTemplate
from app.services.discord_notifications import build_stream_embed
from app.services.stream_platform import StreamInfo
from app.services.uploads import resolve_uploaded_thumbnail


def make_template(**overrides) -> EmbedTemplate:
    values = {
        "guild_id": 1,
        "title": "{streamer} is live",
        "description": "{title}",
        "color": "#e53935",
        "footer_text": None,
        "author_text": None,
        "show_thumbnail": True,
        "show_preview": True,
        "custom_thumbnail_url": None,
    }
    values.update(overrides)
    return EmbedTemplate(**values)


def make_stream_info() -> StreamInfo:
    return StreamInfo(
        platform="twitch",
        streamer_name="alice",
        is_live=True,
        title="Testing",
        url="https://twitch.tv/alice",
        thumbnail_url="https://example.com/thumb.jpg",
        preview_url="https://example.com/preview.jpg",
    )


def test_custom_thumbnail_attachment_uses_discord_attachment_url() -> None:
    template = make_template(custom_thumbnail_url="/uploads/embed-thumbnails/guild/thumb.png")

    embed = build_stream_embed(
        template,
        make_stream_info(),
        base_url="http://127.0.0.1:8000",
        custom_image_attachment_name="thumb.png",
    )

    assert embed.to_dict()["image"]["url"] == "attachment://thumb.png"
    assert "thumbnail" not in embed.to_dict()


def test_custom_thumbnail_attachment_can_be_used_as_thumbnail() -> None:
    template = make_template(
        custom_thumbnail_url="/uploads/embed-thumbnails/guild/thumb.png",
        show_preview=False,
        show_thumbnail=True,
    )

    embed = build_stream_embed(
        template,
        make_stream_info(),
        base_url="http://127.0.0.1:8000",
        custom_image_attachment_name="thumb.png",
    )

    assert embed.to_dict()["thumbnail"]["url"] == "attachment://thumb.png"
    assert "image" not in embed.to_dict()


def test_resolve_uploaded_thumbnail_returns_local_attachment(tmp_path: Path) -> None:
    uploads_dir = tmp_path / "uploads"
    thumbnail = uploads_dir / "embed-thumbnails" / "guild" / "thumb.png"
    thumbnail.parent.mkdir(parents=True)
    thumbnail.write_bytes(b"fake image bytes")

    attachment = resolve_uploaded_thumbnail(
        "/uploads/embed-thumbnails/guild/thumb.png",
        uploads_dir=str(uploads_dir),
    )

    assert attachment is not None
    assert attachment.path == thumbnail.resolve()
    assert attachment.filename == "thumb.png"


def test_resolve_uploaded_thumbnail_rejects_path_escape(tmp_path: Path) -> None:
    uploads_dir = tmp_path / "uploads"
    uploads_dir.mkdir()
    (tmp_path / "outside.png").write_bytes(b"fake image bytes")

    attachment = resolve_uploaded_thumbnail("/uploads/../outside.png", uploads_dir=str(uploads_dir))

    assert attachment is None
