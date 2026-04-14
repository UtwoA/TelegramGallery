from enum import Enum


class UserRole(str, Enum):
    ADMIN = "admin"
    FAMILY = "family"


class MediaType(str, Enum):
    IMAGE = "image"
    VIDEO = "video"


class MediaStatus(str, Enum):
    PENDING = "pending"
    READY = "ready"
    PARTIAL = "partial"
    FAILED = "failed"
