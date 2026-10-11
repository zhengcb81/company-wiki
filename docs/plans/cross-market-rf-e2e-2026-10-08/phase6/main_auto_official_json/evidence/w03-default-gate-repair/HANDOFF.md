# W03 default gate repair — stable MAIN handoff

## Outcome

Source is stable. ROOT can perform independent final review and normal commit/publication. This handoff does not claim a new whole-repository prepush pass: ROOT owns the other two failures and the final normal gate.

- Original native prepush is copied unchanged as `original-prepush-red.log`: 7 FAIL / 3137 PASS / 197.27 s. Five pure failures belong to this task, two unrelated responsibility failures stay with ROOT.
- Exact original five failures reproduced with unchanged tests: `red-original-targeted.log`, 5 FAIL / 1 PASS / 0.85 s.
- Before source repair, fourteen new source-meaning/atomicity/boundary cases: `red-new-semantic.log`, 10 FAIL / 4 PASS / 1.00 s. Four boundary failures were the new test's overly broad assumption that any existing singleton group is a cross-boundary join. That new assertion was corrected to reject a shared group between the distinct-boundary pair. Actual singleton context identity is legal. Historical red output is preserved; the old five tests were not altered.
- Targeted original + new cases: `green-targeted-attempt-01.log`, 20 PASS / 0.69 s.
- One concentrated final responsibility node: `node-pure-business-public.log`, **122 PASS / 35.96 s pytest, 38.4066744 s outer**. Exact command, native log SHA and source stability are in `node-receipt.json`. The node comprises all 60 original/current evidence unit cases, 56 business recall unit cases, four real-parser/native-projection business integration cases, and two relevant public node cases.
- Ruff: 3 owned files clean. Mypy: 2 changed production sources clean. Both used the same independent temporary directory, not repo caches.

## Root cause and repair

### 1. Bare topics had become business relationships

The 0.7 detector's Chinese structure regex accepted `主营…业务`, `包括…产品`, and bare channel/customer/process labels. A company name, a generic activity list or words about paying attention to a market therefore gained `business_structure` and bypassed the old static-description exclusion. The low-altitude and CPO positive spans were already selected; that test failed because a third generic product/solution span was also selected.

The shared policy now recognizes actual operating relationships: product purpose/application, channel supply/sales, production mode/process arrangements, material sourcing, and component enumeration containing a concrete component rather than only generic business categories/activities. It no longer treats a bare heading-like label, generic `研发、生产和销售` category list, or `多类产品和配套解决方案` as structure. Merely mentioning `生产流程` also does not assert a mechanism. The rule is format-independent classification: no company/ticker or document allowlist, source text remains original.

Useful static disclosure remains eligible without an event verb: an industrial controller/electric actuator product split, actual equipment application, an order-driven modular production mode, and an overseas dealer/local installation relationship all have positive controls and original locator replay. No general prohibition on static主营 disclosure was introduced. Existing current progress, concrete emerging-business, industry licensing change, strategy, constraints, finance/table and IPO tests remain unchanged and green.

### 2. A selected product lost its referential event relationship

The old neighbor layer only adds a previous product paragraph when it is not already selected. New 0.7 business structure recall selected that paragraph first; the legacy layer therefore skipped the connection. The event retained a singleton sentence group, while its product antecedent had no group. Both paragraphs were visible at normal budget, but the explanatory `adjacent_subject_context` was lost and a one-span limit could keep an unresolved referential event alone.

The 0.7 business grouping layer now recognizes an explicit same-page immediately adjacent PDF reference to a real event. It retains both original units in one existing-size atomic group and adds `adjacent_subject_context` to the antecedent without overwriting original reasons or adding a score bonus. Existing singleton sentence groups may be extended; genuine multiple-member project/PDF groups retain their separate responsibility. Source/parser/version/role/language and speaker/QA/parent/projection/record/section boundaries still apply. The added bridge only concerns actual PDF text units; TXT, whole native JSON fields and OCR are not reformatted into synthetic quotes.

The one-span negative omits both required members and reports partial with two omitted candidates. The two-span positive retains both literal paragraphs and replays both exact locators. Four boundary negatives independently preserve separate speaker, QA group, parent SHA and section identities. Existing broader mixed role/language/native field/group bounds tests also remain green. Default 96, IPO 160, group 8 units / 1,200 characters are unchanged.

## Actual write set

- `src/company_wiki/source_catalog/narrative_business_policy.py`: 29 insertions / 6 deletions.
- `src/company_wiki/source_catalog/narrative_business_groups.py`: 32 insertions / 4 deletions.
- `tests/unit/test_narrative_evidence.py`: 79 appended lines, 14 parameterized cases. Every original test body and assertion remains unchanged.
- This evidence directory only.

`narrative_evidence.py`, shared runtime/selector binding, all W04 sources, public CLI test, configurations, raw fixture and installations are unchanged. No central PWF/Git mutation. Exact final owned SHA values and all-before/all-after source/config/fixture comparison are in `protection-receipt.json`.

## Version and real-public compatibility

Explicit 0.6 remains the unchanged old algorithm. Its complete ordered MSFT package fingerprint remains `11ad9c7f21c92d10847861f387a16ce1035f94da6a47a50128b354d0594b6d9f`. The repaired default/explicit 0.7 package also remains exactly `c5e498acbb5d5c158a030b6e4d3bcec3713f408f2c49baa85717b3d63b905478`: 103 candidates, 96 selected, 7 omitted, partial. The immutable real TXT still has SHA `4ac3b4f0fa1be928b56b4ef9775cac694a1712d46785bb1fa28d2a6a68d7852a`, parser 0.3.1 and 489 real units. All nine management business anchors remain; both recorded policies resolve every group and the actual public reader/search/lookup returns the true original locator evidence. ROOT's public test and its fingerprint assertions needed no edit.

The other selected public test exercised real batch CLI → compute/model child workers → local loopback model → publication → public read → same-run resume → exact new-run reuse. It asserts actual Chinese/English licensing change contents, role/parent metadata, correct frozen 0.7 policy, exactly three loopback POSTs, model max-output 400, initial accounting 276 tokens, unchanged DB dumps on resume, and zero incremental reuse tokens/cost. This is local deterministic model simulation, not paid supplier execution; no provider acquisition or vendor API occurred.

## Why the earlier node missed this

Earlier W03 tests proved the new rich semantics, version binding, recorded-policy replay and full real TXT recall. The global default then changed from 0.6 to 0.7. Original Chinese negative/noise and selected-antecedent tests were not included in that narrower concentrated responsibility package, so the default's unintended effect on those older contract tests reached the normal prepush gate. This repair includes that entire pure evidence file alongside the new semantic tests and public content path. It does not weaken five old assertions or pin them all to 0.6; legacy pinning remains limited to tests explicitly proving historical behavior. No new human signing, authorization JSON or permission gate was added.

## Restoration and limits

`node-receipt.json` confirms removal of the owned `cwp-w03-gate-*` temporary directory, including test databases, loopback artifacts, originals and mypy cache. Protected configuration/fixture bytes remain unchanged; shared/W04 source hashes remain unchanged. External provider/model calls, paid tokens and cost are zero. Existing source scan coverage is not a claim that every sentence has financial-investment truth or that the selector is semantically exhaustive. Classification remains a deterministic bounded heuristic; future substantive mistakes require source-oriented evidence/quality review rather than more permission layers.
