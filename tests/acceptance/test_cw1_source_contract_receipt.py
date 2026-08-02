"""Hermetic validation for the CW-1 real-workspace source acceptance receipt."""

from datetime import datetime
import hashlib
import json
from pathlib import Path, PurePosixPath
import re


ROOT = Path(__file__).resolve().parents[2]
RECEIPT_PATH = (
    ROOT / "artifacts" / "gates" / "cw1-source-contract-real-sample-receipt.json"
)
TOP_FIELDS = {
    "schema_version",
    "result",
    "observed_at",
    "scope",
    "samples",
    "export",
    "checks",
    "known_gaps",
    "announcement_collection",
    "visual_verification",
    "receipt_sha256",
    "acceptance_id",
}
SAMPLE_FIELDS = {
    "company",
    "entity_id",
    "input_kind",
    "original_path",
    "source_type",
    "published_date",
    "retrieved_at",
    "content_sha256",
    "byte_size",
    "source_id",
    "span_id",
    "locator",
    "parse_status",
    "quality_flags",
}
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
UTC_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


def _receipt():
    assert RECEIPT_PATH.is_file(), "CW-1 real-workspace receipt is not published"
    return json.loads(RECEIPT_PATH.read_text(encoding="utf-8"))


def test_receipt_has_strict_versioned_candidate_shape():
    receipt = _receipt()
    assert set(receipt) == TOP_FIELDS
    assert receipt["schema_version"] == "1.1.0"
    assert receipt["result"] == "candidate"
    assert UTC_RE.fullmatch(receipt["observed_at"])
    datetime.strptime(receipt["observed_at"], "%Y-%m-%dT%H:%M:%SZ")


def test_receipt_hash_and_acceptance_identity_are_canonical():
    receipt = _receipt()
    payload = {
        key: value
        for key, value in receipt.items()
        if key not in {"receipt_sha256", "acceptance_id"}
    }
    canonical = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    expected = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    assert receipt["receipt_sha256"] == expected
    assert receipt["acceptance_id"] == (
        "urn:company-wiki:cw1-acceptance:sha256:" + expected
    )


def test_scope_is_exactly_three_companies_and_four_required_inputs():
    scope = _receipt()["scope"]
    assert scope == {
        "companies": ["北方华创", "中微公司", "中芯国际"],
        "required_inputs": ["announcement", "financial_report", "news", "table"],
        "stockwiki_write_allowed": False,
    }


def test_samples_are_strict_source_only_records():
    samples = _receipt()["samples"]
    assert len(samples) == 3
    assert all(set(sample) == SAMPLE_FIELDS for sample in samples)
    assert {sample["company"] for sample in samples} == {
        "北方华创",
        "中微公司",
        "中芯国际",
    }
    assert {sample["input_kind"] for sample in samples} == {
        "news",
        "announcement",
        "financial_report_table",
    }


def test_sample_identities_paths_and_timestamps_are_canonical():
    for sample in _receipt()["samples"]:
        assert SHA256_RE.fullmatch(sample["content_sha256"])
        assert sample["source_id"] == (
            "urn:company-wiki:source:sha256:" + sample["content_sha256"]
        )
        assert re.fullmatch(
            r"urn:company-wiki:evidence-span:sha256:[0-9a-f]{64}",
            sample["span_id"],
        )
        assert sample["byte_size"] > 0
        assert UTC_RE.fullmatch(sample["retrieved_at"])
        path = sample["original_path"]
        assert "\\" not in path
        assert not path.startswith("/")
        assert ".." not in PurePosixPath(path).parts


