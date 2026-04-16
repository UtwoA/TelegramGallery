from __future__ import annotations

import argparse
import shutil
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from app.core.db import SessionLocal
from app.repositories.media_repository import MediaRepository
from app.repositories.taxonomy_repository import TaxonomyRepository
from app.repositories.user_repository import UserRepository
from app.services.media_service import MediaCreatePayload, MediaService
from app.services.storage_service import storage_service
from app.utils.media_utils import detect_media_type, extension_for_original, guess_mime


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import media from date-based folders into TelegramGallery categories."
    )
    parser.add_argument(
        "--source",
        required=True,
        help="Path to root folder containing dated subfolders, e.g. /media/utowa/AMOGUSMONST/2026",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Scan and print what would be imported without writing to DB/storage.",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip file if same filename already exists in the same category.",
    )
    parser.add_argument(
        "--no-process",
        action="store_true",
        help="Do not generate optimized/thumbnail now (keep status pending).",
    )
    return parser.parse_args()


def iter_media_files(folder: Path) -> list[Path]:
    files: list[Path] = []
    for child in sorted(folder.iterdir()):
        if not child.is_file():
            continue
        mime = guess_mime(child.name, None)
        if detect_media_type(child.name, mime) is None:
            continue
        files.append(child)
    return files


def parse_shot_at_from_folder(folder_name: str) -> datetime | None:
    try:
        return datetime.fromisoformat(folder_name)
    except ValueError:
        return None


def ensure_category(
    taxonomy_repo: TaxonomyRepository,
    folder_name: str,
    sort_order: int,
) -> int:
    existing = taxonomy_repo.get_category_by_name(folder_name)
    if existing:
        return existing.id
    created = taxonomy_repo.create_category(
        name=folder_name,
        description=f"Импорт из папки {folder_name}",
        story_intro=f"Моменты дня {folder_name}",
        sort_order=sort_order,
        show_on_landing=True,
    )
    return created.id


def main() -> None:
    args = parse_args()
    source_root = Path(args.source).expanduser().resolve()
    if not source_root.exists() or not source_root.is_dir():
        raise SystemExit(f"Source folder not found: {source_root}")

    date_dirs = [d for d in sorted(source_root.iterdir()) if d.is_dir() and not d.name.startswith(".")]
    if not date_dirs:
        raise SystemExit(f"No dated subfolders found in: {source_root}")

    db = SessionLocal()
    try:
        user = UserRepository(db).get_or_create_web_user()
        media_service = MediaService(db)
        media_repo = MediaRepository(db)
        taxonomy_repo = TaxonomyRepository(db)

        imported = 0
        skipped = 0
        failed = 0

        for idx, day_dir in enumerate(date_dirs, start=1):
            category_id = ensure_category(taxonomy_repo, day_dir.name, sort_order=idx * 10)
            shot_at = parse_shot_at_from_folder(day_dir.name)

            media_files = iter_media_files(day_dir)
            print(f"[{day_dir.name}] found {len(media_files)} supported files")

            for file_path in media_files:
                if args.skip_existing and media_repo.exists_by_filename_and_category(file_path.name, category_id):
                    skipped += 1
                    continue

                if args.dry_run:
                    print(f"  DRY-RUN import: {file_path.name} -> category {day_dir.name}")
                    imported += 1
                    continue

                try:
                    media_uuid = str(uuid4())
                    ext = extension_for_original(file_path.name)
                    original_rel = storage_service.relative_for("originals", media_uuid, ext)
                    original_abs = storage_service.absolute_path(original_rel)
                    original_abs.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(file_path, original_abs)

                    payload = MediaCreatePayload(
                        filename=file_path.name,
                        mime_type=guess_mime(file_path.name, None),
                        category_id=category_id,
                        shot_at=shot_at,
                    )
                    media_service.create_media_from_existing_original(
                        owner=user,
                        payload=payload,
                        original_rel=original_rel,
                        original_abs=original_abs,
                        process_now=not args.no_process,
                    )
                    imported += 1
                except Exception as exc:  # noqa: BLE001
                    failed += 1
                    print(f"  FAILED {file_path.name}: {exc}")

        print(
            f"Done. imported={imported} skipped={skipped} failed={failed} "
            f"process_now={'no' if args.no_process else 'yes'} dry_run={'yes' if args.dry_run else 'no'}"
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
