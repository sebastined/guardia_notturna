from dataclasses import dataclass

import pytest

from gn_scoring import (
    CombineStrategy,
    Grade,
    RiskBand,
    Severity,
    grade_for,
    parse_severity,
    score_findings,
    score_signals,
)


@dataclass
class Finding:
    severity: Severity


def test_clean_target_scores_perfect_a():
    posture = score_findings([])
    assert posture.score == 100
    assert posture.grade is Grade.A


def test_penalties_accumulate_flat():
    posture = score_findings([Finding(Severity.MEDIUM)] * 3)
    assert posture.score == 70
    assert posture.grade is Grade.C
    assert posture.findings_counted == 3


def test_score_floors_at_zero():
    posture = score_findings([Finding(Severity.CRITICAL)] * 10)
    assert posture.score == 0
    assert posture.grade is Grade.F


def test_info_findings_are_free():
    assert score_findings([Finding(Severity.INFO)] * 5).score == 100


@pytest.mark.parametrize(
    "score,grade",
    [(100, Grade.A), (90, Grade.A), (89, Grade.B), (70, Grade.C), (60, Grade.D), (59, Grade.F)],
)
def test_grade_boundaries(score, grade):
    assert grade_for(score) is grade


def test_the_divergence_that_forced_this_package():
    """abuse=45, fraud=45 is the case the two predecessors disagreed on."""
    signals = {"abuseipdb": 45, "ipqs": 45}

    worst = score_signals(signals, CombineStrategy.WORST_SIGNAL)
    assert worst.value == 45
    assert worst.band is RiskBand.MEDIUM

    additive = score_signals(signals, CombineStrategy.ADDITIVE)
    assert additive.value == 90
    assert additive.band is RiskBand.CRITICAL


def test_default_strategy_is_worst_signal():
    assert score_signals({"a": 45, "b": 45}).band is RiskBand.MEDIUM


def test_dead_provider_is_dropped_not_zeroed():
    """A None must not drag a hostile verdict down toward clean."""
    assert score_signals({"abuseipdb": 90, "ipqs": None}).value == 90
    assert score_signals({"abuseipdb": 90, "ipqs": 0}).value == 90


def test_no_usable_signals_is_low_not_an_error():
    risk = score_signals({"abuseipdb": None, "ipqs": None})
    assert risk.value == 0
    assert risk.band is RiskBand.LOW
    assert risk.signals == {}


def test_additive_ceiling_caps_single_provider():
    additive = score_signals({"solo": 100}, CombineStrategy.ADDITIVE)
    assert additive.value == 50


def test_scanner_severity_aliases_normalise():
    assert parse_severity("MODERATE") is Severity.MEDIUM
    assert parse_severity("Important") is Severity.HIGH
    assert parse_severity("negligible") is Severity.LOW
    assert parse_severity("") is Severity.INFO
    assert parse_severity("wat") is Severity.INFO


def test_severity_orders_by_rank():
    assert Severity.LOW < Severity.CRITICAL
    assert max([Severity.LOW, Severity.HIGH, Severity.INFO]) is Severity.HIGH
