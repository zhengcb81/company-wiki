"""Public source query and source manifest agree on reported fiscal years."""
from __future__ import annotations

from dataclasses import asdict
from hashlib import sha256
from typing import Any

import pytest

from company_wiki.source_catalog.resolver import ResolutionStatus, SourceResolver
from company_wiki.source_catalog.source_read_policy import exact_source_read_policy_sha256
from company_wiki.source_catalog.source_reader import SourceVersionReader
from company_wiki.source_catalog.source_request import SourceRequest
from helpers.source_factory import canonical_source, company_raw_catalog


@pytest.mark.parametrize(
    ("market", "security", "title"),
    [
        ("HK", "09999", "Sample Industrial：2024年年度報告"),
        ("CN", "600999", "样本工业2024年年度报告"),
        ("US", "TSTM", "Sample Industrial Annual Report for Fiscal Year 2024"),
        ("US", "TSTM", "Sample Industrial Annual Report FY2024"),
    ],
)
def test_exact_query_and_manifest_share_captured_report_year(tmp_path, market, security, title):
    original = canonical_source(
        tmp_path, company="Sample Industrial", market=market, security_id=security,
        filename="2025-04-08-annual.pdf", source_title=title,
        extra_sidecar={"document_kind": "annual_report", "published_date": "2025-04-08"},
    )
    catalog = company_raw_catalog(tmp_path, original)
    try:
        reader = SourceVersionReader(catalog)
        request: dict[str, Any] = {
            "schema_version": "1.0", "entity": "Sample Industrial",
            "market": market, "security_id": security, "document_kind": "annual_report",
            "mode": "exact", "as_of_date": "2026-07-31", "allow_download": False,
        }
        match = reader.query_local(SourceRequest(**request, fiscal_year=2024))
        assert match.status == "found", match
        (ref,) = match.matches
        assert reader.describe_candidate(ref)["fiscal_year"] == 2024
        manifest = reader.describe_version(ref)
        assert manifest["fiscal_year"] == 2024
        assert manifest["published_date"] == "2025-04-08"
        assert manifest["content_sha256"] == sha256(original.read_bytes()).hexdigest()
        assert not reader.query_local(SourceRequest(**request, fiscal_year=2025)).matches
    finally:
        catalog.close()


@pytest.mark.parametrize(
    ("title", "extra_sidecar", "expected_year", "unmatched_status"),
    [
        ("Annual Report", {}, None, "not_found"),
        ("Annual Report (Site update 2024)", {}, None, "ambiguous"),
        ("Annual Report 2024-04-08", {}, None, "ambiguous"),
        ("年度報告 2024年4月8日", {}, None, "ambiguous"),
        ("2023/2024 Annual Report", {}, None, "ambiguous"),
        ("Annual Report 2023 / Annual Report 2024", {}, None, "ambiguous"),
        ("Annual Report 2024", {"fiscal_year": 2023}, 2023, "not_found"),
    ],
)
def test_filename_dates_and_unrelated_or_ambiguous_years_are_not_exact_scope(
    tmp_path, title, extra_sidecar, expected_year, unmatched_status,
):
    original = canonical_source(
        tmp_path, company="Sample Industrial", market="HK", security_id="09999",
        filename="2025-04-08-sample-2024-annual.pdf", source_title=title,
        extra_sidecar={"document_kind": "annual_report", "published_date": "2025-04-08", **extra_sidecar},
    )
    catalog = company_raw_catalog(tmp_path, original)
    try:
        reader = SourceVersionReader(catalog)
        query: dict[str, Any] = {
            "schema_version": "1.0", "entity": "Sample Industrial", "market": "HK",
            "security_id": "09999", "document_kind": "annual_report",
            "mode": "exact", "as_of_date": "2026-07-31", "allow_download": False,
        }
        unresolved = reader.query_local(SourceRequest(**query, fiscal_year=2024))
        assert unresolved.status == unmatched_status
        unscoped = reader.query_local(SourceRequest(**query))
        assert unscoped.status == "found"
        (ref,) = unscoped.matches
        if unmatched_status == "ambiguous":
            assert unresolved.matches == (ref,)
            assert unresolved.reason == "reported_fiscal_year_unconfirmed"
        assert reader.describe_candidate(ref)["fiscal_year"] == expected_year
        assert reader.describe_version(ref)["fiscal_year"] == expected_year
        if expected_year is not None:
            assert reader.query_local(SourceRequest(**query, fiscal_year=expected_year)).matches == (ref,)
    finally:
        catalog.close()


