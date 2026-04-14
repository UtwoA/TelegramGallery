from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from app.core.config import settings


@dataclass
class LoginBucket:
    attempts: list[datetime] = field(default_factory=list)
    blocked_until: datetime | None = None


class LoginRateLimiter:
    def __init__(self) -> None:
        self._buckets: dict[str, LoginBucket] = {}

    def is_blocked(self, key: str) -> tuple[bool, int]:
        now = self._now()
        bucket = self._buckets.get(key)
        if not bucket or not bucket.blocked_until:
            return False, 0
        if now >= bucket.blocked_until:
            bucket.blocked_until = None
            return False, 0
        retry_after = int((bucket.blocked_until - now).total_seconds())
        return True, max(1, retry_after)

    def register_failure(self, key: str) -> int:
        now = self._now()
        bucket = self._buckets.setdefault(key, LoginBucket())

        window_start = now - timedelta(seconds=settings.login_rate_limit_window_seconds)
        bucket.attempts = [t for t in bucket.attempts if t >= window_start]
        bucket.attempts.append(now)

        if len(bucket.attempts) >= settings.login_rate_limit_attempts:
            bucket.blocked_until = now + timedelta(seconds=settings.login_rate_limit_block_seconds)

        attempts_left = max(0, settings.login_rate_limit_attempts - len(bucket.attempts))
        return attempts_left

    def register_success(self, key: str) -> None:
        if key in self._buckets:
            del self._buckets[key]

    @staticmethod
    def _now() -> datetime:
        return datetime.now(tz=timezone.utc)


login_rate_limiter = LoginRateLimiter()
