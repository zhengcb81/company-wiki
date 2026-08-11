# FC-905-b Independent Review Report (consumer side)

Reviewer: `reviewer-fc905b-independent` · Reviewed: 2026-08-11T19:38:15Z
Method: independent re-proof on clean checkouts per `independent_review_protocol.md`.
Implementer receipt sha256: `f2ccbb08786e40d3b037a980d81d87d08e8250948d3f9d23af45d170c8794f64`.

## 1. Triplet + HEAD verification

| Repo | Result triplet HEAD | Worktree | Match |
|---|---|---|---|
| revenue | `b5c4dfd8073335344c0b94590701de1e6e288998` | `fc-905b-rev` | yes (detached, clean) |
| filing | `6b617714f253400e6cba93c9aa7fc0fbe3ed46bc` | `fc-905b-fil` | yes (detached, clean) |
| wiki | `fbb482891776a1e4fceab1c97be882ea5bee4604` | company-wiki | yes (unchanged) |

Base triplet: revenue `4ff3d2e17e81fd0c8421768e035bdf3bda30dc0b` / filing
`959d04cdbe2115c8e01fa39a2d5dfe748cc4fedd` / wiki `fbb482891776a1e4fceab1c97be882ea5bee4604`.

## 2. Hash verification

- plan sha256: `0bc6b9f7d6707e470e55c22759d37c18404172081ecd176d2883e184c61fafaa` — MATCH
- command_registry sha256: `215b8077169126b2c4a5eca9d8d6237f291757c2559f6ae6e0ae8ff1c806b089` — MATCH
- implementer receipt sha256 (computed): `f2ccbb08786e40d3b037a980d81d87d08e8250948d3f9d23af45d170c8794f64`

## 3. Dependency receipts (decision accepted)

- company-wiki `assurance/fc/FC-905/12_reviewer_receipt.json` — FC-905-a, verdict `accepted`, reviewer `reviewer-fc905a-independent`, 2026-08-11T19:15:24Z.
- revenue-forecast `assurance/fc/FC-904/12_reviewer_receipt.json` — verdict `accepted`, reviewer `reviewer-fc904-independent`, 2026-08-11T14:05:00Z.

## 4. Changed files vs allowlist

- revenue diff `4ff3d2e..HEAD`: 5 files (scripts/source_preparation.py, tests/test_fc905b_trusted_receipt.py, tests/test_fc904_artifact_selection.py, tests/test_source_preparation.py, tests/test_preparation_e2e_success.py) — all in allowlist.
- filing diff `959d04c..HEAD`: 4 files (scripts/filing_contracts.py, tests/test_fc905b_envelope_fields.py, tests/test_fc903_bundle_contract.py, tests/test_fetch_filing.py) — all in allowlist.
- No user dirty paths in either diff (wiki dirty path `llm_cost_log.csv` is pre-existing, repo untouched by this FC).

## 5. Adversarial diff review

Revenue (`scripts/source_preparation.py`):
- Hardcoded `prompt_injection_status="not_detected"` GONE (base grep 1 → HEAD 0).
- Hardcoded `"parser_calls": 0, "llm_calls": 0` GONE (base grep 1 → HEAD 0).
- `not_reviewed` (and defensively-missing status → `not_reviewed`) raises RuntimeError BEFORE `build_revenue_source_record`.
- `parser_calls`/`llm_calls` None → RuntimeError (never 0).
- Envelope status/counts flow into the record and `reuse_receipt` (which also carries `prompt_injection_status`).
- E2E fixture document now carries `prompt_injection_review` (status not_detected, reviewer, evidence sha256) so the real chain passes the policy gate.

Filing (`scripts/filing_contracts.py`):
- `RESOLUTION_ENVELOPE_PROMPT_INJECTION_STATUSES = {not_detected, detected_and_ignored, not_reviewed}`; out-of-enum → `FilingFetchError upstream_error`.
- Counts: non-negative int or null; bool/float/str/negative all rejected (probe re-confirmed).
- N-1 normalization on a COPY (input untouched, copy returned): missing status → explicit `not_reviewed`, missing counts → `None` — never faked, never clobbered. Probe: status missing + counts present → counts survive, input identical after call.
- No write operations in either production delta (grep of `^+` lines for write/insert/execute/save/open: none).

