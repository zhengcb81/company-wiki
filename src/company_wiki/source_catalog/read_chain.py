"""B10 — the read chains, declared in ONE machine-readable place.

Requirement (R4 execution plan §B, B10): "converge to a single read chain in a small
scope; old entry points only as explicit version adapters; record the revertible version
and the removal conditions for the old fields".  The acceptance adds: "switch only after an
independent review; a rollback of code/config must not roll back raw data or historical
provenance; if it cannot be made compatible, STOP the switch - no permanent silent
double-run".

This module is the "no silent double-run" part.  It does not read anything; it states, in
one place a test can check:

* ``SINGLE_READ_CHAIN``      - the one function every reader of ``documents.metadata_json``
  is expected to converge on (``store.metadata_object``).
* ``LEGACY_READ_ADAPTERS``   - entry points that must NOT be silently re-pointed at that
  chain because their SEMANTICS differ (measured: ``reader.resolve_handle`` and
  ``reader.bundle`` verify the catalog's *claim*, never the bytes).  Each entry carries the
  version it adapts, whether it reads bytes, and the condition under which it may be
  removed.
* ``CONFIRMED_DIRECT_READERS`` - the ratchet baseline of places that still parse the column
  themselves.  It may only SHRINK; a new one fails the gate
  (``tests/contract/test_b10_read_chain.py``), and an entry that no longer exists must be
  removed from the baseline rather than left to rot.

Baseline provenance: ``assurance/runs/2026-09-11_r4-phase-b/evidence/b10_read_chain_inventory.py``
(AST inventory; the run is recorded in ``b10-read-chain-inventory.json`` next to it).
"""

from __future__ import annotations

# The read chain's own version.  A consumer that needs the OLD semantics must say so
# explicitly (through a registered adapter below) instead of depending on which entry
# point happens to still exist.
READ_CHAIN_VERSION = "1"

#: The single read chain for the shared ``documents.metadata_json`` column.
SINGLE_READ_CHAIN = "company_wiki.source_catalog.store.metadata_object"

#: ``module::symbol`` -> what the entry point really does, why it is not on the chain yet,
#: and what would have to be true before it can be removed.
LEGACY_READ_ADAPTERS: dict[str, dict[str, object]] = {
    "company_wiki.source_catalog.service._read_shared_metadata": {
        "version": "1",
        "semantics": "same contract as the single chain; name kept as the v1 adapter",
        "byte_level": False,
        "reads_files": False,
        "removal_condition": (
            "no caller outside this registered adapter for two consecutive R4 cycles, "
            "and the call sites use store.metadata_object directly"
        ),
    },
    "company_wiki.source_catalog.reader.ReadOnlyCatalogReader.resolve_handle": {
        "version": "1",
        "semantics": (
            "CLAIM-level: compares the content_sha256 the CATALOG claims; never opens a "
            "file, so it must not be quietly re-pointed at the byte-level chain"
        ),
        "byte_level": False,
        "reads_files": False,
        "removal_condition": (
            "the callers move to SourceResolver.resolve + read_verified_bytes (the "
            "byte-level chain) and the entry point has no caller in src/, adapters/ or the "
            "consumer repositories for two consecutive R4 cycles"
        ),
    },
    "company_wiki.source_catalog.reader.ReadOnlyCatalogReader.bundle": {
        "version": "1",
        "semantics": (
            "CLAIM-level for the DOCUMENT version (it compares the claimed content_sha256) "
            "but NOT file-free: build_source_bundle -> artifact_handle.validate_artifact "
            "hashes each artifact file on disk. CORRECTED after B-VR-B10-01 (P1): this entry "
            "previously claimed 'never opens a file', which the reviewer refuted by corrupting "
            "an artifact and watching the verdict flip to artifact_hash_mismatch."
        ),
        "byte_level": False,   # the DOCUMENT's bytes are not read
        "reads_files": True,   # artifact files ARE read - do not restate the old claim
        "removal_condition": (
            "same as resolve_handle; the bundle assembly itself is owned by "
            "source_bundle.build_source_bundle and is not affected"
        ),
    },
}

