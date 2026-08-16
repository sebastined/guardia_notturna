# Architecture

## What this is

Guardia Notturna is a security operations platform built by consolidating four
predecessor projects that each occupied a different layer of the same stack and
had begun duplicating one another's foundations.

It does three things:

1. **Assess** targets by inspection — web endpoints and container images.
2. **Detect** threats in runtime telemetry — rule matches and anomalies.
3. **Enrich** entities with external reputation intelligence.

One gateway, one console, one severity vocabulary across all three.

## Design principles

**Scanners are dumb, the spine is smart.** A scanner's job is to observe and
emit `Finding` objects. It does not decide what is important, does not store
anything, and does not talk to other scanners. Correlation and prioritisation
happen once, downstream.

**One vocabulary, enforced by types.** Every component speaks `Severity` from
`gn_scoring`. Vendor severity strings are normalised at the boundary with
`parse_severity`, never propagated inward.

**Degradation is loud.** A provider timeout or a skipped check must surface as
`ScanStatus.PARTIAL` or `IpIntel.degraded`. A component that cannot complete its
work must never return a result that looks like a clean one.

**Auth lives at the edge.** Services trust the `Actor` the gateway resolves.
No service implements its own authentication.

**Contracts change in one place.** New fields land in `gn_schemas` first.
Services do not extend the envelope locally.

## Component map

```
                         ┌─────────────────┐
                         │   web console   │  Next.js 15 · :3000
                         └────────┬────────┘
                                  │ HTTPS + JWT
                         ┌────────┴────────┐
                         │     gateway     │  FastAPI · :8000
                         │  auth · RBAC    │
                         └────────┬────────┘
              ┌───────────────────┼───────────────────┐
              │                   │                   │
      ┌───────┴──────┐    ┌───────┴──────┐    ┌───────┴──────┐
      │   scan-web   │    │scan-container│    │    detect    │
      │    :8020     │    │    :8030     │    │    :8040     │
      └───────┬──────┘    └───────┬──────┘    └───────┬──────┘
              │                   │                   ▲
              │   ┌───────────────┘                   │
              │   │                                   │
              ▼   ▼                                   │
        ┌─────────────┐   ┌──────────┐   ┌────────────┴───┐
        │   ingest    │──▶│  Kafka   │──▶│     store      │
        │ Fluent Bit  │   │  KRaft   │   │  → OpenSearch  │
        └─────────────┘   └──────────┘   └────────────────┘
              ▲                                   ▲
              │                                   │
       ┌──────┴──────┐                    ┌───────┴──────┐
       │   monitor   │                    │    enrich    │
       │ docker · k8s│                    │ IP reputation│
       └─────────────┘                    │    :8010     │
                                          └──────────────┘
```

`enrich` is called synchronously over HTTP by `detect` and `scan-web`. It is not
on the Kafka path — enrichment is a request/response concern with a cache, not a
stream.

## Data flow

**Assessment path.** An operator (or a container event) triggers a scan. The
scanner normalises the target, validates it, runs its checks, scores the result
with `gn_scoring.score_findings`, and publishes a `ScanResult` to
`gn.findings.raw`. `store` indexes it. The console reads from OpenSearch.

**Detection path.** Fluent Bit ships host and container logs into `gn.logs.raw`.
`detect` consumes the stream, evaluates Sigma rules and the anomaly model, and
publishes `Alert` objects to `gn.alerts`. Alerts involving an IP are enriched
inline before publication, so the console never needs a second round trip.

## Kafka topics

| Topic | Producer | Consumer | Payload |
|---|---|---|---|
| `gn.logs.raw` | ingest | detect, store | raw log lines + metadata |
| `gn.findings.raw` | scan-web, scan-container | store | `ScanResult` |
| `gn.alerts` | detect | store, gateway (SSE) | `Alert` |
| `gn.scan.requests` | gateway, monitor | scan-* | scan job |

Retention: 7 days for `gn.logs.raw`, 30 days for the rest. OpenSearch is the
system of record; Kafka is a buffer, not storage.

## OpenSearch indices

| Index pattern | Contents | ILM |
|---|---|---|
| `gn-logs-{yyyy.MM.dd}` | normalised telemetry | hot 7d → delete 30d |
| `gn-findings-{yyyy.MM}` | scan results | hot 30d → warm 1y |
| `gn-alerts-{yyyy.MM}` | detection output | hot 90d → warm 2y |
| `gn-intel-cache` | reputation lookups, TTL-keyed | rolling |

## Trust boundaries

1. **Internet → scanners.** Scan targets are attacker-controlled. All outbound
   fetches resolve the hostname first and refuse non-public IP ranges. See
   [SECURITY.md](../SECURITY.md).
2. **Internet → gateway.** Only the gateway and the console are exposed. Every
   other service binds to the internal network only.
3. **Platform → reputation providers.** Third-party APIs are untrusted and
   unreliable; every call is timeout-bounded and failure-tolerant.

## Deployment

**Development** — `docker compose up -d --build`. Single-node Kafka and
OpenSearch, security plugin disabled, JWT secret auto-generated per process.

**Production** — Kubernetes. Security plugin enabled, `GN_JWT_SECRET` supplied
from a secret store (the gateway refuses to boot without it when
`GN_ENV=production`), scanners horizontally scaled, OpenSearch as a managed
cluster.

Manifests live in `deploy/k8s/`. CI is Jenkins, carried over from the
predecessor pipelines.
