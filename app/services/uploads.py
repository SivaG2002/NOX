import re
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from starlette.datastructures import UploadFile

ALLOWED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
ALLOWED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/webp"}
MAX_UPLOAD_BYTES = 5 * 1024 * 1024
UPLOAD_URL_PREFIX = "/uploads"


class UploadValidationError(ValueError):
    pass


@dataclass(frozen=True)
class UploadedThumbnailAttachment:
    path: Path
    filename: str


def _safe_name(filename: str | None) -> tuple[str, str]:
    original = Path(filename or "thumbnail").name
    suffix = Path(original).suffix.lower()
    if suffix not in ALLOWED_IMAGE_EXTENSIONS:
        raise UploadValidationError("Thumbnail must be a PNG, JPG, JPEG, or WEBP image.")

    stem = Path(original).stem
    stem = re.sub(r"[^A-Za-z0-9_.-]+", "-", stem).strip(".-")[:80]
    return stem or "thumbnail", suffix


def _safe_guild_dir_name(guild_id: str) -> str:
    return re.sub(r"[^0-9A-Za-z_-]+", "", str(guild_id)) or "guild"


def _is_under_directory(path: Path, directory: Path) -> bool:
    try:
        path.relative_to(directory)
    except ValueError:
        return False
    return True


def _looks_like_image(header: bytes, suffix: str) -> bool:
    if suffix == ".png":
        return header.startswith(b"\x89PNG\r\n\x1a\n")
    if suffix in {".jpg", ".jpeg"}:
        return header.startswith(b"\xff\xd8\xff")
    if suffix == ".webp":
        return len(header) >= 12 and header[:4] == b"RIFF" and header[8:12] == b"WEBP"
    return False


async def save_custom_thumbnail(
    upload: UploadFile,
    *,
    guild_id: str,
    uploads_dir: str,
) -> str:
    stem, suffix = _safe_name(upload.filename)
    content_type = (upload.content_type or "").lower()
    if content_type and content_type not in ALLOWED_IMAGE_TYPES:
        raise UploadValidationError("Thumbnail must be a PNG, JPG, JPEG, or WEBP image.")

    root = Path(uploads_dir).resolve()
    target_dir = (root / "embed-thumbnails" / _safe_guild_dir_name(guild_id)).resolve()
    if not _is_under_directory(target_dir, root):
        raise UploadValidationError("Invalid upload destination.")
    target_dir.mkdir(parents=True, exist_ok=True)

    destination = (target_dir / f"{uuid4().hex}-{stem}{suffix}").resolve()
    if not _is_under_directory(destination, root):
        raise UploadValidationError("Invalid upload destination.")

    total = 0
    header = b""
    try:
        with destination.open("wb") as output:
            while chunk := await upload.read(1024 * 1024):
                total += len(chunk)
                if total > MAX_UPLOAD_BYTES:
                    raise UploadValidationError("Thumbnail must be 5 MB or smaller.")
                if len(header) < 16:
                    header += chunk[: 16 - len(header)]
                output.write(chunk)
    except Exception:
        destination.unlink(missing_ok=True)
        raise

    if total == 0:
        destination.unlink(missing_ok=True)
        raise UploadValidationError("Thumbnail image cannot be empty.")
    if not _looks_like_image(header, suffix):
        destination.unlink(missing_ok=True)
        raise UploadValidationError("Thumbnail file contents do not match the image type.")

    relative_path = destination.relative_to(root).as_posix()
    return f"{UPLOAD_URL_PREFIX}/{relative_path}"


def delete_uploaded_thumbnail(url: str | None, *, uploads_dir: str) -> None:
    if not url or not url.startswith(f"{UPLOAD_URL_PREFIX}/"):
        return

    root = Path(uploads_dir).resolve()
    relative_url_path = url.removeprefix(f"{UPLOAD_URL_PREFIX}/")
    candidate = (root / relative_url_path).resolve()
    if not _is_under_directory(candidate, root) or not candidate.is_file():
        return
    candidate.unlink(missing_ok=True)


def resolve_uploaded_thumbnail(
    url: str | None,
    *,
    uploads_dir: str,
) -> UploadedThumbnailAttachment | None:
    if not url or not url.startswith(f"{UPLOAD_URL_PREFIX}/"):
        return None

    root = Path(uploads_dir).resolve()
    relative_url_path = url.removeprefix(f"{UPLOAD_URL_PREFIX}/")
    candidate = (root / relative_url_path).resolve()
    if not _is_under_directory(candidate, root) or not candidate.is_file():
        return None
    return UploadedThumbnailAttachment(path=candidate, filename=candidate.name)
