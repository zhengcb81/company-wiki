# X-C01 Evidence Portability Rework

## Assignment

Make the completed C01 schema-7 rehearsal evidence reproducible after a fresh Windows checkout, then deliver the exact revised evidence package for ROOT review. Work only in `investment-dashboard` and only on C01 evidence, verifier, tests, and handoff files. Do not edit Dashboard product code or any other repository.

## Why this card exists

- Dashboard `main` is modular and currently at `ff6e764f1e4da3aa9de73d1469770a653b8af654`.
- C01 candidate branch `codex/x-c01-schema7-rehearsal` is at `9bfadfe84f64d5b5de0b3a1fc1598ad7d16dd254`.
- Its verifier passed 28/28 in the candidate worktree under explicit UTF-8, but after a local merge into main the same verifier failed because checkout bytes differed from the manifest. The merge was undone; main is unchanged.
- With `core.autocrlf=true`, `tests/audit/c01_schema7_rehearsal/baseline-state.txt` measured 298 working-tree bytes versus 297 committed Git-blob bytes; `ce/ce01-backup.log` measured 371 versus 369. This is line-ending normalization, not a product or encoding failure.
- Main also contains `handoffs/external/X-C01-SCHEMA7-REHEARSAL-FINALIZE-01/README.md`, which the candidate manifest did not enumerate. A complete evidence package must account for it and every other retained C01 file.

## Ownership boundary

Allowed paths, all within the Dashboard repository:

- `handoffs/external/X-C01-SCHEMA7-REHEARSAL-01/**`
- `handoffs/external/X-C01-SCHEMA7-REHEARSAL-FINALIZE-01/**`
- `tests/audit/c01_schema7_rehearsal/**`
- `tests/e2e/c01_schema7_rehearsal/**`
- a narrowly scoped C01-only text-attribute file if needed for reproducibility

Do not change `backend/dashboard/**`, `apps/web/**`, shared package configuration, public DTOs, operation registration, other evidence packages, or another repository. Keep C01 evidence self-contained and consume no other module's private implementation.

## Required implementation

1. Inventory the exact C01 package paths on current main and candidate. Preserve the already-present README and all existing evidence; do not silently omit, overwrite, or delete a file to make a manifest pass.
2. Choose and document one portable byte-binding rule. Preferred rule: hash strict UTF-8 text after a documented CRLF-to-LF canonicalization, reject bare CR, and hash any binary payload as raw bytes. Record canonical byte length separately from checkout byte length. If scoped Git attributes are chosen instead, prove they work with both `core.autocrlf=true` and `false` on fresh checkouts.
3. Make the manifest describe the exact retained file set, not just a selected subset. The verifier must report missing, extra, symlink/reparse, unreadable, and content-changed entries distinctly. It must validate its own package root and must not mutate the repository.
4. Extend C01-focused tests with LF/CRLF materialization controls, manifest extra/missing-file controls, tamper detection, and the existing rehearsal scenario. Keep the 28 original scenario checks intact; do not lower assertions or use a partial PASS as completion.
5. Re-run the focused C01 verifier/test suite from two fresh isolated checkouts configured with `core.autocrlf=true` and `false`. Record exact commit, commands, exit codes, case counts, cleanup result, and final source/status hashes.
6. An independent reviewer must inspect the final commit and rerun the portable manifest checks. Fix every blocking finding and obtain a new review bound to the exact final HEAD before handoff.

## Acceptance and handoff interface

Deliver `handoff.md` and `handoff.json` in the C01 finalize directory. Both must identify:

- repository, branch, base main SHA, final HEAD SHA, and exact changed path list;
- manifest algorithm/version, manifest SHA-256, and exact file count;
- both checkout-mode results and the unchanged 28-scenario result;
- evidence that all temporary roots were absent before and after, and no product/data mutation occurred;
- independent reviewer identity/role, exact final HEAD reviewed, commands run, findings, and PASS;
- any remaining limitation, with no claim that product functionality or overall Dashboard integration changed.

ROOT accepts this package only if the final manifest binds the committed content reproducibly, the two checkout modes and original scenarios pass, the independent review is tied to the final HEAD, and the diff remains inside this card's allowed paths. A failed check is a repair item, not a reason to weaken the verifier.

## Stop conditions

Stop and report if a required change would touch Dashboard product code, a shared module interface, another repository, or original company data. Do not merge or push; hand off the final reviewed branch for ROOT acceptance.
