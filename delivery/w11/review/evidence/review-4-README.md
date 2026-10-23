# Reviewer evidence — W11 independent review 4 (`6b538ca2`)

Produced by the independent re-reviewer, offline, with the workspace interpreter and
`<workspace>/src` on `PYTHONPATH`. Reviewer artifacts, not author artifacts.

## Files

| File | Contents |
|---|---|
| `review-4-probe-output.json` | 78 differential cases. Product probes load `git show 6b538ca2:src/company_wiki/source_catalog/official_discovery.py` (22,353 B / `6bba88a2…`); old results load `2e1dfd04` (22,173 B / `4eaeee5f…`). Covers the 11 exact section labels with `.pdf`, table rows, dated `<li>`/`<article>`, listing/nav links, NR-01/02/03/04/05/07/08/10, IR-01 positives, notices, limits, dedupe and malformed URLs. |
| `review-4-cli-scale.json` | Public CLI on CN/EN announcement tables and nav listings, invalid page URL/malformed row/byte cap; 1k/10k anchor scaling (`6b538ca2` 10k = 0.314 s vs `2e1dfd04` 0.332 s); `hashlib.sha256` counting (1 whole-page hash, 32 calls). |

## Commands

```
$env:PYTHONPATH = '<workspace>/src;<workspace>/tests'
python -X utf8 -B -m pytest tests/integration/test_official_discovery_offline.py -q -p no:cacheprovider --collect-only
python -X utf8 -B -m pytest tests/integration/test_official_source_flow.py -q -p no:cacheprovider --collect-only
python -X utf8 -B -m pytest tests/integration/test_official_discovery_offline.py tests/integration/test_official_source_flow.py -q -p no:cacheprovider
python -X utf8 -B -m pytest tests/integration/test_official_discovery_offline.py tests/integration/test_official_source_flow.py -q -k '<delivered selection>' -p no:cacheprovider
```

Results: 62 + 36 collected; 98 passed full (87.51 s); 69 passed / 29 deselected selection (17.16 s). Reviewer basetemps were relocated by the repo conftest and removed.

## Binding / packaging

- Reviewed HEAD `6b538ca2f18fb8d5805f2ff59a41404b6e8302cd`; committed discovery blob 22,353 B / `6bba88a2…`; test file 31,358 B / `b1a0da02…`.
- `2e1dfd04` (22,173 B / `4eaeee5f…`) used only as the differential baseline.
- Red-probe output is UTF-8 **BOM-free** and parses; `push-gate-round2.log` absent; JUnit 69 cases / no failures; log and JUnit SHAs match `test_results.json`; 11/11 `INPUTS.json` W11 entries match; config hashes unchanged; `companies/`, `.source_catalog/`, `catalog/` absent.
- Remaining handoff-document items (not product): `handoff.json` absent; handoff known-limits missing the extensionless-document-endpoint residual; `prepared_at` postdates the commit; `test_results.json` records only the 69 selection.
