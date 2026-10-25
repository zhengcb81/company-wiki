"""Separate positive text-page observation from optional geometry planning."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from hashlib import sha256
from types import SimpleNamespace

import pytest

from company_wiki.document_understanding.narrative_continuity import NativeSourceContext
from company_wiki.resource_budget import WorkBudget, WorkBudgetExceeded, new_document_work_budget
from company_wiki.source_catalog import narrative_evidence as parser
from company_wiki.source_contract import source_id_for_sha256
from unit.document_understanding_selection.test_reading_native_continuity import native


def _coverage(statuses=("observed", "observed", "empty"), *, source="source-a"):
    return {"schema_version": "native-text-coverage/1", "source_id": source,
            "page_count": len(statuses), "page_statuses": tuple(statuses)}


def _edge(coverage, *, deferred=(3,), opaque=(), native_scan="partial"):
    rows = [native("- Service revenue increased 20%.", 0, page=1, column="measured-body",
                   box=[110, 720, 550, 740]),
            native("ii. Customer count grew 15%.", 1, page=2, column="measured-body",
                   box=[110, 70, 550, 90])]
    wire = {"native_scan": native_scan, "opaque_pages": list(opaque), "deferred_pages": list(deferred)}
    if coverage is not None:
        wire["native_text"] = coverage
    context = NativeSourceContext([row[0] for row in rows],
        provenance={row[0]["unit_id"]: row[1] for row in rows}, coverage=wire,
        work_budget=new_document_work_budget())
    return context, context.page_neighbour(rows[0][0]["unit_id"], rows[1][0]["unit_id"],
                                           furniture_unit_ids=frozenset())


@pytest.mark.parametrize("deferred,opaque", [((3,), ()), ((1, 2, 3), ()), ((), (3,))])
def test_local_positive_text_is_independent_of_geometry_deferral(deferred, opaque):
    coverage = _coverage()
    before = deepcopy(coverage)
    context, proof = _edge(coverage, deferred=deferred, opaque=opaque)
    assert not context.coverage_complete  # whole-source status must remain partial
    assert proof is not None
    assert proof["left_page"] == 1 and proof["right_page"] == 2
    assert coverage == before


@pytest.mark.parametrize("statuses", [
    ("read_failed", "observed", "empty"), ("observed", "empty", "observed"),
    ("observed", "emission_failed", "observed"),
])
def test_unread_or_unemitted_endpoint_never_becomes_a_positive_edge(statuses):
    context, proof = _edge(_coverage(statuses), native_scan="complete", deferred=())
    assert proof is None
    assert context.diagnostics["CONTINUITY_PAGE_COVERAGE_UNPROVEN"] == 1


@pytest.mark.parametrize("mutation", [
    {"page_count": 4}, {"page_count": True}, {"page_statuses": ("observed",)},
    {"page_statuses": ("observed", "unknown", "empty")},
    {"schema_version": "unknown"}, {"source_id": "other-source"},
    {"page_statuses": "observed"},
])
def test_malformed_or_foreign_text_observation_cannot_override_partial(mutation):
    coverage = {**_coverage(), **mutation}
    assert _edge(coverage)[1] is None


def test_absent_text_observation_keeps_existing_legacy_semantics():
    assert _edge(None)[1] is None
    assert _edge(None, native_scan="complete", deferred=())[1] is not None


def test_current_parser_coverage_reaches_structure_citation_and_actual_model_context():
    from company_wiki.source_catalog import narrative_reading as reading
    from unit.document_understanding_selection.test_reading_native_list_ancestry import (
        _list_source, _own_context,
    )
    parsed, units = _list_source("cross_page_roman")
    parsed = replace(parsed, page_count=3, pages_read=3, deferred_table_pages=(3,),
                     native_text_coverage=_coverage(source=parsed.source_id))
    assert not parsed.coverage_complete
    budget = new_document_work_budget()
    pipeline = reading._understand(parsed, title="Neutral annual report", kind="annual_report",
        mime_type="application/pdf", work_budget=budget)
    selected = reading.select_reading_evidence(parsed, title="Neutral annual report",
        existing_kind="annual_report", max_selected=96, max_chars=48000, work_budget=budget)
    observed = _own_context(parsed, pipeline, selected, units["second"],
                            (units["parent"], units["intro"]), units["sibling"])
    assert observed["failures"] == []
    assert not budget.exhausted and budget.used < budget.max_work_units


@pytest.mark.parametrize("mode", ["legacy", "explicit", "planned"])
def test_exhausted_caller_budget_stops_before_native_read_or_duplicate_page_append(monkeypatch, mode):
    from company_wiki.source_catalog import narrative_pdf_intent as intent
    budget = WorkBudget(max_work_units=0)
    collector = SimpleNamespace(pending_pages={}, pages={},
        capture_pending_page=lambda *_args, **_kwargs: None,
        project_page=lambda _number, units: units)
    state = parser._PdfParseState("source-a", "a" * 64, "0.1.1", "en",
        page_count=3, prose_work_budget=budget, layout_collector=collector)
    reads = []

    def read(_page, **kwargs):
        reads.append(kwargs["page_number"])
        return [(0, (90, 100, 550, 120), "Positive source text.")]

    monkeypatch.setattr(parser, "_pdf_text_blocks", read)
    monkeypatch.setattr(intent, "SourceGeometrySession", lambda *_args, **_kwargs:
                        SimpleNamespace(request=lambda *_args: (False, False)))
    try:
        if mode == "legacy":
            parser._scan_pdf_pages(state, [object()] * 3)
        elif mode == "explicit":
            parser._scan_and_emit_pdf_pages(state, [object()] * 3, full_table_scan=False, table_pages=[])
        else:
            intent.scan_planned_pages(state, [object()] * 3, reading_context=None, work_budget=budget)
    except WorkBudgetExceeded:
        pass  # Either explicit budget failure or a partial return must stop native reads.
    assert reads == []
    assert state.pages_read == 0 and state.page_blocks == []
    assert state.native_text_status == {}
    assert budget.exhausted


@pytest.mark.parametrize("mode", ["legacy", "explicit", "planned"])
@pytest.mark.parametrize("failure", [None, "read", "emission"])
def test_parser_records_text_and_emission_in_existing_single_page_walk(monkeypatch, mode, failure):
    fitz = pytest.importorskip("pymupdf")
    doc = fitz.open()
    for index in range(3):
        page = doc.new_page()
        if index < 2:
            page.insert_text((72, 72), f"Division {index} launched a new service for repeat customer orders.")
    data = doc.tobytes()
    digest = sha256(data).hexdigest()
    source_id = source_id_for_sha256(digest)
    actual_read, actual_emit = parser._pdf_text_blocks, parser._emit_pdf_text_units
    read_pages = []

    def read(page, **kwargs):
        number = kwargs["page_number"]
        read_pages.append(number)
        if number == 2 and failure == "read":
            raise RuntimeError("synthetic native read failure")
        return actual_read(page, **kwargs)

    def emit(state, number, blocks):
        if number == 2 and failure == "emission":
            return False
        return actual_emit(state, number, blocks)

    monkeypatch.setattr(parser, "_pdf_text_blocks", read)
    monkeypatch.setattr(parser, "_emit_pdf_text_units", emit)
    budget = new_document_work_budget()
    try:
        parsed = parser._parse_pdf_document(doc, source_id=source_id, source_sha256=digest,
            language="en", selector_version=None if mode == "legacy" else "0.9.0",
            table_pages=[] if mode == "explicit" else None, work_budget=budget)
    finally:
        doc.close()
    assert read_pages == [1, 2, 3]  # cover planning reuses units, not a second native read
    coverage = parsed.native_text_coverage
    assert coverage["source_id"] == source_id
    assert coverage["page_count"] == 3
    assert coverage["page_statuses"] == ("observed", {
        None: "observed", "read": "read_failed", "emission": "emission_failed"}[failure], "empty")
    assert not parsed.coverage_complete  # page3 has no native prose
    if mode != "legacy":
        assert 0 < budget.used < budget.max_work_units
