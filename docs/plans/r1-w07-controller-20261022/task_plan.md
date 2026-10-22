# W07 holdout acceptance controller

Scope: offline reusable test controller only, based on c3b4ebf1. Production src/config, mother plan, sibling repositories and old R1 runs are read-only.

## Phases

1. [complete] Freeze public inputs and valid configured lifecycle/failure expectations (5 behavioral RED).
2. [complete] Implement isolated stage observer and controller; the first complete configured CLI/HTTP/paid pin/replay/outbox/cache/public-reader chain passed.
3. [complete] Finite failure/reentry/unknown-hold controls and related native fences; static checks, owned cleanup and receipt sealing.
4. [in_progress] Normal branch commit and SHA-bound handoff; ROOT performs non-author review and integration.

## Next Step

Normal commit this isolated branch, bind handoff to the product SHA, and stop for ROOT non-author review/integration. No live supplier call or RF consumption is claimed.

Final acceptance: 9 unit/native controls passed in 3.35s; 10 actual configured subprocess E2E passed in 101.20s; strengthening the wire-binding assertion was verified by the affected E2E in 17.14s. All four tool modules pass mypy; all owned tools/tests pass Ruff. Slow lifecycle tests remain integration-only, without CI/precommit changes.

No real key, external API, raw download, supplier fee or RF consumption is allowed in this lane. Provider/model/generation settings remain owned by Config. Same paid operation is preserved while worker leases may advance legitimately.
