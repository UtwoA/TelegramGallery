from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "TelegramGallery"
    debug: bool = False
    secret_key: str = Field(default="change-me-please", min_length=8)

    database_url: str = "sqlite:///./data/telegram_gallery.db"

    media_root: Path = Path("data/media")
    original_dir: str = "originals"
    optimized_dir: str = "optimized"
    thumbnail_dir: str = "thumbnails"

    admin_username: str = "admin"
    admin_password: str = "admin"

    telegram_bot_token: str = ""

    max_upload_size_mb: int = 250
    login_rate_limit_attempts: int = 5
    login_rate_limit_window_seconds: int = 300
    login_rate_limit_block_seconds: int = 600

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="TG_",
        extra="ignore",
    )


settings = Settings()
