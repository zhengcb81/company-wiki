# Annual14 V2 selected-source review

This review is bound to `selection.json` SHA-256 `79abb23d8e5ad60f7d03d366706c4c150602c7bfc719bce41578458bbb5546a0` and the unchanged original 14-target gold. It is a ROOT evidence review, not an independent signoff, a model-response review, an accepted summary, or an RF company audit.

## Run facts

- SourceRef: `urn:company-wiki:source:sha256:7f1431d66eae399d4b35639bb650e23287c7f52dacbb47b4b4a197fb5026d6a2`; original SHA independently matched.
- One bounded 249-page selection; 5,660 units, 1,532 candidates, 96 selected spans and 7,171 selected characters.
- Work budget: 8,613,643 / 16,000,000; not exhausted. Selection is partial at the 96-item cap. The aggregate `budget_full` diagnostic is not used to assign target-level causes.
- No provider calls, downloads, or raw copies. The 52 scoped model-task views were compiled locally; no model response or summary was generated.
- Current selection/source-code binding: `sections.py` `f020e0f6aedcdf37b6e6c74979ea659a51f3cad84fc1b24f22f10fcb1b72a441`; `n6_candidate_operating_facts.py` `029388920d77b93f04d83baebf0ecaf365807bfd8c43d469847785d8c8a84f53`; `narrative_revenue_guidance.py` `003767c162e55807abe8e645a7ad3b940c5a0f0914540d941f5aeb78929ba3fb`.

## Target results

| Target | Result | Current selected-chain evidence and remaining gap |
|---|---|---|
| ST-A01 | Partial | `t10` includes Chemistry revenue and `t23` includes research-to-development facts. The four-business taxonomy including Others and the full Chemistry scope do not travel in the compiled task context. |
| ST-A02 | Partial | Selected views retain some totals/rates, but not the exact continued/discontinued revenue values plus restatement context. A precise financial API/table source remains the suitable completion path. |
| ST-A03 | Partial | Customer-region amounts and the customer-parent location/comparison-period definition are not present in the selected task views. |
| ST-A04 | Partial | The 580.0 亿元 order figure and the detailed remaining-performance-obligation schedule are absent from selected task views. |
| ST-A05 | Partial | `t10` carries Chemistry revenue, `t24` D&M revenue and pipeline, and `t25` TIDES revenue/orders. Their common Chemistry parent and no-double-count scope are not available in the relevant same-task context. |
| ST-A06 | Pass | `t24` carries the D&M 839 additions, 3,452 ending pipeline and stage counts, plus the 22 increase in commercial/Phase III projects. The flow/stock distinction is explicit in that task. |
| ST-A07 | Pass | `t23` carries both >42万 new compounds and 310 R-to-D conversions, with separate measures and no revenue interpretation. |
| ST-A08 | Pass | `t25` carries TIDES revenue/orders; `t11` carries TIDES D&M customer and molecule-count growth with each measure named. |
| ST-A09 | Partial | `t19` carries >4,000kL API capacity; `t26` carries the September Taixing completion; `t27` carries >100,000L peptide-reactor volume. The completion-to-capacity relationship is split across tasks. |
| ST-A10 | Pass | Tasks `t12`/`t13`/`t28` carry Testing revenue, safety-assessment growth and the new-molecule share; `t33` carries the margin decline and price/order-conversion explanation. |
| ST-A11 | Pass | `t14`/`t29` carry Biology revenue/growth and >20% new customers; `t15` carries >30% new-molecule revenue share. The customer and revenue-share measures remain separately named. |
| ST-A12 | Partial | `t30` carries the 2026 guidance values and forecast modality. The following order, industry, trade and regulatory premises, non-commitment and uncertainty are absent from the selected task view. |
| ST-A13 | Missing | The revenue-recognition policy, point-in-time/over-time breakdown and contract-liability-to-revenue explanation do not appear in selected task views. |
| ST-A14 | Pass | The selected chain covers concentration (`t35`), demand/client R&D outsourcing (`t41`), regulation (`t42`), competition (`t43`/`t44`), project delay (`t46`) and FX exposure (`t47`), each in a locally readable task. |

Counts: **6 pass / 7 partial / 1 missing**. Compared with the frozen first review (3/9/2), A07, A11 and A14 improved. Partial means the proposition is incomplete in the selected chain; it does not assert that the omitted item was caused by the selection cap. The exact cause remains unknown unless a target-bound item trace proves it.

## Verification boundary

The exact old `annual14/review.json` and gold remain frozen. This V2 review does not rewrite them or convert original fallback pages into selected evidence. No LLM, summary, cache recovery, or W12 step was run. The full relevant natural test packages passed after a separate test-fixture isolation fix; see current PWF status and progress log.
