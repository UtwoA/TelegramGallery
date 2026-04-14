from datetime import datetime

from pydantic import BaseModel


class MediaUpdateSchema(BaseModel):
    title: str | None = None
    description: str | None = None
    category_id: int | None = None
    tags: list[str] = []
    place_name: str | None = None
    place_city: str | None = None
    place_country: str | None = None
    shot_at: datetime | None = None
