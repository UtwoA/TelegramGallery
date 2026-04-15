from collections import defaultdict
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from slugify import slugify
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import get_db
from app.models import Category, MediaFile, MediaStatus
from app.repositories.media_repository import MediaRepository
from app.repositories.taxonomy_repository import TaxonomyRepository
from app.repositories.user_repository import UserRepository
from app.services.media_processor import media_processor
from app.services.media_service import MediaCreatePayload, MediaService
from app.services.storage_service import storage_service
from app.web.auth import admin_guard, auth_guard, get_client_ip, is_admin, is_authenticated
from app.web.login_rate_limiter import login_rate_limiter

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


SORT_OPTIONS = {
    "uploaded_desc": "Сначала новые",
    "uploaded_asc": "Сначала старые",
    "shot_desc": "Сначала новые по дате съемки",
    "shot_asc": "Сначала старые по дате съемки",
}


DECOR_USAGE_CHOICES = [
    ("", "Нет"),
    ("hero_background", "Hero background"),
    ("section_divider", "Section divider"),
    ("mood", "Mood image"),
    ("section_background", "Section background"),
]


SECTION_FALLBACK_NAMES = [
    "Прибытие",
    "Первые прогулки",
    "Улицы",
    "Кафе",
    "Вечерний Сеул",
    "Достопримечательности",
    "Случайные моменты",
    "Финал поездки",
]


def media_preview_path(media: MediaFile) -> str:
    if media.thumbnail_path:
        return f"/media/{media.thumbnail_path}"
    if media.media_type.value == "video":
        return "/static/img/video-placeholder.svg"
    if media.optimized_path:
        return f"/media/{media.optimized_path}"
    return f"/media/{media.original_path}"


def media_display_path(media: MediaFile) -> str:
    if media.optimized_path:
        return f"/media/{media.optimized_path}"
    return f"/media/{media.original_path}"


IMAGE_OPERATIONS = {
    "rotate_left",
    "rotate_right",
    "flip_horizontal",
    "flip_vertical",
    "grayscale",
    "enhance",
}


def media_public_path(media: MediaFile | None) -> str | None:
    if not media:
        return None
    return media_preview_path(media)


def _bool_from_form(value: str | None) -> bool:
    return value in {"1", "true", "on", "yes"}


def _parse_optional_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _parse_optional_int(value: str | None) -> int | None:
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    try:
        return int(cleaned)
    except ValueError:
        return None


def _build_story_sections(categories: list[Category], media_items: list[MediaFile]) -> list[dict[str, Any]]:
    grouped: dict[int | None, list[MediaFile]] = defaultdict(list)
    for item in media_items:
        grouped[item.category_id].append(item)

    sections: list[dict[str, Any]] = []
    accent_cycle = ["coral", "teal", "orange", "rose", "moss"]

    visible_idx = 0
    for category in categories:
        if not category.show_on_landing:
            continue
        items = grouped.get(category.id, [])
        if not items:
            continue

        intro = category.story_intro or category.description or "Еще одна часть путешествия в кадрах."
        sections.append(
            {
                "id": slugify(category.name),
                "title": category.name,
                "intro": intro,
                "media_items": items,
                "preview_items": items[:5],
                "hidden_count": max(0, len(items) - 5),
                "accent": accent_cycle[visible_idx % len(accent_cycle)],
            }
        )
        visible_idx += 1

    uncategorized = grouped.get(None, [])
    if uncategorized:
        fallback_title = SECTION_FALLBACK_NAMES[min(len(sections), len(SECTION_FALLBACK_NAMES) - 1)]
        sections.append(
            {
                "id": "uncategorized",
                "title": fallback_title,
                "intro": "Свободные моменты поездки без жесткой структуры.",
                "media_items": uncategorized,
                "preview_items": uncategorized[:5],
                "hidden_count": max(0, len(uncategorized) - 5),
                "accent": accent_cycle[visible_idx % len(accent_cycle)],
            }
        )

    return sections


@router.get("/", response_class=HTMLResponse)
def landing_page(request: Request, db: Session = Depends(get_db)):
    guard = auth_guard(request)
    if guard:
        return guard

    media_repo = MediaRepository(db)
    taxonomy_repo = TaxonomyRepository(db)

    categories = taxonomy_repo.list_categories()
    media_items = media_repo.list_gallery(sort="uploaded_desc", include_decorative=False, landing_only=True)
    sections = _build_story_sections(categories, media_items)

    decorative = media_repo.list_decorative()
    hero_bg = next((m for m in decorative if m.decor_usage == "hero_background"), None)
    if hero_bg is None and decorative:
        hero_bg = decorative[0]

    mood_images = [m for m in decorative if m.decor_usage in {"mood", "section_divider"}]

    return templates.TemplateResponse(
        request,
        "landing.html",
        {
            "sections": sections,
            "hero_bg": hero_bg,
            "mood_images": mood_images,
            "is_admin": is_admin(request),
            "preview_path": media_preview_path,
            "public_path": media_public_path,
            "total_count": len(media_items),
        },
    )


