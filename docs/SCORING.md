# Scoring specification

`gn_scoring` is the only place in the platform where severity becomes a number.
Every scanner, detector and view depends on it, which is why it was built first.

## Severity

One five-level taxonomy. Scanners emit these values and nothing else.

| Level | Penalty | Rank |
|---|---|---|
| `critical` | 30 | 4 |
| `high` | 20 | 3 |
| `medium` | 10 | 2 |
| `low` | 5 | 1 |
| `info` | 0 | 0 |

Penalties apply to posture scoring. Rank exists for ordering and comparison —
`Severity` implements `__lt__`, so `max()` over a list of severities works
directly.

Vendor strings are normalised at the boundary:

```python
parse_severity("MODERATE")   # -> Severity.MEDIUM   (Snyk)
parse_severity("Important")  # -> Severity.HIGH     (some advisories)
parse_severity("negligible") # -> Severity.LOW      (Trivy)
parse_severity("wat")        # -> Severity.INFO     (safe default)
```

Unknown values fall back to `INFO` rather than raising. A scanner emitting an
unrecognised severity should not fail the scan, but it should not inflate the
result either.

## Two scales

The single most important thing to understand about this package:

| | Range | Direction | Output | Applies to |
|---|---|---|---|---|
| **Posture** | 0–100 | higher is **better** | `A`–`F` | things assessed by inspection |
| **Risk** | 0–100 | higher is **worse** | `low`–`critical` | things judged by reputation |

A well-configured site scores 100. A hostile IP scores 100. They mean opposite
things, so they are separate types and cannot be passed interchangeably.

### Posture

Start at 100, deduct each finding's penalty, floor at 0, then grade:

| Score | Grade |
|---|---|
| 90–100 | A |
| 80–89 | B |
| 70–79 | C |
| 60–69 | D |
| 0–59 | F |

```python
from gn_scoring import score_findings
posture = score_findings(findings)   # Posture(score=70, grade=Grade.C, findings_counted=3)
```

Penalties are **flat** — three medium findings cost 30 points, with no
diminishing return. This is deliberate: a target with many small problems should
not grade well merely because none is individually severe.

### Risk

| Value | Band |
|---|---|
| 80–100 | critical |
| 50–79 | high |
| 20–49 | medium |
| 0–19 | low |

```python
from gn_scoring import score_signals
risk = score_signals({"abuseipdb": 45, "ipqs": 45})   # Risk(value=45, band=MEDIUM)
```

**Missing signals are dropped, not zeroed.** `None` means the provider did not
answer; it is excluded from the calculation entirely. An unreachable provider
must never drag a hostile verdict toward clean:

```python
score_signals({"abuseipdb": 90, "ipqs": None}).value   # 90, not 45
```

Callers should surface `IpIntel.degraded` when this happens, so an analyst can
tell a confident verdict from a partial one.

## The combine strategy

Two strategies exist because the predecessor implementations disagreed, and the
disagreement was invisible until the codebases were compared:

```python
score_signals({"abuseipdb": 45, "ipqs": 45}, CombineStrategy.WORST_SIGNAL)
# -> 45, medium

score_signals({"abuseipdb": 45, "ipqs": 45}, CombineStrategy.ADDITIVE)
# -> 90, critical
```

`WORST_SIGNAL` is the default. Under `ADDITIVE`, each provider is capped at 50 so
no single source can max the score on its own.

Full rationale and reversal criteria: [ADR-004](DECISIONS.md#adr-004-risk-combine-strategy--worst-signal-not-additive).

## Adding a scanner

1. Emit `Finding` objects carrying `Severity` — never a custom level.
2. Map vendor severities with `parse_severity` at the ingest boundary.
3. Score with `score_findings`, and build the result with
   `ScanResult.from_posture` so score and grade cannot drift apart.
4. Set `status=PARTIAL` and populate `errors` if any check could not run.

## Tests

`packages/gn_scoring/tests/test_scoring.py` pins the boundaries, the
missing-provider semantics, and both sides of the combine divergence. Changing
scoring behaviour should require changing a test — that is the point.
