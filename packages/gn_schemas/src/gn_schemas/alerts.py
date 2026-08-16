from __future__ import annotations

from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4

from gn_scoring import Severity
from pydantic import Field

from .common import Base, Entity, Source, utcnow
from .intel import IpIntel


class AlertStatus(str, Enum):
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    FALSE_POSITIVE = "false_positive"


class Alert(Base):
    """Something the detection engine wants a human to look at.

    Raised by a Sigma rule match or by the anomaly model. `intel` is populated
    by the enrichment sidecar when the alert involves an IP, so the console can
    show reputation without a second round trip.
    """

    id: UUID = Field(default_factory=uuid4)
    rule: str
    severity: Severity
    title: str
    detail: str = ""
    entities: list[Entity] = Field(default_factory=list)
    source: Source
    status: AlertStatus = AlertStatus.OPEN
    intel: IpIntel | None = None
    raised_at: datetime = Field(default_factory=utcnow)
    context: dict[str, object] = Field(default_factory=dict)
