# PDF-C2 prerequisite root-fix independent review

2026-10-25 — PASS_ROOTFIX_ENGINEERING_ONLY; **0 OPEN in this reviewed delta**.

Reviewed the full seven-file source/test delta bound in final-review.json. The pre-existing pre-push file-mode WIP is outside this review and must remain untouched.

## Conclusions

- DOCX default and composed language sampling now share NarrativeNormalization. Usable verified body text is no longer rejected merely because headers/footers are not parsed. Chinese/English neutral fixtures keep coverage partial, while malformed ZIP still produces a named extraction failure. build_batch_events preserves an explicitly configured normalization owner; configured_preview forwards that existing owner.
- Current holdout observation explicitly selects the requested generation. The current PDF path uses PdfReading and one configured work account, without SDK decisions in W18/AUTO or changes to historical defaults. Old observer signature compatibility uses capability inspection and records requested/actual versions and its reason. Implementation TypeError propagates instead of triggering a retry.
- PdfReading.verify_material is called before verified native-range source evidence can be exported. The new multi-member range test and existing range/replay tests protect against the single-locator projection dropping legitimate selections; a failed material check prevents an observation from being exported.
- H1 diagnosis is consistent with segmented evidence: the implicit old-default .8 diagnostic can starve the requested .9 compile. This patch removes that hidden preflight mismatch for current requests; it does not rewrite old selector behavior, mutate baseline attempts, or claim a parser speedup from the altered comparison path.

## Independent checks

A focused independent package completed **68 passed in 9.19 seconds** (12.019 seconds including process launch). Independent counterexamples confirmed: omitted version remains .8; material-verifier refusal aborts; zero budget stops before backend reading; implementation TypeError is not hidden by compatibility retries. All temporary roots were restored absent, and probe input bytes were unchanged. Exact receipts: independent-test-result.json and independent-probes.json.

The first independent test process exited zero, but the review harness had a Windows GBK stdout decode failure. Explicit UTF-8 fixed the harness; the bounded repeat above provides readable counts. No full batch or old 95-second profiler was rerun.

## Release boundary

This signs only the prerequisite DOCX/observation root-fix engineering delta. Freeze it in a normal commit, then perform the planned bounded H1 and DOCX real replay and separately review its receipts. It does **not** sign PDF-C2 on-demand structure enhancement, formal summary quality, cache recovery, RF adoption, new blind holdout coverage, or all PWF completion. These remain OPEN.
