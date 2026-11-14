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

The direct-reader test checks literal JSON parsing in product sources. Reuse of
decoded values, malformed data and exact source behavior have executable tests.

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
#: scanner._previous_provenance_fields,
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
    "prompt_injection.py::read_prompt_injection_review",
    "scanner.py::_merge_metadata_json",
    "service.py::_read_shared_metadata",
    "store.py::metadata_object",
    "store.py::read_pipeline_status",
)
