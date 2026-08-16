"""Threat risk scoring: how dangerous is this entity?

Scale runs 0-100 where **higher is worse**, banded LOW/MEDIUM/HIGH/CRITICAL.
Used for reputation verdicts on IPs, domains and hashes - things we judge from
external intelligence rather than by inspecting them ourselves.

Inverted relative to `gn_scoring.posture` on purpose: a well-configured site
scores 100 and a hostile IP scores 100, and they mean opposite things. Keeping
them as two named types stops that ambiguity leaking into the UI.

-------------------------------------------------------------------------------
OPEN DECISION - combine strategy
-------------------------------------------------------------------------------
The two predecessor implementations disagreed, and the disagreement was silent:

    max(abuse, fraud)                  -> abuse=45, fraud=45 reads MEDIUM
    min(50,abuse) + min(50,fraud)      -> abuse=45, fraud=45 reads HIGH (90)

`WORST_SIGNAL` is the default here. Reputation providers are strongly
correlated - AbuseIPDB and IPQS routinely flag the same IPs from overlapping
data - so adding their scores double-counts one piece of evidence and inflates
the middle of the range, which is exactly where analyst attention is scarcest.

Flip `DEFAULT_STRATEGY` if you disagree, but flip it deliberately and expect
existing alert volumes to move.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

MAX_RISK = 100


class RiskBand(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class CombineStrategy(str, Enum):
    WORST_SIGNAL = "worst_signal"
    ADDITIVE = "additive"


DEFAULT_STRATEGY = CombineStrategy.WORST_SIGNAL

# Band floors, worst first.
_BAND_FLOORS: tuple[tuple[int, RiskBand], ...] = (
    (80, RiskBand.CRITICAL),
    (50, RiskBand.HIGH),
    (20, RiskBand.MEDIUM),
    (0, RiskBand.LOW),
)

# Per-provider ceiling under ADDITIVE, so no single source can max the score.
_ADDITIVE_CEILING = 50


@dataclass(frozen=True, slots=True)
class Risk:
    value: int
    band: RiskBand
    strategy: CombineStrategy
    signals: dict[str, int] = field(default_factory=dict)

    def __str__(self) -> str:
        return f"{self.band.value} ({self.value}/100)"


def band_for(value: int) -> RiskBand:
    for floor, band in _BAND_FLOORS:
        if value >= floor:
            return band
    return RiskBand.LOW


def score_signals(
    signals: dict[str, int | float | None],
    strategy: CombineStrategy = DEFAULT_STRATEGY,
) -> Risk:
    """Combine 0-100 reputation signals into a single banded verdict.

    `signals` maps a provider name to its 0-100 score. `None` means the provider
    was unreachable or returned nothing - it is dropped rather than treated as a
    zero, so a dead provider cannot make a hostile IP look clean.
    """
    usable = {
        name: int(value)
        for name, value in signals.items()
        if isinstance(value, (int, float))
    }

    if not usable:
        return Risk(value=0, band=RiskBand.LOW, strategy=strategy, signals={})

    if strategy is CombineStrategy.WORST_SIGNAL:
        value = max(usable.values())
    else:
        value = sum(min(_ADDITIVE_CEILING, v) for v in usable.values())

    value = max(0, min(MAX_RISK, value))
    return Risk(value=value, band=band_for(value), strategy=strategy, signals=usable)
