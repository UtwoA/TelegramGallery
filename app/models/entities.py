from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.enums import MediaStatus, MediaType, UserRole


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[Optional[int]] = mapped_column(unique=True, index=True, nullable=True)
    username: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    display_name: Mapped[str] = mapped_column(String(128), default="User")
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.FAMILY)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    media_files: Mapped[list["MediaFile"]] = relationship(back_populates="owner")


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(140), unique=True, nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    story_intro: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(default=100)
    show_on_landing: Mapped[bool] = mapped_column(default=True)

    media_files: Mapped[list["MediaFile"]] = relationship(back_populates="category")


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(80), unique=True, nullable=False, index=True)


class Place(Base):
    __tablename__ = "places"
    __table_args__ = (UniqueConstraint("name", "city", "country", name="uq_place_name_city_country"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    slug: Mapped[str] = mapped_column(String(140), index=True, nullable=False)
    country: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    media_files: Mapped[list["MediaFile"]] = relationship(back_populates="place")


class MediaTag(Base):
    __tablename__ = "media_tags"

    media_id: Mapped[int] = mapped_column(ForeignKey("media_files.id", ondelete="CASCADE"), primary_key=True)
    tag_id: Mapped[int] = mapped_column(ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True)


class MediaFile(Base):
    __tablename__ = "media_files"

    id: Mapped[int] = mapped_column(primary_key=True)
    uuid: Mapped[str] = mapped_column(String(36), unique=True, index=True, nullable=False)

    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    media_type: Mapped[MediaType] = mapped_column(Enum(MediaType), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(128), nullable=False)

    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    original_path: Mapped[str] = mapped_column(String(512), nullable=False)
    optimized_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    thumbnail_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_decorative: Mapped[bool] = mapped_column(default=False)
    decor_usage: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    show_on_landing: Mapped[bool] = mapped_column(default=True)
    display_order: Mapped[int] = mapped_column(default=100)

    category_id: Mapped[Optional[int]] = mapped_column(ForeignKey("categories.id"), nullable=True)
    place_id: Mapped[Optional[int]] = mapped_column(ForeignKey("places.id"), nullable=True)
    shot_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    status: Mapped[MediaStatus] = mapped_column(Enum(MediaStatus), default=MediaStatus.PENDING)

    owner: Mapped[User] = relationship(back_populates="media_files")
    category: Mapped[Optional[Category]] = relationship(back_populates="media_files")
    place: Mapped[Optional[Place]] = relationship(back_populates="media_files")
    tags: Mapped[list[Tag]] = relationship("Tag", secondary="media_tags", lazy="selectin")
