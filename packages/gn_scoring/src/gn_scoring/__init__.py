"""Shared scoring for Guardia Notturna.

Two scales, deliberately distinct:

    posture  0-100, higher is better, graded A-F  (how well configured?)
    risk     0-100, higher is worse,  banded      (how dangerous?)
"""

from .posture import PERFECT_SCORE, Grade, Posture, grade_for, score_findings
from .risk import (
    MAX_RISK,
    CombineStrategy,
    DEFAULT_STRATEGY,
    Risk,
    RiskBand,
    band_for,
    score_signals,
)
from .severity import Severity, parse_severity

__all__ = [
    "PERFECT_SCORE",
    "Grade",
    "Posture",
    "grade_for",
    "score_findings",
    "MAX_RISK",
    "CombineStrategy",
    "DEFAULT_STRATEGY",
    "Risk",
    "RiskBand",
    "band_for",
    "score_signals",
    "Severity",
    "parse_severity",
]

__version__ = "0.1.0"
