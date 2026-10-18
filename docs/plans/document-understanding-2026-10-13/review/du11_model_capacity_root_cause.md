# CN/MiMo paid-response failure: common root cause and implementation proposal

## Conclusion

This is **not an output-token shortage**, and raising20 to22 is not a repair. The source reader selected the10 required business facts, then64 native source tasks were placed in one model request with no executable priority/coverage plan and a global20-clause instruction. The model emitted **22 clauses in19 tasks** and omitted45 tasks. Its1264 completion tokens are far below the configured8192; there is no observed truncation. The hard aggregate clause check then killed the entire summary before clause-level diagnostics ran. Separate content failures remain even if that check is removed.

The correct common boundary is: **source-owned finite execution/coverage planning + task-local extractive factual witnesses + existing metered recoverable execution**. Native source tasks are evidence organization, not a model-call schedule. Valid local IDs are not proof that a paraphrase is true.

## Bound evidence and actual offline execution

- Incident source HEAD: `ae9a2fbb`; diagnostic checkout: `6b4aef5631e15ecd4e93c0907b633fdacb14c860`. A read-only `git diff ae9a2fbb..HEAD` over scoped protocol, task planner, dispatch and quality-owner files was empty.
- Original final UTF8 bytes:5004; SHA `93eadb70a031420b382e6e4b845f6469c3cf5a608b3c182d0f2f035c02889277`.
- Actual HTTP-body SHA `a832da49d29b97a478f4b1f0706da20bd7fdd2299e62f91d4e25cca323b03bf2`; reconstructed canonical task-binding SHA `c0e298a66b497f553ed8fceadc6765a00a7e65a2bbbbe9d176f7b395c2846b08`.
- Formal original decoder reproduces `NarrativeContractError: summary claims exceed twenty`.
- Additional diagnostic isolation passes each **unchanged original clause** through its true original task binding.21 are structurally accepted; one bad local reference is rejected. These synthetic single-clause envelopes are diagnostic probes only: they are not a modified production response, final artifact, or evidence that21 clauses are true. Original gzip files remain unmodified.
- Reproducer: `model-capacity-diagnostic.py`; detailed observations: `model-capacity-formal-decoder.json`; structured findings/TDD: `model-capacity-root-cause.json`.
- No API, secret, network, real parsing, unit suite or production write occurred. Only owned scratch reports were created. No original was copied.

## Actual failures and content risks

| Finding | Real observation | Root responsibility |
|---|---|---|
| Global count |22 total,19 tasks; global20 check before all clauses | Output-plan/schema/decoder agree on one finite container; recover bounded usable peers with explicit dispositions |
| Inconsistent cardinality | JSON schema maxItems20 applies to each task array; prose and decoder mean20 total | Program-owned execution schema, not another prompt sentence |
| Invalid citation |t30 second clause uses `p31p2`, prose from t31 | Never repair IDs or move prose across tasks automatically |
| **Legal citation, wrong facts** |t62.p2 is **PRISMO UniMax**, Mini-LED,785mm,164x4/72x6 inch; output is **HiT3**, deepUV,1400deg,18x2 inch from t61.p2 | Need local factual witness/atom fidelity, not ID membership alone; current decoder accepts it |
| Negation scope leakage |t6 cites major operating-change not-applicable but also adds t4 noncore-business not-applicable | An assertion cannot borrow another task's negation; current decoder accepts it |
| Duplicate |t37 repeats Preciomo Udx verification/repeat orders in two clauses | Dedup source event identity before consuming digest slots; stronger verification-passed wording needs its own support |
| Ambiguous table numerics |t1 outputs investment amounts from p4/p5 flagged `table_structure_ambiguous`, despite explicit constraint against attributing values from ambiguous columns | Evidence-quality owner must keep unproven number/column/period attribution unknown; current needs_review label alone retains unsafe numbers |
| Mixed modality |t1,t8,t30-2,t45,t52,t53 combine current/target/future into one clause with one actual/planned enum | An atomic event's subject, period, stage and modality travel together; text may preserve future words while typed metadata misrepresents part of it |
| Incomplete subject |t5 only supplies “该新产品”; some native tasks start mid-sentence; t3 ends at“影” | Heading continuity is not universally closed referent context; retain unknown instead of completing from global memory |
| Input noise allocation |Generic risks, table amounts and some accounting boilerplate compete with product/target facts | Source-owned scope/coverage prioritization, not all native tasks treated equal |

### What happened to the10 selected business checks

The pre-POST oracle reports10/10 **selected support**, not10/10 delivered summaries. Against original failed response bytes:

