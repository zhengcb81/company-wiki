# Reviewer evidence — W11 independent review 2 (`a6d12a53`)

These files were produced by the independent re-reviewer, offline, with the workspace
interpreter and the workspace `src`/`tests` on `PYTHONPATH`. They are reviewer artifacts,
not author artifacts.

## Files

| File | Contents |
|---|---|
| `review-2-probe-output.json` | 61 differential cases. For each case: current workspace module result, base `0d7ada21` result, candidate titles/kinds/dates, limitations, coverage, exclusions, `no_documents_claimed`, and recomputed `receipt.event_sha256`. |
| `review-2-cli-probe-output.json` | 15 public-CLI `--operation discover` subprocess cases: malformed rows/fields, byte-cap over/exact, both inputs, non-list pages, in-session module path. |
| `review-2-red-probe-rerun.txt` | Re-run of `delivery/w11/probes/red_probe.py` (base module rebuilt from git `0d7ada21`), semantically identical to the delivered `red-probe-output.txt`. |
| `review-2-head-bytes-probes.json` | Decisive cases re-run from the committed `git show a6d12a53:src/company_wiki/source_catalog/official_discovery.py` bytes (18,436 B / `a008e1cb…`), after a concurrent uncommitted worktree edit appeared. Binds the review to the reviewed SHA. |

## Commands (all offline)

```
$env:PYTHONPATH = '<workspace>/src;<workspace>/tests'
python -X utf8 -B -m pytest tests/integration/test_official_discovery_offline.py -q -p no:cacheprovider
python -X utf8 -B -m pytest tests/integration/test_official_source_flow.py -q -p no:cacheprovider
python -X utf8 -B -m pytest tests/integration/test_official_discovery_offline.py tests/integration/test_official_source_flow.py -q -k 'discovery or official_index_http or cn_fundraising or TestMaterial or TestNonMaterial or TestTimeWindow or TestUrlAndDedup or TestPagePayload or TestLimits or TestPublicCli' -p no:cacheprovider
```

Results: 40 passed (6.65 s), 36 passed (35.69 s), 47 passed / 29 deselected (11.58 s).
The reviewer's `--basetemp` was relocated by the repo conftest and removed.

## Base module

`git show 0d7ada21:src/company_wiki/source_catalog/official_discovery.py` → 11,008 B,
SHA-256 `7d8fb1292c6728adae9edf5a179242a3718b756e8659bbbb19154aff9f8ec2c3`, loaded as
`company_wiki.source_catalog._base_discovery` next to the workspace module.

## Sealed scan (independent)

- Audit run: 2,052 files / 166,731,220 B; exact-486,789 hits 0; body-SHA hits 0; 84 files in the 400–600 KB band.
- Holdout: 65 files / 17,360,200 B; exact-size hits 0; body-SHA hits 0; 5 files in the 400–600 KB band.
- All 11 `INPUTS.json` `W11-CWP-SOURCES` entries match byte count and SHA-256, including `faa5bf…/stdout.txt` = 2,839 B / `1c33f18b…`.
- Capture dir: `input-0001` and `consume-0001` 250 B each (same SHA), `stderr.txt` 0 B, `stdout.txt` 2,839 B. No body.

This corroborates `body_available=false`; it is not a whole-disk absence claim and does not
make the original replay possible. The derived sealed fixture used in the probes is
`derived_minimal_fixture` (three sealed titles/URLs), not an original page replay.
