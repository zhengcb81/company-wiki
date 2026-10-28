"""Actual registered narrative DAG admits only source-proven partial excerpts."""
from __future__ import annotations

from dataclasses import replace
import hashlib
import json

import pytest

from company_wiki.automation.models import HandlerOutcome, canonical_json, make_job_key
from company_wiki.automation.narrative_contracts import NarrativeBundle, NarrativeSelectResult
from company_wiki.automation.narrative_model import NarrativeModelResponse
from company_wiki.automation.narrative_model_scoped import SCOPED_MODEL_PROJECTION_VERSION
from company_wiki.automation.narrative_runtime import NarrativeRuntimeDependencies, register_narrative_handlers
from company_wiki.automation.narrative_select import NarrativeSelectHandler
from company_wiki.automation.worker import HandlerExecutor
from company_wiki.source_catalog import narrative_evidence as evidence
from company_wiki.source_catalog.narrative_document import NarrativeEvidencePackage
from company_wiki.source_contract import EvidenceCoordinates, EvidenceSpan
from unit.test_narrative_select_handler import FakeReader, _context, _payload
from support.scoped_model_response import source_grounded_scoped_reply


BUSINESS = "Company launched a new device and received repeat orders from overseas customers."


def _pdf(*, text=BUSINESS, opaque=True):
    fitz = pytest.importorskip("fitz")
    with fitz.open() as document:
        page = document.new_page()
        if text:
            page.insert_text((72, 72), text)
        if opaque:
            page = document.new_page()
            page.draw_rect(fitz.Rect(72, 72, 300, 300), fill=(0.2, 0.3, 0.4))
        return document.tobytes()


def _event(data, mime="application/pdf", kind="annual_report"):
    return _payload(data, title="Company annual report", document_kind=kind,
                    language="en", mime_type=mime)


class CountingModel:
    def __init__(self):
        self.calls = []

    def generate(self, request):
        self.calls.append(request)
        data = json.loads(request.data_json)
        # Current sources use the task-scoped model contract. The shared
        # fixture copies actual task-local support without claiming a review.
        body = source_grounded_scoped_reply(data)
        return NarrativeModelResponse("offline-fixture", "offline-fixture", request.prompt_version,
                                      canonical_json(body).encode(), input_tokens=10, output_tokens=10)


def _registered_dag(payload, data, *, reader=None, normalization=None):
    """Execute registered real handlers and actual dependency edges; no provider."""
    model = CountingModel()
    executor = HandlerExecutor()
    register_narrative_handlers(executor, NarrativeRuntimeDependencies(
        reader=reader or FakeReader(payload, data), model=model, normalization=normalization,
        selector_version="0.9.0",
        reading_model_projection=lambda _subject: SCOPED_MODEL_PROJECTION_VERSION))
    base = _context(payload, lambda: None)
    results = {}
    for job_type in ("source.narrative_select", "source.narrative_summarize", "source.narrative_verify"):
        job = replace(base.job, job_type=job_type, job_id=job_type,
                      job_key=make_job_key(job_type, base.job.subject_type, base.job.subject_id,
                                           base.job.input_hash, base.job.policy_version, base.job.handler_version))
        context = replace(base, job=job, attempt=replace(base.attempt, job_id=job.job_id),
                          dependency_results=dict(results))
        result = executor.execute(job_type, context)
        results[job_type] = result
        if result.outcome is not HandlerOutcome.SUCCEEDED:
            break
    return results, model


def _run(data, *, mime="application/pdf", parser=None, selector=None, normalization=None, reader=None):
    payload = _event(data, mime)
    options = {} if parser is None else {"pdf_parser": parser}
    handler = NarrativeSelectHandler(reader=reader or FakeReader(payload, data), selector=selector,
                                    selector_version="0.9.0", normalization=normalization, **options)
    return handler(_context(payload, lambda: None))


def _replace_span(span, **changes):
    fields = {key: getattr(span, key) for key in ("source_id", "coordinates", "raw_text", "structured_value",
                                                "parser_name", "parser_version", "parse_status", "quality_flags")}
    return EvidenceSpan.create(**{**fields, **changes})


