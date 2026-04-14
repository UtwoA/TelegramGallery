# TelegramGallery

`TelegramGallery` — семейный pet-проект: Telegram-бот + веб-приложение для загрузки, хранения, просмотра и организации фото/видео.

## Что реализовано

- FastAPI веб-приложение с Jinja2 UI
- SQLite + SQLAlchemy + Alembic
- Локальное хранение файлов: `original`, `optimized`, `thumbnail`
- Загрузка медиа через веб (обычная + drag-and-drop)
- Storytelling landing page (главная) + отдельная страница `Все фото`
- Галерея/карточки разделов и страница отдельного файла
- Редактирование метаданных: `title`, `description`, `category`, `tags`, `place`, `shot_at`
- Массовое управление на странице `Все фото` (категория, теги, дата съемки, показ на лендинге)
- Storytelling-поля: порядок/intro секций, декоративные изображения, флаг показа на лендинге
- Фильтрация по категории и сортировка
- Telegram-бот (aiogram): `/start`, прием фото и видео
- Общая бизнес-логика обработки медиа для веба и бота
- Авторизация по логину/паролю для доступа к сайту
- Rate-limit на попытки входа (`IP + username`)

## Стек

- Python 3.12+
- FastAPI
- SQLAlchemy + Alembic
- Pydantic
- Jinja2
- aiogram
- Pillow
- imageio-ffmpeg (ffmpeg backend для видео)
- pillow-heif (поддержка HEIC/HEIF с iPhone)

## Структура проекта

```text
app/
  bot/
  core/
  models/
  repositories/
  schemas/
  services/
  static/
  templates/
  utils/
  web/
alembic/
  versions/
data/
  media/
```

## Быстрый запуск

1. Установить зависимости:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Создать `.env`:

```bash
cp .env.example .env
```

3. Накатить миграции:

```bash
alembic upgrade head
```

4. Запустить веб:

```bash
uvicorn app.main:app --reload
```

Открыть: `http://127.0.0.1:8000`

5. (Опционально) Запустить Telegram-бота:

- заполните `TG_TELEGRAM_BOT_TOKEN` в `.env`

```bash
python -m app.bot.runner
```

## Запуск в Docker (рекомендуется для сервера)

1. Подготовить окружение:

```bash
cp .env.example .env
```

2. Построить образ:

```bash
docker compose build
```

3. Запустить веб-приложение:

```bash
docker compose up -d web
```

Веб внутри сервера будет доступен на `127.0.0.1:${TG_WEB_HOST_PORT}` (по умолчанию `18000`, снаружи закрыт, доступ через Nginx).

4. Запустить Telegram-бота (опционально):

- заполните `TG_TELEGRAM_BOT_TOKEN` в `.env`

```bash
docker compose --profile bot up -d bot
```

5. Полезные команды:

```bash
# логи веба
docker compose logs -f web

# логи бота
docker compose --profile bot logs -f bot

# остановка
docker compose down
```

Данные сохраняются в `./data` на хосте (SQLite БД + медиафайлы), поэтому переживают пересоздание контейнеров.

## Деплой с Nginx на субдомен (пример: `seoul.utwoa.ru`)

1. Убедитесь, что DNS `A` запись `seoul.utwoa.ru` указывает на IP VPS.

2. Запустите приложение:

```bash
docker compose up -d web
```

По умолчанию хост-порт: `18000`. Можно изменить в `.env`:

```env
TG_WEB_HOST_PORT=18000
```

3. Установите nginx-конфиг из репозитория:

```bash
sudo cp deploy/nginx/seoul.utwoa.ru.conf /etc/nginx/sites-available/seoul.utwoa.ru
sudo ln -s /etc/nginx/sites-available/seoul.utwoa.ru /etc/nginx/sites-enabled/seoul.utwoa.ru
sudo nginx -t
sudo systemctl reload nginx
```

Если меняете `TG_WEB_HOST_PORT`, обновите в nginx `proxy_pass` на тот же порт.

4. Выпустите HTTPS сертификат:

```bash
sudo certbot --nginx -d seoul.utwoa.ru
```

5. Проверка:

- `https://seoul.utwoa.ru` открывается
- `docker compose logs -f web` не содержит ошибок

## Доступ к сайту

Для доступа к страницам нужен вход:

- URL: `/login`
- Логин: `TG_ADMIN_USERNAME` из `.env`
- Пароль: `TG_ADMIN_PASSWORD` из `.env`

Параметры rate-limit на вход:

- `TG_LOGIN_RATE_LIMIT_ATTEMPTS` — число попыток в окне
- `TG_LOGIN_RATE_LIMIT_WINDOW_SECONDS` — размер окна в секундах
- `TG_LOGIN_RATE_LIMIT_BLOCK_SECONDS` — блокировка после превышения

## Ограничение размера и HEIC

- `TG_MAX_UPLOAD_SIZE_MB` ограничивает размер одного загружаемого файла.
- Чтобы убрать ограничение, установите `TG_MAX_UPLOAD_SIZE_MB=0`.
- Фото в формате HEIC/HEIF (iPhone) поддерживаются и автоматически конвертируются в web-версии (`optimized/thumbnail` в JPEG).

## Структура просмотра

- `/` — витринный storytelling landing page (разделы истории, teaser-сетка, раскрытие секций)
- `/all-photos` — функциональная страница со всеми фото/видео (разделы уже раскрыты)
- `/story/{uuid}` — отдельная страница конкретного медиа

## Видео-обработка и fallback

Для видео используется `imageio-ffmpeg` (бинарник ffmpeg подтягивается пакетом автоматически).

- если backend доступен: создается `thumbnail` и web-optimized `.mp4`
- если backend недоступен или обработка не удалась: оригинал сохраняется, запись помечается как `partial`, и файл все равно доступен в галерее

Примечание: если `imageio-ffmpeg` не сможет получить бинарник, сервис пробует системный `ffmpeg` как резервный вариант.

## Полезные команды

```bash
# создать новую миграцию (после изменений моделей)
alembic revision --autogenerate -m "update schema"

# применить миграции
alembic upgrade head
```

## Примечания

- Проект намеренно без overengineering: без брокеров, очередей, микросервисов.
- Основная цель: простой и надежный self-hosted семейный медиахаб.
