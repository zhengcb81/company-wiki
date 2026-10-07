# G4 MAIN integration — 2026-10-07

The frozen Pipeline/Gate family was merged from delivery 6e6f77c into the current CWP master baseline 7fb29b9. MAIN retirement guide and current source-only user guide replace the retired command instructions. Hook/CI inventories contain no imports from the removed gate_system family; no new engineering gate is added.

Concentrated responsibility check: 211 passed, 38.78 seconds (Pipeline retirement, deployment, writer freeze, legacy caller reachability and preserved current PDF parsing). Worker unit run: 1916 passed; MAIN does not repeat that run locally. Normal exact code CI 37673393822 for df7d7ba58955e224c1799355f479ad5378ef38a7 succeeded in 74 seconds; all steps succeeded.

The CN route now advertises stockinfo-cninfo 1.3.0 and bounded acquisition, using the canonical StockInfoDLSimple/v2-clean-rewrite runtime. This replaces only the three existing pending CN root/version/capability values; HK/US and all other configuration fields are retained. SID eb8495c is published on v2-clean-rewrite. Its final 127 cases pass (27.02s), including three completeness regressions and four real committed-route CWP-to-SID CLI/loopback HTTP cases. Both original execution branches have been fast-forwarded and pushed.

The complete single-intent latest ensure/FF/ET/CWP acquisition transaction remains unfinished G2-12 work. No uncommitted G2-12 source is included in this package. No production document, manifest or database is modified; no paid or live external calls are made. Overall goal remains paused.