#: The convergence ratchet.  ``module.py::Class.method`` -> which TABLE the column belongs to.
#: Keys are qualified (B-VR-B10-03: a bare class key collapsed every method of the class into
#: one entry, so a new method was invisible), and each entry names the table it reads - the
#: `artifacts` table has a column with the SAME name, and the first flat list mixed the two
#: (B-VR-B10-02).
#:
#: Converged so far: batch 1's seven sites (artifact_backfill._classify,
#: artifact_read_model._artifact_row, scanner._merge_document_row,
#: scanner._previous_provenance_fields, source_lifecycle._safety_receipt,
#: service.SourceCatalog.query_filing_candidates via metadata_state, and
#: resolver._metadata_conflict_reason via metadata_state), then batch 2's
#: normalizer._frontmatter, then normalizer.normalize_catalog in the P0 fix
#: (B-VR-B10R2-01).  What REMAINS here and why:
#:
#: * ``section_query`` - declared in EXPLICIT_NON_CHAIN_READERS: its contract is to RAISE a
#:   named error on malformed artifact metadata.
#:
#: CORRECTION (B-VR-B10R3-03): this comment used to claim that the normalizer parses "sit in
#: normalize_catalog's FAILURE path ... a per-document normalization-failure record with
#: attempt counting".  The r2 review proved that FALSE - those parses were OUTSIDE the
#: per-document try, and a malformed column aborted the WHOLE run (measured, P0).  The claim
#: is withdrawn, not reworded: there was no failure record to protect.
#:
#: The set of keys may only shrink; a site that disappears must be deleted here in the same
#: change, or the gate reports the stale entry.
CONFIRMED_DIRECT_READERS: dict[str, dict[str, str]] = {
    "section_query.py::SectionQueryService.list_sections": {
        "table": "artifacts",
        "sites": "1",
        "note": "deliberate raise - see EXPLICIT_NON_CHAIN_READERS",
    },
}

#: ``module.py::Class.method`` -> how many calls in that scope hand the column's value out.
#: A COUNT, not just a key set: the review measured that a SECOND direct reader added inside
#: an already-baselined scope kept the same qualified key and passed (probe: exit code 0,
#: "1 passed").  The count closes that: one more site in a known scope is a new violation,
#: and one fewer means the baseline must be lowered.  The counts are MACHINE-DERIVED from the
#: tree (12 scopes / 15 sites after the batch-2 and P0 convergences; the earlier 13/16 reading
#: was stale text in this comment - B-VR-B10R3-03); my first hand-written version
#: under-counted two of them, which is exactly why they are derived now.
COLUMN_VALUE_HANDOFFS: dict[str, str] = {
    "artifact_backfill.py::_classify": "1",
    "artifact_read_model.py::_artifact_row": "1",
    "backfill_v2.py::run_backfill": "1",
    "extraction_quality.py::ExtractionQualityService._artifact": "1",
    "migration_ledger.py::build_quality_ledger": "1",
    "normalizer.py::normalize_catalog": "1",
    "resolver.py::_metadata_conflict_reason": "1",
    "scanner.py::_merge_document_row": "3",
    "section_query.py::SectionQueryService.list_sections": "1",
    "service.py::SourceCatalog.query": "2",
    "service.py::SourceCatalog.query_filing_candidates": "1",
    "source_lifecycle.py::_safety_receipt": "1",
}

#: Readers that deliberately do NOT go through the chain.  Declared so "not on the chain" is
#: a stated decision, never a silent double-run (the B10 acceptance rule: if it cannot be
#: made compatible, STOP the switch - do not convert it quietly).
#:
#: HISTORY, kept because it is the lesson: this registry once also listed
#: `normalizer.py::normalize_catalog` with the reason "its exception TYPE is recorded data
#: (error_code = type(exc).__name__), so converging it would change failure_reasons".  The
#: review (B-VR-B10R2-02, P1) proved that reason FALSE: the per-document handler covers only
#: the parser call, so the parse at :1638 was not inside it at all, no error code was ever
#: recorded for it, and the "deliberate" declaration was really an unguarded crash path.  It
#: is converged now (B-VR-B10R2-01, P0) and must not come back as a "declared exception".
EXPLICIT_NON_CHAIN_READERS: dict[str, str] = {
    "section_query.py::SectionQueryService.list_sections": (
        "raises SectionQueryError('sections artifact metadata is not valid JSON') on "
        "malformed artifact metadata - degrading to {} would hide that error"
    ),
}

