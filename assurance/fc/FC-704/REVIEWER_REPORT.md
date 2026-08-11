# FC-704 Independent Review Report — reviewer-fc704-independent

**Verdict: ACCEPTED** (reviewed_at 2026-08-11, schema 2.0)

FC-704 (ResolutionEnvelope + AcquisitionTrace) is the anti-fake-evidence
work item: download counts on the reuse receipt must come from the
acquisition journal/events, never inferred from "whether a handle was
returned" (scenario_matrix §2). The prior FC-703 r1 defect class (spy
assertions satisfied by unrelated SQL shape) was in mind throughout; the
verification below re-derives the evidence, not the summary.

## Sealing hashes

- plan_sha256 `158fc1e1…` — recomputed from task_plan.md at revenue-forecast
  commit 2d64186 (frozen plan): MATCH. On-disk plan refreshed by
  d662c82/53b984d (headers only) and therefore hashes differently — same
  precedent as FC-703 r3.
- command_registry_sha256 `215b8077…` — recomputed from
  compatibility/command_registry.json (tracked, unmodified): MATCH.

## Triplet

- revenue HEAD 1a78889 == result; filing HEAD 85731b2 == result; wiki
  worktree HEAD c3fd9c4 (implementer receipt commit) on 6bf213d == result.
- All base commits exist; `merge-base --is-ancestor c11efd6 6bf213d` →
  ANCESTRY-OK.
- Diff scope: exactly 8 code/test files (3 wiki + 3 filing + 2 revenue),
  all in the allowlist, zero unrelated changes. IMPLEMENTATION_PLAN_FC704.md
  in the wiki commit is a plan doc (acceptable).

## What the code actually does (read from the diffs)

- **wiki resolver.py** `build_resolution_envelope`: structural outcome map
  (REUSED_* → reused_existing, AMBIGUOUS → ambiguous, MISSING → missing,
  IDENTITY_CONFLICT → rejected); journal reconciliation reads `read_all()`
  in append order so the **LATEST** entry for the request_id wins;
  `download_events` is 1 only for journal outcomes
  {downloaded_new, deduplicated_after_download} — never inferred from the
  handle; all 9 ACQUISITION_OUTCOMES are mapped; policy_hash/activation_epoch
  come only from the RuntimePolicySnapshot dict (null without); bundle_status
  hard-coded "unavailable". Reads the journal only — zero-write.
- **wiki cli.py**: `resolve` attaches the envelope via a read-only journal
  read; `ensure` builds the envelope AFTER the ensure call has journaled the
  attempt — no double-write (record() has zero callers in cli.py/resolver.py);
  `_plain()` builds fresh dicts so the envelope attach cannot alias shared
  state; `SourceEnsureResult.resolution` exists.
- **filing-fetch**: `validate_resolution_envelope` deep-validates schema
  version, outcome taxonomy, download_events (0/1, bool rejected), policy_hash
  (64-hex or null), epoch (text or null), bundle_status enum — anything
  outside is `upstream_error`; forwarded verbatim (shallow copy) in
  `resolve_filing`; envelope-less old company-wiki resolves normally (N/N-1).
- **revenue**: `prepare_source` fail-closes (RuntimeError) when the envelope
  is missing or download_events ∉ {0,1}; receipt `download_calls` =
  envelope download_events; outcome/policy_hash/activation_epoch/bundle_status
  carried into the receipt. Grep sweep: no `0 if handle else 1` fake remains
  anywhere.

## Fresh replays (all at result triplet, clean worktree)

| Command | Result |
|---|---|
| wiki `pytest tests/contract/test_resolution_envelope_fc704.py -q` | 9 passed |
| wiki Phase-7 cluster fc704+fc703+fc702+fc701+fc604 | 32 passed |
| filing `pytest tests/test_fetch_filing.py -q -k envelope` | 3 passed |
| revenue `pytest tests/test_source_preparation.py -q` | 9 passed |
| revenue `pytest tests/test_preparation_e2e_success.py -q` (REAL chain) | 1 passed |
| ruff on all 8 changed files (3 repos) | all passed |
| PORT-01 spot-check (unique test symbols) | 2 failed / 3 passed — reproduces the implementer's recorded pre-existing failures exactly; file untouched by FC-704 (not in the diff) |

The E2E test spawns the real chain (revenue client → filing-fetch →
company-wiki resolve CLI) and asserts `download_calls == 0`; since
`prepare_source` raises RuntimeError without an envelope, the pass itself
proves the envelope flows end-to-end. I also ran the chain manually and read
the produced receipt: outcome `reused_existing`, download_calls 0,
policy_hash null, activation_epoch null, bundle_status `unavailable` — the
fixture has no runtime_policy.json, so null is honest, not fabricated.

## Mutations (both KILLED, both reverted, trees verified clean)

- **M1 (revenue)**: restored `"download_calls": 0 if handle else 1` →
  ENV-09 FAILS (1 failed / 8 deselected). The legacy inference lies exactly
  as scenario_matrix §2 forbids.
- **M2 (wiki)**: removed the journal reconciliation loop (structural outcome
  only) → ENV-03/ENV-04/ENV-04b FAIL (3 failed / 6 passed) — the exact kill
  set the implementer recorded as M4. The reconciliation is load-bearing.

## Zero-write verification

Built the envelope over an **existing** journal (recorded `downloaded_new`)
and confirmed the journal file is byte-, sha256-, and mtime-identical after
the build. ENV-08 covers the not-created case; this covers the
not-modified case. resolve is genuinely read-only with respect to the
journal.

## Validator gate

`python tools/receipt_validator.py --receipt …/FC-704/11_implementer_receipt.json`
(from revenue-forecast): `OK: 1 receipt(s) valid`, exit 0.

## Self-hash convention

The reviewer receipt self-hash `ea7af062…` follows the FC-703 r3 convention
(verified by re-deriving c900db24… for the r3 receipt): sha256 of the JSON
with the `reviewer_receipt_sha256` field blanked, serialized
`json.dumps(…, ensure_ascii=False, indent=2)` plus trailing newline. The
naive "write → hash → update → re-hash" fixed-point iteration cannot
converge (hash of a file containing its own hash is a random mapping); the
blanked-field convention is the established, verifiable one.

## Findings

All informational, none blocking:

1. Full wiki suite not rerun (6.5 min) — PORT-01 claim spot-checked and
   reproduced; focused/cluster replayed instead.
2. No remote branch for the fcap branch (carried precedent).
3. `ensure` CLI now reads runtime_policy.json a second time to feed the
   envelope (wrapped, None-safe) — extra read only, no behavior change.
4. Revenue re-checks only download_events (0/1, bool rejected) plus
   dict-ness; the deep taxonomy validation happens once at the filing-fetch
   boundary — adequate for the single-producer chain.

## Side effects

Zero downloads, zero catalog mutations, zero external writes. The only
writes were the two reverted mutations and this report + reviewer receipt
under assurance/fc/FC-704/.
