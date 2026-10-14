# Findings: du3-quality

## Interfaces (frozen DU3/1)
- `observe_final_material(material, originals, *, sample_id, execution, limits=None)` -> du-observed/1.
  The envelope addresses evidence by *alias* rows and *group alias*; none are original locators, so
  the observer resolves each alias to a verified original unit. Text/locator/role are copied from the
  original; the envelope may omit a role (default_source_role) but may never contradict one. There is
  no `gold` parameter — gold cannot fill an observer answer.
- `compare_runs(baseline, candidate, *, frozen_suite)` -> du-quality-comparison/1. Comparability is
  same source + same read scope + same assembly budget + same gold denominator; otherwise INCOMPARABLE.

## Decisions worth recording
- **Coverage diagnostics are lifted to the top level.** `du-observed/1` coverage normalisation keeps
  only its fixed fields and stashes the rest in `coverage.raw`. The additive final-material diagnostics
  (shared_alias_ids, duplicate_body_alias_ids, unread_is_not_absence, unresolved_aliases) are re-attached
  to `coverage` after validation so consumers see them without reaching into `raw`. Additive only.
- **Cross-subject / parent-source packaging is a group whose members span >1 source scope_id.** That is
  a self-contained check on the material; it does not need the originals to declare group membership.
  (Earlier a `originals.groups` mismatch check was tried; it conflicted with the legitimate shared-alias
  case and was replaced by the scope-span check.)
- **Body duplication is grouped by text**, not (text, locator): the same body carried by two evidence
  rows is shared content to report, whatever their locators.
- **Gold identity is verified only on a *declared* mismatch.** A run that reports `gold_digest` differing
  from the frozen suite is INCOMPARABLE; a run that reports none is recorded in `unverified_gold` but not
  auto-disqualified (the denominator check is the load-bearing swapped-gold guard).
- **`_sample_outcome` never force-PARTIAL on the inherent semantics gap.** A comparison PASS means
  "a real improvement on comparable measured ground", not "summary fidelity verified"; fidelity stays
  NOT_EVALUATED in the checks and in `unmeasured`. PARTIAL is used when the grader itself degraded.

## Fresh gold (genuinely new companies)
中芯国际 (CN, 2025 annual), 安踏體育 (HK, 二零二五年年報), Apple Inc (US, 10-K FY2025). Companies and
originals absent from every prior gold/finding/tuning note. Support sets frozen before any new output was
read (`support_set_frozen_before_output` + `support_set_digest`, content-verifiable). All 23 exact quotes
replay against the real source text (9/9, 7/7, 7/7) and all three SHAs match the bound originals.

## Node C measured result (real, honest)
Baseline selector (existing public parser/selector) critical recall 0.50 / 0.00 / 0.33 on the fresh gold.
These FAILs are the deliverable — a measured production gap, not a broken benchmark. Semantics NOT_EVALUATED.