| Business fact | Source task | Model result |
|---|---|---|
|Five-year60%/70% target |t17|Missing|
|Current50+ products/>30% product category coverage |t17|Missing|
|Completed controlling acquisition of CMP business |t16|Missing completed event; t8 conditional synergy cannot substitute|
|Preciomo Udx shipment/validation/repeat order |t37|Present with duplication|
|PRISMO PD5 validation+repeat orders |t39|Missing; t40 unnamed new GaN shipment is another event|
|8inchSiC validation stage |t41|Present|
|InP development started + H2 prospective shipment |t44|Missing|
|Primo Matrix prospective shipment |t45|Present text, bundled in actual clause|
|TSV300E serving/repeat orders |t45|Present|
|ThirdgenTSV order + future validation shipment |t45|Present text, mixed modality|

This is manual content comparison, not an official final-artifact score: **there is no final artifact**. The stated future/current/target coverage gaps are important even though production must not consume benchmark gold or enforce all64 tasks as a new gate.

## Compare implementation choices

| Choice | Benefits | Limits / decision |
|---|---|---|
|Raise20 or take first20 |Cheap apparent success |Leaves wrong product, negation leakage, duplicates and missing key business facts. Reject.|
|Only stronger prompt |No architecture change |Already explicit on subject/stage/units/localbasis; supplier emitted errors anyway. Reject as root repair.|
|**Source-owned finite plan and focused batches** |Controls attention, real output allocation and omissions before spending; preserves all64 native tasks |Necessary. Calls must use existing budget/lease/outbox; no unbounded fanout or onecallpertask assumption. Explicit deferred state is valid when budget cannot cover all.|
|**Exact quote/offset witness and extractive business cards** |Prevents valid-ID/fake-prose being silently accepted; keeps product/quantity/period/stage together |Necessary complement, not a separate parsing engine. Exact quote proves extraction, not arbitrary attached paraphrase. Safe fallback is source extract/unknown; a free-form paraphrase cannot receive automatic semanticPASS merely because a quote is present.|
|Extra model verifier for every clause |May detect some entailment errors |Costs more, adds own error/recovery; not first fix and no blanket extra paid loop. Any selective verifier must consume the same configured budget and retain unknown states.|

## Concrete interface/owner plan (no code changes yet)

### A. Plan source scopes separately from model execution

Keep `SummaryTaskPlan` and all64 source tasks/evidence unchanged as the causal inventory. Add a **finite execution-plan view** in the existing source task/scoped compiler owner, versioned and hash-bound to source selection, task binding, configured model/output/cumulative budget and reading policy. Each planned batch contains:

- Stable batch ID and ordered original task keys, closed support/context sets, input bounds and allocated output slots.
- Required coverage **categories from existing reading strategy**, source-owned priority/reason, without company-specific constants or benchmark gold.
- Task dispositions: emitted, redundant-with-source-event, deferred_budget, unsupported_context, failed_reference or unprocessed. Missing is not negative evidence.
- Cross-task current/target or same-project stage relations must remain an explicit closed scope. Dedup only same evidence/event; do not merge unrelated products or erase historical versus present stages.

A compact final digest may keep20. Detailed source-scope business cards must not be silently discarded to fit that digest. Choose an explicit versioned representation in the **existing canonical artifact** and update its consumers/tests if the old canonical20 limit is kept; do not add a second authoritative summary store or hide unlimited cards in metadata. Every physical output remains bounded by configured byte/token/cost limits. This is one responsibility-level contract change, not a new approval chain.

### Existing signals are sufficient to begin finite allocation, not to pretend perfect semantic ranking

The existing task owner already carries `selection_reasons`, `topics`, support role, kind, section role and support/context IDs. Per-span quality and existing reading groups/policies/section anchors are also available without reparsing semantics. The current model presentation deliberately omits diagnostic selection reason strings, but the program can consume their typed meaning when planning.

Actual examples: t16 has `corporate_development`/`new_business`; t17 has exact `business_coverage_relation` reason/topic; t1 is operating_table with `table_structure_ambiguous`; t2/t3 are risk kind. These are enough to reserve business-category coverage before spending slots on table amounts and generalized risks. However,55/64 tasks are native_continuity with section_role unknown; t44 InP has only generic `operating_description_unknown`/core_business. t64 pure lease accounting even has core_business/capacity_projects/operating_restriction. **Do not rank solely by role, generic new_business label or a noisy reason as if it were semantic truth.** Use source-owned explicit event/category signals plus fair coverage across existing section/support scopes, quality-aware limits, and honest unknown/deferred states. Exact InP importance is not already typed; do not invent that label. A finite balanced MOCVD scope batch can cover its source paragraph without new parsing or company-specific rules.

