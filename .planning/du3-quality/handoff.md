# DU3-QUALITY handoff

Lane: quality · Branch `codex/du3-quality-20261014` · Base `195aba20` · Implementation `44cbd62d`
Worktree `C:/Users/郑曾波/Projects/_harness_worktrees/shared-reading-completion-20261014/quality`
Owned write scope: `tools/document_understanding_benchmark/**`, `.planning/du3-quality/**`. Nothing else touched.

## What this card delivered

Two additive public entry points on the existing benchmark package (no second evaluator,
`evaluate` untouched in behaviour):

- **`observe_final_material(material, originals, *, sample_id, execution, limits=None)`**
  — measures the *actual final ModelRequest* (the decode of `NarrativeModelRequest.data_json`,
  or a frozen-equivalent fixture) and resolves every evidence-row alias and group alias back to
  an already-verified original unit. Text, locator, page and role come from the original, never
  from the envelope or from gold (there is no `gold` parameter). It refuses — as a malformed run,
  not a quality verdict — fabricated row text, unknown/duplicate aliases, a material bound to a
  different source, two units sharing one locator, and a group that merges distinct source scopes
  (cross-subject / parent-source packaging). It reports shared-body duplication and records
  explicitly that unread is not absence. Returns `du-observed/1` so `evaluate` consumes it unchanged.

- **`compare_runs(baseline, candidate, *, frozen_suite)`** — `du-quality-comparison/1`, status
  `PASS|FAIL|PARTIAL|INCOMPARABLE`. Only same-source / same-read-scope / same-budget /
  same-gold-denominator comparisons are scored; anything else is `INCOMPARABLE` with the reason.
  A shrunken denominator never reads as an improvement (direction reported); a fact that moved
  `FAIL → NOT_EVALUATED` is named in `moved_to_not_evaluated`; the Microsoft 4/8 critical failure
  is preserved as a failure, never re-scored green.

Plus, for the card's §3 "full-chain risk checks": currency-vs-evidence and non-company-voice-as-
management-fact checks in `check_basis_fact`, and two new mutations (`currency_swap`,
`editorial_as_management`) that the oracle detects. A `contamination` list (which originals were
already inspected vs genuinely fresh), a `coverage_matrix` (A/H/US annual·interim·quarterly,
10-K/Q/20-F, IPO/S-1/F-1, equity/convertible, IR, call, results release/deck, 8-K/6-K exhibit,
amended filing, low-business/administrative — real/synthetic/missing separated, schema validity is
never semantic coverage), and fresh holdout gold for three new companies.

## A/B/C evidence

| node | command | result |
|---|---|---|
| A (TDD RED) | `pytest tests/test_final_material.py tests/test_paired_comparison.py tests/test_fresh_split.py` | RED first (missing entries + gaps), then GREEN |
| B (impl/eng) | `pytest tools/document_understanding_benchmark/tests` | **213 passed, 7 skipped (real-data opt-in), exit 0**, ~6s |
| B (CLI) | `python -m tools.document_understanding_benchmark --mode offline` | 5 fixtures, **56/56 applicable mutations detected**, exit 3 (honest PARTIAL), sentinel restored, tmp cleaned |
| C (real baseline) | `python .planning/du3-quality/_baseline_c.py` | 3 fresh originals replayed; **quote replay 9/9, 7/7, 7/7**; raw unchanged; semantics NOT_EVALUATED |

## Node C — real baseline on the three fresh companies

Read-only replay through the existing public parser/selector (`source_catalog.narrative_evidence`),
no model, no network. Full receipt: `.planning/du3-quality/baseline_c.json`.

| sample | company | market | carrier | quote replay | critical recall | status |
|---|---|---|---|---|---|---|
| `fresh-cn-smic-fy2025` | 中芯国际 | CN | pdf | 9/9 | 0.50 | FAIL |
| `fresh-hk-anta-fy2025` | 安踏體育 | HK | pdf | 7/7 | 0.00 | FAIL |
| `fresh-us-apple-10k` | Apple Inc | US | htm | 7/7 | 0.33 | FAIL |

These FAILs are the deliverable: the baseline selector genuinely under-carries business facts
(e.g. ANTA's segment/profit rows, Apple's segment/tariff qualifiers). They are a measured
production quality gap, exactly like the documented Microsoft 4/8, not a broken benchmark.
`semantics.entailment` stays **NOT_EVALUATED** — no real model is called in this card.

## Fresh gold (the genuinely-new companies)

Companies and originals absent from every prior gold/finding/tuning note. Each support set was
**frozen before any new output was read** (`support_set_frozen_before_output` + content
`support_set_digest`, verified by `test_fresh_split`). Quotes ≤8KiB per document. Business-fact
support sets are AND within a group / OR across groups; importance set by business value from the
source; general financial numbers are `correctness_if_emitted` while operating volume / table
header / unit / risk qualifiers stay `required_business`.

## Known gaps (honest, for ROOT)

- No real US **S-1/F-1**, **8-K/6-K exhibit**, or **amended-filing pair** on this host —
  `coverage_matrix` marks them `missing` with the specific gap; not faked with old samples.
- Final-material observation runs on frozen-equivalent **synthetic** envelopes; ROOT must feed
  actual `NarrativeModelRequest.data_json` once a real summary producer is wired.
- `semantics.entailment` is `NOT_EVALUATED` until ROOT runs the independent G2/G4/G5 review.
- Fresh-gold critical recall is low (0.5/0.0/0.333) on the baseline — re-measure after production
  selector wiring.

## Resources / restoration

`model_calls 0 · paid_calls 0 · network_calls 0`. Measured: elapsed, spans, candidates, units,
quote-replay, text/bytes, artifact sizes. RSS and model usage not measured (no model called).
Originals read-only; SHA/mtime/size unchanged for all three fresh originals (`source_unchanged:true`).
Production config untouched. Offline CLI tmp dir wrote only its own summary, restored the sentinel,
then removed. Local bindings (`~/.du-bench/bindings.local.json`) updated with the 3 fresh paths —
machine-local, **not committed**.

## Next ROOT action

1. Wire actual `NarrativeModelRequest.data_json` → `observe_final_material` once a real producer exists.
2. Run `compare_runs` over a frozen suite for a candidate selector; never report improvement on a changed denominator.
3. Run the independent G2/G4/G5 semantic review → `evaluate(review=...)`.
4. Acquire the missing S-1/F-1, 8-K/6-K exhibit, amended-filing pair to close the coverage holes.
5. Re-measure fresh-gold critical recall after production wiring.

STOP here per the card; ROOT integrates master / pushes the main line.
