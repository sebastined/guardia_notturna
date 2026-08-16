# Security

A security platform is held to what it measures. This documents the controls the
platform applies to itself.

## Reporting a vulnerability

Report privately to the maintainer rather than opening a public issue. Include
reproduction steps and affected component. Expect acknowledgement within a few
days.

## Threat model

| Boundary | Assumption |
|---|---|
| Scan targets | **Fully attacker-controlled.** Anything fetched during a scan is hostile input. |
| Reputation providers | Untrusted and unreliable. Responses are parsed defensively; outages are expected. |
| Internal network | Trusted. Services bind internally and rely on gateway auth. Revisit for multi-tenant. |
| Operators | Authenticated and role-limited, but not assumed benign — actions are attributable. |

## Controls

**SSRF protection.** Scanners resolve a target's hostname *before* fetching and
refuse non-public address space — loopback, link-local, RFC1918, carrier-grade
NAT, and IPv6 equivalents. This runs on every redirect hop, not only the initial
URL, since a redirect into internal space is the standard bypass.

**Outbound isolation.** Scan traffic is timeout-bounded, retry-capped, and size-
limited. Response bodies are truncated before parsing.

**Authentication.** JWT with ranked RBAC at the gateway. Passwords are bcrypt-
hashed. The gateway **refuses to start** in production without an explicit
`GN_JWT_SECRET` — in development it generates an ephemeral one per process,
which invalidates tokens on restart by design. There is no default secret to
forget to change.

**Rate limiting.** Per-token and per-IP limits at the gateway. Batch scan
endpoints are capped by target count.

**Secret handling.** Configuration comes from environment variables. `.env` and
`.env.*` are git-ignored *without* a trailing slash, and `.env.example` is the
only committed variant.

> This rule is written the way it is because of a specific failure: a
> predecessor repository leaked six live third-party API keys after its ignore
> rule was written `.env/`. With a trailing slash the pattern matches only a
> directory, so the `.env` **file** was tracked silently. If you edit
> `.gitignore`, do not reintroduce the slash.

**Container hardening.** Images run as a non-root user (uid 10001), build from
slim bases, and carry healthchecks. Shared packages install ahead of service
code so the dependency layer caches independently.

**Dependency scanning.** The platform scans its own images with the same Trivy
and Snyk pipeline it offers as a product feature.

## Handling a leaked credential

1. **Rotate first.** Revoke at the provider before touching git history — the
   key is compromised from the moment it is pushed, and history rewriting does
   not un-publish it.
2. Remove the file and correct the ignore rule.
3. Rewrite history only if the repository is or ever was public. For a
   consistently private repository, rotation is normally sufficient.
4. Audit provider logs for use during the exposure window.

## Known gaps

- No pre-commit secret scanning yet — currently relies on the ignore rules
  alone.
- OpenSearch runs with the security plugin disabled in the development compose
  stack. Production enables it; do not expose the dev stack.
- No audit log of operator actions yet. `Actor` is threaded through the schemas
  in preparation.
