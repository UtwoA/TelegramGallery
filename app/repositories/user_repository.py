from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import User


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_or_create_web_user(self) -> User:
        user = self.db.scalar(select(User).where(User.username == "web-admin"))
        if user:
            return user

        user = User(username="web-admin", display_name="Web Admin")
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def get_or_create_telegram_user(self, telegram_id: int, username: str | None, display_name: str | None) -> User:
        user = self.db.scalar(select(User).where(User.telegram_id == telegram_id))
        if user:
            if username and user.username != username:
                user.username = username
            if display_name and user.display_name != display_name:
                user.display_name = display_name
            self.db.commit()
            self.db.refresh(user)
            return user

        user = User(
            telegram_id=telegram_id,
            username=username,
            display_name=display_name or username or f"tg-{telegram_id}",
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user
