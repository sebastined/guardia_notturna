# Decision log

Architecture decisions, newest last. Each records what was chosen, what it was
chosen over, and what would justify revisiting it.

---

## ADR-001: Consolidate four projects into one platform

**Status:** accepted

Four separate repositories had converged on the same problem space from
different angles — external web scanning, container security, SIEM/detection,
and IP reputation — while independently reimplementing scoring, auth, and
frontend foundations. A fifth was an earlier prototype of a sixth.

**Decision.** Merge into a single monorepo with independently deployable
services.

**Rejected:** keeping them separate and sharing code via published packages.
Version skew across four repos with one maintainer costs more than it saves.

**Consequence.** Roughly fifteen services under one roof. Operational weight,
not code merging, is the real price — mitigated by sequencing the migration
incrementally rather than as a single cutover.

---

## ADR-002: FastAPI across all services

**Status:** accepted

Three of four predecessors were already FastAPI; the detection engine was Flask,
and one prototype was Node/Express.

**Decision.** FastAPI everywhere. The Node prototype is retired outright (it was
superseded by a Python port with an identical output schema). The Flask
detection engine is converted during its port.

**Consequence.** Single dependency set, uniform async model, one OpenAPI surface.
The detection engine conversion is the only non-trivial migration.

---

## ADR-003: Two inverted scoring scales, as distinct types

**Status:** accepted

The platform needs to express both "how well is this configured" and "how
dangerous is this". Both are natural 0–100 scales running in opposite
directions.

**Decision.** Keep them separate: `Posture` (higher is better, graded A–F) and
`Risk` (higher is worse, banded low–critical). Distinct types, not a shared int
with a convention.

**Rejected:** one unified 0–100 scale. Any single direction makes one of the two
domains read backwards, and the convention would eventually leak into the
console as an inverted colour scale.

---

## ADR-004: Risk combine strategy — worst signal, not additive

**Status:** accepted · **reversible via one constant**

The two predecessor implementations disagreed silently:

```
max(abuse, fraud)               abuse=45, fraud=45  ->  45  medium
min(50,abuse) + min(50,fraud)   abuse=45, fraud=45  ->  90  critical
```

Same inputs, different verdict, and nothing in either codebase acknowledged the
divergence.

**Decision.** Default to `WORST_SIGNAL`.

**Rationale.** Reputation providers are strongly correlated — AbuseIPDB and IPQS
routinely flag the same addresses from overlapping upstream data. Summing them
double-counts a single piece of evidence, and the inflation lands hardest in the
middle of the range, which is exactly where analyst attention is scarcest.

**Reversal.** Change `DEFAULT_STRATEGY` in `gn_scoring/risk.py`. Both behaviours
are pinned by `test_the_divergence_that_forced_this_package`, so a flip is
visible in CI rather than silent. Revisit if measured false-negative rates on
corroborated-but-moderate signals prove the conservatism wrong.

---

## ADR-005: Authentication at the gateway only

**Status:** accepted

Predecessors ranged from full JWT with RBAC, through a single shared API key, to
no authentication at all.

**Decision.** JWT with ranked RBAC (`viewer` < `analyst` < `admin`), enforced at
the gateway. Internal services trust the resolved `Actor` and bind to the
internal network only.

**Rejected:** per-service auth. It multiplies the places a mistake can be made,
for a threat model that does not currently include a hostile internal network.

**Consequence.** The gateway is a single point of failure for access control.
Revisit if the platform becomes multi-tenant.

---

## ADR-006: Italian product name, functional module names

**Status:** accepted

Predecessor modules were named `ofo`, `umunna`, `ikenga`, `glacier` — culturally
coherent, but opaque about function.

**Decision.** Brand at the product layer (*Guardia Notturna*); plain descriptive
names underneath (`scan-web`, `detect`, `enrich`, `store`). Short form `gn` for
image tags, package prefixes, and the Kubernetes namespace.

**Rationale.** The problem with the old names was opacity, not language.
Substituting equally opaque Italian names would rebuild the same problem.

---

## ADR-007: Postgres over Supabase

**Status:** accepted

One predecessor used Supabase for user storage; nothing else did.

**Decision.** Plain Postgres, self-hosted alongside the stack.

**Rationale.** Supabase's value is the managed auth and realtime layer, both of
which duplicate what the gateway and Kafka already provide. Keeping it would
leave one service with a data layer unlike every other.

---

## ADR-008: Secrets never enter git, enforced by explicit ignore rules

**Status:** accepted

A predecessor leaked six live third-party API keys because its `.gitignore` rule
was written `.env/` — with a trailing slash, matching only a *directory* and
letting the `.env` file through unnoticed.

**Decision.** Ignore rules are `.env` and `.env.*` with no trailing slash, with
`!.env.example` re-included, and a comment in `.gitignore` explaining exactly
why. Config is supplied through environment variables; the gateway refuses to
boot in production without a real `GN_JWT_SECRET` rather than falling back to a
default.

**Consequence.** No committed secret can be dismissed as an accident of a subtle
pattern rule. Pre-commit secret scanning is a candidate follow-up.
