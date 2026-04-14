from sqlalchemy import select
from sqlalchemy.orm import Session
from slugify import slugify

from app.models import Category, Place, Tag


class TaxonomyRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_categories(self) -> list[Category]:
        return list(self.db.scalars(select(Category).order_by(Category.sort_order.asc(), Category.name.asc())).all())

    def get_category(self, category_id: int) -> Category | None:
        return self.db.get(Category, category_id)

    def create_category(
        self,
        name: str,
        description: str | None = None,
        story_intro: str | None = None,
        sort_order: int = 100,
        show_on_landing: bool = True,
    ) -> Category:
        slug = slugify(name)
        idx = 1
        while self.db.scalar(select(Category).where(Category.slug == slug)):
            idx += 1
            slug = f"{slugify(name)}-{idx}"

        category = Category(
            name=name.strip(),
            slug=slug,
            description=description,
            story_intro=story_intro,
            sort_order=sort_order,
            show_on_landing=show_on_landing,
        )
        self.db.add(category)
        self.db.commit()
        self.db.refresh(category)
        return category

    def find_or_create_tags(self, names: list[str]) -> list[Tag]:
        result: list[Tag] = []
        for raw_name in names:
            cleaned = raw_name.strip()
            if not cleaned:
                continue
            tag = self.db.scalar(select(Tag).where(Tag.name == cleaned))
            if not tag:
                slug = slugify(cleaned)
                if not slug:
                    continue
                suffix = 1
                base = slug
                while self.db.scalar(select(Tag).where(Tag.slug == slug)):
                    suffix += 1
                    slug = f"{base}-{suffix}"
                tag = Tag(name=cleaned, slug=slug)
                self.db.add(tag)
                self.db.flush()
            result.append(tag)
        self.db.commit()
        for tag in result:
            self.db.refresh(tag)
        return result

    def find_or_create_place(self, name: str, city: str | None = None, country: str | None = None) -> Place:
        existing = self.db.scalar(
            select(Place).where(Place.name == name.strip(), Place.city == city, Place.country == country)
        )
        if existing:
            return existing

        slug = slugify(name)
        place = Place(name=name.strip(), slug=slug, city=city, country=country)
        self.db.add(place)
        self.db.commit()
        self.db.refresh(place)
        return place
