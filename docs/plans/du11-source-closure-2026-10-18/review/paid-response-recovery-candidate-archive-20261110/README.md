# Paid-response durability handoff archive — 2026-11-10

This folder consolidates the candidate implementation handoff, batch recovery
receipt, design note, independent reviews, and original cleanup receipt from
the superseded `du11-extractive-runtime` worktree. The source files were copied
byte-for-byte and SHA-256 checked before the old checkout was considered for
removal. It records engineering evidence; it does not by itself close the
current real-summary/RF adoption milestone.

## What the archived evidence says

- The candidate used a content-addressed paid-response pin in the existing
  object store and nullable metadata on the existing reservation row. It did
  not add a second job ledger or cache.
- Focused TDD evidence records 18 initial RED failures / 2 passes, then the
  repaired component suite and a synthetic loopback crash/recovery path. The
  batch recovery handoff records 1 pass after the final source-mutation fix.
- Both independent reviews record PASS against their bound hashes. They cover
  source/test design and synthetic recovery. They do not claim full real
  summary artifact activation or RF consumption; those remain ROOT milestones.
- Live provider/API calls: 0. The loopback POST was synthetic. The handoff
  explicitly retains uncertainty for a remote charge before local bytes become
  durable and forbids blind resend or recovery of unbound objects.
- Original handoff cleanup had been rejected by the tool platform. On
  2026-11-10, each of its eight named Temp paths was rechecked under the exact
  `%LOCALAPPDATA%\Temp` root: all were ordinary non-reparse directories with
  zero files. Their remaining empty test directories were removed; no company
  originals, credentials, or production data were in those paths.

## Files

- `implementation-handoff.md/json`: candidate design, exact source/test
  fingerprints, scope, and limitations.
- `batch-recovery-handoff.json`: recovery test result and review binding.
- `paid-response-durability-design.md/json`: original design and boundaries.
- `paid-response-independent-review.md/json` and
  `paid-batch-recovery-test-independent-review.md/json`: independent review
  reports.
- `cleanup.json`: original failed cleanup attempt, retained as history.
- `cleanup-followup-20261110.json`: ROOT cleanup verification and result.

These copies do not imply that all archived intermediate logs are needed. The
old worktree's remaining `.planning` test logs and snapshots are disposable
once its current-main code ancestry and original-document correspondence are
confirmed in the local reconciliation report.
