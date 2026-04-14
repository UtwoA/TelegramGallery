import mimetypes
from pathlib import Path

from app.models.enums import MediaType

ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".mov", ".m4v", ".webm", ".avi", ".mkv"}


def guess_mime(filename: str, explicit_mime: str | None = None) -> str:
    if explicit_mime and explicit_mime != "application/octet-stream":
        return explicit_mime
    guessed, _ = mimetypes.guess_type(filename)
    return guessed or "application/octet-stream"


def detect_media_type(filename: str, mime_type: str) -> MediaType | None:
    ext = Path(filename).suffix.lower()
    if mime_type.startswith("image/") or ext in ALLOWED_IMAGE_EXTENSIONS:
        return MediaType.IMAGE
    if mime_type.startswith("video/") or ext in ALLOWED_VIDEO_EXTENSIONS:
        return MediaType.VIDEO
    return None


def extension_for_original(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    return ext if ext else ".bin"
