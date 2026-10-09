# Findings

CodeGraph and exact ceac91e7 source inspected. Current writer uses long date/provider/provider-ID/title names for every kind except call TXT. Atomic provenance adds another suffix without a path budget. Official import unconditionally removes owned staging in finally, including after writer failure. Writer removes staging before official fact commit, so changing only finally is insufficient. Existing async HTTP transport can cancel real async body reads; current official CLI exposes import/discover only and executors download separately.

Approved write set: canonical_writer.py, official_source_flow.py, additive official_source_cli.py and focused tests. Existing AcquisitionJournal and BudgetedAsyncHTTPTransport are reused. No new task database or authorization mechanism.

Further actual RED found after initial grouped M2: a receipt storage OSError after successful capture omitted real HTTP usage; local MIME parsing ran twice; unregistered complete retained SHA made a second GET. Common flow now preserves named orphan raw/usage, parses local format once while actual staged SHA remains checked, and resumes complete retained captures before network. All covered by final88-pass M2. Historical bytes not reconstructed; incomplete and receipt-unavailable states remain explicitly unavailable.


## Independent review: three common-root defects and systemic repair

IR-W04-01: cleanup was durable for raw/catalog but erased the only capture-ID lookup, so reply loss made recovery non-idempotent. The same capture mechanism now persists a bounded completed result projection linked to its existing successful acquisition journal attempt. It stores SourceRef/status/historical cap/actual receipt only, no body or storage path. fsync+atomic replacement completes before staging cleanup. Existing file mutex serializes same-ID recover; public SourceVersionReader.verify_version streams actual canonical SHA under current roots and describe_version returns current source facts. Repeated recover reports zero current acquisition delta while preserving the unchanged actual HTTP receipt. A result-write failure after journal success retains raw/descriptor and can resume.

IR-W04-02: retained reuse consumed the historical cap while canonical reuse used the current cap. Retained import now uses min(historical cap, optional current cap), reads at most cap+1 and refuses source_byte_limit before import; capture forwards its current cap to recovery. Explicit recover/CLI accept additive optional max_bytes (omission preserves historical semantics). Completed replay also composes both caps. Refusal preserves historical receipt/body and makes no new GET.

IR-W04-03: JSON syntax success was treated as proof of object shape. Both retained/completed records now pass bounded strict JSON/object parsing, required field/type checks and shared nested metadata/receipt/usage validation before access. Duplicate/nonfinite JSON and excessively deep malformed structures refuse safely. Inventory reports unavailable for malformed retained records; public recover returns safe named JSON exit2 without restoring capture/usage claims or deleting raw. Arbitrary programming exceptions are not broadly suppressed in the CLI.

The first grouped rerun also exposed diagnostic-order regression, fixed in the product: actual byte SHA failure precedes receipt identity mismatch, matching the unchanged existing bad-SHA test. No legacy RED evidence or independent reviewer report was modified. No new permission or review receipt was introduced.