The current task order starts with operating table, two risks, background, then55 native-continuity business tasks: source inventory registration order is not priority order and exposes a primacy bias. Execution order and slot allocation must be an explicit program-owned plan. `model-capacity-task-signals.json` records all64 actual signal rows for TDD reuse.

### B. One output contract, clause-local recovery

Use either one flat bounded clause array with task_key or explicit per-task allocated slots; schema, request and decoder share total bounds. Do not only change schema wording: current JSON-object transport does not guarantee schema enforcement. Bounded parsing validates all recoverable clauses and records every diagnostic; source/model/request identity and explicit translation stay whole-response failures. Bad localbasis/text/modality affects that clause. Overflow means a visible partial/deferred execution outcome; never first20 slicing, silently relabeling22 as20, or promoting this old failed v4 response to a new protocol success.

### C. Source-grounded business cards before free paraphrase

Each card binds original task key plus exact witness offsets/quote to factual parts. Program rechecks quote bytes and canonical evidence IDs and retains support/context closure. Card atoms keep product/subject, quantity+unit+currency+period, actual/target/conditional stage and negation together. Stable identifiers and numbers must be supported locally, never merely elsewhere in the document. `table_structure_ambiguous` cannot prove attributed numeric fields without independent validated owner evidence. Mixed current/future clauses split or abstain. If paraphrase entailment remains uncertain, preserve original extract or explicit unknown/quality diagnostics; do not call structural validity truth. No human signoff requirement is introduced.

An additional traceability detail: `resolve_basis` computes exact selected basis_ids, but the canonical claim currently emits the entire task.support_ids. For t1 a p4/p5 claim therefore cites all9 task fragments. Native closure is intentional and should remain; the versioned business-card contract should preserve **exact factual witness IDs/offsets separately from support/context closure**, so broad closure cannot stand in for the exact asserted quantity. Do not remove qualifiers merely to make a narrower citation look valid.

### D. Execute and recover through the current system

Every focused batch is an existing metered narrative execution unit, under **BudgetedNarrativeCaller + AUTO lease/generation/outbox**, the same run/mother budget and existing final artifact activation/cache. Each batch's request/body/selection/task-binding/model/decoder identity is pinned. Persist a bounded **complete paid response** in the existing attempt/artifact-outbox path before decoding/activation, then allow exact-byte decoder replay at0POST. No second taskstore, responsecache, client, ledger or authorization JSON. Invalid/clipped/missing bytes cannot be claimed replayable; changed selection/protocol cannot masquerade as the same request. Unknown reservations remain charged conservatively.

Current response usage was settled once (13555 input+1264 output=14819tokens,2681microUSD). Mother snapshot after this call is **628394tokens /393953microUSD**, limits2M/$20 and historical unknown7 retained. This is a snapshot, not a new budget origin. The current failure diagnostic happens to contain complete5004bytes, but `failed_final` generally supports clipping and only a SHA is durable in the usage row; diagnostic prefixes are not a general paid-response cache. This runner correctly stops with no blind resend. Its activation/cache0POST branches were **not reached** because summary failed first; do not report them PASS.

## TDD and large-node acceptance

1. **Offline real-response regression:** unchanged22clause bytes still reproduce old CLAIMS_LIMIT. Diagnose the badbasis, t62 swap and t6 scope leak independently. Old v4 result retains failed status/version and charge; no editing response to create a green receipt.
2. **Planning synthetic controls:**64+ tasks, reordered irrelevant tasks, duplicates, dense and sparse content, multi-stage/current-target relation, insufficient token/budget. Every source task has an explicit disposition; finite batches and slots remain within actual configuration; gold is absent from production planning.
3. **Quality contract controls:** wrong product with validID; correct product/wrong number orunit; another task's negation; question versus management; plan versus actual; orders versus validation versus mass production; ambiguous table attribution; unsupported subject. Keep originals and partial safe extracts available, with no fabricated facts or manual permit.
4. **Existing durable execution E2E:** crash after provider return/before decode, after decode/before activation, exact replay0POST, ledgeronce, same/crossrun cache, tampered response/input/taskbinding/source refusal. Modelcall not repeated on decoder restart. Per-batch partial failure cannot redownload raw or resummarize completed peer batches.
5. **One concentrated real E2E node after offline fixes:** configured CN/MiMo, HK/DeepSeek, US/MiniMax routes unchanged, finite declared batch budgets, input recall and final content quality separately scored. Freeze reviewed source; run existing activation interruption and0POST checks; cleanup test directories/sentinels and originalSHA. Do not resume paid calls until common fix is selected and offline checks green.

Detailed findings and proposed tests/interfaces are in the adjacent JSON. This document supplies a design decision for ROOT/PWF, not permission to change runtime or spend.
