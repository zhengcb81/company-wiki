"""Resolve-check: the lane's ``fixtures`` package must be this lane's copy.

``tests/fixtures`` also exists in this repository and is reachable as a
namespace package, so the lane pins the resolution explicitly instead of
trusting sys.path order.
"""

from __future__ import annotations

from pathlib import Path

import p3_fixtures
import p3_fixtures.sidecar_catalog as sidecar_catalog

LANE_DIR = Path(__file__).resolve().parent


def test_lane_fixtures_resolve_to_this_lane():
    locations = [Path(item).resolve() for item in p3_fixtures.__path__]
    assert LANE_DIR / "p3_fixtures" in locations, locations
    assert Path(sidecar_catalog.__file__).resolve().parent == LANE_DIR / "p3_fixtures"


def test_fixture_builds_a_readable_indexed_source(plain):
    assert plain.ref.byte_size == len(plain.body)
    assert plain.ref.mime_type == "text/plain"
    assert plain.ref.schema_version == "2.0"
    assert plain.manifest["security_id"] == "688012"
    assert plain.manifest["fiscal_year"] == 2026
    assert plain.manifest["fiscal_period"] == "H1"
    assert plain.manifest["period_end"] == "2026-06-30"
    assert plain.manifest["source_url"] == "https://example.invalid/acme-2026.txt"
    assert plain.config_path.is_file()
    assert plain.catalog_dir.is_dir()
