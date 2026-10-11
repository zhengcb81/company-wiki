# W03 pure business recall — stable handoff

Scope: MAIN isolated tree, pure source selection only. Source and test writes are finished. No commit, push, installation, provider acquisition, LLM call, production configuration/DB/raw write, or root PWF change. This report accepts a responsibility node, not the complete AUTO/RF pipeline.

## 1. Exact write set

Two existing source files and two new cohesive helpers; two new responsibility test files. Neither `narrative_neighbors.py` nor `narrative_group_candidates.py` was changed. The tracked source diff is 53 insertions / 10 deletions across the two existing files; new helper and test line counts appear below.

| File | Lines | Stable byte SHA-256 |
|---|---:|---|
| `src/company_wiki/source_catalog/narrative_evidence.py` | 1811 | `8d96775ab0880a1f0ffa1261dc2c967df78afbaeb325a233cef7d6efb9f83dc3` |
| `src/company_wiki/source_catalog/narrative_candidates.py` | 299 | `1374ccd3c74554cb742fe974604b113496f321f507001e8acb96d8b0bed5ef88` |
| `src/company_wiki/source_catalog/narrative_business_policy.py` | 180 | `fde99e4425720b2d344387df6ac4ab6932d3c1563951b51626b7075d7470dfeb` |
| `src/company_wiki/source_catalog/narrative_business_groups.py` | 193 | `859cece970dcc3dd1c4c8a7c5964772c79c3eb804b3292a38aac14763ab3081c` |
| `tests/unit/test_narrative_business_recall.py` | 336 | `a64750af0a0c53e45b034ce7cef7054195fb52a764817e27bf3069b3864605c8` |
| `tests/integration/test_narrative_business_recall.py` | 188 | `8f0203f0dd85eccc356d5f0098c96f08c85cf6c7fc236bd7bff2158d72a341d5` |

The receipt `handoff-final-shas.json` separately records these files and every owned evidence log/script/JSON SHA. New files are untracked pending ROOT's commit. Do not edit existing archived logs to tidy their output.

## 2. Pure API and version ownership

```python
SUPPORTED_NARRATIVE_SELECTOR_VERSIONS = frozenset({"0.6.0", "0.7.0"})
class NarrativeSelectorVersionError(ValueError): ...
def resolve_narrative_selector_version(version: str | None = None) -> str: ...
def select_narrative_evidence(
    parsed: NarrativeParseResult, *, title: str,
    existing_kind: str = "unknown", max_selected: int | None = None,
    selector_version: str | None = None,
) -> NarrativeEvidencePackage: ...
```

In this handoff the global default is still **0.6.0**. `None` resolves the current default once. Explicit 0.6.0 uses the original policy, explicit 0.7.0 uses the new one; unsupported and non-string versions raise the typed ValueError. No parser/source/locator version changes. Metadata producers must use `resolve_narrative_selector_version(requested_version)` and the same explicit value used for selection. A package does not gain a new selector-version or diagnostic field.

`_candidate_rules(*, selector_version: str | None = None) -> CandidateRules` and `_base_candidates(..., selector_version=...)` are internal pure seams. `CandidateRules.reject_text: Callable[[str], bool]` is appended after `static_definition`, retaining every old positional field. Its legacy default accepts text; only the new policy replaces it.

A final actual negative proved why the fundraising reassessment must also receive `effective_version`: under a monkeypatched default 0.7, explicit 0.6 originally changed `dropped_financial_count` from 0 to 1 for a restored project row. The two initial candidates and the restored row otherwise stayed identical. That global leak is now fixed, not hidden by keeping the default old. Both normal and finance-headed fundraising rows replay identically under the changed global default; complete ordered MSFT legacy fingerprint also remains exact.

## 3. Business meaning and bounded support groups

`narrative_business_policy.py` exposes:

```python
def business_objects(text: str) -> frozenset[str]: ...
def business_qualification(text: str) -> bool: ...
def detect_business_fact(text: str) -> OperatingFact: ...
def reject_finance_only_text(text: str) -> bool: ...
```

Concrete industry operating objects (export/import licensing, operating approvals, supply/demand, industry policy/access/standards) have an independent same-clause actual-change predicate before the generic product/customer noun requirement. Recent/latest attention alone is not change. The originally unreachable industry branch was a real defect found by ROOT review and is now covered by Chinese/English positives and boilerplate/recency-only negatives.

The new detector extends the original operating fact detector with bounded clause relationships: actual operating events, cost/efficiency/model-routing mechanisms, explicit company product/production/channel structure, operating constraints, current industry change, and concrete operating strategy. The policy has no company names, ticker rules or QA-number exceptions. Business structure can be valuable without an event verb. Definitions, administrative language, vague customer/innovation aspirations, dividend-only content and financial notices remain negative. New meanings do not gain a financial-table exemption.

