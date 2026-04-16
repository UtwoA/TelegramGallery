from pathlib import Path

from fastapi import UploadFile

from app.core.config import settings


class StorageService:
    def __init__(self) -> None:
        self.root = settings.media_root

    def ensure_dirs(self) -> None:
        for part in [settings.original_dir, settings.optimized_dir, settings.thumbnail_dir]:
            (self.root / part).mkdir(parents=True, exist_ok=True)

    def absolute_path(self, relative_path: str) -> Path:
        return self.root / relative_path

    def save_bytes(self, relative_path: str, data: bytes) -> Path:
        path = self.absolute_path(relative_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return path

    async def save_upload_stream(
        self,
        relative_path: str,
        upload: UploadFile,
        max_size_bytes: int = 0,
        chunk_size: int = 1024 * 1024,
    ) -> tuple[Path, int]:
        path = self.absolute_path(relative_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        total_size = 0
        with path.open("wb") as dst:
            while True:
                chunk = await upload.read(chunk_size)
                if not chunk:
                    break
                total_size += len(chunk)
                if max_size_bytes > 0 and total_size > max_size_bytes:
                    dst.close()
                    if path.exists():
                        path.unlink()
                    raise ValueError("File exceeds size limit")
                dst.write(chunk)

        await upload.seek(0)
        return path, total_size

    def delete_if_exists(self, relative_path: str | None) -> None:
        if not relative_path:
            return
        path = self.absolute_path(relative_path)
        if path.exists():
            path.unlink()

    def relative_for(self, zone: str, media_uuid: str, ext: str) -> str:
        clean_ext = ext if ext.startswith(".") else f".{ext}"
        return f"{zone}/{media_uuid}{clean_ext}"


storage_service = StorageService()
