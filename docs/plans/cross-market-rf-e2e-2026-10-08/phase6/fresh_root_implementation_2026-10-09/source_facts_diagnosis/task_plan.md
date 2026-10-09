# W06 source facts diagnosis — read-only lane

## Goal

Trace RC10 publication evidence gaps, RC11 title-null contract omission, and unresolved RC28 latest-US-annual metadata gap to actual original bytes, isolated catalog rows and shared producer entrypoints. Deliver a concrete TDD implementation handoff to MAIN without source/config/raw writes or external calls.

## Scope and ownership

Only this `source_facts_diagnosis/` directory is writable. Existing mFresh originals, sealed executions and reports are read-only. No main PWF, producer/consumer source, key/config or CI writes. Independent TEMP reproduction, if needed, uses only this lane's copied fixtures and is restored.

## Phases

1. Recover frozen W06 and source reports: complete.
2. Inventory exact original bytes and catalog exclusion chain: complete.
3. Characterize common metadata/assertion/discovery boundaries: complete.
4. Produce root-cause evidence, TDD cases, exclusive write set and bounded discovery plan: complete.

## Next Step

MAIN owns this diagnosis handoff. A separately authorized W06 implementation will use the dedicated worktree/plan; these read-only diagnostic artifacts are complete and do not claim implementation GREEN.

## Acceptance

Each diagnosis must cite an actual artifact/locator or observed current code boundary. Unknown publication and true absence remain distinct; no guessed dates, issuer-specific fix or manufactured title. A proposed test is marked planned unless actually executed. Report safe counts/metadata, never credentials.