## 6. Command replays (python -B, clean checkouts)

| Command | Result |
|---|---|
| revenue `pytest tests/test_fc905b_trusted_receipt.py -q` | **6 passed** |
| filing `pytest tests/test_fc905b_envelope_fields.py -q` | **7 passed** |
| revenue `pytest tests/ -q` | **402 passed, 106 subtests, 0 failures** (18.93s) |
| filing `pytest tests/ -q` | **283 passed, 11 skipped (3 T3 without env), 54 subtests, 0 failures** (79.22s) |
| ruff check + py_compile (changed files, both repos) | clean / compile OK |

Layout note: the first revenue full run showed 12 failures — every one traced to the
review checkout layout (manifest/contract/e2e tests resolve sibling repos at
`parents[2]/<revenue-forecast|filing-fetch|company-wiki>` which did not exist next to
`fc-905b-rev`/`fc-905b-fil`). Directory junctions to the review worktrees and the real
wiki restored the canonical layout; with the layout normalized the full suite passes
402/106 exactly as the implementer recorded. No code was modified.

## 7. RED replay

`git show 4ff3d2e:scripts/source_preparation.py` — `not_detected` count = 1
(hardcoded status) and `"parser_calls": 0` count = 1 (hardcoded counts). At HEAD both
are 0. RED confirmed.

## 8. Mutation replay (all four, temp-mutate → single test → FAIL → restore)

| Mutation | Change | Expect | Observed |
|---|---|---|---|
| FC-905b-M1 | disable `if prompt_injection_status == "not_reviewed":` | test_b1 FAIL | FAILED — killed |
| FC-905b-M2 | disable `if parser_calls is None or llm_calls is None:` | test_b5 FAIL | FAILED — killed |
| FC-905b-M3 | disable status enum validation (filing) | filing test_b5 FAIL | FAILED — killed |
| FC-905b-M4 | disable N-1 status normalization (filing) | filing test_b1 FAIL | FAILED — killed |

All restored via `git checkout --`; focused suites re-passed (6 / 7); both worktrees
git-clean afterward.

## 9. Side-effect reconciliation

Production deltas are read-only (envelope.get / pure validation). Full-suite replays
ran the real three-repo E2E chain against tmp fixture wikis (zero downloads, fixture
reuse). No catalog mutations, no external root writes, no new writes in diffs. Both
worktrees clean after all replay activity.

## 10. CodeGraph reachability

The CodeGraph index (main repo) did not record caller edges for `prepare_source` /
`validate_resolution_envelope` (index reflects main tree; callers query empty).
Reachability verified by direct source evidence on clean checkouts:
- `prepare_source` — single production entry via `main()` (source_preparation.py:150,
  call at 167, `__main__` at 186).
- `validate_resolution_envelope` — called by fetch_filing.py:791 (existing
  validate/forward path).
- FC-905-b adds no new call edges. Matches implementer claim (1 → 1).

## 11. Observations (non-blocking)

- Installed skill copies at `~/.agents/skills/filing-fetch`, `~/.claude/skills/filing-fetch`,
  `~/.codex/skills/filing-fetch` are stale by 11 files (`sync_installs_b3.py --check`
  exit 1: test files incl. FC-905-b ones, SKILL.md, references/contract-ownership.md).
  This is pre-existing deployment staleness of the live installation (also includes
  test_fc805_real_download_t3.py, i.e. predates FC-805) and is outside the repo state
  this FC seals; runtime scripts are NOT in the drift. Deployment refresh via
  `--apply` is a release-owner action, not a defect of the change.
- `revenue.quality.sync` registry entry uses `sync_installations.py --check`, a flag the
  tool does not implement (it has `--apply|--print-manifest`). Pre-existing registry/tool
  mismatch, unrelated to FC-905-b.

## 12. Verdict

**ACCEPTED** — all mandatory commands replayed from clean checkouts, all four mutations
killed, RED proven, no new writes, no unresolved findings.
