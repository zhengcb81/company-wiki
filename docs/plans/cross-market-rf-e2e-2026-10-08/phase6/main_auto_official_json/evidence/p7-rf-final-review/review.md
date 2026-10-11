# P7-RF independent MAIN reception review

Verdict: **specific blocker**, not accepted as complete. The applicability-period repair itself passes the targeted independent controls. No source changes were made by this reviewer.

## Precise blocker: scoped support lost at CLI projection

`scripts/research_support_diagnostics.py:35–42` flattens referenced calibrations into one global parameter-ID covering map; lines51–53 use that map for every segment. In a valid model where both Segment A and Segment B consume the same existing native FY2026 roots, calibration `reference_bridge` remains explicitly scoped to Segment A. `validate_document` succeeds, calibration is `referenced_range`, and the CLI incorrectly marks all three Segment B FY2026 cells `supported`, reasons empty.

The minimal input is `shared_root_minimal_input.json`. Reproduction uses the actual native validator, operating projection and public diagnostics function, not a substitute algorithm. Changes are solely Segment B FY2026 driver references to the already-existing same-scenario Segment A roots, and the corresponding research ID references updated to those actual consumed roots. Original parameter values, parameter/claim provenance, calibration scope and source facts remain intact. A shared parameter is legitimate; it must not be prohibited to conceal this diagnostic error.

Fix the shared relationship query at actual segment × scenario × year with calibration scope and scenario output ID/period. Company-wide scopes remain legitimate when their explicit relation covers the actual cell. This is an optional diagnostic correction; no new permission, identity validation, schema gate or arithmetic change is justified. Re-run this minimal counterexample after the fix, with Segment A positive and Segment B negative expectations.

## Independent probes

Five small pure-memory probes, with actual native validation, were run once; the full119 tests and four public E2E cases were read as existing evidence and were not rerun.

| Probe | Result |
|---|---|
| Shared root across Segment A/B, calibration scope A only | **FAIL**: B FY2026 falsely supported |
| Same direct root actually consumed in FY2026 and FY2027 | PASS: direct FY2027 mismatch diagnosed |
| FY2025 measurement, FY2024 disclosure, FY2026 applicability | PASS: independent periods remain valid |
| Company-scope FY2031 parameter/output in real FY2026 cell | PASS: unverified/unsupported |
| Explicit FY2025→FY2026 native conversion bridge with FY2024 disclosure | PASS: referenced range retained |

Absent optional research still returns None. Archived emitter output controls accept4.2.0 and4.2.1 for schemas3.7/3.8/3.9; old sealed outputs were not rewritten. Existing handoff evidence reports unchanged forecast arithmetic and stable-fsum confidence for the repaired synchronized-period attack; this reviewer did not claim a new repeated forecast or pinned-old-runtime test.

## Protection and bounds

All10 source/test/reference working-file SHA values matched the stable implementation handoff before and after review. All23 protected original configuration/fixtures/old PWF/handoff/log bytes matched their original protection list. ROOT's normal Git commit/HEAD changes are allowed and do not constitute source contamination. The isolated RF worktree contains no AGENTS.md; CodeGraph reports that this worktree is not initialized, so the already identified files were read directly without writing an index.

No RF/shared PWF/raw/config files were written, no Git mutation or installation was performed, no publication registry was invoked, and no TEMP products were created. Environment unchanged, provider calls0, model calls0, costUSD0. Reviewer writes are limited to this unique evidence directory. See `receipt.json` for exact source SHA, native probe relations and results, and `probes.py` for reproducible argv.
