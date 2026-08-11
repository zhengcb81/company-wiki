# FC-803 Independent Review Report

- Reviewer: reviewer-fc803-independent (did NOT implement FC-803)
- Review date: 2026-08-11
- Verdict: **ACCEPTED**
- Evidence receipt: `assurance/fc/FC-803/12_reviewer_receipt.json` (self-hash `23ee8c5e...`)

## Scope

FC-803 (minimal download + second-request zero fetch/write) per the FCAP-2026-08-09-r2
honest-implementer protocol. Sealed triplet: revenue `84c9e7e4` (unchanged) / filing
`354b171` -> `065976e` / wiki `656adac` -> `8a2efdd`. The review ran fresh against the
clean worktree and the read-only main checkouts.

## 1. Receipt + triplets

- Implementer receipt `11_implementer_receipt.json` present; base/result triplets match
  the sealed values and repo HEADs; revenue-forecast HEAD == base == result.
- `plan_sha256 158fc1e1...` recomputed from `task_plan.md` at revenue 2d64186: MATCH.
- `command_registry_sha256 215b8077...` recomputed on disk: MATCH.
- Ancestry: base filing 354b171 ancestor of result 065976e (FILING-ANCESTRY-OK); base wiki
  656adac ancestor of result 8a2efdd (WIKI-ANCESTRY-OK). Wiki HEAD 18a2792 = 8a2efdd +
  receipt-docs commit (only `assurance/fc/FC-803/`).

## 2. Diff scope

- filing `git diff --stat 354b171 065976e` = exactly 3 files:
  `scripts/fetch_filing.py` (+8/-1), `tests/e2e_support/spy_adapter.py` (+136),
  `tests/test_fc803_minimal_download.py` (+269).
- wiki `git diff --stat 656adac 8a2efdd` = exactly 2 files:
  `src/company_wiki/source_catalog/close_gap.py`, `cli.py`. Zero unrelated changes.

## 3. Code read

- `spy_adapter.py`: real `json_command_v1` subprocess provider; every discover/fetch
  invocation appends a JSONL line to `SPY_ADAPTER_LOG` (action + payload + argv); discovery
  returns scripted candidates from `SPY_ADAPTER_FIXTURE`; fetch writes a deterministic PDF
  into the staging dir and echoes a matching receipt; `SPY_ADAPTER_FAULT=provider_unavailable`
  exits non-zero with the structured 1.0 error JSON (LT-05 path).
- `fetch_filing.py:698`: `has_missing = bool(gap_plan and gap_plan.get("missing"))` gates the
  close-gap transaction; empty plans fall through to a structured `{"status": "gap", ...}`
  response carrying the gap_plan (reuse / provider_unavailable / future details).
- `close_gap.py` step 3: `staged_request` is built per missing candidate
  (fiscal_year / provider_document_id / form_type / provider), `mode="exact"`; the failure
  path calls `_cleanup_staging(staged_request.request_id)` (REAL-FIX-3) whose dir name is
  derived from the request id tail.
- `cli.py`: close-gap gains `--allow-acquisition-while-paused` + `--worker-config`; `main()`
  raises `RuntimeError` when worker `desired_state == "paused"` without the bypass flag
  (REAL-FIX-2).

## 4. Fresh runs (real cross-process chain)

| Command | Result |
|---|---|
| `pytest tests/test_fc803_minimal_download.py -q` (filing) | **5 passed** (34.6s) |
| `pytest tests/test_fc802_gap_orchestration.py tests/test_fetch_filing.py -q` | 210 passed, 2 skipped, 54 subtests |
| `ruff check` (3 filing files) | clean |
| `pytest -B tests/contract/test_close_gap_fc801.py -q` (wiki worktree) | **7 passed** |
| `ruff check` (close_gap.py + cli.py) | clean |

The T1 tests run the REAL chain: filing-fetch CLI subprocess -> company-wiki CLI subprocess
(editable install -> main checkout src) -> spy adapter subprocess, against a temp wiki root.
Zero mocks. LT-09 asserts the second identical request yields `status gap, missing==[]` with
spy fetch count still 1 and `companies/` byte-unchanged.

## 5. Mutation replay (adversarial, both killed)

- **M1** (remove the actionable gate: `has_missing = True`):
  `-k "lt01 or lt05 or lt07"` -> **3 failed** (lt01, lt05, lt07), 2 deselected. Reverted;
  `git diff HEAD` empty; post-revert full T1 re-run 5 passed (27.5s).
- **M2b** (null the per-candidate binding in close_gap.py, applied in a temporary wiki
  worktree at 8a2efdd, lt09 run with PYTHONPATH to the mutated src):
  **1 failed** — `AssertionError: 0 != 1` at `test_fc803_minimal_download.py:179`
  (spy fetch count): the close-gap re-resolved the older local document as reused and
  never staged the gap — precisely the REAL-FIX-1 failure mode. Worktree removed.

## 6. Validator

`python tools/receipt_validator.py --receipt .../FC-803/11_implementer_receipt.json`
-> `OK: 1 receipt(s) valid` (exit 0).

## 7. Side effects

No downloads (spy writes only into temp staging dirs). Zero writes outside
`12_reviewer_receipt.json` + this report. Filing-fetch main checkout clean; company-wiki
main checkout untouched (its pre-existing `llm_cost_log.csv` modification and untracked
FC-802/REVIEWER_REPORT_R2.md predate this review).

## Findings

None. Both mandated mutations killed. **Verdict: ACCEPTED.**
