# W03 evidence-group design review

Status: design research only; no source edits, tests, production writes, external HTTP or paid calls. Main source observed at d6444ef9fbce1586652bff903a51285ee680964b. CodeGraph consulted for summary validation and exact canonical claim parsing before known-file reads.

## Root and minimal interface

Current `NarrativeModelRequest` 1.3 / prompt1.6.0 preserves each selected original text with e1.. aliases but omits `selection_group_id` membership. Canonical `validate_summary_draft` / `validate_summary_claim` checks source, citation membership and speaker role; it explicitly does not prove semantic entailment. Existing `selected_summary_input` already groups pinned spans by `structured_value.selection_group_id`, retaining exact member IDs, locators and original text. Reuse that established membership meaning; no second group registry or persisted mutable state is needed.

Proposed model-only envelope:

```json
{"evidence_group_columns":["id","member_ids"],"evidence_groups":[["g1",["e1","e2"]]],"coverage":"selected_excerpts"}
```

A model claim should declare separate `evidence_group_ids` (g aliases) and explicit `evidence_ids` (e aliases/canonical IDs). For each declared group, its exact pinned member set must be a subset of the claim's explicit cited set. Unknown, malformed or uncovered declared groups discard the entire claim with a safe diagnostic. Do not append the omitted members; do not infer group declaration from adjacency. Preserve all original source IDs, hashes, raw text, locators, roles and quality flags. Include group mapping plus the new schema/prompt semantics in immutable input/generation fingerprints.

Absent group declaration must not silently mean an affirmative empty declaration. For legacy/missing declarations or explicit [] with only part of an atomic group, retain a valid narrow claim only as `needs_review`, computed after standard quality projection. A complete singleton/subset can remain usable; mechanical closure is not a new permission to read the source. Declared/full group closure cannot clear OCR ambiguity or make unsupported proposition text true. Adjacent unrelated evidence remains outside that claim unless explicitly cited; a claim that joins independent propositions needs explicit support for each and major-node semantic review.

The accepted W02 contract `test_fragment_count_does_not_split_a_bounded_sentence_from_its_cancellation_condition` contains one nine-span PDF/OCR atomic sentence, including its cancellation qualifier. Current model schema `evidence_ids.maxItems=8` cannot express that complete citation. Canonical `_claim_from_dict` has no eight-item restriction; adapt the model cap to the actual pinned selection cardinality, keeping20claims/text280 and existing128KiB provider /64KiB canonical summary byte limits. Output planning must consider expansion from short aliases to canonical IDs and retained claims; do not change configured8192tokens or swap providers implicitly.

## Exact sealed RC07 samples

### HK annual source

Source SHA d19f183452e9b8d0c47bcb7543dcbf435b585b2610759b42c0cba7c13f7361c7. Sealed artifact `Projects/revenue-forecast-audit/runs/fresh-20261009T065028-hk-00700/roles/storage/public-narrative-observation.json`, byte SHA9ef96be132bf61bf2c03fe76118e057d11885d2f986352a4625bc8ef703058b8; item0 has12spans. All following source_role company_filing, no quality flags.

| Locator | Span SHA suffix | Original raw text | Group |
|---|---|---|---|
| loc:v1/page:9/paragraph:32 | 98bce6d3fc07d14d7b358766434d40a73fe94b5eaee714c017226e2f3739927c | － [newline]金融科技及企業服務業務截至二零二五年十二月三十一日止年度的收入同比增長8% 至人民幣2,294 億元。 | G |
| loc:v1/page:9/paragraph:33 | 3967b1a62437ec2a7e051af742e916560fee91449f08ef3e3a77c16f131d162d | 金融科技服務收入同比以高個位數百分比增長，乃由於理財服務、消費貸款服務及商業支付活動的收入增加。 | G |
| loc:v1/page:9/paragraph:34 | f6a96ebcb9f2c7d211594a145df3e8bfbe03d7c5945dfdf8a371e95dfac3520e | 企業服務收入同比增長接近20%，得益於國內及海外對雲服務的需求（包括對AI 相關服務的需求）增加，以及 | G:operating-fact:0 |
| loc:v1/page:9/paragraph:35 | 61fc052970cc544c039c42de59f0d940fcce765659ef364c638592422ed3c4c3 | 由於微信小店交易額上升而帶動的商家技術服務費收入增長。 | G:operating-fact:0 |

