"""W22: the real projection store keeps working through the shared writer.

persist_projection is the consumer ROOT's W21 reception actually failed in:
its destination basename is a 64-character SHA-256 plus suffix, and the legacy
staging name duplicated that basename. The round trip here drives the real
store entry (canonical payload, hash identity, atomic sealed write, load back)
rather than calling the shared helper directly. A second test sizes the
catalog directory so the legacy staging shape for the projection destination
would cross the native Windows path limit while the destination itself stays
inside it; hosts whose temp layout cannot fit that boundary skip honestly.
"""
import json
from types import SimpleNamespace

import pytest

from company_wiki.source_catalog.official_json_projection import (
    PROJECTION_ID_PREFIX, PROJECTION_SCHEMA_VERSION, SourceProjection,
    load_projection, persist_projection)

NATIVE_LIMIT = 259
LEGACY_STAGE_OVERHEAD = 1 + 8 + 4


def _self_consistent_projection() -> SourceProjection:
    from company_wiki.source_catalog.official_json_projection import _payload_sha256
    from company_wiki.source_catalog.official_json_structure import (
        CWP_JSON_STRUCTURE_PARSER_VERSION)

    draft = SourceProjection(
        schema_version=PROJECTION_SCHEMA_VERSION,
        projection_id="pending",
        projection_sha256="0" * 64,
        parent_source_refs=(),
        adapter={"parser": "cwp_official_json/1.0.1",
                 "structure_parser_version": CWP_JSON_STRUCTURE_PARSER_VERSION},
        issuer={"name": "w22 integration fixture"},
        as_of_date="2026-10-30",
        records=(),
        coverage={},
    )
    sha = _payload_sha256(draft)
    return SourceProjection(
        schema_version=draft.schema_version,
        projection_id=PROJECTION_ID_PREFIX + sha,
        projection_sha256=sha,
        parent_source_refs=(), adapter=draft.adapter, issuer=draft.issuer,
        as_of_date=draft.as_of_date, records=(), coverage={},
    )


def test_persist_projection_roundtrip_through_shared_writer(tmp_path):
    catalog = SimpleNamespace(
        config=SimpleNamespace(catalog_dir=str(tmp_path / "catalog")))
    projection = _self_consistent_projection()
    projection_id = persist_projection(catalog, projection)
    assert projection_id == PROJECTION_ID_PREFIX + projection.projection_sha256
    restored = load_projection(catalog, projection_id)
    assert restored.projection_sha256 == projection.projection_sha256
    assert restored.issuer == {"name": "w22 integration fixture"}
    # The store stays idempotent: the sealed file is reused, not rewritten.
    assert persist_projection(catalog, projection) == projection_id
    store = tmp_path / "catalog" / "projections"
    assert [item.name for item in store.iterdir()] == [
        projection.projection_sha256 + ".json"]


def test_persist_projection_target_valid_while_legacy_stage_would_break(
        tmp_path):
    # Catalog directory sized so the projection destination stays inside the
    # native limit while the legacy "<sha256>.json.<8rand>.tmp" staging name
    # would cross it: total characters land exactly on 247.
    padding = NATIVE_LIMIT - LEGACY_STAGE_OVERHEAD + 1 - (
        len(str(tmp_path)) + len("/projections/") + len("x" * 64 + ".json"))
    if padding < 1:
        pytest.skip("host pytest temp too deep to fit the legacy boundary")
    catalog_dir = tmp_path / ("c" * padding)
    catalog = SimpleNamespace(config=SimpleNamespace(catalog_dir=str(catalog_dir)))
    projection = _self_consistent_projection()
    destination = catalog_dir / "projections" / (projection.projection_sha256 + ".json")
    assert len(str(destination)) <= NATIVE_LIMIT
    assert len(str(destination)) + LEGACY_STAGE_OVERHEAD > NATIVE_LIMIT
    projection_id = persist_projection(catalog, projection)
    assert projection_id == PROJECTION_ID_PREFIX + projection.projection_sha256
    payload = json.loads(destination.read_text(encoding="utf-8"))
    assert payload["projection_id"] == projection_id
    assert payload["projection_sha256"] == projection.projection_sha256


def test_source_catalog_atomic_write_survives_legacy_boundary(tmp_path):
    # The other production entry (SourceCatalog index/CSV writer) on the same
    # boundary: destination valid at 247 characters, the legacy staging shape
    # for it would cross the limit by exactly one character, and the bounded
    # 20-character stage name fits with one character to spare.
    padding = NATIVE_LIMIT - LEGACY_STAGE_OVERHEAD - (
        len(str(tmp_path)) + 1 + len("index.md"))
    if padding < 1:
        pytest.skip("host pytest temp too deep to fit the legacy boundary")
    from company_wiki.source_catalog.service import SourceCatalog

    parent = tmp_path / ("c" * padding)
    parent.mkdir()
    destination = parent / "index.md"
    assert len(str(destination)) <= NATIVE_LIMIT
    assert len(str(destination)) + LEGACY_STAGE_OVERHEAD > NATIVE_LIMIT
    SourceCatalog._atomic_write(destination, "# sealed index\n")
    assert destination.read_text(encoding="utf-8") == "# sealed index\n"
    assert list(parent.iterdir()) == [destination]
