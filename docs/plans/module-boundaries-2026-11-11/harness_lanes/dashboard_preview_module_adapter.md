# Dashboard B-real document preview: modular intake card

## Assignment

Reconcile the unfinished B-real listing/preview work against current Dashboard `main`, then bring forward only the still-needed behavior through the current Dashboard module interfaces. Preserve the modular architecture. Do not merge the old staged tree as a unit.

## Baseline and evidence

- Current Dashboard `main`: `ff6e764f1e4da3aa9de73d1469770a653b8af654`.
- Historical worktree for reference only: `investment-dashboard/.worktrees/all31-listing-preview-combo`, HEAD `e158288c622553bff17ed631a90a33dc0b57a9e9`, with 120 staged paths. At the time of intake, 108 staged blobs already matched current main, 10 differed, and 2 UI files were absent from current main. The branch plan still said `IN_PROGRESS`; its staged set includes old PWF/evidence and must not be cherry-picked wholesale.
- Product candidates requiring current-main comparison were `apps/web/src/components/OriginalPreview.tsx`, `apps/web/src/views/Documents.tsx`, `backend/dashboard/transport/http.py`, and preview integration tests. Treat the old source as behavior/evidence only. Re-inventory paths and blobs before editing.
- The available CodeGraph index reported only 52 files and an older single-service shape inconsistent with the current main tree. Verify current `main` and live paths directly; do not use stale index output to justify an internal cross-module call.

## Module ownership

Use a new isolated worktree based on the current `main`; leave the historical staged worktree unchanged as a read-only reference until ROOT receives this card.

Allowed product scope:

- `apps/web/src/views/Documents.tsx`
- `apps/web/src/components/OriginalPreview.tsx` (or a current-main equivalent component)
- `backend/dashboard/transport/**` only for HTTP routing/serialization owned by transport
- preview-specific unit/integration/browser tests and an isolated handoff under this package's own directory

The UI must call the Dashboard's public HTTP API. Transport may call only the current public application operation/DTO. The existing Dashboard owner adapter/application operation must consume company-wiki's public source/stream port. Do not make UI or transport read physical company folders, SQLite, source manifests, other repositories' internal modules, or private symbols. Do not add a second CWP/FF client or a second data path.

Do not modify `backend/dashboard/application/ops/**`, Dashboard domain contracts, CWP/FF/RF/StockWiki/IQS code, shared package configuration, CI policy, or the C01 evidence paths. If the current public operation/DTO cannot express the required behavior, stop and document the smallest owner-level contract proposal instead of reaching into internals.

## Required work

1. Read the current Dashboard and company-wiki public browsing/streaming contracts, the owner request, and the staged B-real task receipts. Build a small path-by-path table: already present, still needed, replaced by a newer interface, or historical evidence only.
2. Reproduce the desired UI behavior from existing source/receipts. Preserve exact source identity/hash and locator; render loading, empty, unsupported, and owner-error states honestly. Keep the UI presentation-only.
3. Write failing tests at the owning boundary first. Route tests must prove that HTTP calls the public application operation and does not access adapters/private functions directly. UI tests must prove rendering and cancellation/error behavior through the HTTP contract. Keep existing security checks (untrusted HTML/PDF content inert, original bytes not rewritten) intact.
4. Implement only the smallest current-main changes. Prefer existing routes/DTOs and operation registration. Do not restore an old service dispatcher or an old single-file adapter.
5. Run the focused frontend/transport/preview tests and the existing public adapter/boundary suite that covers the touched path. Run one isolated end-to-end preview using the configured public source path when the existing test environment supports it; use a disposable test workspace and restore its initial file set afterward. Do not download production originals or call paid APIs.
6. An independent reviewer must inspect the final diff against current main, trace each call through public module interfaces, and run the focused acceptance command(s). Fix all blocking findings and bind the report to the exact final HEAD.

## Acceptance

The delivery is ready for ROOT only when:

- the diff is within the allowed product/test/PWF paths;
- the old staged tree has been reconciled path-by-path, with already-absorbed items omitted;
- no Dashboard layer reaches into a peer's private function, storage, or DB;
- the source ID/hash/locator survive transport and UI preview unchanged;
- focused tests and the independent review pass on the exact final HEAD;
- temporary test workspace is restored to its initial state;
- `handoff.md` and `handoff.json` state exact base/final SHA, paths, commands/results, reviewer-bound SHA, and any owner-contract limitation.

Do not merge or push. ROOT will compare the reviewed branch to current `main` and accept only the modular delta.