G = urn:company-wiki:context-group:sha256:dfac0eef36837c6a4b3cad900aa60749caba3a0dcb3790b77d6df34a464cab0a. Full span IDs use `urn:company-wiki:evidence-span:sha256:` prefix. Oldc4 cites32/33/34 but text also states35's technical-service-fee cause; it has needs_review=false. Deliberately declaring the operating-fact group with only34 catches the exact mechanical omission; no automatic addition35 is allowed.

### US presentation source

Source SHA c02f4ea1a2719b74d5752559ad7b907d89dd4b47d292424ade8988396fb2dcd4. Sealed artifact `Projects/revenue-forecast-audit/runs/fresh-20261009T065028-us-msft/roles/storage/public-narrative-reread-observation.json`, byte SHA12f2b5d680d968c12b2cbf7c489812b3092549d43f92ef9917f5c5df3a75d8a4;15spans. All following source_role company_filing, flags layout_ambiguous/ocr_used, parser cwp_document_normalization/2.0.0.

| Locator | Span SHA suffix | Original raw text |
|---|---|---|
| loc:v1/page:7/paragraph:8 | 2dffff9465922346c0f799db12ed4b1ff4dc66b7fbe61153bddc48614b4cb700 | · Microsoft 365 commercial cloud will now include GitHub cloud and other developer cloud services as well as Security Copilot which were |
| loc:v1/page:7/paragraph:9 | 58dc15af83cb1dc84818a4bbee4b5494760b3ff0d01ebaaf259e5ea055a1fa4b | previously reported in Azure |
| loc:v1/page:7/paragraph:10 | f458635ae94649ef04c9212054e0ba985009b288271b3b3de0e78058c61ceb42 | · Microsoft 365 consumer cloud is unchanged |

All THREE old members share urn:company-wiki:context-group:sha256:8d73c33ea32801b58aea962f879f911ceb871c28bd15b8973ed4ec4e59776ca0:operating-fact:0. Para10 is a separate unrelated bullet: this is also an old RC06 producer grouping defect. Never describe sealed membership as8/9 only. Use separate tests: exact old three-member wire membership; corrected W02-style8/9group with10unrelated. Actual new source replay is needed to prove W02 produces the latter. Oldc3 cites8/11/13/14 and says 'previously in Azure', omitting9. Oldc5 joins truncated paragraph1 ('our consulting and support businesses. Devices and Consumer will include...') with20 (unchanged Frontier and support), leaving segment ownership ambiguous. W03 closure cannot repair missing original subject or establish proposition ownership; W02 selection plus original-slide semantic review remains necessary.

## Persistence compatibility and major-node tests

Public `SummaryClaim` / `_claim_from_dict` is an exact six-key shape: claim_id,text,evidence_ids,claim_type,modality,needs_review. `SourceSummaryDraft` and summary-result2.0 are exact schemas; old persisted model identity/prompt remains part of its sealed generation. Strip model-only group fields before canonical parsing/persistence and preserve old bundle decode/read behavior. Do not add mandatory group declarations to `validate_summary_draft` for historical public bundles or retroactively label their hashes verified. New prompt version ensures recompute where new generation semantics apply.

Concentrated responsibility tests should cover: actual HK omission and US omission; declared complete groups; missing/empty declaration partial-group diagnostic; unknown groups/IDs and malformed arrays discard whole claim; nine-span cancellation group; mixed question/management roles stay distinct; unrelated adjacent bullet not auto-attached; model-only fields absent from public draft; original selection unchanged and old persisted bundle still readable; exact-size overflow remains a typed bounded failure. Keep actual group closure and semantic entailment as separate assertions. No additional human approval or small-node gate is proposed.
