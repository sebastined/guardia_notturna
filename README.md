# Guardia Notturna

A security operations platform: scanners feed a detection spine, reputation
enrichment hangs off the side, one gateway and one console in front.

> Status: **scaffold**. The shared packages, the gateway and the local stack are
> real and tested. The scanners, detection engine and console are not built yet.

---

## Architecture

```
                    ┌──────────────┐
                    │  web console │  Next.js 15
                    └──────┬───────┘
                           │
                    ┌──────┴───────┐
                    │   gateway    │  FastAPI · JWT · RBAC
                    └──────┬───────┘
        ┌──────────────────┼──────────────────┐
        │                  │                  │
 ┌──────┴──────┐    ┌──────┴──────┐    ┌──────┴──────┐
 │  scan-web   │    │scan-container│   │   detect    │
 │ hdrs/TLS/DNS│    │ Trivy · Snyk │   │ Sigma · ML  │
 └──────┬──────┘    └──────┬───────┘   └──────┬──────┘
        │                  │                  │
        └────────► ingest ─┴──► store ────────┘
                   Kafka        OpenSearch
                                     ▲
                              ┌──────┴──────┐
                              │   enrich    │  IP reputation
                              └─────────────┘
```

Scanners and monitors publish findings to Kafka; the indexer lands them in
OpenSearch; the detection engine correlates against Sigma rules and an anomaly
baseline; `enrich` is called as a sidecar by both `detect` and `scan-web`.

| Path | Role |
|---|---|
| `packages/gn_scoring` | Severity taxonomy, posture and risk scoring |
| `packages/gn_schemas` | Pydantic wire contracts shared by all services |
| `services/gateway` | Auth, RBAC, request routing |
| `deploy/` | Compose (dev) and Kubernetes (prod) manifests |

---

## Two scales, deliberately inverted

The single most common source of confusion in this codebase, so it is named
explicitly in the types:

| | Range | Direction | Output |
|---|---|---|---|
| **Posture** | 0–100 | higher is **better** | grade `A`–`F` |
| **Risk** | 0–100 | higher is **worse** | band `low`–`critical` |

A well-configured site scores 100. A hostile IP scores 100. They mean opposite
things, so they are separate types (`Posture`, `Risk`) and never interchangeable.

### Open decision: risk combine strategy

Predecessor implementations disagreed silently on how to merge reputation
signals. With `abuse=45, fraud=45`:

- `WORST_SIGNAL` → **45, medium**
- `ADDITIVE` → **90, critical**

The default is `WORST_SIGNAL`, because reputation providers are strongly
correlated and adding their scores double-counts one piece of evidence. Change
`DEFAULT_STRATEGY` in `packages/gn_scoring/src/gn_scoring/risk.py` if you
disagree — but expect alert volumes to move. Both behaviours are locked in by
`test_the_divergence_that_forced_this_package`.

---

## Quick start

```bash
# shared packages, editable
pip install -e packages/gn_scoring -e packages/gn_schemas

# tests
pip install pytest && pytest packages/gn_scoring

# local stack: kafka + opensearch + gateway
cp .env.example .env
docker compose up -d --build
curl localhost:8000/health
```

---

## Technology

| Layer | Stack |
|---|---|
| Runtime | Python 3.12, FastAPI, `httpx` async |
| Streaming | Kafka (KRaft mode), Fluent Bit |
| Search | OpenSearch 2.17 |
| Detection | Sigma rules, scikit-learn IsolationForest |
| Scanning | Trivy, Snyk |
| Auth | JWT (python-jose), bcrypt, RBAC — admin / analyst / viewer |
| Observability | Prometheus, Grafana |
| Console | Next.js 15, React 19, recharts, zustand |
| Deploy | Docker Compose (dev), Kubernetes (prod) |

---

## Conventions

- **Secrets never enter git.** `.gitignore` rules are `.env` and `.env.*`
  without a trailing slash — a rule written `.env/` matches only a directory and
  lets the file through. Real API keys reached a predecessor repo exactly that
  way.
- **Scanners emit the shared `Severity`,** never their own levels. Normalise
  vendor strings at the boundary with `parse_severity`.
- **A dead provider is dropped, not zeroed.** An unreachable reputation source
  must never make a hostile entity look clean; `ScanResult.status=partial` and
  `IpIntel.degraded` exist to say so out loud.
- **Envelope changes land in `gn_schemas` first.** Services do not extend the
  contract locally.

---

## Roadmap

- [x] Shared scoring package with the severity decision settled
- [x] Shared schemas
- [x] Gateway with JWT + RBAC
- [x] Local stack (Kafka + OpenSearch)
- [ ] `ingest` / `store` — Fluent Bit → Kafka → OpenSearch
- [ ] `enrich` — IP reputation fan-out
- [ ] `scan-web` — headers, TLS, DNS, cookies
- [ ] `scan-container` — Trivy + Snyk
- [ ] `detect` — Sigma + anomaly model
- [ ] `web` — Next.js console
