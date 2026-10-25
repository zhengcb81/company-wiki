"""Replay observes the requested reader, never an implicit legacy preflight."""
import hashlib
from types import SimpleNamespace

from tools.document_understanding_benchmark import observer
from tools.holdout_replay import worker


def test_explicit_pdf_observation_shares_owner_budget_and_intent(tmp_path, monkeypatch):
    import pymupdf
    from company_wiki.source_catalog.narrative_pdf_reading import PdfReading

    with pymupdf.open() as doc:
        doc.new_page().insert_text((72, 72), "Overseas revenue grew 12 percent from new customer orders.")
        data = doc.tobytes()
    path = tmp_path / "report.pdf"
    path.write_bytes(data)
    seen = {}
    read = PdfReading.read
    def capture(self, raw, request, **kwargs):
        seen.update(request=request, budget=kwargs["work_budget"])
        return read(self, raw, request, **kwargs)
    monkeypatch.setattr(PdfReading, "read", capture)
    result = observer.observe_native(path, sha256=hashlib.sha256(data).hexdigest(),
        sample_id="neutral", existing_kind="semi_annual_report", selector_version="0.9.0", language="en")
    assert result["execution"]["selector_version"] == "0.9.0"
    assert seen["request"].document_kind == "semi_annual_report"
    assert seen["request"].language == "en"
    assert seen["budget"] is not None and seen["budget"].used > 0
    assert result["execution"]["work_used"] == seen["budget"].used


def test_worker_requests_current_observation_and_records_legacy_fallback(tmp_path, monkeypatch):
    calls = []
    def current(path, *, selector_version, **kwargs):
        calls.append(selector_version)
        return {"execution": {"selector_version": selector_version}}
    monkeypatch.setattr(observer, "observe_native", current)
    sample = {"sample_id": "neutral", "source_ref": {"content_sha256": "a" * 64}}
    result = worker._native_observation(tmp_path / "unused", sample, selector_version="0.9.0")
    assert calls == ["0.9.0"]
    assert result["execution"]["selector_version"] == "0.9.0"

    def historical(path, *, sha256, sample_id, existing_kind):
        return {"execution": {"selector_version": "0.8.0"}}
    monkeypatch.setattr(observer, "observe_native", historical)
    result = worker._native_observation(tmp_path / "unused", sample, selector_version="0.9.0")
    assert result["execution"]["selector_version"] == "0.8.0"
    assert result["execution"]["requested_selector_version"] == "0.9.0"
    assert result["execution"]["compatibility_reason"] == "producer_observer_has_no_selector_port"


def test_material_verified_range_is_not_dropped_by_single_unit_projection():
    from company_wiki.source_contract import EvidenceCoordinates
    span = SimpleNamespace(locator="page:1:range", raw_text="原始跨单元经营描述。",
        coordinates=EvidenceCoordinates(page_number=1), structured_value={"source_role": "company_filing"})
    assert observer._source_evidence([span], [], material_verified=True)[0]["text"] == span.raw_text
    assert observer._source_evidence([span], []) == []


def test_real_native_range_uses_owner_replay_before_projection():
    from unit.test_narrative_native_ranges import members, as_span, api, SOURCE
    from company_wiki.source_catalog.narrative_document import DocumentStructure
    from company_wiki.source_catalog.narrative_pdf_reading import PdfReading

    units, _ = members()
    carrier = api().native_range_unit(units)
    assert carrier is not None
    span = as_span(carrier)
    parsed = DocumentStructure(SOURCE, "a" * 64, "zh", tuple(units), page_count=2, pages_read=2)
    PdfReading().verify_material(parsed, [span])
    rows = observer._source_evidence([span], units, material_verified=True)
    assert len(rows) == 1 and rows[0]["text"] == span.raw_text
    assert rows[0]["material_proof"] == "reading_owner_replay"
