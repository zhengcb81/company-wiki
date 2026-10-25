"""The PDF reading boundary must survive replacing its implementation."""
from dataclasses import replace
import json
from types import SimpleNamespace

from company_wiki.automation import narrative_select as execution
from company_wiki.automation import narrative_selector_binding as binding
from company_wiki.automation.narrative_contracts import SourceRevisionEventPayload
from company_wiki.automation.narrative_generation import generation_manifest
from company_wiki.source_catalog.narrative_document import DocumentStructure, NarrativeEvidencePackage
from unit.test_narrative_batch import Reader, _module, _request


def test_replacement_parser_receives_same_budget_and_logical_reading_context(monkeypatch):
    observed = {}

    def parser(data, **kwargs):
        budget = kwargs.get("work_budget")
        assert budget is not None, "A replacement lost the caller's shared account"
        observed["budget"] = budget
        observed["context"] = kwargs["reading_context"]
        budget.charge(17)
        return DocumentStructure("source", "a" * 64, "en", (), page_count=1, pages_read=1)

    def selector(parsed, **kwargs):
        assert kwargs["work_budget"] is observed["budget"]
        assert kwargs["work_budget"].used == 17
        kwargs["work_budget"].charge(11)
        return NarrativeEvidencePackage(parsed.source_id, parsed.source_sha256,
            "annual_report", "skipped_no_narrative", (), 64, 0, 0, 0, 0, True)

    monkeypatch.setattr(binding, "select_narrative_evidence", selector)
    handler = execution.NarrativeSelectHandler(reader=object(), pdf_parser=parser,
        selector_version="0.9.0")
    payload = SimpleNamespace(source_ref=SimpleNamespace(mime_type="application/pdf",
        source_id="source", content_sha256="a" * 64),
        source_metadata=SimpleNamespace(language="en", title="Annual Report",
                                       document_kind="annual_report"))
    handler._select_pdf(payload, b"fixture", SimpleNamespace(checkpoint=lambda: None))
    assert observed["budget"].used == 28
    assert observed["context"].title == "Annual Report"


def test_pdf_actual_reading_recipe_is_not_silently_ignored_by_generation():
    request = _request()
    module = _module()
    event = module.build_batch_events(request, Reader(), now="2026-10-09T00:00:00Z").events[0]
    payload = SourceRevisionEventPayload.from_dict(json.loads(event.payload_json))
    wire = payload.to_dict()
    wire["source_ref"]["mime_type"] = "application/pdf"
    wire["source_metadata"].update(source_class="filing", document_kind="annual_report")
    payload = SourceRevisionEventPayload.from_dict(wire)
    request = replace(request, sources=(payload.source_ref,))
    recipe = {"parser_name": "selective_narrative_parser", "parser_version": "0.1.1",
              "format": "pdf", "reader_recipe": "native", "runtime": {"pymupdf": "1.0"}}
    arguments = {"execution_versions": module._execution_versions(request)}
    one = generation_manifest(request, payload, parser_components=recipe, **arguments)
    two = generation_manifest(request, payload,
        parser_components={**recipe, "runtime": {"pymupdf": "2.0"}}, **arguments)
    assert one != two, "PDF runtime changes must invalidate the causal generation"
    assert one["parser_components"] == recipe


def test_composition_shares_the_same_complete_reading_owner():
    from company_wiki.automation.narrative_runtime import (
        NarrativeRuntimeDependencies, register_narrative_handlers,
    )
    from company_wiki.source_catalog.narrative_pdf_reading import PdfReading
    handlers = {}
    registrar = SimpleNamespace(register=lambda name, handler: handlers.setdefault(name, handler))
    reading = PdfReading()
    register_narrative_handlers(registrar,
        NarrativeRuntimeDependencies(reader=object(), model=None, pdf_reading=reading))
    assert handlers["source.narrative_select"]._pdf_reading is reading
    assert handlers["source.narrative_verify"]._pdf_reading is reading


def test_native_recipe_omits_unrelated_installed_backends(monkeypatch):
    from company_wiki.source_catalog import narrative_pdf_reading as pdf
    called = []
    def installed(name):
        called.append(name)
        assert name == "pymupdf"
        return "1.2.3"
    monkeypatch.setattr(pdf, "version", installed)
    recipe = pdf.PdfReading().describe_recipe()
    assert recipe["runtime"] == {"pymupdf": "1.2.3"}
    assert "docling" not in json.dumps(recipe).lower()
    assert called == ["pymupdf"]


def test_frozen_pdf_recipe_drift_cannot_resume_as_current():
    import pytest
    from company_wiki.automation.narrative_batch import _validate_normalization_binding
    request = _request()
    event = _module().build_batch_events(request, Reader(), now="2026-10-09T00:00:00Z").events[0]
    payload = SourceRevisionEventPayload.from_dict(json.loads(event.payload_json))
    wire = payload.to_dict()
    wire["source_ref"]["mime_type"] = "application/pdf"
    wire["source_metadata"].update(source_class="filing", document_kind="annual_report")
    payload = SourceRevisionEventPayload.from_dict(wire)
    manifest = generation_manifest(request, payload,
        execution_versions=_module()._execution_versions(request))
    _validate_normalization_binding({"one": manifest}, None)
    manifest["parser_components"]["runtime"]["pymupdf"] = "another-version"
    with pytest.raises(ValueError, match="BATCH_FROZEN_BINDING_INVALID"):
        _validate_normalization_binding({"one": manifest}, None)


