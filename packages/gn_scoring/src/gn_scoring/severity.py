"""Severity taxonomy shared by every scanner and detector in the platform.

One vocabulary, one penalty table. Scanners emit `Severity`; they never invent
their own levels and never carry their own weights.
"""

from __future__ import annotations

from enum import Enum


class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"

    @property
    def penalty(self) -> int:
        """Points deducted from a perfect posture score by one finding."""
        return _PENALTY[self]

    @property
    def rank(self) -> int:
        """Ordering handle. Higher is worse; INFO is 0."""
        return _RANK[self]

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, Severity):
            return NotImplemented
        return self.rank < other.rank


_PENALTY: dict[Severity, int] = {
    Severity.CRITICAL: 30,
    Severity.HIGH: 20,
    Severity.MEDIUM: 10,
    Severity.LOW: 5,
    Severity.INFO: 0,
}

_RANK: dict[Severity, int] = {
    Severity.INFO: 0,
    Severity.LOW: 1,
    Severity.MEDIUM: 2,
    Severity.HIGH: 3,
    Severity.CRITICAL: 4,
}


def parse_severity(value: str, default: Severity = Severity.INFO) -> Severity:
    """Coerce a scanner's native severity string into the shared taxonomy.

    Trivy, Snyk and Sigma all spell severities slightly differently; normalise
    at the boundary so nothing downstream has to care.
    """
    if not value:
        return default
    key = value.strip().lower()
    aliases = {
        "crit": Severity.CRITICAL,
        "critical": Severity.CRITICAL,
        "high": Severity.HIGH,
        "important": Severity.HIGH,
        "moderate": Severity.MEDIUM,
        "medium": Severity.MEDIUM,
        "low": Severity.LOW,
        "minor": Severity.LOW,
        "info": Severity.INFO,
        "informational": Severity.INFO,
        "none": Severity.INFO,
        "unknown": default,
        "negligible": Severity.LOW,
    }
    return aliases.get(key, default)
