from __future__ import annotations

from datetime import datetime

from gn_scoring import RiskBand
from pydantic import Field

from .common import Base, utcnow


class ProviderResult(Base):
    """One reputation provider's answer, kept whole.

    `score` is the provider's contribution normalised to 0-100 (higher = worse);
    `None` means the provider did not answer and must be excluded from the
    verdict rather than counted as clean. `raw` is retained verbatim so an
    analyst can audit a verdict without re-querying.
    """

    provider: str
    score: int | None = Field(default=None, ge=0, le=100)
    ok: bool = True
    error: str | None = None
    raw: dict[str, object] = Field(default_factory=dict)
    latency_ms: int | None = None


class IpIntel(Base):
    """Aggregated reputation and geolocation for a single IP."""

    ip: str
    country: str | None = None
    region: str | None = None
    city: str | None = None
    org: str | None = None

    proxy: bool = False
    vpn: bool = False
    tor: bool = False
    hosting: bool = False

    risk_score: int = Field(ge=0, le=100)
    risk_band: RiskBand
    providers: list[ProviderResult] = Field(default_factory=list)
    enriched_at: datetime = Field(default_factory=utcnow)

    @property
    def degraded(self) -> bool:
        """True when any provider failed, so callers can flag low-confidence verdicts."""
        return any(not p.ok for p in self.providers)
