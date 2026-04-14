import asyncio
import io
import logging

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message

from app.core.config import settings
from app.core.db import SessionLocal
from app.repositories.user_repository import UserRepository
from app.services.media_service import MediaCreatePayload, MediaService

logger = logging.getLogger(__name__)


dp = Dispatcher()
_album_counts: dict[tuple[int, str], int] = {}
_album_tasks: dict[tuple[int, str], asyncio.Task] = {}
_album_lock = asyncio.Lock()


@dp.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        "Привет! Отправь фото или видео, и я добавлю его в семейную галерею TelegramGallery."
    )


@dp.message(F.photo)
async def on_photo(message: Message, bot: Bot):
    photo = message.photo[-1]
    file = await bot.get_file(photo.file_id)
    buf = io.BytesIO()
    await bot.download(file, destination=buf)

    filename = f"photo_{photo.file_unique_id}.jpg"
    await _store_telegram_media(message, filename, buf.getvalue(), "image/jpeg")


@dp.message(F.video)
async def on_video(message: Message, bot: Bot):
    video = message.video
    if not video:
        return

    file = await bot.get_file(video.file_id)
    buf = io.BytesIO()
    await bot.download(file, destination=buf)

    filename = video.file_name or f"video_{video.file_unique_id}.mp4"
    await _store_telegram_media(message, filename, buf.getvalue(), video.mime_type or "video/mp4")


async def _store_telegram_media(message: Message, filename: str, data: bytes, mime_type: str):
    if not message.from_user:
        await message.answer("Не удалось определить пользователя.")
        return

    db = SessionLocal()
    try:
        user_repo = UserRepository(db)
        media_service = MediaService(db)

        tg_user = message.from_user
        owner = user_repo.get_or_create_telegram_user(
            telegram_id=tg_user.id,
            username=tg_user.username,
            display_name=tg_user.full_name,
        )

        payload = MediaCreatePayload(
            filename=filename,
            bytes_data=data,
            mime_type=mime_type,
            description=None,
        )
        media_service.create_media(owner, payload)
        await _ack_success(message)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to process telegram media")
        await message.answer(f"Не удалось обработать файл: {exc}")
    finally:
        db.close()


async def _ack_success(message: Message) -> None:
    chat = message.chat
    group_id = message.media_group_id

    if not chat or not group_id:
        await message.answer("Готово! Добавлено 1 файл")
        return

    key = (chat.id, group_id)
    async with _album_lock:
        _album_counts[key] = _album_counts.get(key, 0) + 1
        existing_task = _album_tasks.get(key)
        if existing_task and not existing_task.done():
            existing_task.cancel()
        _album_tasks[key] = asyncio.create_task(_flush_album_ack(message, key))


async def _flush_album_ack(message: Message, key: tuple[int, str]) -> None:
    try:
        await asyncio.sleep(1.1)
        async with _album_lock:
            count = _album_counts.pop(key, 0)
            _album_tasks.pop(key, None)
        if count > 0:
            suffix = "файл" if count == 1 else "файлов"
            await message.answer(f"Готово! Добавлено {count} {suffix}")
    except asyncio.CancelledError:
        return


async def main() -> None:
    if not settings.telegram_bot_token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not configured")

    logging.basicConfig(level=logging.INFO)
    bot = Bot(settings.telegram_bot_token)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
