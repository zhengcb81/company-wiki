# W08 annual14 V4 independent review

**Verdict: blocked by one P2 shared-root classification defect.** This review binds the exact V4 source/test hashes in `freeze.json`; it is historical and does not certify code changed afterward.

## Content visibility

The frozen 14-item checklist produced **7 pass / 5 partial / 2 missing** in V4 selected evidence and compiled model-task membership. This measures local evidence visibility only; no model response or final business correctness was reviewed. The separate 2-fact selector oracle is not the 14-item checklist.

| Target | Result | Evidence/remaining gap |
|---|---|---|
| ST-A01 | partial | Service scope restored; Others and full parent/child scope remain missing. (t19) |
| ST-A02 | partial | 15.84% growth is retained; the three actual revenue definitions and restatement remain missing. (t34) |
| ST-A03 | missing | Regional amounts, growth and measurement definition are missing.  |
| ST-A04 | missing | Group orders, RPO and recognition schedule are missing.  |
| ST-A05 | partial | Amounts exist but Chemistry parent/child scope is not closed.  |
| ST-A06 | pass | Stage project count is complete. (t25) |
| ST-A07 | pass | 42万 and 310 are both present. (t24) |
| ST-A08 | pass | Three indicator types are explicitly distinguished. (t11, t26) |
| ST-A09 | partial | Capacity and dated timing remain split across tasks.  |
| ST-A10 | pass | Testing target material is complete.  |
| ST-A11 | pass | Biology and group new-customer object are explicit.  |
| ST-A12 | pass | Full outlook and premise are together in the task. (t31) |
| ST-A13 | partial | Policy enters task; exact timing classification and two amounts remain missing.  |
| ST-A14 | pass | Risk target material is complete.  |

Testing and Biology new-molecule tasks each retain their own parent; no cross-business leakage was observed.

## P2 blocker

`narrative_source_purpose.py` still classified “本集团的收入确认会计政策涵盖履约义务及客户控制权。” and its English equivalent as `operating`. The rule accepted the nouns “revenue recognition”, “performance obligations”, and “customer control” without an actual obtain/transfer/performance relation. V5 adds red tests for both phrasings and tightens the predicate to require a customer obtains/gains control or an explicit transfer/delivery relation.

## Binding and test evidence

See `freeze.json` for source/test hashes and V4 artifact SHA-256 values; `target-checklist-binding.json` separates the 14-item checklist from the 2-item selector oracle. The natural suite was **2,153 passed / 11 skipped / 0 failed** in 60.42 seconds, source-stable, with the owned temporary root removed. The independent reviewer did not execute tests or edit product files.
