# Progress

2026-10-09: MAIN authorization consumed; isolated branch from a40eb065; existing main CodeGraph used, no index creation.

- Initial responsibility RED: 6 failed / 1.89s (`red.log`). Dedup RED: 2 failed, 6 passed / 2.32s (`dedup-red.log`).
- First implementation corrected active/retired handling, sourcefacts atomicity, ensure zero-fetch composition and local import dedup. Existing writer initialization regression was caught by concentrated tests and repaired; full failure log retained.
- Actual caller fixture mistakes were corrected against the unchanged public contracts; receipts retained. MAIN authorized the legacy 32-span normalization port migration.
- Actual producer counterexamples: FF physical-key rejection and SEC inline whitespace; exact failed receipts retained, generic regression tests added.
- Bounded unindexed Dayu group discovery RED: 1 failed / .60s; generic configured-layout discovery implemented.
- Final concentrated node: 166 passed / 39.34s (`concentrated-delivery.log`); short owned TEMP and TEMP/TMP restored, directory absent.
- Real four-original node: exit0 / 56.248s (`actual_originals_receipt.json`); Microsoft three quarters reused via actual FF and public byte reader; CN honest gap; repeats idempotent; publication-before requests refused. Zero network attempts/download/model/supplier calls. Protected raw/meta/source-sidecars/production configs unchanged. Owned TEMP absent and environment restored.
- Exact owned-file Ruff --no-cache and git diff --check passed. Normal code commit 7ced0b50b8cabb5a8becc50374cd6f8216d212ff: Ruff + host guard passed; contract mypy/config-doctor skipped by unchanged path scope.
- Documentation and complete handoff prepared in this package only. MAIN integration pending.
