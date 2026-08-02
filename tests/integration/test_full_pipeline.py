"""Hermetic component integration for classify -> extract -> validate."""

from pdf_extract_v3 import classify_pdf_v2, extract_pdf_text_v3, validate_extraction


def test_synthetic_pdf_runs_through_classify_extract_validate(synthetic_announcement_pdf):
    classification = classify_pdf_v2(synthetic_announcement_pdf.name)
    assert classification["doc_type"] == "announcement"
    assert classification["confidence"] >= 0.9
    assert classification["skip"] is False

    extraction = extract_pdf_text_v3(synthetic_announcement_pdf)
    assert extraction["error"] is None
    assert extraction["total_pages"] == 3
    assert extraction["pages_read"] == 3
    assert extraction["total_chars"] >= 500
    assert extraction["quality_score"] >= 0.30
    assert "Company announcement" in extraction["text"]

    validation = validate_extraction(extraction, classification["doc_type"])
    assert validation["status"] == "passed"
    assert validation["failed_checks"] == []


def test_extraction_max_pages_is_enforced(synthetic_announcement_pdf):
    extraction = extract_pdf_text_v3(synthetic_announcement_pdf, max_pages=1)
    assert extraction["error"] is None
    assert extraction["total_pages"] == 3
    assert extraction["pages_read"] == 1
    assert "Page 1" in extraction["text"]
    assert "Page 2" not in extraction["text"]