@router.get("/all-photos", response_class=HTMLResponse)
def all_photos_page(
    request: Request,
    category_id: str | None = None,
    sort: str = "uploaded_desc",
    db: Session = Depends(get_db),
):
    guard = auth_guard(request)
    if guard:
        return guard

    media_repo = MediaRepository(db)
    taxonomy_repo = TaxonomyRepository(db)

    if sort not in SORT_OPTIONS:
        sort = "uploaded_desc"

    parsed_category_id = _parse_optional_int(category_id)

    media_items = media_repo.list_gallery(
        category_id=parsed_category_id,
        sort=sort,
        include_decorative=False,
        landing_only=False,
    )
    categories = taxonomy_repo.list_categories()
    sections = _build_story_sections(categories, media_items)

    return templates.TemplateResponse(
        request,
        "all_photos.html",
        {
            "sections": sections,
            "categories": categories,
            "selected_category_id": parsed_category_id,
            "sort": sort,
            "sort_options": SORT_OPTIONS,
            "is_admin": is_admin(request),
            "preview_path": media_preview_path,
            "total_count": len(media_items),
        },
    )


@router.post("/all-photos/bulk-update")
async def bulk_update_media(
    request: Request,
    media_ids: list[str] = Form(default=[]),
    category_action: str = Form(default="no_change"),
    category_id: str | None = Form(default=None),
    tags_action: str = Form(default="no_change"),
    tags: str | None = Form(default=None),
    shot_at_action: str = Form(default="no_change"),
    shot_at: str | None = Form(default=None),
    show_on_landing_action: str = Form(default="no_change"),
    db: Session = Depends(get_db),
):
    guard = admin_guard(request)
    if guard:
        return guard

    media_repo = MediaRepository(db)
    taxonomy_repo = TaxonomyRepository(db)

    unique_ids = list(dict.fromkeys(media_ids))
    media_items = media_repo.by_uuids(unique_ids)
    if not media_items:
        return RedirectResponse(url="/all-photos?bulk_error=1", status_code=303)

    parsed_tags = [item.strip() for item in (tags or "").split(",") if item.strip()]
    tag_entities = taxonomy_repo.find_or_create_tags(parsed_tags) if parsed_tags else []

    parsed_shot_at = _parse_optional_datetime(shot_at)
    parsed_category_id = _parse_optional_int(category_id)

    for media in media_items:
        if category_action == "set":
            media.category_id = parsed_category_id
        elif category_action == "clear":
            media.category_id = None

        if tags_action == "add" and tag_entities:
            existing_ids = {tag.id for tag in media.tags}
            media.tags = media.tags + [tag for tag in tag_entities if tag.id not in existing_ids]
        elif tags_action == "replace":
            media.tags = tag_entities
        elif tags_action == "clear":
            media.tags = []

        if shot_at_action == "set":
            media.shot_at = parsed_shot_at
        elif shot_at_action == "clear":
            media.shot_at = None

        if show_on_landing_action == "show":
            media.show_on_landing = True
        elif show_on_landing_action == "hide":
            media.show_on_landing = False

        media_repo.save(media)

    return RedirectResponse(url=f"/all-photos?bulk_saved={len(media_items)}", status_code=303)


@router.get("/upload", response_class=HTMLResponse)
def upload_page(request: Request, db: Session = Depends(get_db)):
    guard = admin_guard(request)
    if guard:
        return guard

    categories = TaxonomyRepository(db).list_categories()
    return templates.TemplateResponse(
        request,
        "upload.html",
        {"categories": categories, "is_admin": True, "decor_usage_choices": DECOR_USAGE_CHOICES},
    )


