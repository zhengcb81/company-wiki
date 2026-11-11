# P3 public stream and parser owner port — closeout

**Status:** implementation, focused regression, and independent review complete locally; publication status is recorded in `CURRENT_STATUS.md` and `CURRENT_STATUS.json` after the commit/push operation.

## Scope delivered

- Added pathless `SourceProcessingDescriptor` and public `SourceVersionPort` operations for describing, opening, verifying, and streaming one immutable source version.
- Added structural `SourceReadBudgetPort` / resettable budget contracts. The same caller-owned budget governs candidate count, bytes, deadline, and cancellation; the old fixed 256 MiB candidate cap was removed.
- Added a transactional `SourceChunkSink`: source chunks stay provisional until the source owner validates the requested identity, byte count, and SHA and commits a receipt. Failed candidates are discarded before same-version fallback.
- Moved processed-document format routing and parser staging into `processed_document_parser.py`. The endpoint composes only the public source and parser ports; source storage paths, catalog internals, and raw manifest objects do not cross to the endpoint or parser.
- Direct-normalization formats consume the verified content value. Other parser formats receive a parser-owned temporary stage only after source verification. Cleanup attempts the temporary-directory removal even if candidate discard fails; a cleanup error does not replace an earlier source/parser failure.
- Exported the source-version types through the `source_contract` package API. Replaced dynamic `getattr` sink dispatch with direct protocol methods and runtime structural protocol validation so the package boundary checker can verify the owner API.

## Root causes found and fixed during this node

1. The CLI's multi-format E2E initially failed because `VerifiedContent` was defined in the public contract implementation module but omitted from the package exports. The public export table now includes the verified content and receipt values.
2. The cross-package boundary checker rejected string-based sink dispatch because it could not prove the dynamic method belonged to the public protocol. Calls now bind to declared protocol methods directly.
3. Two pre-push scratch tests used pytest's deeply nested `%TEMP%` fixture as the simulated checkout root. That root always exceeded the unchanged 60 UTF-16 path budget on this host. The tests now create a unique, short-lived directory beside the checkout and keep the production path budget unchanged.
4. Independent review identified that discard failure could skip temporary-directory cleanup and that cleanup failure could mask a primary source/parser error. Two regression tests were written RED first; cleanup is now attempted in both cases, with a named cleanup error on an otherwise successful operation and a diagnostic warning while preserving a primary failure.
5. The fixed fast-gate then exposed two old narrative-read tests monkeypatching the removed `source_reader._read_verified_bytes` helper. Their original one-source-read/proof-order assertion is unchanged; the observation now wraps the public `SourceResolver.read_verified_source_location` port. The two tests passed in the host process.

## Verification

Final focused combination:

```text
python -m pytest -q tests/contract/test_processed_document_cli.py tests/contract/test_processed_document_owner_boundary.py tests/contract/test_source_version_reader.py tests/contract/test_r4b02_candidate_selection.py tests/contract/test_r4b03_stable_bytes.py tests/contract/test_source_catalog_module_contracts.py tests/contract/test_layer_public_boundaries.py tests/unit/test_pre_push_gate.py
```

Result: **205 passed, 1 skipped in 63.58 seconds**. The set exercises real CLI flows for text, PDF, XLSX, and DOCX fixtures; exact identity and source-byte checks; streaming fallback, cancellation, byte accounting, public-owner boundaries; and fast-gate inventory. The one skip is retained and is not counted as a pass.

After the final logging-only diagnostic adjustment, the five cleanup/public-boundary tests passed again. Ruff passed on all changed source, test, and gate files. Mypy passed on the seven touched source-contract/catalog modules.

The exact host fast-gate command, after replacing the stale private-helper test spy, passed **277/277 in 59.18 seconds**. Running the same gate under the restricted sandbox initially produced 16 `WinError 5` hard-link failures in unrelated temporary fixtures; the same gate under the authorized host process removed those failures and isolated the two genuine stale test references described above. No cases were skipped or removed to obtain the green result.

Independent read-only review: **PASS, no blockers**. Review scope was the current stream/parser owner-port implementation and cleanup/boundary changes; reviewer did not run tests. The review does not assert whole-project decoupling is complete.

## Remaining scope

This closes one P3 implementation node only. Whole-project modularity remains **OPEN**. The next P3 work is to replay any historical stream/canonical candidate claims against the current mainline before adopting them, then continue the remaining owner-boundary scan. Cross-package and cross-repository boundaries, R4 workload accounting, refreshed real-summary/cache-recovery/RF-adoption acceptance, and the fixed-company review loop remain open under the parent plan.
