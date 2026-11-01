# P2 test-fixture ownership delta — independent addendum

Decision: **PASS; no new blocking finding.** This is a small test-material review only. The production code and v5 engineering acceptance in `review-v5-final.md` remain unchanged; company economic research remains OPEN.

The helper at `C:/Users/郑曾波/Projects/_r2/tests/test_shared_reading_narrative_contract.py:27` changes only `FIXTURES` from the docs archive to `tests/fixtures/shared_reading_wire`. Independent normalized-text comparison found no test-logic or assertion change. Its exact file SHA-256 is `9e82226d50aed9a042689831e385f0ae35f5a95809d732657fb97ffcf5cd7826`.

All six copied files, **12,018 bytes total**, are independently byte-identical to the existing RF docs archive. Both compressed bundle bodies also retain the hashes and byte sizes declared by their existing requests; no gzip or JSON regeneration was substituted for copying.

| File under `tests/fixtures/shared_reading_wire/` | Bytes | SHA-256 |
|---|---:|---|
| `actual-080-bundle.json.gz` | 1,435 | `3113b0a33b25cdb241408a9929335dc2a6a2d8b21ea6822a17f016a88ac17f11` |
| `actual-080-receipt.jsonl` | 1,855 | `b6966a1ac7e88fb3f12571a20f5dbe4bcbb75b963b0ee6ec5c10a42ca737be48` |
| `actual-080-request.json` | 981 | `112465239a3217575518a21e28db6f2bbd0c35407f2e554c1323a4a2cc7cef85` |
| `actual-090-bundle.json.gz` | 4,905 | `941b3c562b6d2b5936ec10829f75e74b520b54f4df4976237cf6f88e4e53ef68` |
| `actual-090-receipt.jsonl` | 1,860 | `e8bf242d6f1d3b508154ace393c4dafff2bf73b6b8f9a681e3c25dc985b15aaf` |
| `actual-090-request.json` | 982 | `25cfd6cf747d8085251ab0d7677241294c09ecf53a79bc0fea77cf61ee1b9ed4` |

`quality.yml` is unchanged: its existing sparse checkout includes `tests` and excludes `docs`. The transitive `projected_context → actual()` reader now resolves all six saved wire files within that test-owned tree. The old archive remains intact in the RF main checkout, while the reviewed sparse `_r2` work area has no docs fixture directory. No CI download, docs-tree expansion, runtime dependency, or shipping of test material is added.

Recorded execution evidence was read, not rerun by this reviewer:

- `rf-ci-fixture-red.log`: after docs removal, the projected formal-publication case fails with the expected `FileNotFoundError` for `actual-090-request.json`; 1 failed, 3 passed, 25 deselected. This establishes the actual transitive material failure.
- `rf-ci-fixture-green.log`: with the test-owned copies and docs still absent, **81 passed in 4.21 seconds** (new lineage 29 plus related wire 52, as identified by ROOT).

The independent stdlib probe records 10 passing predicates in `fixture-migration-probe.json`, including all six byte comparisons, one-constant-only helper change, current sparse/docs boundaries, unchanged workflow, and exact equality of all previously frozen production/test code and v5 artifact hashes. It ran no author script, tests, source parser, model, download or network call. No broader production re-signature or remote-CI claim is made here.
