# W04 selected subject availability — bounded follow-up

**STOP / 2026-10-11.** G1 sealed verdict unchanged. No source changes, full engine, tests, HTTP, provider or model calls.

## Actual evidence

- Parent SHA: `c620093812d9e420a4847ea0348906e5d167b9dc429a181f223c730c00064271`; 7,102 bytes; official paged QA page 54/65. The page contains 久日新材、中微公司、晶升股份 with distinct record identities and timestamps.
- Selected 中微 record: `/datas/0/records/1`; record ID 2508080, companyId 145565, activityCompanyId 57790. The sealed projection separately pins CN/688012 and subject SHA `b0c6bfb3faa447f292330ae9d73a27a09367184a820bb6f8c454ab60ead7e695`.
- Management `content` pointer: `/datas/0/records/1/content`, token bytes 2739:3338, decoded SHA `d68338dd98d21e16cc32b117323dd10e09b84133ecb1f1171e0fe3ff4de2f4ff`. Question pointer: `/datas/0/records/1/questionContent`, token bytes 4571:4702.
- Row observations: `crtTime=2026-09-10 15:36:00`, `auditTime/updTime=2026-09-10 15:37:45`, `questionDate/questionUpdDate=2026-09-10 15:29:25`. Selected row has no publish/release/linked-announcement field; selected content/question has no HTTP link. The event title contains “2026年半年度”, but does not establish a typed reporting period for this nonperiod claim.
- Raw manifest issuer, publication and fiscal-period fields are null. Actual public raw receipt **2.2** is `status=ok`, SHA/size verified, **availability_evidence=null**. Raw retrieval was 2026-10-11; requested as-of is 2026-10-08. Receipt byte SHA: `6c2086e0672a679446ebcd4916c2583195c1300c0a92b03c01da64a5fb01ad88`.

**This selected claim's first publication, reporting period and historical capture eligibility remain unknown.** Projection selection `as_of_eligibility=eligible` filters observed revision dates; the producer explicitly keeps `answer_first_publication_known=false`. Neither a row revision date nor present-day local possession may become a prior capture receipt.

## Responsibility and scope

The raw multi-issuer container correctly retains null global issuer/period metadata. Projection identity is already distinct. No neighboring issuer date or period was assigned to 中微.

The inspected interface does have a scope gap: RF capture qualifies the **whole raw SourceRef/manifest**, while 2.2 takes no selected subject/record/field clock input. Its proof is an authenticated existing acquisition `DownloadReceipt`, bound to exact raw SHA/size/MIME and a full sidecar SHA; it cannot represent a selected-version publication fact. The raw candidate must not copy projection issuer facts into its null manifest.

This gap concerns a future source-qualified selected claim in a container without a single publication date. **It does not prove that this row already has adequate publication evidence.** Adding a DTO alone would leave this actual row unknown. Correct refusal is not a G1 defect or an economic-quality acceptance.

## Minimum seam for ROOT's WP07/G2 decision

Add one source-owned, versioned **subject qualification** on the existing verified projection/public-read path:

1. Keep raw SourceRef and subject_ref distinct; retain full parent SHA, projection SHA, original record/field pointers and content hashes.
2. Source adapter alone establishes selected issuer, nullable typed data period, and selected-version publication/availability from verified provider clock semantics or genuine archive/capture proof. Preserve original fields, values, locators and extractor version. Missing semantics/proof returns unknown.
3. RF consumes that authenticated qualification and checks its as-of once, then binds explicit rationale to the genuine capture/projection and original locator. Keep raw publication/FY/identity null; preserve parameter values.
4. Reuse existing projection storage, public reader and verified raw buffer. Preserve whole-raw 2.2 semantics; no second database, duplicate issuer resolution, artificial authorization or fabricated availability credential.

Bounded TDD seam: actual c620 remains unknown; audit/creation/event-title or neighbor evidence cannot qualify it; SHA/pointer/content-version changes invalidate proof; a source-authenticated scoped fixture qualifies only its own selected version/as-of. A later **real** selected-version public receipt is needed to clear this management chain in G2. Synthetic signed fixtures establish contract behavior only.

## Reproduction and limits

`investigation.json` contains the exact legal raw reader argv, sealed /3 request, original pointers, actual receipt fields and inspected source hashes. Two bounded local reads inspected this same 7,102-byte parent; no whole-lake scan, other originals or external publisher semantics were investigated. No source gate bypass or SourceCapture promotion occurred. Original G1 JSON/MD hashes remain unchanged.
