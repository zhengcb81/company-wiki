# Reviewer evidence — W11 independent review 1

These files are raw output from the independent reviewer, not author artifacts. They were produced offline with the workspace interpreter and the workspace `src`/`tests` on `PYTHONPATH`.

## Test logs

| File | Command | Result |
|---|---|---|
| `offline-26-stdout.txt` | `python -X utf8 -B -m pytest tests/integration/test_official_discovery_offline.py -q -p no:cacheprovider --basetemp=<workspace>/tmp/review-pytest-1` | 26 passed in 17.15 s |
| `existing-36-stdout.txt` | `python -X utf8 -B -m pytest tests/integration/test_official_source_flow.py -q -p no:cacheprovider` | 36 passed in 48.05 s (first run: 36 passed in 141.62 s) |
| `combined-selection-stdout.txt` | `python -X utf8 -B -m pytest tests/integration/test_official_discovery_offline.py tests/integration/test_official_source_flow.py -q -k 'discovery or official_index_http or cn_fundraising or TestMaterial or TestNonMaterial or TestTimeWindow or TestUrlAndDedup or TestPagePayload or TestLimits or TestPublicCli' -p no:cacheprovider` | 33 passed, 29 deselected in 15.24 s |

`PYTHONPATH` for all three: `<workspace>/src;<workspace>/tests`.

## Probe outputs

- `probe-output.json` — 45 probes. Base module for differential comparison was extracted with
  `git show 0d7ada21:src/company_wiki/source_catalog/official_discovery.py > tmp/review/base_discovery.py`
  (raw blob 11,008 B, SHA-256 `7d8fb1292c6728adae9edf5a179242a3718b756e8659bbbb19154aff9f8ec2c3`)
  and loaded as `company_wiki.source_catalog._base_discovery` next to the patched workspace module.
- `extra-probe-output.json` — 14 probes (page-level timestamps, multi-page limits, CLI edges, derived dynamic variant).

The probe scripts themselves were reviewer scratch and were removed after the review; every input and expected/actual result is recorded in `independent-review-1.md` and in these JSON files. The sealed-result derived fixture is `derived_minimal_fixture` (403 B, SHA-256 `37e86e5969f210b5499d17b858a05621b67efbc0159dfda359cf92a6a444e516`), not an original replay; the 486,789 B body remains absent.

## Sealed evidence scan (independent)

- Audit run `runs/r1-20261021-cn-wuxi-apptec`: 2,052 files / 166,731,220 bytes; exact-size 486,789 hits = 0; SHA-256 `f1e822a8…` hits = 0; 89 files in the 400–600 KB band.
- Holdout `.planning/shared-reading-production/r1-holdout-20261021`: 65 files / 17,360,200 bytes; exact-size hits = 0; body-SHA hits = 0.
- All 11 `INPUTS.json` `W11-CWP-SOURCES` entries match byte count and SHA-256, including `faa5bf…/stdout.txt` = 2,839 B / `1c33f18b…`.

This corroborates `body_available=false`. It is not a whole-disk absence claim and does not make the original replay possible.
