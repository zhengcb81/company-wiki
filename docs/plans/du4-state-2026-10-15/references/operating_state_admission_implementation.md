# §7.6 IR operating state / denial — executable TDD design

**READ-ONLY PREPARATION / SOURCE AND TESTS STOP.** 2026-10-14, `/root/table_admission_review`. This is a design and baseline observation, not completed implementation or a passed TDD suite. No source/tests/PWF/config/Git writes, original reopen/parse, download or LLM call occurred.

## 1. Established evidence and limits

Primary retained evidence: `.planning/shared-reading-production/type-matrix-root/root-cause-followup/{handoff.md,handoff.json,cn-ir.json,execution.json}`. Original source SHA is `221467c15a24180205a8226f96fea9bda0262c866d5ba8aa31889ec96e6466d7` (153,851 bytes, six pages). Its earlier bounded observer read 302 native units once and selected 38 spans; original before/after and canonical/native verification passed. This preparation **uses that retained receipt**, and does not rehash or reopen the PDF.

Target `m41` is a complete, untruncated QA package with three members and no package diagnostic/withholding. It contains the actual investor question and two management answer units. First answer:

> 答：您好，公司现无生产 VC（碳酸亚乙烯酯）的情况，根据公司控
> 股股东中国节能信息，中国节能与宁德时代已经建立了联系，并希望建立
> 业务协同与合作。

Actual native unit: `urn:company-wiki:narrative-unit:sha256:bd75a8c377fefb5f82492bb8191c62d815aa2dae2233cdb3e077107a2dc0b087`, management, `loc:v1/page:3/table:0/row:0/column:1`, text SHA `75d6843575a7923f58d9cf417379115876830f6760fecd0c2eaa683efd317d0d`. The current pure predicate and `_admitted` were called on the saved text/role/profile: `eligible=False`, score 0, `admitted=False`.

The second answer concerns the shareholder's share purchases. It is not a separate operating anchor. It still belongs to the **existing complete QA closure**; admitting the business answer must not silently shrink that closure, discount its cost or mechanically make every context member a business claim. The question's large procurement aspiration is also context, not a company statement.

The `m35` shadow duplicate was correctly withheld. Route is investor_qa, section role unknown, and the configured reading strategy already asks for explicit denials and parent/subsidiary attribution. Missing prose/OCR, incomplete QA, route, cap/fairness and shadow exclusion do **not** explain this target omission. Old gold 0/6 and role/whitespace compatibility findings remain historical observations; this preparation does not change gold or certify analyst/model quality.

### Baseline probe

`baseline_probe.py` invokes only existing pure predicates over the three retained target texts and 32 generic synthetic statements. `baseline-observations.json` records their exact inputs/results, source/catalog/receipt SHA+mtime before/after, and zero original/parse/provider/model counts. Process exited 0; protected files were unchanged. No pytest assertions were executed.

- 13/20 specified useful synthetic statements currently fail eligibility: production/involvement denials, some uncommercialized/suspended cases and concrete contact/intention relations.
- 9/12 specified low-information statements currently become eligible **and admitted** in unknown-section management prose: definitions, administrative negation about shareholder questions, bare lifecycle noun lists, generic hopes, and an English financial-total composition.
- Existing explicit qualification/conditional-plan examples already work; preserve them rather than writing a redundant recognizer.
- A question and a QA shadow can contain operating keywords, yet both correctly fail `_admitted` through their source role. That responsibility should stay at the source/structure boundary, not be replaced by punctuation guessing.

All synthetic expectations are **specifications, not a representative recall score**. The exact same-source real omission is proven; proposed generalizations need TDD and later original replay.

## 2. One shared source predicate, with bounded assertion semantics

Primary repair belongs to `source_catalog/narrative_business_policy.py::detect_reading_business_fact`, already consumed by the shared reading selector. Do not add an IR-only selector, a company/product vocabulary, forced-all-QA path, higher cap or a second ranking engine.

Current common cause is broader than one missing negative expression:

