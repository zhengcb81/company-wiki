"""Reject impossible UTC calendar values before any owner proof read."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from company_wiki.source_catalog.public_canonical_browser import (  # noqa: E402
    CanonicalBrowseError, PublicCanonicalBrowser, REQUEST_SCHEMA,
)


def request(as_of):
    return {
        "schema_version": REQUEST_SCHEMA,
        "canonical_entity_id": "ENT_00000000-0000-4000-8000-000000000001",
        "listing_id": None, "analysis_subject_id": None, "as_of": as_of,
        "document_kinds": None, "fiscal_years": None, "language": None,
        "limit": 1, "cursor": None, "proof_snapshot_id": None,
    }


class OwnerReached(Exception):
    pass


def browser():
    value = object.__new__(PublicCanonicalBrowser)
    def owner(*args):
        raise OwnerReached("calendar validation finished")
    value._resolve_binding = owner
    return value


@pytest.mark.parametrize("value", [
    "2026-02-30T00:00:00Z",
    "2026-02-29T00:00:00Z",
    "2026-13-01T00:00:00Z",
    "2026-10-30T25:00:00Z",
    "2026-10-30T00:60:00Z",
    "0000-01-01T00:00:00+00:00",
])
def test_invalid_calendar_never_reaches_owner(value):
    with pytest.raises(CanonicalBrowseError, match="invalid_as_of"):
        browser().browse(request(value))


@pytest.mark.parametrize("value", [
    "2024-02-29T00:00:00Z",
    "2026-10-30T23:59:59+00:00",
    "2026-10-30T00:00:00.123456Z",
])
def test_valid_utc_calendar_reaches_owner(value):
    with pytest.raises(OwnerReached):
        browser().browse(request(value))