@router.post("/upload")
async def upload_files(
    request: Request,
    files: list[UploadFile] = File(...),
    title: str | None = Form(default=None),
    description: str | None = Form(default=None),
    category_id: str | None = Form(default=None),
    tags: str | None = Form(default=None),
    place_name: str | None = Form(default=None),
    place_city: str | None = Form(default=None),
    place_country: str | None = Form(default=None),
    shot_at: str | None = Form(default=None),
    is_decorative: str | None = Form(default=None),
    decor_usage: str | None = Form(default=None),
    show_on_landing: str | None = Form(default=None),
    display_order: int = Form(default=100),
    db: Session = Depends(get_db),
):
    guard = admin_guard(request)
    if guard:
        return guard

    user = UserRepository(db).get_or_create_web_user()
    service = MediaService(db)
    parsed_category_id = _parse_optional_int(category_id)

    uploaded_ids: list[str] = []
    for upload in files:
        content = await upload.read()
        if settings.max_upload_size_mb > 0:
            max_size = settings.max_upload_size_mb * 1024 * 1024
            if len(content) > max_size:
                raise HTTPException(status_code=400, detail=f"File {upload.filename} exceeds size limit")

        parsed_shot_at = None
        if shot_at:
            try:
                parsed_shot_at = datetime.fromisoformat(shot_at)
            except ValueError:
                parsed_shot_at = None

        payload = MediaCreatePayload(
            filename=upload.filename or "file.bin",
            bytes_data=content,
            mime_type=upload.content_type,
            title=title,
            description=description,
            category_id=parsed_category_id,
            tags=[item.strip() for item in (tags or "").split(",") if item.strip()],
            place_name=place_name,
            place_city=place_city,
            place_country=place_country,
            shot_at=parsed_shot_at,
            is_decorative=_bool_from_form(is_decorative),
            decor_usage=decor_usage or None,
            show_on_landing=_bool_from_form(show_on_landing),
            display_order=display_order,
        )
        media = service.create_media(user, payload)
        uploaded_ids.append(media.uuid)

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return {"ok": True, "uploaded": uploaded_ids}

    return RedirectResponse(url="/all-photos?uploaded=1", status_code=303)


@router.get("/story/{media_uuid}", response_class=HTMLResponse)
def media_details(request: Request, media_uuid: str, db: Session = Depends(get_db)):
    guard = auth_guard(request)
    if guard:
        return guard

    media = MediaRepository(db).by_uuid(media_uuid)
    if not media:
        raise HTTPException(status_code=404, detail="Media not found")

    categories = TaxonomyRepository(db).list_categories()
    return templates.TemplateResponse(
        request,
        "media_detail.html",
        {
            "media": media,
            "categories": categories,
            "is_admin": is_admin(request),
            "display_path": media_display_path(media),
            "original_path": f"/media/{media.original_path}",
            "decor_usage_choices": DECOR_USAGE_CHOICES,
        },
    )


@router.post("/story/{media_uuid}/edit")
async def edit_media(
    request: Request,
    media_uuid: str,
    title: str | None = Form(default=None),
    description: str | None = Form(default=None),
    category_id: str | None = Form(default=None),
    tags: str | None = Form(default=None),
    place_name: str | None = Form(default=None),
    place_city: str | None = Form(default=None),
    place_country: str | None = Form(default=None),
    shot_at: str | None = Form(default=None),
    is_decorative: str | None = Form(default=None),
    decor_usage: str | None = Form(default=None),
    show_on_landing: str | None = Form(default=None),
    display_order: int = Form(default=100),
    db: Session = Depends(get_db),
):
    guard = admin_guard(request)
    if guard:
        return guard

    media_repo = MediaRepository(db)
    media = media_repo.by_uuid(media_uuid)
    if not media:
        raise HTTPException(status_code=404, detail="Media not found")

    taxonomy_repo = TaxonomyRepository(db)
    parsed_category_id = _parse_optional_int(category_id)

    media.title = title
    media.description = description
    media.category_id = parsed_category_id

    parsed_shot_at = None
    if shot_at:
        try:
            parsed_shot_at = datetime.fromisoformat(shot_at)
        except ValueError:
            parsed_shot_at = None
    media.shot_at = parsed_shot_at

    media.is_decorative = _bool_from_form(is_decorative)
    media.decor_usage = decor_usage or None
    media.show_on_landing = _bool_from_form(show_on_landing)
    media.display_order = display_order

    if place_name:
        place = taxonomy_repo.find_or_create_place(place_name, city=place_city, country=place_country)
        media.place_id = place.id
    else:
        media.place_id = None

    media.tags = taxonomy_repo.find_or_create_tags([item.strip() for item in (tags or "").split(",") if item.strip()])

    media_repo.save(media)
    return RedirectResponse(url=f"/story/{media_uuid}?saved=1", status_code=303)


