"""Reject impossible UTC calendar values before any owner proof read."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from company_wiki.source_catalog import CatalogConfig, RootSpec, SourceCatalog  # noqa: E402
from company_wiki.source_catalog.public_canonical_browser import (  # noqa: E402
    CanonicalBrowseError, ProofTransportError, PublicCanonicalBrowser, REQUEST_SCHEMA,
)


def request(as_of):
    return {
        "schema_version": REQUEST_SCHEMA,
        "canonical_entity_id": "ENT_00000000-0000-4000-8000-000000000001",
        "listing_id": None, "analysis_subject_id": None, "as_of": as_of,
        "document_kinds": None, "fiscal_years": None, "language": None,
        "limit": 1, "cursor": None, "proof_snapshot_id": None,
    }


@pytest.fixture
def browser(tmp_path):
    class OwnerProbe:
        def read(self, *, entity_id, listing_id, as_of):
            raise ProofTransportError("owner_probe_reached")

    catalog = SourceCatalog(CatalogConfig(
        project_root=tmp_path, catalog_dir=tmp_path / "catalog",
        roots=(RootSpec("fixture", tmp_path, "company_raw"),),
    ))
    try:
        yield PublicCanonicalBrowser(catalog, OwnerProbe())
    finally:
        catalog.close()


@pytest.mark.parametrize("value", [
    "2026-02-30T00:00:00Z",
    "2026-02-29T00:00:00Z",
    "2026-13-01T00:00:00Z",
    "2026-10-30T25:00:00Z",
    "2026-10-30T00:60:00Z",
    "0000-01-01T00:00:00+00:00",
])
def test_invalid_calendar_never_reaches_owner(browser, value):
    with pytest.raises(CanonicalBrowseError, match="invalid_as_of"):
        browser.browse(request(value))


@pytest.mark.parametrize("value", [
    "2024-02-29T00:00:00Z",
    "2026-10-30T23:59:59+00:00",
    "2026-10-30T00:00:00.123456Z",
])
def test_valid_utc_calendar_reaches_owner(browser, value):
    result = browser.browse(request(value))
    assert result["binding"]["reason_codes"] == ["owner_probe_reached"]
