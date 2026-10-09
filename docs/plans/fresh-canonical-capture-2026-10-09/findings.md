# Findings

CodeGraph and exact ceac91e7 source inspected. Current writer uses long date/provider/provider-ID/title names for every kind except call TXT. Atomic provenance adds another suffix without a path budget. Official import unconditionally removes owned staging in finally, including after writer failure. Writer removes staging before official fact commit, so changing only finally is insufficient. Existing async HTTP transport can cancel real async body reads; current official CLI exposes import/discover only and executors download separately.

Approved write set: canonical_writer.py, official_source_flow.py, additive official_source_cli.py and focused tests. Existing AcquisitionJournal and BudgetedAsyncHTTPTransport are reused. No new task database or authorization mechanism.

Further actual RED found after initial grouped M2: a receipt storage OSError after successful capture omitted real HTTP usage; local MIME parsing ran twice; unregistered complete retained SHA made a second GET. Common flow now preserves named orphan raw/usage, parses local format once while actual staged SHA remains checked, and resumes complete retained captures before network. All covered by final88-pass M2. Historical bytes not reconstructed; incomplete and receipt-unavailable states remain explicitly unavailable.
