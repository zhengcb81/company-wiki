# Security remediation runbook

## Current verified state

- Current tracked active credential candidates: **0**.
- Reachable Git history contains **3 unique active credential fingerprints**.
- The ignored local `.env` contains **2 active credentials**, both matching historical fingerprints.
- A remote tracking ref exists, so history exposure must be treated as published.
- Machine-readable, redacted evidence is stored in `artifacts/security/secret-decision.json`.

No secret value, prefix continuation, or reversible encoding may be copied into an issue, log, commit message, review, or remediation receipt.

## Required external actions

1. Rotate/revoke the current DeepSeek credential at the provider.
2. Rotate/revoke the current Tavily credential at the provider.
3. Revoke any older DeepSeek credential that may have been embedded in historical local command permissions.
4. Record provider, rotation timestamp, operator, and provider-side confirmation ID in an external security system. Do not record the credential itself.
5. Replace values only in the ignored local `.env`; rerun the redacted audit.

Until provider-side evidence exists, `provider_rotation` must remain `external_action_pending`.

## History rewrite decision

History rewrite is destructive and requires explicit authorization plus coordination with every clone and remote consumer. Before execution:

1. Freeze pushes and create a fresh verified bundle.
2. Agree the affected refs and maintenance window.
3. Rewrite all affected refs with an approved tool and reviewed replacement rules.
4. Force-update the remote only after independent verification.
5. Invalidate old clones and require fresh clones.
6. Rescan every reachable blob and verify the three active fingerprints are absent.

Do not run a history rewrite from an implementation model without that authorization.

## Recurrence prevention

Run this deterministic preflight before any commit or in CI:

```powershell
python scripts/secret_audit.py scan-staged --root .
```

Exit code 0 means no staged active candidate. Exit code 2 blocks the commit. Findings contain only path, line, kind, length, classification, and a non-reversible short fingerprint; values are never emitted.

The project does not install `.git/hooks` automatically. Hook installation changes user-local Git state and must be an explicit operator decision.
