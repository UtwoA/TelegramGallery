from dataclasses import dataclass
from datetime import datetime
from uuid import uuid4

from sqlalchemy.orm import Session

from app.models import MediaFile, MediaStatus, MediaType, User
from app.repositories.media_repository import MediaRepository
from app.repositories.taxonomy_repository import TaxonomyRepository
from app.services.media_processor import media_processor
from app.services.storage_service import storage_service
from app.utils.media_utils import detect_media_type, extension_for_original, guess_mime


@dataclass
class MediaCreatePayload:
    filename: str
    bytes_data: bytes
    mime_type: str | None = None
    title: str | None = None
    description: str | None = None
    category_id: int | None = None
    tags: list[str] | None = None
    place_name: str | None = None
    place_city: str | None = None
    place_country: str | None = None
    shot_at: datetime | None = None
    is_decorative: bool = False
    decor_usage: str | None = None
    show_on_landing: bool = True
    display_order: int = 100


class MediaService:
    def __init__(self, db: Session):
        self.db = db
        self.media_repo = MediaRepository(db)
        self.taxonomy_repo = TaxonomyRepository(db)

    def create_media(self, owner: User, payload: MediaCreatePayload) -> MediaFile:
        mime_type = guess_mime(payload.filename, payload.mime_type)
        media_type = detect_media_type(payload.filename, mime_type)
        if media_type is None:
            raise ValueError("Unsupported file type")

        media_uuid = str(uuid4())
        ext = extension_for_original(payload.filename)
        original_rel = storage_service.relative_for("originals", media_uuid, ext)
        original_abs = storage_service.save_bytes(original_rel, payload.bytes_data)

        media = MediaFile(
            uuid=media_uuid,
            owner_id=owner.id,
            media_type=media_type,
            mime_type=mime_type,
            original_filename=payload.filename,
            original_path=original_rel,
            title=payload.title,
            description=payload.description,
            category_id=payload.category_id,
            shot_at=payload.shot_at,
            is_decorative=payload.is_decorative,
            decor_usage=payload.decor_usage,
            show_on_landing=payload.show_on_landing,
            display_order=payload.display_order,
            status=MediaStatus.PENDING,
            uploaded_at=datetime.utcnow(),
        )
        media = self.media_repo.add(media)

        if payload.place_name:
            place = self.taxonomy_repo.find_or_create_place(
                payload.place_name,
                city=payload.place_city,
                country=payload.place_country,
            )
            media.place_id = place.id

        if payload.tags:
            media.tags = self.taxonomy_repo.find_or_create_tags(payload.tags)

        if media_type == MediaType.IMAGE:
            optimized_rel = storage_service.relative_for("optimized", media_uuid, ".jpg")
            thumb_rel = storage_service.relative_for("thumbnails", media_uuid, ".jpg")
            ok, error = media_processor.process_image(
                original_abs,
                storage_service.absolute_path(optimized_rel),
                storage_service.absolute_path(thumb_rel),
            )
            if ok:
                media.optimized_path = optimized_rel
                media.thumbnail_path = thumb_rel
                media.status = MediaStatus.READY
            else:
                media.status = MediaStatus.FAILED
                media.description = self._append_processing_error(media.description, error)

        if media_type == MediaType.VIDEO:
            optimized_rel = storage_service.relative_for("optimized", media_uuid, ".mp4")
            thumb_rel = storage_service.relative_for("thumbnails", media_uuid, ".jpg")
            opt_ok, thumb_ok, error = media_processor.process_video(
                original_abs,
                storage_service.absolute_path(optimized_rel),
                storage_service.absolute_path(thumb_rel),
            )
            if opt_ok:
                media.optimized_path = optimized_rel
            if thumb_ok:
                media.thumbnail_path = thumb_rel

            if opt_ok or thumb_ok:
                media.status = MediaStatus.READY if opt_ok and thumb_ok else MediaStatus.PARTIAL
            else:
                media.status = MediaStatus.PARTIAL
                media.description = self._append_processing_error(media.description, error)

        return self.media_repo.save(media)

    @staticmethod
    def _append_processing_error(description: str | None, message: str | None) -> str:
        text = description.strip() if description else ""
        error_msg = (message or "media processing failed").strip()
        if text:
            return f"{text}\n[processing] {error_msg}"
        return f"[processing] {error_msg}"