def test_complete_backend_preserves_actual_context_identity_and_replay():
    import hashlib
    import pymupdf
    import pytest
    from company_wiki.resource_budget import WorkBudget
    from company_wiki.source_catalog.narrative_pdf_reading import (
        NativePdfBackend, PdfReading, PdfReadingRequest,
    )
    with pymupdf.open() as document:
        document.new_page().insert_text((40, 60), "Cloud orders grew 20 percent in 2025.")
        raw = document.tobytes()
    sha = hashlib.sha256(raw).hexdigest()
    source_id = "urn:company-wiki:source:sha256:" + sha
    request = PdfReadingRequest(source_id, sha, "en", "Annual Report", "annual_report")
    seen = []
    class Backend(NativePdfBackend):
        def describe_recipe(self):
            return {**super().describe_recipe(), "reader_recipe": "native-compatible-test/1"}
        def read(self, data, logical_request, **options):
            seen.append((logical_request, options["work_budget"]))
            return super().read(data, logical_request, **options)
        def replay(self, data, **options):
            seen.append("same-backend-replay")
            return super().replay(data, **options)
    reading = PdfReading(Backend())
    budget = WorkBudget(100000)
    parsed = reading.read(raw, request, selector_version="0.9.0", work_budget=budget)
    assert seen == [(request, budget)] and budget.used > 0
    assert parsed.layout_coverage is not None
    spans = (parsed.units[0].to_evidence_span(topics=("business",), selection_reasons=("test",)),)
    reading.verify_material(parsed, spans)
    verified, failed = reading.replay(raw, source_id=source_id, source_sha256=sha,
        evidence_spans=spans, language="en")
    assert verified == (spans[0].span_id,) and not failed
    assert seen[-1] == "same-backend-replay"
    with pytest.raises(ValueError):
        reading.replay(raw + b"changed", source_id=source_id, source_sha256=sha,
            evidence_spans=spans, language="en")


def test_backend_cannot_return_a_different_producer_under_native_identity():
    import pytest
    from company_wiki.source_catalog.narrative_pdf_reading import (
        NativePdfBackend, PdfReading, PdfReadingRequest,
    )
    def parser(data, **kwargs):
        return DocumentStructure("different-source", "a" * 64, "en", (), page_count=1, pages_read=1)
    reading = PdfReading(NativePdfBackend(parser=parser))
    with pytest.raises(ValueError, match="different source or producer"):
        reading.read(b"fixture", PdfReadingRequest("source", "a" * 64, "en"),
            selector_version="0.9.0")


def test_empty_shared_account_stops_even_a_replacement_before_io():
    import pytest
    from company_wiki.resource_budget import WorkBudget, WorkBudgetExceeded
    from company_wiki.source_catalog.narrative_pdf_reading import (
        NativePdfBackend, PdfReading, PdfReadingRequest,
    )
    calls = []
    reading = PdfReading(NativePdfBackend(parser=lambda *args, **kwargs: calls.append("io")))
    budget = WorkBudget(0)
    with pytest.raises(WorkBudgetExceeded):
        reading.read(b"fixture", PdfReadingRequest("source", "a" * 64, "en"),
            selector_version="0.9.0", work_budget=budget)
    assert calls == [] and budget.used == 0 and budget.exhausted


def test_recipe_snapshot_is_detached_and_execution_rejects_backend_drift():
    import pytest
    from company_wiki.source_catalog.narrative_pdf_reading import (
        NativePdfBackend, PdfReading, PdfReadingRequest,
    )
    class Backend(NativePdfBackend):
        marker = "one"
        def describe_recipe(self):
            return {**super().describe_recipe(), "options": {"marker": self.marker}}
    backend = Backend()
    reading = PdfReading(backend)
    described = reading.describe_recipe()
    described["options"]["marker"] = "caller-mutated"
    assert reading.describe_recipe()["options"]["marker"] == "one"
    backend.marker = "two"
    with pytest.raises(ValueError, match="frozen recipe"):
        reading.read(b"fixture", PdfReadingRequest("source", "a" * 64, "en"),
            selector_version="0.9.0")


def test_optional_pdf_dependency_does_not_affect_non_pdf_composition(monkeypatch):
    from importlib.metadata import PackageNotFoundError
    import pytest
    from company_wiki.source_catalog import narrative_pdf_reading as pdf
    from company_wiki.automation.narrative_verify import NarrativeVerifyHandler
    def missing(name):
        raise PackageNotFoundError(name)
    monkeypatch.setattr(pdf, "version", missing)
    execution.NarrativeSelectHandler(reader=object())
    NarrativeVerifyHandler(reader=object())
    with pytest.raises(RuntimeError, match="PDF_DEPENDENCY_UNAVAILABLE"):
        pdf.PdfReading().describe_recipe()