def test_reported_year_does_not_change_existing_exact_read_identity(tmp_path):
    original = canonical_source(
        tmp_path, source_title="Acme 2025 Annual Report",
        extra_sidecar={"document_kind": "annual_report", "published_date": "2026-02-20"},
    )
    catalog = company_raw_catalog(tmp_path, original)
    try:
        reader = SourceVersionReader(catalog)
        result = reader.query_local(SourceRequest(
            entity="Acme", document_kind="annual_report", as_of_date="2026-07-31",
            market="CN", security_id="600519", fiscal_year=2025, mode="exact",
            allow_download=False, schema_version="1.0",
        ))
        (ref,) = result.matches
        reported = reader.describe_version(ref)
        # These are the persisted observations in the pre-change scope hash.
        original_scope_facts = {
            key: reported[key] for key in (
                "document_kind", "canonical_entity_id", "market", "security_id",
                "fiscal_year", "fiscal_period", "period_end", "published_date",
                "form_type", "title", "language",
            )
        }
        original_scope_facts["fiscal_year"] = None
        legacy_pin = exact_source_read_policy_sha256(
            catalog.config, None, source_ref=asdict(ref),
            source_facts=original_scope_facts, registered_root_ids=("company_raw",),
        )
        assert reader.read_policy_sha256(ref) == legacy_pin
        opened, manifest = reader.open_described_version(ref, expected_read_policy_sha256=legacy_pin)
        assert (opened.document_id, opened.source_id, opened.content_sha256) == (
            ref.document_id, ref.source_id, ref.content_sha256,
        )
        assert opened.data == original.read_bytes()
        assert manifest["fiscal_year"] == 2025
    finally:
        catalog.close()

@pytest.mark.parametrize(
    ("title", "reported"),
    [
        ("Sample Industrial Annual Report 2024 (filed 2025-04-08)", 2024),
        ("Sample Industrial Annual Report 2025-04-08", None),
    ],
)
def test_acquisition_shortcut_cannot_verify_the_filing_date_as_fiscal_year(tmp_path, title, reported):
    original = canonical_source(
        tmp_path, company="Sample Industrial", filename="2025-04-08-annual.pdf",
        market="HK", security_id="09999", source_title=title,
        url="https://www1.hkexnews.hk/listedco/listconews/sehk/2025/0408/sample.pdf",
        extra_sidecar={"document_kind": "annual_report", "published_date": "2025-04-08"},
        content=b"%PDF-1.4\nsample original bytes\n",
    )
    catalog = company_raw_catalog(tmp_path, original)
    try:
        resolver = SourceResolver(catalog)
        request: dict[str, Any] = {
            "schema_version": "1.0", "entity": "Sample Industrial",
            "market": "HK", "security_id": "09999", "document_kind": "annual_report",
            "mode": "exact", "as_of_date": "2026-07-31", "allow_download": False,
        }
        wrong, verified = resolver.resolve_for_acquisition(
            SourceRequest(**request, fiscal_year=2025), reconcile_scope=True,
        )
        assert wrong.status is ResolutionStatus.MISSING
        assert verified is None
        if reported is not None:
            selected, verified = resolver.resolve_for_acquisition(
                SourceRequest(**request, fiscal_year=reported), reconcile_scope=True,
            )
            assert selected.status is ResolutionStatus.REUSED_EQUIVALENT
            assert verified is not None
            assert verified.source_ref.content_sha256 == sha256(original.read_bytes()).hexdigest()
            assert selected.matches[0].fiscal_year == reported
    finally:
        catalog.close()