#: The column's VALUE being passed into a call.  A parse-by-helper indirection is invisible
#: to the `json.loads` scan above - measured, not theorised: I built a probe with a generic
#: helper (`_parse(raw)`) called as `_parse(row["metadata_json"])` in a temp copy and the
#: whole gate passed.  Building this list then showed that REAL sites already parse that way
#: (`extraction_quality._artifact`, `scanner._merge_document_row` via
#: `_previous_provenance_fields`/`_merge_metadata_json`), i.e. the confirmed list above is a
#: ratchet over the common shape, NOT a completeness proof.  This second ratchet closes the
#: indirection: any NEW place that hands the column's value into a call fails the gate.
#:
#: The scan looks for a SUBSCRIPT/`.get()` of the column INSIDE the call's arguments, so the
#: SQL text that merely mentions the column name (the majority of the name matches) is not
#: counted.  `metadata_object(...)`/`metadata_state(...)` call sites appear here too, and
#: that is intended: they are the chain, and they must not grow either.

#: What the two ratchets above do NOT catch, MEASURED on temp copies rather than assumed.
#: Written into the product so nobody trusts the gate beyond its reach: it recognises two
#: common SYNTACTIC shapes, it is not a dataflow analysis and not a completeness proof.
#: Each entry was built as a probe and RUN against the gate; the verdict is recorded.
GATE_BOUNDARIES: dict[str, str] = {
    "intermediate_variable": (
        "`raw = row[\"metadata_json\"]` followed by `parse(raw)`: the column never appears "
        "in a call argument. PROBED: the gate passed (still open)."
    ),
    "subscript_inside_the_callee": (
        "`def f(obj): ... obj[\"metadata_json\"] ...` called as `f(row)`: the subscript is "
        "an assignment inside the callee, not a call argument. PROBED: the gate passed."
    ),
    "third_party_or_alternative_parser": (
        "`json.JSONDecoder().decode(...)`, orjson/ujson, or any wrapper whose call site and "
        "parameter both avoid the column name. PROBED BY CONSTRUCTION (not run): the scans "
        "key on the `json.loads` name and on `[" + "\"metadata_json\"" + "]`/`.get(...)`."
    ),
    "closed_helper_at_call_site": (
        "`_parse(row[\"metadata_json\"])` with a GENERIC helper was the first bypass found "
        "(probe passed, and three production sites already had that shape); "
        "COLUMN_VALUE_HANDOFFS closes it. PROBED: now caught."
    ),
    "readers_outside_the_scanned_roots": (
        "the ratchet scans `src/company_wiki/source_catalog/**`; a second hard rule covers "
        "the REST of the PRODUCT package (`src/company_wiki/**` minus source_catalog) and "
        "currently finds ZERO readers there - that rule is ENFORCED. MEASURED OUTSIDE IT "
        "(2026-09-17): `scripts/` had 2 direct readers of this column (legacy_observer.py:96, "
        "wu904_remediation_restore.py:65) and `tests/` had 10 (fixtures), while `tools/` had "
        "0 - tools/ and scripts/ were OUTSIDE the rule's root, so those numbers were "
        "OBSERVATIONS, not enforcement (B-VR-B10R3-02: injecting a reader into either place "
        "left the gate green). CONVERGED 2026-09-18 (owner instruction): both `scripts/` sites "
        "now call `store.metadata_object`, and `tests/contract/test_b10_read_chain.py::"
        "test_b10_scripts_have_no_direct_reader` enforces a HARD ZERO over `scripts/` - the "
        "follow-up this boundary registered is closed. What remains outside every rule is "
        "`tests/` (fixtures, reported not enforced) and any code outside the three roots."
    ),
}

#: Sites whose enclosing symbol merely MENTIONS the column.  Reported, never enforced.
#: Kept here (with the machine-derived values, not from memory - the first version of this
#: tuple was written from memory and named four symbols that do not exist) so the
#: distinction is explicit rather than rediscovered:
#:   * ``store.py::metadata_object``      - the single chain itself;
#:   * ``service.py::_read_shared_metadata`` - the registered v1 adapter;
#:   * ``scanner.py::_merge_metadata_json``  - a true reader under a renamed argument;
#:   * ``store.py::read_pipeline_status``    - a FALSE POSITIVE (parses ``report_json``).
HEURISTIC_READER_CANDIDATES: tuple[str, ...] = (
    "extraction_quality.py::ExtractionQualityService._artifact",
    "normalizer.py::normalize_catalog",
    "prompt_injection.py::read_prompt_injection_review",
    "prompt_injection.py::record_prompt_injection_review",
    "prompt_injection_guard.py::_receipt_from_store",
    "scanner.py::_merge_metadata_json",
    "service.py::_read_shared_metadata",
    "store.py::metadata_object",
    "store.py::read_pipeline_status",
)