def test_backend_receives_the_same_absolute_deadline_and_expiry_prevents_io():
    import time
    import pytest
    from company_wiki.source_catalog.narrative_pdf_reading import (
        NativePdfBackend, PdfReading, PdfReadingRequest,
    )
    observed = []
    class Backend(NativePdfBackend):
        def read(self, data, request, **options):
            observed.append(options["deadline"])
            return DocumentStructure(request.source_id, request.source_sha256,
                request.language, (), page_count=1, pages_read=1)
    deadline = time.monotonic() + 60
    reading = PdfReading(Backend(), deadline=deadline)
    request = PdfReadingRequest("source", "a" * 64, "en")
    reading.read(b"fixture", request, selector_version="0.9.0")
    assert observed == [deadline]
    with pytest.raises(RuntimeError, match="PDF_READING_DEADLINE"):
        PdfReading(Backend(), deadline=0).read(b"fixture", request, selector_version="0.9.0")
    assert observed == [deadline]


def test_owner_rejects_secret_and_physical_location_recipe_fields(tmp_path):
    import pytest
    from company_wiki.source_catalog.narrative_pdf_reading import NativePdfBackend, PdfReading
    for extension in ({"api_key": "test-placeholder-only"},
                      {"options": {"model_path": str(tmp_path / "model")}},
                      {"runtime": {"location": "/example/cache"}},
                      {"options": {"ACCESS_TOKEN": "test-placeholder-only"}}):
        class Backend(NativePdfBackend):
            def describe_recipe(self):
                return {**super().describe_recipe(), **extension}
        with pytest.raises(ValueError):
            PdfReading(Backend()).describe_recipe()


def test_transcript_material_validation_never_opens_optional_pdf_runtime(monkeypatch):
    import hashlib
    from importlib.metadata import PackageNotFoundError
    from company_wiki.source_catalog import narrative_pdf_reading as pdf
    from company_wiki.source_catalog.narrative_evidence import parse_transcript_text
    def missing(name):
        raise PackageNotFoundError(name)
    monkeypatch.setattr(pdf, "version", missing)
    raw = b"Full Conference Call Transcript\nCEO: Our cloud business grew 20 percent in 2025.\n"
    sha = hashlib.sha256(raw).hexdigest()
    parsed = parse_transcript_text(raw.decode("utf-8"), source_id="urn:company-wiki:source:sha256:" + sha,
                                  source_sha256=sha, parser_version="0.1.0", language="en")
    assert parsed.units
    span = parsed.units[0].to_evidence_span(topics=("business",), selection_reasons=("test",))
    package = NarrativeEvidencePackage(parsed.source_id, parsed.source_sha256,
        "investor_call_transcript", "selected", (span,), 64, 1, 1, 0, 0, True)
    execution.NarrativeSelectHandler._verify_selected_material(
        parsed, package, mime_type="text/plain", pdf_reading=pdf.PdfReading())


def test_completed_pdf_history_keeps_unknown_recipe_omitted_without_resigning_it():
    from copy import deepcopy
    from company_wiki.automation.narrative_batch import _completed_history_generation_matches
    old = {"schema_version": "narrative-generation/1", "model": {},
        "source_ref": {"mime_type": "application/pdf", "content_sha256": "a" * 64},
        "source_metadata": {"source_class": "filing"}, "parser_component": {"version": "0.1.1"}}
    original = deepcopy(old)
    current = {**old, "parser_components": {"reader_recipe": "native-pdf/1"}}
    assert _completed_history_generation_matches(current, old, completed_history=True)
    assert not _completed_history_generation_matches(current, old, completed_history=False)
    assert not _completed_history_generation_matches(
        {**current, "parser_component": {"version": "9.9"}}, old, completed_history=True)
    assert not _completed_history_generation_matches(
        current, {**old, "parser_components": {"reader_recipe": "retired"}}, completed_history=True)
    assert old == original and "parser_components" in current


def test_backend_cannot_mix_another_sources_units_under_one_document():
    import pytest
    from company_wiki.source_catalog.narrative_evidence import _make_unit
    from company_wiki.source_contract import EvidenceCoordinates
    from company_wiki.source_catalog.narrative_pdf_reading import NativePdfBackend, PdfReading, PdfReadingRequest
    other = _make_unit(source_id="other-source", parser_version="0.1.1",
        coordinates=EvidenceCoordinates(page_number=1, paragraph_index=0),
        raw_text="Other business orders grew 25 percent.", unit_kind="pdf_text_block",
        source_role="company_filing", language="en", metadata={})
    def parser(data, **kwargs):
        return DocumentStructure("source", "a" * 64, "en", (other,), page_count=1, pages_read=1)
    with pytest.raises(ValueError, match="different source or producer"):
        PdfReading(NativePdfBackend(parser=parser)).read(b"fixture",
            PdfReadingRequest("source", "a" * 64, "en"), selector_version="0.9.0")
