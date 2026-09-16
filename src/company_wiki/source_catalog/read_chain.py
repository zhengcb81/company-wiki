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
        "removal_condition": (
            "the callers move to SourceResolver.resolve + read_verified_bytes (the "
            "byte-level chain) and the entry point has no caller in src/, adapters/ or the "
            "consumer repositories for two consecutive R4 cycles"
        ),
    },
    "company_wiki.source_catalog.reader.ReadOnlyCatalogReader.bundle": {
        "version": "1",
        "semantics": (
            "CLAIM-level, same rule as resolve_handle, plus SourceBundle assembly"
        ),
        "byte_level": False,
        "removal_condition": (
            "same as resolve_handle; the bundle assembly itself is owned by "
            "source_bundle.build_source_bundle and is not affected"
        ),
    },
}

#: The convergence ratchet.  ``module.py::symbol`` pairs that still parse the shared column
#: directly.  Derived from the AST inventory; it may only shrink.  A site that disappears
#: must be deleted here in the same change, or the gate reports the stale entry.
CONFIRMED_DIRECT_READERS: tuple[str, ...] = (
    "artifact_backfill.py::_classify",
    "artifact_read_model.py::_artifact_row",
    "normalizer.py::_frontmatter",
    "normalizer.py::normalize_catalog",
    "resolver.py::_metadata_conflict_reason",
    "scanner.py::_merge_document_row",
    "section_query.py::SectionQueryService",
    "service.py::SourceCatalog",
    "source_lifecycle.py::_safety_receipt",
)

#: The column's VALUE being passed into a call.  A parse-by-helper indirection is invisible
#: to the `json.loads` scan above - measured, not theorised: I built a probe with a generic
#: helper (`_parse(raw)`) called as `_parse(row["metadata_json"])` in a temp copy and the
#: whole gate passed.  Building this list then showed that THREE REAL sites already parse
#: that way (`extraction_quality._artifact_metadata`, `scanner._previous_provenance_fields`,
#: `scanner._merge_metadata_json`) - i.e. the confirmed list above is a ratchet over the
#: common shape, NOT a completeness proof.  This second ratchet closes the indirection: any
#: NEW place that hands the column's value into a call fails the gate.
#:
#: The scan looks for a SUBSCRIPT/`.get()` of the column INSIDE the call's arguments, so the
#: SQL text that merely mentions the column name (the majority of the 37 name matches) is not
#: counted.  `metadata_object(...)`/`_read_shared_metadata(...)` call sites appear here too,
#: and that is intended: they are the chain and its adapter, and they must not grow either.
COLUMN_VALUE_HANDOFFS: tuple[str, ...] = (
    "artifact_backfill.py::_classify",
    "artifact_read_model.py::_artifact_row",
    "backfill_v2.py::run_backfill",
    "extraction_quality.py::ExtractionQualityService",
    "migration_ledger.py::build_quality_ledger",
    "normalizer.py::_frontmatter",
    "normalizer.py::normalize_catalog",
    "resolver.py::_metadata_conflict_reason",
    "scanner.py::_merge_document_row",
    "section_query.py::SectionQueryService",
    "service.py::SourceCatalog",
    "source_lifecycle.py::_safety_receipt",
)

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
    "extraction_quality.py::ExtractionQualityService",
    "normalizer.py::normalize_catalog",
    "prompt_injection.py::read_prompt_injection_review",
    "prompt_injection.py::record_prompt_injection_review",
    "prompt_injection_guard.py::_receipt_from_store",
    "scanner.py::_merge_metadata_json",
    "service.py::_read_shared_metadata",
    "store.py::metadata_object",
    "store.py::read_pipeline_status",
)
