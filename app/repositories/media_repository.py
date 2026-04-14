from sqlalchemy import select
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

    def list_gallery(
        self,
        category_id: int | None = None,
        sort: str = "uploaded_desc",
        include_decorative: bool = False,
        landing_only: bool = False,
    ) -> list[MediaFile]:
        query = select(MediaFile).options(
            selectinload(MediaFile.tags), selectinload(MediaFile.category), selectinload(MediaFile.place)
        )
        if not include_decorative:
            query = query.where(MediaFile.is_decorative.is_(False))
        if landing_only:
            query = query.where(MediaFile.show_on_landing.is_(True))
        if category_id:
            query = query.where(MediaFile.category_id == category_id)

        if sort == "uploaded_asc":
            query = query.order_by(MediaFile.uploaded_at.asc())
        elif sort == "shot_desc":
            query = query.order_by(MediaFile.shot_at.desc().nullslast(), MediaFile.uploaded_at.desc())
        elif sort == "shot_asc":
            query = query.order_by(MediaFile.shot_at.asc().nullslast(), MediaFile.uploaded_at.desc())
        else:
            query = query.order_by(MediaFile.display_order.asc(), MediaFile.uploaded_at.desc())

        return list(self.db.scalars(query).all())

    def list_decorative(self, usage: str | None = None) -> list[MediaFile]:
        query = (
            select(MediaFile)
            .where(MediaFile.is_decorative.is_(True), MediaFile.show_on_landing.is_(True))
            .order_by(MediaFile.display_order.asc(), MediaFile.uploaded_at.desc())
        )
        if usage:
            query = query.where(MediaFile.decor_usage == usage)
        return list(self.db.scalars(query).all())
