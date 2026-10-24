# W08 annual14 V5 independent review

**Verdict: no remaining engineering blocker in the reviewed V5 source-purpose fix; business-content visibility remains partial (7 pass / 5 partial / 2 missing).** This is a read-only independent review bound to the V5 freeze. It reviews selected spans and compiled task context; it does not certify a model response, final summary, or business conclusion.

## Frozen inputs

- Worktree HEAD: `f404026e6921bdab973bddd15f96d8f57a45ea94`
- V5 freeze SHA-256: `c9a4e3ca54d4677f3db29c2080302849ca7cd78997534191814ac601250f7fef`
- Selection SHA-256: `5602c4fe205128459af3079972e05f4a024603534c83c001c40e099ad4b5e9df`
- 14-item checklist SHA-256: `92aafc341326845cac2aada578b67d6211f99244163f90345269686fedf0b258`
- The V5 `oracle_sha256` (`ea6e95…0b05`) is a separate two-checkpoint selector oracle, not the 14-item business checklist.
- All seven modified source-file and seven modified test-file byte hashes match `freeze.json`. `trace`, `model-view`, `selection`, and natural-suite receipt hashes also match the freeze.

## Target results

| Target | Result | Evidence and remaining gap |
|---|---|---|
| ST-A01 | Partial | t19 has service scope; Others and complete Chemistry scope/TIDES parent-child relation are absent. |
| ST-A02 | Partial | t34 has 15.84% revenue growth; actual revenue definitions, 21.40% and restatement are absent. |
| ST-A03 | Missing | Customer-region amounts/growth and parent-company measurement definition are absent. |
| ST-A04 | Missing | Group orders, RPO and 2026 recognition amount/schedule are absent. |
| ST-A05 | Partial | t10/t25/t26 have figures; Chemistry internal parent-child relation is not closed within the task. |
| ST-A06 | Pass | t25 states new, ending and stage project counts. |
| ST-A07 | Pass | t24 includes both 420,000 compounds and 310 molecules. |
| ST-A08 | Pass | t11/t26 distinguish customer, molecule and order growth indicators. |
| ST-A09 | Partial | Capacity and dated timing exist in t20–t22/t27–t28, but the relation remains split across tasks. |
| ST-A10 | Pass | Testing target material is complete. |
| ST-A11 | Pass | t14/t17/t30 identifies Biology revenue and both distinct denominators. |
| ST-A12 | Pass | t31 contains guidance span `14f5…` and its complete premise span `b127…`. |
| ST-A13 | Partial | Policy spans are visible in t50–t53/t16; exact recognition amounts and Testing/Biology period classification remain absent. |
| ST-A14 | Pass | t35/t40–t46 cover the target risk facts. |

The independent reviewer opened context for all 55 compiled tasks. Testing t13/t29 keeps only Testing parents; Biology t17/t30 keeps only Biology parents. No cross-business sibling leakage was found. t33 names its three businesses separately in the source support.

## Root-fix review

V4 exposed one P2 shared-root defect: the source-purpose classifier treated pure nouns (“revenue recognition”, “performance obligations”, “customer control”) as evidence of an operating event. V5 changes the customer-control rule to require an actual relationship such as a customer obtaining control, control being transferred, or goods/services being delivered to a customer. The Chinese and English noun-only counterexamples now remain accounting-policy material, while positive transfer/delivery and timing examples remain covered. An independent source-safety reviewer confirmed the current 7 source and 7 test file hashes match the V5 freeze; no new blocker was found.

## Test and execution boundary

- Focused regression: 119 passed.
- Natural repository suite: 2,155 passed, 11 skipped, 0 failures in 54.08 seconds; source remained stable and the owned test temp directory was removed.
- Real annual-report selector replay: 249 pages, 1,533 candidates, 96 selected spans / 7,767 characters; 8,845,814 / 16,000,000 work units, not exhausted; 2 bounded checkpoints passed.
- No external model calls, downloads, or raw copies occurred.
- This review ran no product code, tests, compilation, or writes.

The selector evidence is not a summary-quality pass. A03/A04 and the partial targets remain open; the next step is a bounded target-by-target source/dependency/task-closure diagnosis, then fix shared causes and rerun the same frozen 14-item checklist once at the next major node.
