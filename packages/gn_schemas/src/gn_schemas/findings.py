from __future__ import annotations

from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4

from gn_scoring import Posture, Severity
from pydantic import Field

from .common import Base, Entity, Source, utcnow


class ScanStatus(str, Enum):
    OK = "ok"
    PARTIAL = "partial"
    FAILED = "failed"


class Finding(Base):
    """One problem observed on one target.

    Emitted identically by the web scanner and the container scanner - the only
    difference is what goes in `source` and `evidence`.
    """

    id: UUID = Field(default_factory=uuid4)
    target: Entity
    severity: Severity
    title: str
    detail: str = ""
    remediation: str = ""
    reference: str | None = Field(default=None, description="CVE, CWE or doc URL")
    evidence: dict[str, object] = Field(default_factory=dict)
    observed_at: datetime = Field(default_factory=utcnow)


class ScanResult(Base):
    """A completed assessment of a single target.

    `status=PARTIAL` means some checks could not run - a scanner must say so
    rather than silently returning a better-looking score than it earned.
    """

    id: UUID = Field(default_factory=uuid4)
    target: Entity
    source: Source
    status: ScanStatus = ScanStatus.OK
    findings: list[Finding] = Field(default_factory=list)
    score: int = Field(ge=0, le=100)
    grade: str
    started_at: datetime
    finished_at: datetime = Field(default_factory=utcnow)
    errors: list[str] = Field(default_factory=list)

    @classmethod
    def from_posture(
        cls,
        *,
        target: Entity,
        source: Source,
        findings: list[Finding],
        posture: Posture,
        started_at: datetime,
        status: ScanStatus = ScanStatus.OK,
        errors: list[str] | None = None,
    ) -> "ScanResult":
        """Build a result from a scored posture, so score and grade cannot drift."""
        return cls(
            target=target,
            source=source,
            status=status,
            findings=findings,
            score=posture.score,
            grade=posture.grade.value,
            started_at=started_at,
            errors=errors or [],
        )
