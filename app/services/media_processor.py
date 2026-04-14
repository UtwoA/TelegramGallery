import subprocess
from pathlib import Path

from imageio_ffmpeg import get_ffmpeg_exe
from PIL import Image, ImageOps


class MediaProcessor:
    def __init__(self) -> None:
        self.ffmpeg_bin = self._resolve_ffmpeg_bin()

    def process_image(self, original: Path, optimized: Path, thumbnail: Path) -> tuple[bool, str | None]:
        try:
            optimized.parent.mkdir(parents=True, exist_ok=True)
            thumbnail.parent.mkdir(parents=True, exist_ok=True)

            with Image.open(original) as img:
                img = ImageOps.exif_transpose(img)
                if img.mode not in ("RGB", "L"):
                    img = img.convert("RGB")

                optimized_img = img.copy()
                optimized_img.thumbnail((1920, 1920))
                optimized_img.save(optimized, format="JPEG", quality=86, optimize=True)

                thumb = ImageOps.fit(img, (480, 480), method=Image.Resampling.LANCZOS)
                if thumb.mode != "RGB":
                    thumb = thumb.convert("RGB")
                thumb.save(thumbnail, format="JPEG", quality=82, optimize=True)
            return True, None
        except Exception as exc:  # noqa: BLE001
            return False, str(exc)

    def process_video(
        self,
        original: Path,
        optimized: Path,
        thumbnail: Path,
    ) -> tuple[bool, bool, str | None]:
        """Returns: optimized_created, thumbnail_created, error_message."""
        optimized.parent.mkdir(parents=True, exist_ok=True)
        thumbnail.parent.mkdir(parents=True, exist_ok=True)

        thumb_ok = self._run(
            [
                self.ffmpeg_bin,
                "-y",
                "-i",
                str(original),
                "-ss",
                "00:00:01",
                "-frames:v",
                "1",
                str(thumbnail),
            ]
        )

        opt_ok = self._run(
            [
                self.ffmpeg_bin,
                "-y",
                "-i",
                str(original),
                "-vf",
                "scale='min(1280,iw)':-2",
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-crf",
                "28",
                "-c:a",
                "aac",
                "-movflags",
                "+faststart",
                str(optimized),
            ]
        )

        if not thumb_ok and not opt_ok:
            return False, False, "video processing failed (ffmpeg backend unavailable or errored)"
        return opt_ok, thumb_ok, None

    @staticmethod
    def _resolve_ffmpeg_bin() -> str:
        try:
            return get_ffmpeg_exe()
        except Exception:  # noqa: BLE001
            # Fallback to system ffmpeg if imageio-ffmpeg cannot resolve bundled binary.
            return "ffmpeg"

    def _run(self, cmd: list[str]) -> bool:
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
            return proc.returncode == 0
        except FileNotFoundError:
            return False


media_processor = MediaProcessor()
