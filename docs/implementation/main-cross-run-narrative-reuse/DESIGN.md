# Generation reuse design

The implementation composes existing AUTO run scope and immutable catalog artifacts. It keeps run/event/job/effect/work identity and original reservations. It does not make model-call identity interchangeable with budget-run identity.

## Generation manifest

One canonical generation manifest per source binds SourceRef bytes/size/MIME/logical identity; effective source_class/title/document_kind/language; per-carrier parser name/version; selector, prompt, request/bundle/material schema, handler and bundle-producer versions; effective profile and model endpoint/name/output-generation parameters. Exact manifest SHA is stored in existing artifact metadata_json, and also in new run binding/3, with common settings factored to retain the existing 262144-byte cap for 100 sources. Execution-only budget/time/storage/price/key-environment/run/batch-other-member/physical-root/read-policy fields are excluded. Current admission and six-field source/read checks still apply. Each carrier uses its actual parser_component; HTML does not absorb the global PPTX normalization version. The optional pathless parser_components argument accepts the normalization owner's actual fingerprint at MAIN's integration point. Stable raw bytes alone are insufficient.

## New run preparation

Take existing catalog-scoped OS generation locks in sorted key order, with bounded acquisition by request deadline. Under the existing DB owner lock, query bounded same-source visible generation candidates. Validate manifest, complete coverage/summary, exact artifact bytes, current SourceRef and locator replay through the existing public NarrativeTransportReader. Complete valid pins enter binding/3; only misses create normal AUTO jobs. An all-hit run does not open the source-catalog writer, activate workers or reserve worst-case model output storage; it checks actual owned storage growth. Empty scope is already supported by create_run. Current run gains no old reservations. All-hit returns completed with current-run zero usage without activating workers.

## Resume and refresh

Binding/1 and /2 preserve legacy exact intent and immutable job scope. Binding/3 explicitly covers requested sources by persisted reuse pins plus owned three-job groups. Resumes freeze old generation manifests/pins, validate current raw bytes, and retain normal request conflict checks. Optional refresh defaults false without changing old default request wire/hash. A new refresh run forces generation; repeated exact refresh run resumes its own prior work. Failed refresh does not publish a replacement, so old visible pins remain readable.

## Concurrency and uncertainty

OS locks are not task/expense records. Same catalog generation across distinct AUTO DBs waits before the second candidate lookup, then reuses a published result. A minimal per-generation recovery locator contains only origin AUTO path/run ID, never job status or accounting. Original AUTO state is read through its existing read-only run store/connection. Known terminal work with no publication pending can retire the locator; verified visible publication also retires it after a cleanup interruption, including before explicit refresh. Process death releases OS locks but does not transfer surviving AUTO runtime ownership. A different run receives the existing named owner-recovery condition; it cannot move jobs or avoid an unknown reservation by doing new work. The original run recovers its leases/outbox and retains unknown fees conservatively; only then can a subsequent run reuse visible content. The base had a generic output budget defect that blocked actual POST-loss retry; MAIN's one-module temporary budget overlay now proves completed recovery while retaining the unknown fee. The owned base module remains unchanged; the strict recovery test depends on MAIN's budget correction. ACKed/prepared publication recovery is independently proven to complete without another POST.

## Concentrated proof

First RED: actual configured finite A/B with HTML/PDF/TXT and public verified read demonstrates the existing second POST. Identity tests cover causal changes/misses and execution-only changes/hits. Integration covers mixed hit/miss, earlier compatible generation behind newer incompatible version, missing/tampered/incomplete artifacts, refresh success/failure, same and distinct DB concurrent entry, staged worker/lease and outbox loss recovery. Existing exact-run conflict, source scope, budget and execution-upgrade behavior is retained. Parser/OCR files and narrative_formats stay with their owners.

## MAIN normalization integration

Supply the actual pathless normalization_identity result as parser_components at generation_manifest's _run_owned composition call. Pure HTML must retain its own parser identity when PPTX/OCR changes. The current sole coverage gate is read_reuse_pin: selected plus completed currently additionally requires coverage_complete. MAIN's shared OCR TDD will permit a complete selected derivation with honest incomplete whole-source recall, preserving exact bytes/hash/current-source/parser and every selected locator proof; no- narrative skips still require complete coverage and no evidence. No extra permission or human approval state is added.
