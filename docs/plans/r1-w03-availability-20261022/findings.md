# Findings

- source_catalog.qualify_source already supports byte-bound availability; narrative_transport currently passes only publication and rejects every unknown publication.
- raw reader 2.2 uses verified_availability_evidence(catalog, ref) after its existing verified open. Reuse that owner, not a second raw process or new proof storage.
- Only optional top-level availability_evidence in narrative-read-receipt/1 is added. No proof means key omitted. Immutable bundle/generation are not touched. Projected receipt/3 must remain unchanged.
- Existing untracked .planning files in this reused worktree predate this task and are preserved.
- Owned new short TEMP is mother CWP .planning/r1w3a; it was absent before this task. Evidence lives under this plan; no mother PWF edits.

TDD evidence: seven genuine null-publication reads failed despite valid owner raw2.2 proof. After minimal CWP transport wiring all 22 new controls pass within the final suite. Proof does not enter immutable artifact or its generation. Native raw2.2 and narrative receipt proofs are byte-equivalent data. Actual source byte reader and availability helper are each called once per narrative read; source-fact writes are forbidden by test. Projected two-parent receipt/3 never invokes the raw proof helper and refuses a root proof or tampered other parent.
