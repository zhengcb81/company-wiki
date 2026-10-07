# MAIN acceptance — 2026-10-07

Worker delivery `34d020f4490862c6ce66c7aaf8cfe0d6a3fa536f`; implementation `245a7f773a75a7e757ce71b9fca093d99788a9e6`.

MAIN removes the five retired writers from public help and dispatch, retains hidden compatibility names returning `MAINTENANCE_OPERATION_RETIRED` before configuration/Store/filesystem initialization, and retains current readonly `duplicates` inventory. Legacy flags no longer suggest an authorization or backup step. Unknown flags on live commands still fail.

The worker fingerprint no longer depends on retired focus-cleanup. The stale `self.store,` count test is replaced with a public scan into a temporary company/raw tree followed by a readonly lookup; writer-construction and zero-write reader assertions remain.

Concentrated combined maintenance/reader/source-facts run: **113 passed + one failed new scan fixture / 44.37s**. That fixture incorrectly put a document at the company root instead of the adapter's entity/raw layout. Corrected public scan and explicit database tests: **5 passed / 0.62s**. The union of final responsible cases is **115**, including one subsequently added output/input collision case; this is not a claim that 115 ran in a single command. CLI RED and new tests were written before wiring.

No production raw/catalog writes, no G2-12 acquisition changes included. Normal pre-push and one CI-equivalent unit run plus exact remote CI are recorded in MAIN selected PWF.
