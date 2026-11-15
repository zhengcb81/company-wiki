"""FF-1 B1: the unknown-published-date branch names its shape.

Exactly one undated semantic match gets its own reason
(``unique_match_published_date_unknown``); several keep the umbrella reason
(``matching_sources_have_unknown_published_date``).  Status stays AMBIGUOUS,
and the count plus the enriched (pathless) excluded-candidate diagnostics ride
the resolution result for the ensure self-heal (B2) and the operation
projection (B4).
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from company_wiki.source_catalog import (  # noqa: E402
    CatalogConfig,
    RootSpec,
    SourceCatalog,
)
from company_wiki.source_catalog.resolver import (  # noqa: E402
    CANDIDATE_EXCLUSION_REASONS,
    ResolutionStatus,
    SourceRequest,
    SourceResolver,
    UNKNOWN_PUBLISHED_DATE_REASONS,
)
from contract.test_source_version_reader import (  # noqa: E402
    BODY,
    OTHER,
    OTHER_SHA,
    SHA,
    _write,
)

#: The candidate-projection whitelist the excluded diagnostic now carries
#: (B4 contract): physical locators must stay out.
_CANDIDATE_FIELDS = (
    "document_id", "title", "document_kind", "provider", "provider_document_id",
    "form_type", "fiscal_year", "fiscal_period", "language", "content_sha256",
    "byte_size", "publication_status", "exclusion_reason",
)


def _undated_catalog(tmp_path: Path, *, revisions: int) -> SourceCatalog:
    """A company_raw catalog whose annual filings declare no filing date."""
    companies = tmp_path / "companies"
    bodies = ((BODY, SHA, "doc-1"), (OTHER, OTHER_SHA, "doc-2"))[:revisions]
    for index, (body, sha, provider_id) in enumerate(bodies):
        _write(
            companies / "Acme" / "raw" / "financial_reports" / "annual",
            name=f"2025-revision-{index}.pdf", body=body, sha=sha,
            provider_id=provider_id, filing_date=None,
        )
    catalog = SourceCatalog(
        CatalogConfig(
            project_root=tmp_path,
            catalog_dir=tmp_path / ".source_catalog",
            roots=(
                RootSpec("company_raw", companies, "company_raw", priority=10,
                         adapter_id="company_raw_v1", read_only=False,
                         reusable_for_filing=True, canonical_write_target="companies"),
            ),
        )
    )
    catalog.scan()
    return catalog


def _request() -> SourceRequest:
    return SourceRequest(
        entity="Acme", market="US", security_id="ACME",
        document_kind="annual_report", fiscal_year=2025,
        as_of_date="2026-10-08", allow_download=True,
    )


def test_single_undated_match_gets_the_unique_named_reason(tmp_path):
    catalog = _undated_catalog(tmp_path, revisions=1)
    try:
        result = SourceResolver(catalog).resolve(_request())
    finally:
        catalog.close()

    assert result.status is ResolutionStatus.AMBIGUOUS
    assert result.reason == "unique_match_published_date_unknown"
    assert result.reason in UNKNOWN_PUBLISHED_DATE_REASONS
    assert result.unknown_date_match_count == 1
    assert result.to_dict()["unknown_date_match_count"] == 1
    assert result.to_dict()["reason"] == "unique_match_published_date_unknown"


def test_multiple_undated_matches_keep_the_umbrella_reason(tmp_path):
    catalog = _undated_catalog(tmp_path, revisions=2)
    try:
        result = SourceResolver(catalog).resolve(_request())
    finally:
        catalog.close()

    assert result.status is ResolutionStatus.AMBIGUOUS
    assert result.reason == "matching_sources_have_unknown_published_date"
    assert result.unknown_date_match_count == 2
    assert len(result.excluded_candidates) == 2


def test_undated_excluded_candidate_carries_the_pathless_whitelist(tmp_path):
    catalog = _undated_catalog(tmp_path, revisions=1)
    try:
        result = SourceResolver(catalog).resolve(_request())
    finally:
        catalog.close()

    diagnostic, = result.excluded_candidates
    assert diagnostic["exclusion_reason"] == "published_date_unknown"
    assert diagnostic["exclusion_reason"] in CANDIDATE_EXCLUSION_REASONS
    assert diagnostic["publication_status"] == "unknown"
    for field in _CANDIDATE_FIELDS:
        assert field in diagnostic, f"missing candidate field: {field}"
    assert diagnostic["document_kind"] == "annual_report"
    assert diagnostic["fiscal_year"] == 2025
    assert diagnostic["content_sha256"] == SHA
    assert diagnostic["byte_size"] == len(BODY)
    assert diagnostic["provider"] == "sec"
    assert "path" not in json.dumps(diagnostic)


def test_dated_single_match_stays_reused_and_carries_no_count(tmp_path):
    companies = tmp_path / "companies"
    _write(companies / "Acme" / "raw" / "financial_reports" / "annual")
    catalog = SourceCatalog(
        CatalogConfig(
            project_root=tmp_path,
            catalog_dir=tmp_path / ".source_catalog",
            roots=(
                RootSpec("company_raw", companies, "company_raw", priority=10,
                         adapter_id="company_raw_v1", read_only=False,
                         reusable_for_filing=True, canonical_write_target="companies"),
            ),
        )
    )
    try:
        catalog.scan()
        result = SourceResolver(catalog).resolve(_request())
    finally:
        catalog.close()

    assert result.status is ResolutionStatus.REUSED_EQUIVALENT
    assert result.unknown_date_match_count == 0
    assert "unknown_date_match_count" not in result.to_dict()


@pytest.mark.parametrize("code", sorted(UNKNOWN_PUBLISHED_DATE_REASONS | CANDIDATE_EXCLUSION_REASONS))
def test_new_reason_codes_are_registered_in_the_taxonomy(code: str):
    """FC-1301: an emitted code without a registry entry fails closed."""
    from company_wiki.source_catalog.observability import REASONS, STAGES_BY_REASON

    assert code in REASONS, f"unregistered reason code: {code}"
    assert code in STAGES_BY_REASON, f"reason code without a stage: {code}"