New selection reasons are `specific_business_event`, `operating_mechanism`, `business_structure`, `business_risk_or_constraint`, `current_industry_context`, and `business_strategy`; existing original reasons remain possible. Weak bare `targets`/`because` or a product noun next to a financial notice were actual negative-test failures and have been narrowed to concrete relationships.

`narrative_business_groups.py` exposes:

```python
@dataclass(frozen=True)
class BusinessGroupDiagnostic:
    reason: str
    locators: tuple[str, ...]
    unit_count: int

@dataclass(frozen=True)
class BusinessEnrichmentResult:
    candidates: tuple[EvidenceCandidate, ...]
    group_ids: Mapping[str, str]
    excluded_unit_ids: frozenset[str]
    diagnostics: tuple[BusinessGroupDiagnostic, ...]

def enrich_business_groups(
    units: Sequence[NarrativeUnit], *,
    initial_candidates: Sequence[EvidenceCandidate],
    initial_group_ids: Mapping[str, str], rules: CandidateRules,
) -> BusinessEnrichmentResult: ...
```

Groups retain original unit IDs, text and coordinates, with the existing `selection_group_id` context group. Additional context reasons are `business_group_context` and `operating_qualification`. Existing parser metadata is preserved. Required conditions/negations may not be discarded while only their optimistic seed is selected. Same-source/parser/role/language and QA/speaker/section/parent/projection/record boundaries are enforced; different named products do not cross PDF pages. Analyst and investor questions do not seed company facts. Whole native JSON fields and OCR units are not fabricated into character slices or joined by this helper.

Existing budgets stay unchanged: default 96 spans, fundraising route 160, generic support group at most 8 units / 1,200 characters. Existing project context retains its prior bounds. Oversized or incomplete required groups retain candidates but are excluded through the existing `finalize_selection(excluded_context_unit_ids=...)`; candidate/omitted counts and partial status expose the omission. No optimistic complete claim and no default cap increase.

Diagnostics are an internal tuple: at most 16 entries, each with at most 8 true locator strings and no source text. Actual reasons are `business_group_character_limit` and `business_group_unit_limit`. The exclusion set is not truncated when diagnostics are capped. The public package retains its old shape; ROOT can map existing `candidate_count`, `omitted_candidate_count`, `status`, `coverage_complete` honestly without adding a strict DTO field. `coverage_complete` describes source scan/extraction coverage; it does not override budget omissions or a partial status.

## 4. TDD / static evidence

- `RED-01.txt`: missing explicit version interface.
- `RED-02-semantic.txt`: also exposed new fixture caller errors; corrected unsupported coordinate fields, selector return assumption, and PDF replay keyword only. Expectations were not relaxed.
- `RED-03-semantic.txt`: genuine semantic baseline, 23 FAIL / 17 PASS.
- `GREEN-attempt-01.txt`: two remaining failures; missing actual performance object and typed projection replay caller corrected.
- `GREEN-attempt-02.txt`: original new responsibility matrix 40 PASS.
- `RED-04-bounds-vague-business.txt`: real weak aspiration / because / financial notice failures; semantic relationships narrowed.
- `RED-05-industry-strategy.txt`: generic current industry change and concrete strategy RED.
- **`NODE-01-concentrated.txt`: 109 PASS / 7.28 s**, once, comprising own 47 unit + 4 integration, existing architecture43, budget9, package6.
- **`RED-06-legacy-default-isolation.txt`: 3 FAIL / 1 PASS**, actual global version leak plus old positional signature shift.
- **`GREEN-06-legacy-default-isolation.txt`: 4 PASS / 1.53 s** after the two minimal fixes. No second whole-node rerun.
- **`static-ruff-final.txt`: exit0, all checks pass** for four owned sources and two tests.
- **`static-mypy-final.txt`: exit0, no issues in four owned source files**; owned cache removed.
- **`RED-07-industry-change-without-product.txt`: 2 FAIL / 3 PASS** confirms the unreachable industry-change branch.
- **`GREEN-07-industry-change-without-product.txt`: 30 PASS / 1.17 s**, industry positives/boilerplate/recency negatives plus relevant finance/administrative/generic business/legacy routing.
- **`GREEN-07-full-txt-anchors.txt`: 1 PASS / 1.76 s**, same genuine full TXT and all true-anchor/role/96span replay checks after the fix.
- **`static-ruff-industry-final.txt` and `static-mypy-industry-final.txt`: exit0**; latest code static checks, owned cache removed.

