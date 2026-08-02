"""Hermetic boundaries for PDF stage-1 behavior."""

import pytest

from pdf_extract_v3 import classify_pdf_v2, extract_pdf_text_v3


@pytest.mark.parametrize(
    ("filename", "expected_type", "expected_period"),
    [
        ("测试公司：2024年年度报告.pdf", "annual_report", "2024-12-31"),
        ("测试公司：2024年半年度报告.pdf", "semi_annual_report", "2024-06-30"),
        ("测试公司：2024年第一季度报告.pdf", "quarterly_report", "2024-03-31"),
        ("测试公司：首次公开发行股票招股说明书.pdf", "prospectus", None),
        ("测试公司：2024年5月投资者关系活动记录表.pdf", "investor_relations", None),
        ("年度报告摘要.pdf", "abstract", None),
    ],
)
def test_classification_contract(filename, expected_type, expected_period):
    result = classify_pdf_v2(filename)
    assert result["doc_type"] == expected_type
    assert result["period"] == expected_period


def test_missing_pdf_returns_explicit_error(tmp_path):
    missing = tmp_path / "missing.pdf"
    result = extract_pdf_text_v3(missing)
    assert result["error"] == f"File not found: {missing}"
    assert result["pages_read"] == 0
    assert result["total_chars"] == 0


def test_synthetic_pdf_is_not_classified_as_scanned(synthetic_announcement_pdf):
    result = extract_pdf_text_v3(synthetic_announcement_pdf)
    assert result["error"] is None
    assert result["is_scanned"] is False
    assert result["scan_confidence"] == 0.0