def test_original_announcement_raw_and_collection_provenance_are_visible():
    receipt = _receipt()
    announcement = next(
        sample
        for sample in receipt["samples"]
        if sample["input_kind"] == "announcement"
    )
    assert announcement["source_type"] == "company_announcement"
    assert announcement["parse_status"] == "parsed"
    assert announcement["quality_flags"] == []
    assert announcement["locator"] == "loc:v1/page:1/paragraph:0"
    assert announcement["published_date"] == "2026-03-25"
    assert announcement["content_sha256"] == (
        "888f427abdb31cb5b284b73263d6b0aebf08f0e5e75814268cea85139857fc87"
    )
    assert announcement["original_path"] == (
        "companies/中微公司/raw/announcements/"
        "888f427abdb31cb5b284b73263d6b0aebf08f0e5e75814268cea85139857fc87.pdf"
    )
    assert receipt["known_gaps"] == []

    collection = receipt["announcement_collection"]
    assert set(collection) == {
        "collection_id",
        "collector_name",
        "collector_version",
        "source_url",
        "manifest_path",
        "manifest_file_sha256",
        "provenance_path",
        "provenance_file_sha256",
    }
    assert re.fullmatch(
        r"urn:company-wiki:announcement-collection:sha256:[0-9a-f]{64}",
        collection["collection_id"],
    )
    assert collection["collector_name"] == "company-wiki-explicit-announcement"
    assert collection["collector_version"] == "1.0.0"
    assert collection["source_url"].startswith("https://star.sse.com.cn/")
    assert collection["manifest_path"].startswith(
        "source_manifests/companies/中微公司/"
    )
    assert collection["provenance_path"].startswith(
        "source_provenance/companies/中微公司/announcements/"
    )
    assert SHA256_RE.fullmatch(collection["manifest_file_sha256"])
    assert SHA256_RE.fullmatch(collection["provenance_file_sha256"])


def test_financial_table_locator_matches_visual_verification():
    receipt = _receipt()
    financial = next(
        sample
        for sample in receipt["samples"]
        if sample["input_kind"] == "financial_report_table"
    )
    assert financial["locator"] == "loc:v1/page:10/table:0/row:2/column:1"
    assert financial["parse_status"] == "parsed"
    assert financial["quality_flags"] == []
    visual = receipt["visual_verification"]["financial_table"]
    assert visual == {
        "document": "中芯国际2025年第一季度报告",
        "page_number": 10,
        "table_index": 0,
        "row_index": 2,
        "column_index": 1,
        "label": "货币资金",
        "period": "2025-03-31",
        "unit": "CNY_thousand",
        "raw_text": "36,042,919",
        "render_result": "legible_no_clipping_or_overlap",
    }


def test_announcement_visual_verification_matches_original_pdf():
    visual = _receipt()["visual_verification"]["announcement"]
    assert visual == {
        "document": "中微公司关于召开2025年度业绩说明会的公告",
        "page_count": 2,
        "page_number": 1,
        "security_code": "688012",
        "announcement_number": "2026-016",
        "title": "关于召开2025年度业绩说明会的公告",
        "signature_date": "2026-03-25",
        "render_result": "legible_no_clipping_or_overlap",
    }


def test_export_identity_counts_and_all_positive_checks_are_valid():
    receipt = _receipt()
    exported = receipt["export"]
    assert exported["schema_version"] == "1.0.0"
    assert exported["counts"] == {"source_manifests": 3, "evidence_spans": 3}
    assert SHA256_RE.fullmatch(exported["bundle_sha256"])
    assert exported["export_id"] == (
        "urn:company-wiki:source-export:sha256:" + exported["bundle_sha256"]
    )
    assert receipt["checks"]
    assert all(value is True for value in receipt["checks"].values())


def test_receipt_contains_no_exported_body_or_downstream_investment_state():
    receipt = _receipt()
    assert all("raw_text" not in sample for sample in receipt["samples"])
    assert all("structured_value" not in sample for sample in receipt["samples"])
    text = json.dumps(receipt, ensure_ascii=False, sort_keys=True).lower()
    forbidden = (
        "target_price",
        "position_size",
        "buy_rating",
        "sell_rating",
        "investment_conclusion",
        "research_acceptance",
    )
    assert not any(term in text for term in forbidden)
