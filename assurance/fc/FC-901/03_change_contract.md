# FC-901 Change Contract — artifact 绑定迁移（dry-run 分桶）

> Owner: company-wiki · Base triplet: revenue `3617335` / filing `81d9cd9` / wiki `9907a3b`
> Dependencies: FC-405 (accepted), FC-704 (accepted) · Scenario IDs: MIG-01, MIG-03, MIG-05

## Intended behavior delta (observable)

A read-only **dry-run** classifies every legacy artifact in the catalog into exactly
one of five buckets; an **authorized apply** writes shadow source-bindings for the
`bindable` subset only. Catalog artifact rows/files are never mutated or deleted.

## Buckets (exactly one per artifact; first failing gate wins, reusing validate_artifact)

| Bucket | Assigned when (`validate_artifact` reason) |
|---|---|
| `bindable` | `reusable=True` — source/document/content/generator/schema all provable |
| `hash_mismatch` | `artifact_hash_mismatch` (file bytes ≠ content_sha256) / `artifact_hash_malformed` |
| `missing_bytes` | `artifact_file_missing` |
| `unknown_generator` | `artifact_generator_unregistered` |
| `legacy_unbound` | any other reason — incl. `artifact_source_sha_mismatch` (lineage to source unverifiable), `artifact_source_binding_mismatch`, status/schema/created_at/path — provenance not provable, **never guessed** (MIG-05) |

Rationale: `hash_mismatch` = the artifact's OWN content doesn't verify (file
corruption); `source_sha_mismatch` = lineage to the source can't be proven, which is
a provenance failure (legacy_unbound), not file corruption.

An artifact whose source row cannot be loaded (null `source_id`, or no matching
`sources` row, or document lacks `primary_source_id`) goes to `legacy_unbound`.

## Reconciliation (MIG-01 closure)

`input == bindable + hash_mismatch + missing_bytes + unknown_generator + legacy_unbound`
(exactly one bucket per artifact; no artifact unclassified). The result also carries
a per-bucket capacity estimate (byte_size sum) and, per `bindable` artifact, a binding
proposal: `(artifact_id → source_id, content_sha256, generator_name/version, bundle_hash)`.

## Idempotency (MIG-03)

- Two consecutive dry-runs over an unchanged catalog produce **byte-identical** result
  JSON (deterministic ordering by artifact_id) and identical proposal/bundle hashes.
- Apply twice creates **zero duplicate** bindings (binding key = artifact_id; second
  apply is a no-op skip, recorded as `already_bound`, not an insert).

## Apply semantics (authorized this batch; zero-deletion, reversible)

- New table `artifact_bindings` (shadow): insert-only.
  `(binding_id, artifact_id, source_id, document_id, content_sha256, generator_name,
   generator_version, bundle_hash, evidence_basis, visibility_state='shadow',
   schema_version, created_at)`; `UNIQUE(artifact_id)`.
- The legacy `artifacts` table is **never** UPDATEd/DELETEd.
- Reversal = `DELETE FROM artifact_bindings WHERE binding_id IN (...)` (shadow rows only).

## Allowed symbols / files

- NEW `src/company_wiki/source_catalog/artifact_backfill.py` (classify + run + CLI;
  owns the `artifact_bindings` DDL via `CREATE TABLE IF NOT EXISTS` in apply mode
  so the legacy 49GB catalog is not forced through a store.py schema migration).
- NEW `tests/contract/test_source_catalog_artifact_backfill.py`.
- No change to `store.py`, `resolver.py`, or any existing production module.

## Forbidden changes

- DELETE / UPDATE on `artifacts`, `documents`, `sources`, `locations`, or any real root file.
- Any write path in `dry-run` mode.
- Guessing `source_id`/`period`/`fiscal_year` from file names or paths (MIG-05).
- Lowering validate_artifact gates or skipping buckets to inflate `bindable`.
- Hardcoding generator names outside the passed-in registry.

## Expected call-edge delta

- New production symbol `run_artifact_backfill` (caller>=1 via CLI now; FC-902 resolver
  consumes `artifact_bindings` next). No legacy edge removed in this FC.

## Side-effect budget

| Effect | Budget |
|---|---|
| artifact file reads | ≤ input artifact count (7712 production) |
| catalog writes (dry-run) | 0 |
| catalog writes (apply) | = `bindable` count (insert into `artifact_bindings` only) |
| external root writes | 0 |
| deletions | 0 |

## Diff budget

~1 new module (≤200 lines) + DDL (~12 lines) + CLI wiring + tests (≤250 lines).
Exceeds → split into FC-901-a (dry-run classify) / FC-901-b (apply+bindings table).

## Rollback

`DELETE FROM artifact_bindings WHERE created_by='fc-901'` (shadow rows only); dry-run
leaves zero footprint. No artifacts/documents/sources touched.
