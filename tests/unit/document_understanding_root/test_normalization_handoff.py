"""Real public frontend -> DU policy -> model-facing evidence, no network."""
import hashlib

from company_wiki.document_normalization import NormalizationLimits, normalize_document, replay_unit
from company_wiki.document_understanding import build_summary_input, understand_units


def test_container_child_policy_reaches_summary_and_reading_expectation():
    original = b"<html><body><h1>FORM 8-K</h1><p>Current Report</p><h2>Exhibit 99.1</h2><h2>Second Quarter Results</h2><h3>Business Highlights</h3><p>During the quarter, we launched a new subscription product and opened a new manufacturing facility in Europe.</p></body></html>"
    sha = hashlib.sha256(original).hexdigest()
    source_id = "urn:company-wiki:source:sha256:" + sha
    normalized = normalize_document(original, source_id=source_id, source_sha256=sha, mime_type="text/html")
    metadata = {"regime": "sec", "form_type": "8-K", "published_at": "2026-01-02"}
    pipeline = understand_units(normalized.units, source_id=source_id, source_sha256=sha,
                                mime_type="text/html", metadata=metadata)
    request = build_summary_input(pipeline)
    assert pipeline["route"]["subtype"] == "sec_current_report_8k"
    assert pipeline["plan"]["expects_business_narrative"] is True
    assert not any(d["code"] == "NO_NARRATIVE_EXPECTED" for d in pipeline["diagnostics"])
    assert any(p["reading_profile_id"] == "results_release" and p["summary_focus"] for p in request["evidence_packages"])
    assert request["source_metadata"]["published_at"] == "2026-01-02"
    by_id = {unit.unit_id: unit for unit in normalized.units}
    for package in request["evidence_packages"]:
        for member in package["members"]:
            unit = by_id[member["unit_id"]]
            assert replay_unit(original, source_sha256=sha, unit=unit, limits=NormalizationLimits()) == member["text"]
            assert member["locator"] == unit.metadata["source_locator"]


def test_unknown_document_does_not_assert_absence_of_business():
    original = b"<html><body><p>An unclassified disclosure.</p></body></html>"
    sha = hashlib.sha256(original).hexdigest()
    source_id = "urn:company-wiki:source:sha256:" + sha
    normalized = normalize_document(original, source_id=source_id, source_sha256=sha, mime_type="text/html")
    pipeline = understand_units(normalized.units, source_id=source_id, source_sha256=sha, mime_type="text/html")
    assert pipeline["route"]["family"] == "unknown"
    assert pipeline["plan"]["expects_business_narrative"] is None
    assert not any(d["code"] == "NO_NARRATIVE_EXPECTED" for d in pipeline["diagnostics"])