def test_registered_partial_pdf_dag_preserves_actual_coverage_and_reopens_original(tmp_path, monkeypatch):
    data = _pdf()
    original = tmp_path / "original.pdf"
    sentinel = tmp_path / "sentinel"
    original.write_bytes(data)
    sentinel.write_bytes(b"before")
    frozen = (hashlib.sha256(data).hexdigest(), original.stat().st_mtime_ns)
    calls = []
    parser = evidence._parse_pdf_document

    def counted(*args, **kwargs):
        calls.append(1)
        return parser(*args, **kwargs)

    monkeypatch.setattr(evidence, "_parse_pdf_document", counted)
    try:
        results, model = _registered_dag(_event(data), original.read_bytes())
        assert list(results) == ["source.narrative_select", "source.narrative_summarize", "source.narrative_verify"]
        assert all(result.outcome is HandlerOutcome.SUCCEEDED for result in results.values()), results
        selected = NarrativeSelectResult.from_dict(results["source.narrative_select"].result)
        bundle = NarrativeBundle.from_dict(results["source.narrative_verify"].result)
        assert selected.selection.status == "partial" and not selected.selection.coverage_complete
        assert selected.selection.pages_total == 2
        assert selected.reading_context["unread"]["opaque_pages"] == (2,)
        assert len(model.calls) == 1
        assert bundle.replay.locator_count == len(selected.evidence_spans)
        assert bundle.selection == selected.selection
        assert len(results["source.narrative_verify"].effects) == 1
        assert len(calls) == 2  # one select parse + the final source reopen/replay, no admission reparse
        assert hashlib.sha256(original.read_bytes()).hexdigest() == frozen[0]
        assert original.stat().st_mtime_ns == frozen[1]
        assert sentinel.read_bytes() == b"before"
    finally:
        original.unlink()
        sentinel.unlink()
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("data", [b"%PDF-invalid-content", None])
def test_registered_pre_model_negative_dag_never_calls_model(data, tmp_path):
    data = _pdf(text="", opaque=False) if data is None else data
    sentinel = tmp_path / "sentinel"
    sentinel.write_bytes(b"before")
    try:
        results, model = _registered_dag(_event(data), data)
        assert list(results) == ["source.narrative_select"]
        result = results["source.narrative_select"]
        assert result.outcome is HandlerOutcome.TERMINAL_FAILURE
        assert result.error.code == "PARSER_INCOMPLETE"
        assert not model.calls and not result.effects and result.metrics.tokens == 0
        assert sentinel.read_bytes() == b"before"
    finally:
        sentinel.unlink()
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("operation", ["get_text", "find_tables"])
def test_other_page_local_parser_failure_does_not_discard_proven_prose(monkeypatch, operation):
    fitz = pytest.importorskip("fitz")
    actual = getattr(fitz.Page, operation)

    def local_failure(page, *args, **kwargs):
        if page.number == 1:
            raise RuntimeError("isolated second-page extraction failure")
        return actual(page, *args, **kwargs)

    monkeypatch.setattr(fitz.Page, operation, local_failure)
    result = _run(_pdf())
    assert result.outcome is HandlerOutcome.SUCCEEDED, result.error
    selected = NarrativeSelectResult.from_dict(result.result)
    assert selected.evidence_spans
    assert not selected.selection.coverage_complete and selected.selection.status == "partial"
    assert selected.reading_context["unread"]["native_scan"] == "partial"


def test_equivalent_html_fragment_runs_registered_dag_with_partial_coverage():
    data = f"<p>{BUSINESS}</p>".encode()
    results, model = _registered_dag(_event(data, "text/html"), data)
    assert all(result.outcome is HandlerOutcome.SUCCEEDED for result in results.values()), results
    assert len(results) == 3 and len(model.calls) == 1
    selected = NarrativeSelectResult.from_dict(results["source.narrative_select"].result)
    assert not selected.selection.coverage_complete
    assert selected.summary_scope == "selected_evidence_only"


@pytest.mark.parametrize("mutation", ["source", "text", "locator", "native-range", "parser"])
def test_forged_selected_pdf_material_is_rejected_before_model(mutation):
    data = _pdf(opaque=False)

    def selector(parsed, **kwargs):
        package = evidence.select_narrative_evidence(parsed, selector_version="0.9.0", **kwargs)
        span = package.evidence_spans[0]
        if mutation == "source":
            forged = _replace_span(span, source_id="urn:company-wiki:source:sha256:" + "a" * 64)
        elif mutation == "text":
            forged = _replace_span(span, raw_text="Invented acquisition not present in original source.")
        elif mutation == "locator":
            forged = _replace_span(span, coordinates=EvidenceCoordinates(page_number=1, paragraph_index=9999))
        elif mutation == "parser":
            forged = _replace_span(span, parser_version="9.9.9")
        else:
            from company_wiki.source_catalog.narrative_native_ranges import NATIVE_RANGE_PARSER_NAME, NATIVE_RANGE_PARSER_VERSION
            metadata = dict(span.structured_value)
            metadata.update(unit_kind="pdf_native_range", native_range={"version": "forged"})
            forged = _replace_span(span, structured_value=metadata, parser_name=NATIVE_RANGE_PARSER_NAME,
                                  parser_version=NATIVE_RANGE_PARSER_VERSION)
        return replace(package, evidence_spans=(forged,), reading_context=None, reading_dependencies=None)

    result = _run(data, selector=selector)
    assert result.outcome is HandlerOutcome.TERMINAL_FAILURE
    assert result.error.code in {"PARSER_INCOMPLETE", "INPUT_SCHEMA_INVALID"}
    assert result.metrics.tokens == 0 and not result.effects


def test_partial_source_cannot_be_falsely_promoted_to_complete_by_selector():
    def selector(parsed, **kwargs):
        package = evidence.select_narrative_evidence(parsed, selector_version="0.9.0", **kwargs)
        return replace(package, status="selected", coverage_complete=True)

    result = _run(_pdf(), selector=selector)
    assert result.outcome is HandlerOutcome.SUCCEEDED, result.error
    selected = NarrativeSelectResult.from_dict(result.result)
    assert not selected.selection.coverage_complete and selected.selection.status == "partial"
    assert selected.reading_context["unread"]["opaque_pages"] == (2,)


