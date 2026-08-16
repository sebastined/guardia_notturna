"""Posture scoring: how well is this target configured?

Scale runs 0-100 where **higher is better**, graded A-F. This is the scale used
for anything we assess by inspection - web security headers, TLS configuration,
container image hygiene.

Do not confuse it with `gn_scoring.risk`, which runs the other way round.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable, Protocol

from .severity import Severity

PERFECT_SCORE = 100


class Grade(str, Enum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"
    F = "F"


_GRADE_FLOORS: tuple[tuple[int, Grade], ...] = (
    (90, Grade.A),
    (80, Grade.B),
    (70, Grade.C),
    (60, Grade.D),
    (0, Grade.F),
)


class HasSeverity(Protocol):
    severity: Severity


@dataclass(frozen=True, slots=True)
class Posture:
    score: int
    grade: Grade
    findings_counted: int

    def __str__(self) -> str:
        return f"{self.grade.value} ({self.score}/100)"


def grade_for(score: int) -> Grade:
    for floor, grade in _GRADE_FLOORS:
        if score >= floor:
            return grade
    return Grade.F


def score_findings(findings: Iterable[HasSeverity]) -> Posture:
    """Deduct each finding's penalty from a perfect score, then grade.

    Deliberately flat: N medium findings cost N x 10, with no diminishing
    return. A target with many small problems should not grade well simply
    because none of them is individually severe.
    """
    score = PERFECT_SCORE
    counted = 0
    for finding in findings:
        score -= finding.severity.penalty
        counted += 1

    score = max(0, min(PERFECT_SCORE, score))
    return Posture(score=score, grade=grade_for(score), findings_counted=counted)
