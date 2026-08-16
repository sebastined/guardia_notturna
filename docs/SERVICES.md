# Service specifications

Status legend: **built** · **scaffolded** (skeleton committed, logic pending) ·
**planned** (specified, no code)

| Service | Port | Status |
|---|---|---|
| [gateway](#gateway) | 8000 | scaffolded |
| [enrich](#enrich) | 8010 | planned |
| [scan-web](#scan-web) | 8020 | planned |
| [scan-container](#scan-container) | 8030 | planned |
| [detect](#detect) | 8040 | planned |
| [report](#report) | 8050 | planned |
| [ingest](#ingest) | — | planned |
| [store](#store) | — | planned |
| [monitor](#monitor) | — | planned |
| [web](#web) | 3000 | planned |

---

## gateway

**Responsibility.** Terminate authentication, enforce RBAC, route to internal
services. No domain logic.

**Endpoints**

| Method | Path | Role | Purpose |
|---|---|---|---|
| GET | `/health` | none | liveness probe |
| POST | `/auth/token` | none | issue JWT from credentials |
| GET | `/me` | viewer | echo resolved identity |
| POST | `/scans` | analyst | trigger a scan |
| GET | `/scans/{id}` | viewer | fetch a result |
| GET | `/alerts` | viewer | query alerts |
| PATCH | `/alerts/{id}` | analyst | acknowledge / resolve |
| GET | `/intel/ip/{ip}` | viewer | reputation lookup |
| POST | `/users` | admin | user management |

**Roles.** Ranked — `viewer` (0) < `analyst` (1) < `admin` (2). A guard admits
its minimum rank and everything above.

**Depends on:** every internal service. **Consumed by:** the console.

---

## enrich

**Responsibility.** Aggregate external reputation for an IP into one banded
verdict.

**Providers.** IPInfo (geo), AbuseIPDB (abuse confidence), IPQualityScore
(fraud/proxy/VPN/Tor), IPGeolocation (geo fallback), Project Honey Pot HTTP:BL.

**Behaviour.** Providers are queried concurrently via `asyncio.gather` with
per-call timeouts. A provider that fails contributes `ProviderResult(ok=False,
score=None)` and is **excluded** from the verdict rather than counted as zero —
an unreachable source must never make a hostile IP look clean. Results are
cached in `gn-intel-cache` with a 6-hour TTL.

**Endpoints:** `POST /enrich/ip`, `POST /enrich/bulk` (max 100), `GET /health`.

**Returns:** `IpIntel`, with `degraded=true` when any provider failed.

**Notes.** This is the highest-value integration in the platform: it replaces
the predecessor SIEM's static `iocs.yaml` with live multi-source reputation.

---

## scan-web

**Responsibility.** Assess an HTTP endpoint's security posture by inspection.

**Checks.** Security headers (HSTS, CSP, X-Frame-Options, X-Content-Type-Options,
Referrer-Policy, Permissions-Policy), TLS version and certificate validity,
redirect chains, cookie flags (`Secure`, `HttpOnly`, `SameSite`), DNS records
(SPF, DMARC, DNSSEC, CAA).

**Pipeline.** normalise input → enforce http/https → resolve hostname → **reject
non-public IPs (SSRF guard)** → fetch with retry and timeout → analyse → score →
emit `ScanResult`.

**Input handling.** Accepts bare hostnames, full URLs, and wildcards like
`*.example.com` (scans the base domain). Batch capped at 5 targets per request.

**Endpoints:** `POST /scan`, `POST /scan/batch`, `GET /health`.

---

## scan-container

**Responsibility.** Vulnerability scanning for container images.

**Scanners.** Trivy and Snyk, run in parallel. Findings are deduplicated by
CVE ID; where both report the same CVE with different severities, the **higher**
is kept and both sources recorded in `evidence`.

**Triggering.** On demand via the gateway, or automatically from `monitor`
events when a new image appears.

**Endpoints:** `POST /scan/image`, `GET /scan/{id}`, `GET /health`.

---

## detect

**Responsibility.** Turn telemetry into alerts.

**Two engines.**
- *Sigma rules* — deterministic detection from `detect/rules/*.yml`. Seeded with
  failed SSH logins, sudo abuse, and direct root login.
- *Anomaly model* — scikit-learn IsolationForest, trained on a rolling window of
  1000 recent events, 10% expected contamination. Flags statistical outliers the
  rules do not cover.

**Enrichment.** Alerts carrying an IP entity call `enrich` before publication.

**Output.** `Alert` objects to `gn.alerts`, plus Prometheus counters
(`gn_detections_total`, `gn_alerts_total` by severity and rule).

**Migration note.** The predecessor detection engine is Flask. It is the only
non-FastAPI component and gets converted during the port — see
[ADR-002](DECISIONS.md#adr-002-fastapi-across-all-services).

---

## report

**Responsibility.** Render scan results and alerts as JSON, CSV, or PDF.

Separated from the scanners so export formatting never blocks a scan and every
artefact type is produced from one code path.

**Endpoints:** `POST /report/scan/{id}`, `POST /report/alerts`, `GET /health`.

---

## ingest

**Responsibility.** Fluent Bit collecting host and container logs, forwarding to
`gn.logs.raw`. Configuration-only; no application code.

---

## store

**Responsibility.** Kafka consumer that normalises and indexes into OpenSearch.
Owns index templates and ILM policies. Idempotent on message ID so replays do
not duplicate.

---

## monitor

**Responsibility.** Watch Docker and Kubernetes event streams; emit scan
requests when new images are deployed. Deployed as a DaemonSet in production.

---

## web

**Responsibility.** Operator console — dashboards, alert triage, scan history,
report download.

**Stack.** Next.js 15, React 19, recharts (charts), zustand (state), jspdf
(client-side export), framer-motion, lucide-react.

**Views.** Overview · Alerts · Scans · Intel lookup · Admin.