1. `activity` uses `_OBJECT × _ACTIVITY` co-occurrence in a clause. It admits words such as “产品认证与商业化” without a disclosed operating assertion, or a sentence negating receipt of **questions about** commercialization.
2. Source-bound state predicates such as “does not manufacture NAME / 现无生产 NAME / not involved in BUSINESS / suspended production” are missing.
3. The legacy `detect_business_fact` OR path can bypass narrower new relation semantics; e.g. “products segment comprises revenue and profit” is admitted as business structure.
4. Concrete **contact** and **intended cooperation** have no shared relation predicate. A strategy string promising their preservation does not execute admission.

### Implementation shape

- Keep the existing `OperatingFact` API and the existing opt-in 0.9 reading path. Old `detect_business_fact`, N6 legacy recognition and explicit 0.8 replay stay unchanged.
- Use the existing `matching_reading_text` and bounded `_reading_clauses`; native line wrapping/Traditional Chinese conversion affects only the predicate view. Raw text, spans, parser versions, IDs, locators and source roles remain unchanged.
- Replace bare reading-only activity co-occurrence with a **bounded operating predicate/target relation**. Add private state/denial and contact-stage helpers in the same file. Reuse the existing vocabulary and financial-payload helpers where applicable. An arbitrary product name can be the operand of a manufacturing/selling/shipping predicate; it need not appear in a product dictionary or contain the literal word “产品”.
- Useful states include current operating scope/absence, not yet commercially available, suspension/discontinuation, qualification pending/failed/restricted, and a concrete disclosed relationship stage. Negative state is useful source information; it is not a successful milestone or necessarily a risk conclusion.
- Keep qualifier binding local. `not yet` concerns current completion, not permanent absence. `only for pilot use` is not production approval. `project not cancelled` does not prove it was commissioned. A future plan conditional on qualification is useful, but remains conditional/future.
- Apply semantic low-information exclusions to the **affected assertion**, not a whole multi-assertion unit. Definitions/examples, administrative actions about receiving questions/notices, bare nouns and unsupported generic good wishes must not obtain fact status through another OR branch. “感谢关注，公司现无生产 X” remains useful. A real operating statement following a definition also remains useful.
- Financial-total composition must not borrow a product/segment noun to become business structure. Conversely, “shipments were suspended, reducing product revenue” contains an operating cause and remains useful. Add a financial exemption only for the actually qualified operating relation, not for any negative word or any finance section.
- Preserve the existing single `OperatingFact` accumulation and ordinary bounded score. New reasons can distinguish `operating_state_boundary` and `business_relationship_stage`; they must not imply completed cooperation or increase scores solely because several negation tokens match. No universal negative-word blacklist.
- Do not require another company lookup, actor ID, header echo, hash check or permission receipt. The source layer already owns source identity. Missing attributed actor/period can remain unknown where genuinely absent; no compulsory invented stage or quantity.

### Actual IR meaning that must survive

| Source speaker | Attributed actor | What the source says | Must not become |
|---|---|---|---|
| Management | Issuer (“公司”) | Currently no production of VC | Current production; another product's absence; no battery business of any kind |
| Management, citing controlling-shareholder information | Controlling shareholder 中国节能 | Contact with 宁德时代 has been established | Issuer established contact; independently verified customer relationship |
| Management, same attributed actors | Controlling shareholder and counterpart | Hopes for business synergy/cooperation | Signed cooperation, supplier qualification, purchase order, shipment or revenue |
| Investor | Question premise | Asks about possible large procurement support | Established company procurement fact |

`source_role=management` identifies the **speaker**, not the beneficiary/legal actor. `source_id` identifies the document source, not every statement's subject. Keep these distinct without adding a public actor DTO. Do not automatically classify “no current production” into an invented commercialization ladder stage; the configured policy explicitly allows stage not applicable.

## 3. RED-first test package and acceptance assertions

Suggested exclusive new file: `tests/unit/test_reading_operating_states.py`. Use pure `NarrativeUnit`/`DocumentStructure` post-parse builders and existing public `select_reading_evidence`; no real PDF parse in the unit/integration node. Use fixed arbitrary names, then parameterize several fresh company/product tokens and Chinese/English/Traditional Chinese/native-wrap forms. These are all **NOT_RUN TDD specifications**; baseline observations are not substituted for failing tests.