The final responsibility tests are 56 unit cases and four integration cases. No combined final total is claimed as a single execution: concentrated109, four specific legacy regression controls, thirty related industry/finance/admin/version controls and one genuine full TXT replay are separate recorded runs.

## 5. Real data and original locator replay

### Full actual TXT

`full-transcript-final-metrics.json` records actual original MSFT TXT SHA, unchanged before/after, 66,324 bytes, 489 parser0.3.1 units. No test fixture pruning or re-typing.

- Explicit0.6:51 candidates /51 selected /0 omitted /51 verified, ordered package fingerprint `11ad9c7f21c92d10847861f387a16ce1035f94da6a47a50128b354d0594b6d9f`.
- Explicit0.7:103 candidates /96 selected /7 omitted, statuspartial, all96 original TXT spans replay verified;8 atomic groups, largest5 units /681 characters.
- True management anchors recovered include actual launch,50% less cost,90% task routing, resilience if a model disappears, continued cyber operations, return-math negation, silicon price performance, token usage and portfolio mix. Locators for each are recorded in that JSON. These are source statements, not endorsed forecasts or research conclusions.

Original TXT SHA: `4ac3b4f0fa1be928b56b4ef9775cac694a1712d46785bb1fa28d2a6a68d7852a`.
`full-transcript-industry-final-metrics.json` records the final post-review pure policy metrics and whether its full ordered new fingerprint equals the earlier frozen measurement; earlier logs and JSON remain unchanged.
`legacy-0.6.0-msft.json` is the full ordered snapshot; its file SHA includes a trailing newline and differs from the canonical JSON fingerprint above. Do not confuse these hashes.

### Existing original PDFs, public source transport

`real-source-pdf-node-01.txt` and `real-source-pdf-node.json` record exit0, source-reader receiptstatusok and actual matching bytes from the existing source catalog. No acquisition.

- Annual SHA `d64c410832f22f5127277bad6dc357c664aede523561af99150c494857fd3aa5`,9,165,875 bytes /259 pages; bounded original p44:21 old vs24 new selected, all24 actual PDF locator replays; CVD/HAR/ALD and repeated production-order anchors present.
- IPO SHA `19cdb41e03b2d86ac15007753784f5859e1450a2bf79b514a7c0d4bd6830be67`,11,211,796 bytes; bounded original p173–174:14 old vs23 new selected, all23 actual PDF locator replays; build-to-order, negation, sudden-order and short-term supplier constraints present.

The genuine original PDFs were read through `source_reader_cli`, copied only into an owned TemporaryDirectory for parsing/replay and removed. Original complete SHA / original page, paragraph, table and block coordinates were preserved. These bounded page examinations do not claim full-document0.7 coverage. Partial statuses are retained. The miniature PDF integration fixtures are hermetic parser/policy tests, not claims of original page layout.

To repeat the original-source node only if necessary: supply the read-only catalog config as the script's explicit first argument to `real_source_pdf_node.py`, with `PYTHONPATH` pinned to this isolated tree'ssrc. The script receives binary stdout privately and prints only receipts/anchor counts. Existing logs must not be overwritten; choose a new evidence node if repeat is authorized.

### Native official JSON

The new integration test uses a real owned temporary SourceCatalog, imports original native JSON, builds/persists the real official projection, opens `VerifiedProjectionView`, calls the common explicit0.7 selector, converts the actual3.0 select DTO and invokes `replay_verified_projection`. Parent SHA, record/field pointer, language, original source role, question association and issuer scope remain true. Another issuer's finance-only record and translations do not become company facts. Original bytes are read back and equal; the owned catalog/import directory restores to its starting file set. No production handler/result fabrication or source-parser imitation.

## 6. Restoration and limits

- Provider calls0; LLM calls0; incremental vendor cost0.
- All integration owned directories restored and source fixture bytes unchanged.
- Genuine PDF own copies removed; actual source-reader SHA checks passed.
- Production config SHA before/after and at final handoff: `3d159a4edc8e0e4d09b83afa95601c5ec885a18f7bd5d163579f3ff446e3f968`.
- No production source state, original document, projection leaf, automation, RF, audit or shared planning file changed by this line.

## 7. ROOT integration next

ROOT exclusively owns default upgrade, retrieval historical routing, runtime worker/manifest/generation/run binding/resume/reuse and public metadata. Use the exact effective selector version at every producer and replay the declared supported version. Merely accepting old tags while selecting with the current default would fail the recorded0.6fingerprint contract. A new0.7generation cannot reuse0.6selection pins as though their semantics were unchanged.

This source node does not certify full batch publication, RF model quality, recall of every business statement, or complete documents. It supplies bounded additional candidate meaning and source-faithful support groups for ROOT's next cross-boundary node. No extra small-step gate or manual receipt has been added.