def test_blocked_package_cannot_be_admitted_just_because_a_span_exists():
    def selector(parsed, **kwargs):
        return replace(evidence.select_narrative_evidence(parsed, selector_version="0.9.0", **kwargs), status="blocked")

    result = _run(_pdf(opaque=False), selector=selector)
    assert result.outcome is HandlerOutcome.TERMINAL_FAILURE and result.error.code == "PARSER_INCOMPLETE"


def test_empty_incomplete_source_cannot_become_skip():
    def selector(parsed, **_kwargs):
        return NarrativeEvidencePackage(parsed.source_id, parsed.source_sha256, "annual_report", "skipped_no_narrative",
                                        (), 96, 0, 0, len(parsed.units), 0, False)

    result = _run(_pdf(text="", opaque=False), selector=selector)
    assert result.outcome is HandlerOutcome.TERMINAL_FAILURE and result.error.code == "PARSER_INCOMPLETE"


def test_complete_administrative_source_keeps_zero_model_skip():
    data = b"<html><body><p>This policy describes meeting administration procedures.</p></body></html>"
    payload = _payload(data, title="Investor relations management policy", document_kind="ir_policy",
                       language="en", mime_type="text/html")
    results, model = _registered_dag(payload, data)
    assert len(results) == 3 and not model.calls
    selected = NarrativeSelectResult.from_dict(results["source.narrative_select"].result)
    assert selected.selection.status == "skipped_no_narrative" and selected.selection.coverage_complete


def test_source_sha_mismatch_remains_pre_model_failure():
    data = _pdf(opaque=False)
    payload = _event(data)
    reader = FakeReader(payload, data)
    reader.opened = replace(reader.opened, data=b"wrong original bytes")
    results, model = _registered_dag(payload, data, reader=reader)
    assert results["source.narrative_select"].error.code == "SOURCE_HASH_MISMATCH"
    assert not model.calls


def test_missing_required_selected_group_member_is_not_fixed_by_admission():
    def selector(parsed, **kwargs):
        package = evidence.select_narrative_evidence(parsed, selector_version="0.9.0", **kwargs)
        context = dict(package.reading_context)
        context["groups"] = [{"group_id": "broken-group", "kind": "operating_table", "section_role": "business",
                              "evidence_ids": [package.evidence_spans[0].span_id, "urn:company-wiki:evidence-span:sha256:" + "f" * 64]}]
        return replace(package, reading_context=context)

    result = _run(_pdf(opaque=False), selector=selector)
    assert result.outcome is HandlerOutcome.TERMINAL_FAILURE and result.error.code == "INPUT_SCHEMA_INVALID"


@pytest.mark.parametrize("field", ["source_locator", "source_sha256", "source_role", "parser"])
def test_forged_normalized_metadata_is_rejected_against_this_parse(field):
    data = f"<html><body><p>{BUSINESS}</p></body></html>".encode()

    def selector(parsed, **kwargs):
        package = evidence.select_narrative_evidence(parsed, selector_version="0.9.0", **kwargs)
        span = package.evidence_spans[0]
        metadata = dict(span.structured_value)
        if field == "parser":
            forged = _replace_span(span, parser_version="9.9.9")
        else:
            metadata[field] = {"source_locator": "cwp-html-dom/1|n=999999",
                               "source_sha256": "a" * 64, "source_role": "management"}[field]
            forged = _replace_span(span, structured_value=metadata)
        return replace(package, evidence_spans=(forged,), reading_context=None, reading_dependencies=None)

    result = _run(data, mime="text/html", selector=selector)
    assert result.outcome is HandlerOutcome.TERMINAL_FAILURE
    assert result.error.code in {"PARSER_INCOMPLETE", "INPUT_SCHEMA_INVALID"}
    assert result.metrics.tokens == 0 and not result.effects


@pytest.mark.parametrize("flag", ["low_ocr_confidence", "locator_unstable"])
def test_unreliable_selected_material_is_not_hidden_by_partial_label(flag):
    def selector(parsed, **kwargs):
        package = evidence.select_narrative_evidence(parsed, selector_version="0.9.0", **kwargs)
        bad = _replace_span(package.evidence_spans[0], quality_flags=(flag,))
        return replace(package, status="partial", evidence_spans=(bad,), reading_context=None, reading_dependencies=None)

    result = _run(_pdf(opaque=False), selector=selector)
    assert result.outcome is HandlerOutcome.TERMINAL_FAILURE and result.error.code == "PARSER_INCOMPLETE"


def test_package_source_binding_cannot_be_replaced_by_event_identity():
    def selector(parsed, **kwargs):
        package = evidence.select_narrative_evidence(parsed, selector_version="0.9.0", **kwargs)
        return replace(package, source_sha256="a" * 64)

    result = _run(_pdf(opaque=False), selector=selector)
    assert result.outcome is HandlerOutcome.TERMINAL_FAILURE and result.error.code == "PARSER_INCOMPLETE"
