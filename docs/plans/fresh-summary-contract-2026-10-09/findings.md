# W03 findings

The sealed CN annual used input2716/output8192 tokens, finished MODEL_OUTPUT_TRUNCATED and no annual bundle; actual failure remains immutable. Existing twenty-claim schema/prompt does not give a concrete compact output plan.

The sealed HK c4 cited p9 paragraphs32/33/34 while its technical-service-fee proposition needs paragraph35. US c3 omitted slide7 paragraph9 containing previously-reported-in-Azure. Current prompt omits selection_group_id, decoder checks only known IDs/roles. Mechanical membership does not establish entailment.

Independent group-design research is running.

## Interface decision and actual test responsibilities

- Model request1.4/prompt1.7 carries g-alias membership from existing selected_summary_input. Group fields are transient model input/output only; public SummaryClaim remains exactly six fields. Declared full group requires explicit full canonical citations, otherwise whole claim is discarded. No neighboring citation is added. Groupless/[] narrower content stays consumable; known partial atomic context projects needs_review only, never a permission gate. Entailment still requires M3 independent quality review.
- Existing model-only maxItems8 prevents citing an accepted W02 nine-fragment atomic sentence including cancellation qualifier. Citations now bounded by actual pinned span count, existing twenty-claim/280-character promise and unchanged128KiB model/64KiB summary byte caps. Foreign, duplicate alias/canonical and oversized ID lists are rejected. This repairs a producer/consumer contract mismatch, not arbitrary cap inflation.
- Current schema promised twenty claims/280chars only to the model, but decoder accepted21claims/281chars; review RED demonstrates it. Implementing those existing mechanical bounds leaves public DTO unchanged.
- Legacy shared synthetic selection(count) marked every independent complete sentence on a different page as one context group. Independent review reproduced12 quality-test failures from that fixture semantics; fix assigns singleton group per independent sentence, retaining good-claim needs_reviewFalse assertions and explicit real multi-span positive/negative tests.
- Existing integration test creates a CURRENT run and then changes code versions to9; literals1.6/1.3 incorrectly assert historical current version. It now captures actual current constants and still proves zero-rework/unchanged ledger under version upgrade plus request/config/raw invalidation. No completed-run contract is relaxed.
- Token planning is explicitly heuristic: <=8 material claims target,180char target, derived from actual configured HTTP cap without changing provider/model/temperature/thinking/reasoning options; schema still20/280 maximum. Stub compliance is engineering proof only, not real-model quality or M3 proof.

- The old long-summary compatibility test was additionally routed directly through canonical result parsing/validation and bundle projection, retaining all25claims with520characters underoldprompt1.6.0. Producer20/280bounds are not applied to existing persisted reader data. Independent probe proved this before test correction.
