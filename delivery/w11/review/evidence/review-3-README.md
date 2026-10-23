# Reviewer evidence — W11 independent review 3 (`2e1dfd04`)

Produced by the independent re-reviewer, offline, with the workspace interpreter and
`<workspace>/src` on `PYTHONPATH`. Reviewer artifacts, not author artifacts.

## Files

| File | Contents |
|---|---|
| `review-3-probe-output.json` | 75 differential cases. Product probes load `git show 2e1dfd04:src/company_wiki/source_catalog/official_discovery.py` (22,173 B / `4eaeee5f…`); old results load `a6d12a53` (18,436 B / `a008e1cb…`). Includes NR-01/02/03/04/05/07/08/10 checks, IR-01 positives, notices, limits, URL/dedup and the R3-01 exact-section-label regression. |
| `review-3-cli-scale.json` | Public-CLI invalid-page-URL/malformed-row/byte-cap cases; 1k/5k/10k anchor scaling (`2e1dfd04` 10k = 0.808 s vs `a6d12a53` 7.292 s); `hashlib.sha256` call counts (1 whole-page hash vs 30). |
| `review-3-cli-section-labels.json` | Public-CLI reproduction of R3-01: CN `公告` announcement table and EN `Press Release`/`Announcement` table both return `candidates=[]`, `checked_index_only`, `limitations=[]`; plus result/receipt/candidate schema-key comparison. |

## Commands

```
$env:PYTHONPATH = '<workspace>/src;<workspace>/tests'
python -X utf8 -B -m pytest tests/integration/test_official_discovery_offline.py -q -p no:cacheprovider
python -X utf8 -B -m pytest tests/integration/test_official_source_flow.py -q -p no:cacheprovider
python -X utf8 -B -m pytest tests/integration/test_official_discovery_offline.py tests/integration/test_official_source_flow.py -q -k '<delivered selection>' -p no:cacheprovider
```

Results: 48 passed (26.10 s), 36 passed (89.07 s), 55 passed / 29 deselected (27.12 s).
The reviewer's explicit `--basetemp` was relocated by the repo conftest and removed.

## Binding

- Reviewed HEAD `2e1dfd041fdfb9e14a0a1b911049b077df1e06d4`; committed discovery blob 22,173 B / `4eaeee5f…`; test file 29,924 B / `8e6a558d…`.
- `a6d12a53` was used only as the differential baseline (18,436 B / `a008e1cb…`).
- Delivery: all `delivery/w11/**/*.json` parses (red-probe with `utf-8-sig`), JUnit 55 cases/no failures, log and JUnit SHAs match `test_results.json`, 11/11 `INPUTS.json` W11 entries match, config hashes unchanged, `companies/`, `.source_catalog/`, `catalog/` absent.