@router.post("/story/{media_uuid}/image-action")
async def apply_image_action(
    request: Request,
    media_uuid: str,
    operation: str = Form(...),
    db: Session = Depends(get_db),
):
    guard = admin_guard(request)
    if guard:
        return guard

    if operation not in IMAGE_OPERATIONS:
        return RedirectResponse(url=f"/story/{media_uuid}?image_error=1", status_code=303)

    media_repo = MediaRepository(db)
    media = media_repo.by_uuid(media_uuid)
    if not media:
        raise HTTPException(status_code=404, detail="Media not found")
    if media.media_type.value != "image":
        return RedirectResponse(url=f"/story/{media_uuid}?image_error=1", status_code=303)

    source_rel = media.optimized_path or media.original_path
    source_abs = storage_service.absolute_path(source_rel)
    if not source_abs.exists():
        source_abs = storage_service.absolute_path(media.original_path)
    if not source_abs.exists():
        return RedirectResponse(url=f"/story/{media_uuid}?image_error=1", status_code=303)

    if not media.optimized_path:
        media.optimized_path = storage_service.relative_for("optimized", media.uuid, ".jpg")
    if not media.thumbnail_path:
        media.thumbnail_path = storage_service.relative_for("thumbnails", media.uuid, ".jpg")

    ok, _error = media_processor.apply_image_operation(
        source_image=source_abs,
        optimized=storage_service.absolute_path(media.optimized_path),
        thumbnail=storage_service.absolute_path(media.thumbnail_path),
        operation=operation,
    )
    if not ok:
        media.status = MediaStatus.FAILED
        media_repo.save(media)
        return RedirectResponse(url=f"/story/{media_uuid}?image_error=1", status_code=303)

    media.status = MediaStatus.READY
    media_repo.save(media)
    return RedirectResponse(url=f"/story/{media_uuid}?image_saved=1", status_code=303)


@router.post("/story/{media_uuid}/delete")
async def delete_media(
    request: Request,
    media_uuid: str,
    db: Session = Depends(get_db),
):
    guard = admin_guard(request)
    if guard:
        return guard

    media_repo = MediaRepository(db)
    media = media_repo.by_uuid(media_uuid)
    if not media:
        raise HTTPException(status_code=404, detail="Media not found")

    storage_service.delete_if_exists(media.original_path)
    storage_service.delete_if_exists(media.optimized_path)
    storage_service.delete_if_exists(media.thumbnail_path)

    media.tags = []
    media_repo.delete(media)
    return RedirectResponse(url="/all-photos?deleted=1", status_code=303)


@router.get("/categories", response_class=HTMLResponse)
def categories_page(request: Request, db: Session = Depends(get_db)):
    guard = admin_guard(request)
    if guard:
        return guard

    categories = TaxonomyRepository(db).list_categories()
    return templates.TemplateResponse(
        request,
        "categories.html",
        {"categories": categories, "is_admin": True},
    )


@router.post("/categories")
def create_category(
    request: Request,
    name: str = Form(...),
    description: str | None = Form(default=None),
    story_intro: str | None = Form(default=None),
    sort_order: int = Form(default=100),
    show_on_landing: str | None = Form(default=None),
    db: Session = Depends(get_db),
):
    guard = admin_guard(request)
    if guard:
        return guard

    TaxonomyRepository(db).create_category(
        name=name,
        description=description,
        story_intro=story_intro,
        sort_order=sort_order,
        show_on_landing=_bool_from_form(show_on_landing),
    )
    return RedirectResponse(url="/categories", status_code=303)


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request, next: str | None = None):
    if is_authenticated(request):
        return RedirectResponse(url=next or "/", status_code=303)
    context: dict[str, Any] = {"is_admin": is_admin(request), "next": next or "/"}
    return templates.TemplateResponse(request, "login.html", context)


@router.post("/login")
def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    next: str = Form(default="/"),
):
    bucket_key = f"{get_client_ip(request)}::{username.strip().lower()}"
    blocked, retry_after = login_rate_limiter.is_blocked(bucket_key)
    if blocked:
        return templates.TemplateResponse(
            request,
            "login.html",
            {
                "error": f"Слишком много попыток. Попробуйте через {retry_after} сек.",
                "next": next or "/",
                "is_admin": False,
            },
            status_code=429,
        )

    if username == settings.admin_username and password == settings.admin_password:
        login_rate_limiter.register_success(bucket_key)
        request.session["is_admin"] = True
        return RedirectResponse(url=next or "/", status_code=303)

    attempts_left = login_rate_limiter.register_failure(bucket_key)
    return templates.TemplateResponse(
        request,
        "login.html",
        {
            "error": f"Неверный логин или пароль. Осталось попыток: {attempts_left}",
            "next": next or "/",
            "is_admin": False,
        },
        status_code=400,
    )


@router.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/", status_code=303)
