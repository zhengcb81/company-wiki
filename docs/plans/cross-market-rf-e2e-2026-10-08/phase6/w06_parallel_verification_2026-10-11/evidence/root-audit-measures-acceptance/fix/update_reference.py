"""Clarify only the new tool's typed contract; shared reviewer instructions belong to ROOT."""
from pathlib import Path
path = Path("C:/Users/郑曾波/Projects/_harness_worktrees/w06/audit-measures-root/skills/revenue-forecast-audit/references/financial-measure-audit.md")
body = path.read_text(encoding="utf-8")
body = body.replace("`growth` -> `period_start`+`period_end`; `ratio`/`count` -> window or point.",
                    "`growth`/`ratio`/`count` -> one explicit window or point (e.g. a change in two dated ratio levels).")
body = body.replace("  Result is `percent`/`decimal` (a rate).", "  Result is same-entity `growth` in `percent`/`decimal` (a rate), anchored to the end observation.")
old = """Comparison: expected vs declared `result.value`. Rounding is applied only when `rounding.places` is
declared with a `basis` (display precision); rounding without basis is INVALID. `absolute_tolerance`
must be small: a tolerance that would mask an order-of-magnitude error (>= 0.5*|expected|) is
INVALID (`excessive_tolerance`); a bare huge tolerance never turns a wrong-magnitude result green."""
new = """Comparison: expected vs declared `result.value`, in the declared result units. `rounding.places`
must be an actual integer in [-12,30] (not bool, float or coerced text), with nonempty display-precision
`basis`. The declared result must itself fit that precision. Positive `absolute_tolerance` requires
that same basis, may not exceed half the display quantum, and may not hide half the true expected
magnitude. Otherwise INVALID. With no display rounding, numerical epsilon is relative to the expected
value (1e-20), with no one-unit absolute floor; exact zero has no guessed tolerance. This avoids tiny
shares/rates becoming PASS after a unit change or million-fold mismatch."""
assert old in body
body = body.replace(old, new)
body += """

## ROOT repair contract — explicit typed relations, not permission checks

The original delivery's GREEN suite missed 16 acceptance vectors; the frozen original logs remain
under its handoff. ROOT adds `root_acceptance_regressions.json`, 19 portable frozen tests and typed
contract regressions, then repairs the shared relation boundary. No company-specific conditions,
source scans, API calls, identity database, permission file or human receipt are involved.

- Top-level schema must be `financial-measure-ledger/1`; `as_of_date` must be a real YYYY-MM-DD.
  Malformed JSON field types, duplicate relation ids and incorrect operand counts return structured
  INVALID reports. Conversions have exactly one input; difference/growth/CAGR/share exactly two;
  sum at least two. No extra input is silently ignored. Every check is local to its declared ledger.
- Normalization preserves status alongside finite Decimal value, unit and context. INVALID or
  UNRESOLVED input/result cannot become a PASS relation merely because arithmetic is possible.
  Source references still require only the existing source_id+locator interface, not new approvals.
- Conversion preserves entity, economic definition, kind and exact time anchor; only scale or the
  explicit FX changes. Sum preserves these fields in its result and joins contiguous, non-overlapping
  flow windows. Amount difference preserves entity/line/kind/currency, comparing like temporal
  anchors; a ratio-level difference produces `growth` in percentage_points.
- Growth/CAGR compare the same entity/definition/currency/kind. Base precedes end, flow windows
  cannot overlap, and durations must agree within three calendar days (calendar quarters/leap years).
  Result kind is growth at the end observation anchor. Positive-base simple growth may fall to zero
  or negative values; zero/negative base is UNRESOLVED. CAGR separately requires positive end and
  explicit positive years, cross-checked to anchor gap within three days using 365.2425 days/year.
  This is an audit of explicit inputs, not auto-annualization or a rebuilt forecast formula.
- Share compares quantities of matching kind/currency/exact time, with an explicit inclusion
  declaration. Cross-entity market shares can be declared; no entity is re-resolved or inferred.
  Result is a numerator-entity ratio at the same time. A text inclusion declaration is *not verified*
  by this arithmetic tool, and profitability ratios above 100% are not automatically invalidated.
- Economic definition strings are opaque. Conversions/sums/amount differences preserve the base
  line; derived growth/ratio outputs can have their own explicit label. The report exposes underlying
  definitions in `input_contexts`; semantic accuracy of a derived label is checked by the process
  and analyst reviewers, not guessed from its spelling.
- Evidence roles stay explicit. Guidance/assumption/stress inputs cannot produce a more factual
  output role. Future guidance and explicit analyst scenarios are legal and keep their roles;
  reported facts with a future target are UNRESOLVED. Rationale describes an assumption; it cannot
  override a dimensional, currency, entity or temporal mismatch.
- Optional `available_by` expresses source availability independently of target period. A malformed
  date is INVALID; availability after as-of is UNRESOLVED. Absent availability is an explicit unknown
  diagnostic and never a source qualification claim. Source-byte reading remains outside this tool.
  FX likewise requires date/source and cannot be dated after as-of.

Report additions: relation `arithmetic_status`, `input_contexts`, `result_evidence_role`, plus top-level
`source_qualification_verified=false`. `coverage_pass` is false unless the *overall declared checks*
PASS; it is not a source-quality certificate. `source_truth_verified=false` and
`economic_reasonableness=not_evaluated` always remain. Output is still a fresh exclusive attempt,
with existing redaction/receipt/input-SHA logic unchanged.

Known scope: the current sum operator joins temporal flow windows, not simultaneous business-segment
sums; 52/53-week unequal fiscal windows need a separately explicit comparability contract rather than
being guessed; source truth, label semantics, complete company evidence coverage and buy-side model
reasonableness are not evaluated here. These are visible scope limits, not requests for approval.
"""
path.write_text(body, encoding="utf-8")
print(path)
