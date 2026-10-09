# Generic legacy local reconcile

Status: completed in isolated worktree; MAIN integration pending.

Base: a40eb065da1bb21d231d2644449e2ecd8a2f98d6.
Branch: codex/main-legacy-local-reconcile-20261009.
Code commit: 7ced0b50b8cabb5a8becc50374cd6f8216d212ff.

1. Actual approved card and existing CodeGraph structure — complete; no new index.
2. Responsibility RED tests — complete; initial 6 RED, dedup 2 RED, inline SEC form 2 RED, bounded discovery 1 RED retained.
3. Local inventory, actual facts, atomic restore, ensure/dedup composition and explicit public localprepare — complete.
4. Concentrated responsibility node — 166 PASS / 39.34s; actual four originals node — complete / 56.248s, 3 reused and 1 honest gap, zero network/download/model requests.
5. Scoped code commit and owned handoff package — complete; normal hooks pass.

Owned: local inventory/intake/sourcefacts/dedup and these tests/docs.
MAIN: source_availability.py, source_reader_cli.py, FF composition, production/main PWF and integration.
No main merge/push/install or production DB/raw/config/Dayu changes.
