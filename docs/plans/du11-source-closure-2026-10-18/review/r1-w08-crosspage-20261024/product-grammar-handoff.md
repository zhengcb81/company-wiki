# Product plural classification — frozen engineering handoff

## Result

Final new test was frozen before source writes: **17 failed / 21 passed**. Same 38 assertions now pass; bounded full selection/DU4 synthetic-contract-boundary/production set **274 passed / 2.05s**. Ruff PASS; mypy 3 sources PASS. Import guard resolves this W08 checkout. Exact raw hashes in `handoff.json`.

## Root fixes

- `product_reference.product_head_suffix` derives a trailing head from existing finite head vocabulary and Latin word boundaries. Relations NP classifier and independent subject classifier now reuse it; no arbitrary trailing-s stemming or new consumer dictionary. Shared head matching is case insensitive like the original suffix grammar.
- Existing English SUBJECT_TAIL tokens receive a letter boundary; Analysis is not truncated to Analys. No added modal/identity list.
- Shared first actual predicate boundary reuses the existing nonpredicate set. `and` does not erase a customer conjunct before the existing conjunct splitter can classify it.

No raw/ref rewriting, identity inference, new metric/schema, policy/predicate/reading/structure/continuity change or cap increase. Ambiguous company-name heads keep attribution unknown and cannot create a local reference dependency. Existing positive completion remains uncertain where its original operator scope is unproved; `positive-baseline.json` is pre-change evidence.

## Honest test history

`red-final` is the actual frozen 38-case RED; test rawSHA matches final GREEN. Earlier draft failures remain, including status spelling and overstrong CN/positive expectations corrected against the real schema **before production edits**. No old oracle was changed. `green` then exposed a genuine mixed-subject loss (37P/1F), repaired at the shared subject boundary owner without altering frozen assertions.

`green-final` includes 274P/7F caused only by absent tracked DU4 JSON test assets in the sparse checkout; ROOT restored those exact HEAD assets later. Do not classify those seven as product failures or claim they were run green here. `green-confirmed` explicitly lists the 274 available engineering cases; full DU4/public13 combined review remains ROOT responsibility.

## Cleanup and scope

All seven exclusively owned pytest tmp roots plus own mypy cache were initially absent and restored absent; exact checked paths are in cleanup.json. Zero model/download/network/original/PDF reads and no Git mutations. No changes to original public13, old tests, mother PWF, other harness worktrees, policy or predicate.

## Acceptance

This is a finite engineering freeze for ROOT's independent original13 and concentrated natural-suite replay. It does not sign off the earlier wholeannual14, which remains version-specific PARTIAL. Stop writing after this handoff.