### A. Pure shared predicate: current state and strong exclusions

Turn the 32 rows in `baseline-observations.json::synthetic` into explicit parameterized tests with the intended booleans. Assert eligibility, specific state/contact reason and no `business_progress` implication where no progress occurred; avoid brittle exact total-score snapshots. Preserve the existing working positive controls. Key pairs:

| Useful assertion — eligible | Paired control — not a meaningful operating fact |
|---|---|
| 公司现无生产 QJ-11；We do not currently manufacture Novalon | 收到/未收到关于生产问题的签到文件；no questions were received about commercializing a platform |
| 公司目前未涉及某存储业务；not involved in storage services | 本公司术语表中“业务参与”的定义；owned glossary containing `our/company` |
| A platform remains a research prototype, unavailable for commercial sale | “Product qualification and commercialization” noun list |
| 第三方暂停其滤芯生产；supplier suspended production after unsuccessful validation | Revenue/profit declined, without any disclosed operating cause |
| Parent has not obtained customer qualification; third party is approved only for pilot use | Pure financial totals under a products/segment heading |
| Named actors held technical discussions about equipment and hope to cooperate | “Thank you, look forward to cooperation”; generic hopes that adoption will go well |

Additional paired boundaries:

- Current negative plus **concrete conditional next-stage plan** remains useful; changing `if qualification is obtained` to an already completed milestone is not permitted.
- `not cancelled` versus `cancelled`; `not yet in production` versus `not a production bottleneck`; preserve each denial's grammatical scope. Do not infer the opposite positive proposition from double negation or absence of a denied event.
- An operating assertion followed/preceded by a glossary or courtesy sentence remains useful. Finance/administrative words elsewhere in the unit must not borrow the product predicate or suppress a real separate business assertion.
- Arbitrary names, existing abbreviation handling (`Ltd.`/`Inc.`), Simplified/Traditional and native newline equivalents retain the same eligibility; **raw bytes/locators remain distinct and unchanged**.
- “没有/No” **without an observed referent**, “不便评论/We have nothing further to disclose”, and unanswered questions do not become production absence or a completed stage. Separately test an actual complete, same-record yes/no operating Q+A (e.g. “Have you started commercial shipment of Product N?” / “No.”): that may carry a source-bound denial, but only through the genuine full exchange, never the question premise alone or an unrelated adjacent answer. The current text-only predicate may lack this exact interface; a RED should report the required source consumer change to ROOT before expanding ownership. Do not quietly declare all binary answers worthless or create an IR-only heuristic. Referent-only qualifiers use existing closure, not guessed linkage across units.

### B. Real selector integration: roles, actors, stages and closure

Use normal `select_reading_evidence` over constructed parsed units in unknown section; repeat business denial in investor QA, ordinary annual prose and a call. Assert exact original raw text/role/locator/parser identity, source ownership and unchanged inputs, not merely selected count.

1. Complete QA: investor asks whether issuer supplies Product N; management says issuer does not make N, parent contacted Counterparty Z and only hopes to cooperate. Select the **complete existing Q+A package**, business answer as anchor and Q as context. No extracted completion or invented numeric requirement.
2. Add a second management answer about share purchases, matching real m41 topology. Its whole raw text stays charged as QA context; it does not obtain business anchor/value merely through membership. Do not trim this member to make the budget fit.
3. Question-only, shadow-only and no-answer controls: no fact anchor. Preserve `ANSWER_MISSING`/nonselectable diagnostics. Do not globally delete source shadow units.
4. Identical questions with different answers/turn IDs, and adjacency across genuine source parents: do not borrow another actor's answer or create a synthetic closed QA. Existing source group ownership is authoritative.
5. Capacity below the full QA member/character cost: whole exchange withheld/deferred, not a cheaper selected denial without its needed context. At normal unchanged 96 spans / 48,000 chars, eligible complete QA is available; no cap increase.
6. Same text spoken by management vs investor_question: only source-owned answer can anchor. Literal `问/答` inside quoted body does not reverse actual role.
7. Admission versus value: unknown-section definition/admin/noun-list has no fact. A business-section description may remain readable, but must not become `meaningful_fact` solely because its section has business priority.
8. A conditional plan and actual contact use the same source-owned raw spans but preserve different wording/stages; all sent policy constraints include the existing actor/negation/stage responsibilities.

