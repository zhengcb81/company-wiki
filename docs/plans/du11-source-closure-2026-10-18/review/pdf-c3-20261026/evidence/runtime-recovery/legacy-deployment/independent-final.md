# Legacy parent-cache fixture — independent final review

Reviewer: `/root/c3_cache_independent_review`, not the test-fix author. Date: 2026-10-26.

**PASS; OPEN = 0 for `tests/integration/test_reading_parent_cache_migration.py`.** The failure was a historical-deployment fixture identity mismatch; the repair restores a valid test setup instead of weakening the production cache or its assertions.

## Exact scope

- Reviewed test byte SHA-256: `ca8159ae4f35496db9e89842a4fac19f648dcb1ed46a3ce9d117cd6384d80035`.
- LF SHA-256: `ab9444118640140443a0e92d2825f135e3239a9d55e1c19b26b10f3b57ba840f`.
- Reviewed git diff, the physical inventory owner, actual green public-generation receipt, terminal log/XML, diagnostic RED evidence, and test launcher/reset/cleanup helpers.
- This repair changes the test fixture only. The batch/generation changes under separate C3 cache review are not accepted by this report. The green run records identical before/after product SHA values.

## Why the correction is valid

Previously, the fixture executed historical sections text inside the current module namespace and changed `__file__`. The production inventory deliberately hashes the physical `structure/*.py` package beside its owner. Thus the executed old code was falsely labeled with current source identity, and the new run correctly reused the incorrectly labeled old result.

The new helper copies the physical package shell, `decision_inventory.py`, and the small structure package into the isolated fixture, replacing only `sections.py` with the tracked historical bytes. Other reading modules fall through to the current package. The bootstrap installs that package before any current reading package is loaded and refuses an incompatible preloaded package. Current-phase `_launcher` rewrites the bootstrap and subsequent fresh processes import canonical current sources again.

The compatibility observer drops `native_context` and `work_budget` only when the actual historical callable signature lacks them and has no `**kwargs`. Current callable arguments still pass unchanged. It delegates actual section construction, does not fabricate semantic sections, material, output hashes or cache decisions, and only provides the already-required empty legacy optional context fields.

This remains a deliberately limited historical component migration, not a reconstruction of an entire old release. That limitation is stated in the test docstring and record.

## Independent short checks

1. **All 25 original assertion ASTs are unchanged**, in original order; `independent-static-check.json` binds this to the final test SHA.
2. In two independent fresh Python processes, import the physical legacy overlay and then the canonical current package. Confirm `sections.build_sections.__code__.co_filename == sections.__file__` and the inventory entry equals the LF SHA of that same physical file. Only the `structure.sections` inventory key differs:
   - legacy: `7f010ccbe6815f5b842f2d90b99d751fd95478cea750c907292c3aaff39080d0`;
   - current: `abddf859e804e65765c34bc336ed7a8eb91de0d3894f761c63eafd8b77e94287`.

The inventory owner itself is imported from the legacy physical package in the old process and canonical source in the new process. Evidence: `independent-identity-probe.py/json`. This short check made no parser/model calls and its own temporary tree was removed. It is separate from, and does not pretend to be, a per-file hash trace from the author's green full run.

## Terminal full-node evidence inspected

The author ran the original full node once after the correction: **1 PASS**, zero failures/errors/skips, process exit 0, no timeout, process duration 33.153s, XML suite duration 31.598s. `green-run.json` binds the exact reviewed test and relevant production source SHA before and after. I did not repeat this costly node.

`green-public-cache-result-0.json`, checked against the retained assertions, shows:

- Old and new initial runs complete; exactly **2 local loopback POSTs**, zero external calls.
- Old-b and new-d each reuse their own generation with **0 charged tokens**; neither executes structure again.
- The old producer path is the real fixture `legacy-deployment/.../sections.py`. New observations point to canonical `src/.../sections.py`.
- Old/new `business_algorithms` differ (`7f85b2bc…` vs `d35e6ae0…`); public artifact references and material hashes differ (`7c156572…` vs `34741b8f…`). Shared formal-generation checks bind the actual posted model material to public evidence and published generation.
- The two identical “New product revenue exceeds 30%” sentences retain distinct locators. New contexts contain respectively Diagnostics services and Technical services plus “During the period:”; neither borrows its sibling's parent. Old context had only the common management heading.
- Exact old-reference read returns the original old bundle unchanged after new publication. Current public read returns the new reference.

## Cleanup and limits

The original protected-source/config/sentinel checks remain intact. Green public receipt records `owned_lake_removed=true`; independently checked `.c3leggreen` is absent after author cleanup. The green process receipt records its PID terminated. Reviewer-owned `C:/Temp/c3-legacy-independent-20261026` is also absent. No product edits, downloads, paid providers or production writes were made by the reviewer. Evidence and probe source remain intentionally under this review directory.

No additional full-suite or paid validation is required for this test-fixture correction. This is an engineering migration acceptance, not a real-company content-quality or whole historical-release acceptance.
