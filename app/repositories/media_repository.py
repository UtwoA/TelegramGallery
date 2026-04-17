from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models import MediaFile


class MediaRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, media: MediaFile) -> MediaFile:
        self.db.add(media)
        self.db.commit()
        self.db.refresh(media)
        return media

    def save(self, media: MediaFile) -> MediaFile:
        self.db.add(media)
        self.db.commit()
        self.db.refresh(media)
        return media

    def delete(self, media: MediaFile) -> None:
        self.db.delete(media)
        self.db.commit()

    def by_uuid(self, media_uuid: str) -> MediaFile | None:
        return self.db.scalar(
            select(MediaFile)
            .where(MediaFile.uuid == media_uuid)
            .options(selectinload(MediaFile.tags), selectinload(MediaFile.category), selectinload(MediaFile.place))
        )

    def by_uuids(self, media_uuids: list[str]) -> list[MediaFile]:
        if not media_uuids:
            return []
        query = (
            select(MediaFile)
            .where(MediaFile.uuid.in_(media_uuids))
            .options(selectinload(MediaFile.tags), selectinload(MediaFile.category), selectinload(MediaFile.place))
        )
        return list(self.db.scalars(query).all())

    def exists_by_filename_and_category(self, filename: str, category_id: int | None) -> bool:
        query = select(MediaFile.id).where(MediaFile.original_filename == filename)
        if category_id is None:
            query = query.where(MediaFile.category_id.is_(None))
        else:
            query = query.where(MediaFile.category_id == category_id)
        return self.db.scalar(query) is not None

    def list_gallery(
        self,
        category_id: int | None = None,
        sort: str = "uploaded_desc",
        include_decorative: bool = False,
        landing_only: bool = False,
        uncategorized_only: bool = False,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[MediaFile]:
        # Lightweight query for gallery pages: relationships are not required there
        # and selectinload on big datasets significantly slows down rendering.
        query = select(MediaFile)
        if not include_decorative:
            query = query.where(MediaFile.is_decorative.is_(False))
        if landing_only:
            query = query.where(MediaFile.show_on_landing.is_(True))
        if uncategorized_only:
            query = query.where(MediaFile.category_id.is_(None))
        elif category_id:
            query = query.where(MediaFile.category_id == category_id)

        if sort == "uploaded_asc":
            query = query.order_by(MediaFile.uploaded_at.asc())
        elif sort == "shot_desc":
            query = query.order_by(MediaFile.shot_at.desc().nullslast(), MediaFile.uploaded_at.desc())
        elif sort == "shot_asc":
            query = query.order_by(MediaFile.shot_at.asc().nullslast(), MediaFile.uploaded_at.desc())
        else:
            query = query.order_by(MediaFile.display_order.asc(), MediaFile.uploaded_at.desc())

        if offset > 0:
            query = query.offset(offset)
        if limit and limit > 0:
            query = query.limit(limit)

        return list(self.db.scalars(query).all())

    def count_gallery(
        self,
        category_id: int | None = None,
        include_decorative: bool = False,
        landing_only: bool = False,
        uncategorized_only: bool = False,
    ) -> int:
        query = select(func.count(MediaFile.id))
        if not include_decorative:
            query = query.where(MediaFile.is_decorative.is_(False))
        if landing_only:
            query = query.where(MediaFile.show_on_landing.is_(True))
        if uncategorized_only:
            query = query.where(MediaFile.category_id.is_(None))
        elif category_id:
            query = query.where(MediaFile.category_id == category_id)
        return int(self.db.scalar(query) or 0)

    def list_decorative(self, usage: str | None = None, limit: int | None = None) -> list[MediaFile]:
        query = (
            select(MediaFile)
            .where(MediaFile.is_decorative.is_(True), MediaFile.show_on_landing.is_(True))
            .order_by(MediaFile.display_order.asc(), MediaFile.uploaded_at.desc())
        )
        if usage:
            query = query.where(MediaFile.decor_usage == usage)
        if limit and limit > 0:
            query = query.limit(limit)
        return list(self.db.scalars(query).all())