Do not introduce a permissive stub that forces the predicate true in selector tests. The suite must invoke the production shared predicate so missing wiring is observable.

### C. Legacy, cache and final quality responsibilities

- Verify explicit old 0.8 selection and parser/span identity against existing regression fixtures; reading-only semantic changes must not rewrite old results.
- Bump `READING_BUSINESS_POLICY_VERSION` when the semantics change. The existing inventory already imports it. Add one cache invalidation assertion through the real inventory/freezer/comparator; do not add another hash manifest or whole-repository fingerprint.
- Selection tests can prove that original negation, attributed actor and future wording reached the sent closed evidence/policies. They **cannot prove arbitrary generated prose is factually correct** merely from header language, citation membership or a fake model response.
- ROOT later schedules one bounded actual-original IR replay, guarded SHA/mtime/size before/after and no budget/cap change. Target is actual m41's source-owned business answer plus complete closure; do not force an exact new total span count, rewrite gold, or call it full-source recall.
- Real model summary, if ROOT includes it in the existing planned live node, requires independent claim review of the four-row meaning table above. A parent→issuer change or hope→contract change is a quality failure even if JSON/citations are valid. No model call is authorized or performed by this design task.

## 4. Precise non-overlapping ownership recommendation

| Owner | Exclusive write scope when ROOT opens next window | Interface and handoff |
|---|---|---|
| Semantic lane | `src/company_wiki/source_catalog/narrative_business_policy.py`; new `tests/unit/test_reading_operating_states.py` | Existing `detect_reading_business_fact(text)->OperatingFact`; same public type, original wording untouched; RED/final concentrated logs + exact SHA |
| ROOT | Existing integration/PWF/generation/version receipt and later real replay/summary quality | Reads semantic lane's unchanged API and new policy version; publishes once major node is green |
| Routing lane, if assigned | Normalization/form evidence, observation/profile signal files and its own tests | No semantic-predicate edits; route-specific `narrative_reading.py` integration remains ROOT-owned |
| Parser budget lane, if assigned | Existing parser/subprocess resource files and its own tests | No semantic-predicate edits or cap/QA changes |

Semantic lane should **not** edit `n6_candidate_operating_facts.py`, `n6_scope_changes.py`, `narrative_reading.py`, source matcher/replay files, shared QA structure, table qualification, catalog/compiler, model/decoder, or existing broad tests as an initial repair. Existing catalog already states the desired denials/stage/actor requirements. If a new RED proves the shared consumer or a catalog entry genuinely lacks a needed interface, report the exact file/line and let ROOT reassign ownership before editing it.

## 5. One major verification node, then SOURCE STOP

1. Write the new dedicated RED suite and save actual failure output; do not alter existing tests/gold to accept old behavior.
2. Implement the shared reading-only predicate/branch reconciliation with its policy-version change. Keep source IDs, original role, budget and API fixed.
3. Run one concentrated node: new tests plus existing reading semantic value, structured QA, cross-script relations, relevant legacy business/native-boundary tests and real dependency/cache tests; Ruff and mypy for changed source. No need for whole repository/long native-format parsing at every helper step.
4. Save RED/failed/resolved commands, exits and exact changed source SHA; isolated Temp/sentinel/config finally restored, 0 suppliers. Return SOURCE STOP to ROOT.
5. ROOT performs the existing combined integration/actual replay/quality node once other non-overlapping lanes are ready, then commits, pushes and updates PWF. No per-case approval, new manual signature, canary permission, public/private classification or another identity handshake.

The independent counterexample reviewer proposed the same common cause and 12 bilingual pairs. Its suggestions were NOT_RUN and have been incorporated into the design rather than represented as tested fixes.
