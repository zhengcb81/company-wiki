# W06 scope qualification interface

Owner: source_catalog.assertion_service shared with local_reconcile, resolver and SourceVersionReader; local_inventory retains bounded raw verification. SourceRef/manifest schema unchanged.

* query_local is a DB/stat candidate lookup; found is not actual-body qualification.
* Reusable SEC scope evidence: current verified SHA-bound source_fact_evidence covers entity/market/security_id linked to registered issuer provenance (existing issuer record where present); entity proof contains extracted primary CIK and sec-primary-dei/1 method. Fiscal year/period/form/end have the correct DEI field locators, values, SHA and extraction method. Imported canonical labels or partial form-only patches are insufficient. No new SQL schema/ledger.
* Old proofs lack genuine original scope: existing same LocalReadBudget reads/retains original once; extractor checks CIK and scope. A cache claiming the request yet contradicted by raw body returns blocked primary_scope_conflict (or primary_issuer_conflict), not empty. An actually proven old period without a contradictory request hit may be excluded before irrelevant date/cache errors.
* restore_document_facts gains optional computed-facts mode via the existing fact_replay callback. Default explicit facts/evidence remains compatible; compute and append take place under one catalog operation lock with optimistic catalog observation. No re-open after scope extraction or redundant final SHA.
* Final ready can select only a document qualified in this prepare request. Ordinary public reader byte/root/version checks remain intact, consumers do not duplicate scope checks.
* Budgets remain candidate16/group256/entries4096/256MiB/30s by default; provided object never resets. Exhaustion propagates named unavailable instead of incomplete-as-empty. Titles remain nullable display fields, publication dates remain observed or unknown.

## Additional normal-API causal audit: shared read qualification

After prepare-only GREEN, normal SourceAcquisitionService.ensure still reuses false cached original before prepare. FF's real provisional JSON candidate plus current open_version(filing_reuse) also accepts actual CIK99999/request12345. The attached two causal receipts record zero external calls and full TEMP restore; in-process FF transport is explicitly not claimed as a complete FF subprocess test.

Implemented common owner interface (MAIN-authorized within the 14-file source responsibility set): assertion_service supplies one SEC filing scope qualification object from current source facts/registered issuer/declared scope; it checks complete existing raw DEI/hash-bound evidence or requires the same verified original buffer. SourceResolver's candidate read and SourceReader's filing_reuse share that object, using existing bounded _read_verified_bytes so SHA and scope refer to the same buffer. No source writes in public readers, no new consumer identity check, no separate ledger/manual receipt. Generic source_export/raw preview does not become a research-period gate. Semantic conflicts must never invoke canonical claim fallback or be recoded as byte absence.

prepare's existing writer stores genuine original facts in the existing assertion after one read; readonly entries reuse this evidence when present, or validate their own one SHA buffer when absent. Sources requiring another parser remain governed by their established source contracts; W05 parser and external projects untouched.


### Public and internal interface limits

SourceRef, v2 manifest, VerifiedContent and VerificationReceipt schemas do not change. open_version has no new request DTO; filing_reuse verifies the currently registered SourceRecord's issuer and period against original scope. SourceResolver additionally uses its existing SourceRequest match, and passes the same qualified source object into actual candidate verification. acquisition ensure/select/stage benefit via SourceResolver; they are unmodified. Current FF/RF request and candidate period/identity checks are reused, not duplicated.

Internal factory: source_scope_qualification(catalog, ref, metadata, request=None, identity=None). Provided prepare identity is preserved. Readonly factory first consumes genuine registered provider CIK/observed SEC Archives URL. Unknown provider facts may use existing source master as fallback; known provenance does not trigger a new master lookup. Genuine source-fact evidence requires raw DEI method, primary CIK, SHA/value/correct field locators and existing issuer binding; canonical/import labels and URLs alone never prove raw scope. Each new physical read is a new observation; only within the same CWP call is a verified buffer reused once.

Internal SourceReader._verified_version accepts scope_qualification=None; its public filing_reuse auto-constructs one. Retains original only when facts need extraction. SourceResolver's qualified candidate uses the existing _read_verified_bytes, then the same qualifier. Semantic errors propagate with a named blocked cause and cannot be converted to canonical claim fallback, empty result or download permission. Byte fallback across exactly identical registered copies remains the existing reader responsibility. All source_export/raw preview defaults remain byte/root/version validation only.
