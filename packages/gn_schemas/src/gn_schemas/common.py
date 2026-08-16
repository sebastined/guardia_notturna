from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class EntityKind(str, Enum):
    IP = "ip"
    DOMAIN = "domain"
    URL = "url"
    IMAGE = "image"
    CONTAINER = "container"
    HOST = "host"
    FILE_HASH = "file_hash"
    USER = "user"


class Entity(Base):
    """A thing the platform can assess, alert on, or enrich."""

    kind: EntityKind
    value: str

    def __str__(self) -> str:
        return f"{self.kind.value}:{self.value}"


class Source(Base):
    """Which component produced a record, and which version of it."""

    service: str = Field(description="e.g. scan-web, scan-container, detect")
    version: str = "0.1.0"
    instance: str | None = None


class Actor(Base):
    """Authenticated principal, carried for audit."""

    subject: str
    email: str | None = None
    role: str = "viewer"
