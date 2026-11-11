"""Cross-process contract for the company-level source index.

The index is the only company-wide listing the StockWiki default research
entrypoints may consume.  This suite freezes the wire, the deterministic
order/pagination, the as-of semantics, the identity/availability mapping and
the owner's duplicate-copy version semantics.  It uses two isolated physical
roots and never reads or copies production material.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from company_wiki.source_catalog import CatalogConfig, RootSpec, SourceCatalog  # noqa: E402
from company_wiki.source_catalog.store import retire_document  # noqa: E402


WIRE_FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "company_source_index" / "wire_v1.json"
CLI_MODULE = "company_wiki.source_catalog.company_source_index_cli"

AMEC_ENTITY = "ent-amec"
AMEC_NAME = "AMEC"
# Identity requests use the supported market-family vocabulary (CN/HK/US);
# the listing venue remains encoded in the security identifier suffix.
AMEC_MARKET = "CN"
AMEC_SECURITY = "688012.SH"

OTHER_ENTITY = "ent-other"
OTHER_NAME = "Other Works"
OTHER_MARKET = "CN"
OTHER_SECURITY = "600000.SH"


def _body(label: str) -> bytes:
    return f"# {label}\nrevenue and margin disclosure for {label}\n".encode("utf-8")


def _sidecar(
    *, entity: str, display: str, market: str, security_id: str,
    kind: str, fiscal_year: int, fiscal_period: str, period_end: str,
    published: str, body: bytes, provider_doc: str,
) -> dict:
    return {
        "schema_version": "1.0",
        "ingest_complete": True,
        "canonical_entity_id": entity,
        "display_name": display,
        "company_name": display,
        "market": market,
        "security_id": security_id,
        "document_kind": kind,
        "fiscal_year": fiscal_year,
        "fiscal_period": fiscal_period,
        "period_end": period_end,
        "filing_date": published,
        "language": "zh",
        "form_type": "annual" if kind == "annual_report" else "",
        "content_sha256": hashlib.sha256(body).hexdigest(),
        "source_url": f"https://example.invalid/{provider_doc}",
        "provider": "fixture",
        "provider_document_id": provider_doc,
        "retrieved_at": "2026-06-01T00:00:00Z",
        "collector_name": "fixture",
        "collector_version": "1.0",
    }


def _write(
    root: Path, name: str, body: bytes, sidecar: dict,
) -> None:
    (root / name).write_bytes(body)
    (root / (name + ".source.json")).write_text(
        json.dumps(sidecar, ensure_ascii=False), encoding="utf-8"
    )


def _roots(tmp_path: Path) -> tuple[Path, Path]:
    root_a = tmp_path / "lake_a" / "amec"
    root_b = tmp_path / "lake_b" / "mirror"
    root_a.mkdir(parents=True)
    root_b.mkdir(parents=True)
    annual = _body("amec annual 2025")
    _write(root_a, "2026-03-20_annual.md", annual, _sidecar(
        entity=AMEC_ENTITY, display=AMEC_NAME, market=AMEC_MARKET,
        security_id=AMEC_SECURITY, kind="annual_report", fiscal_year=2025,
        fiscal_period="FY", period_end="2025-12-31", published="2026-03-20",
        body=annual, provider_doc="amec-annual-2025",
    ))
    # Owner duplicate semantics: identical bytes in a second root are one
    # source version with two physical copies, not two sources.
    _write(root_b, "copy_2026-03-20_annual.md", annual, _sidecar(
        entity=AMEC_ENTITY, display=AMEC_NAME, market=AMEC_MARKET,
        security_id=AMEC_SECURITY, kind="annual_report", fiscal_year=2025,
        fiscal_period="FY", period_end="2025-12-31", published="2026-03-20",
        body=annual, provider_doc="amec-annual-2025",
    ))
    q1 = _body("amec q1 2026")
    _write(root_a, "2026-04-28_q1.md", q1, _sidecar(
        entity=AMEC_ENTITY, display=AMEC_NAME, market=AMEC_MARKET,
        security_id=AMEC_SECURITY, kind="quarterly_report", fiscal_year=2026,
        fiscal_period="Q1", period_end="2026-03-31", published="2026-04-28",
        body=q1, provider_doc="amec-q1-2026",
    ))
    research = _body("amec broker research")
    _write(root_b, "2026-05-10_research.md", research, _sidecar(
        entity=AMEC_ENTITY, display=AMEC_NAME, market=AMEC_MARKET,
        security_id=AMEC_SECURITY, kind="broker_research", fiscal_year=2026,
        fiscal_period="", period_end="2026-05-10", published="2026-05-10",
        body=research, provider_doc="amec-research-1",
    ))
    h1 = _body("amec h1 2025")
    _write(root_b, "2025-08-30_h1.md", h1, _sidecar(
        entity=AMEC_ENTITY, display=AMEC_NAME, market=AMEC_MARKET,
        security_id=AMEC_SECURITY, kind="semi_annual_report", fiscal_year=2025,
        fiscal_period="H1", period_end="2025-06-30", published="2025-08-30",
        body=h1, provider_doc="amec-h1-2025",
    ))
    other = _body("other works annual")
    _write(root_a, "2026-03-25_other_annual.md", other, _sidecar(
        entity=OTHER_ENTITY, display=OTHER_NAME, market=OTHER_MARKET,
        security_id=OTHER_SECURITY, kind="annual_report", fiscal_year=2025,
        fiscal_period="FY", period_end="2025-12-31", published="2026-03-25",
        body=other, provider_doc="other-annual-2025",
    ))
    return root_a, root_b


def _config(
    tmp_path: Path, root_a: Path, root_b: Path, *, catalog_dir: Path | None = None,
) -> Path:
    payload = {
        "schema_version": "1.0",
        "catalog_dir": str(catalog_dir or (tmp_path / ".source_catalog")),
        "roots": [
            {
                "root_id": "lake_a", "path": str(root_a), "kind": "directory",
                "priority": 10, "adapter_id": "sidecar_filing_v1",
                "read_only": True, "reusable_for_filing": True,
            },
            {
                "root_id": "lake_b", "path": str(root_b), "kind": "directory",
                "priority": 20, "adapter_id": "sidecar_filing_v1",
                "read_only": True, "reusable_for_filing": True,
            },
        ],
        "reusable_root_kinds": ["directory"],
    }
    config_path = tmp_path / "source_catalog.yaml"
    config_path.write_text(json.dumps(payload), encoding="utf-8")
    return config_path


def _scan(tmp_path: Path, root_a: Path, root_b: Path) -> SourceCatalog:
    catalog = SourceCatalog(CatalogConfig(
        project_root=tmp_path,
        catalog_dir=tmp_path / ".source_catalog",
        roots=(
            RootSpec("lake_a", root_a, "directory", priority=10,
                     adapter_id="sidecar_filing_v1", read_only=True,
                     reusable_for_filing=True),
            RootSpec("lake_b", root_b, "directory", priority=20,
                     adapter_id="sidecar_filing_v1", read_only=True,
                     reusable_for_filing=True),
        ),
        reusable_root_kinds=("directory",),
    ))
    catalog.scan()
    return catalog


def _request(**overrides: object) -> dict:
    payload: dict[str, object] = {
        "schema_version": "company-wiki-company-source-index-request/1",
        "company": {
            "entity": AMEC_NAME,
            "market": AMEC_MARKET,
            "security_id": AMEC_SECURITY,
        },
        "as_of_date": "2026-11-02",
        "document_kinds": [],
        "page_size": 25,
        "cursor": None,
    }
    payload.update(overrides)
    return payload


def _run_cli(
    config_path: Path, request: dict, cwd: Path,
) -> subprocess.CompletedProcess[bytes]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src") + os.pathsep + env.get("PYTHONPATH", "")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        [sys.executable, "-m", CLI_MODULE, "--config", str(config_path)],
        input=json.dumps(request, ensure_ascii=False).encode("utf-8"),
        cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        check=False, timeout=60,
    )


def _ok(config_path: Path, request: dict, cwd: Path) -> dict:
    proc = _run_cli(config_path, request, cwd)
    assert proc.returncode == 0, proc.stderr.decode("utf-8", "replace")
    return json.loads(proc.stdout.decode("utf-8"))


def _walk_pages(config_path: Path, request: dict, cwd: Path) -> tuple[list[dict], list[dict]]:
    pages: list[dict] = []
    collected: list[dict] = []
    cursor = None
    for _ in range(20):
        page = _ok(config_path, {**request, "cursor": cursor}, cwd)
        pages.append(page)
        collected.extend(page["sources"])
        cursor = page["page"]["next_cursor"]
        if not page["page"]["has_more"]:
            assert cursor is None
            break
    else:  # pragma: no cover - guards against a non-terminating cursor
        raise AssertionError("pagination did not terminate")
    return pages, collected


def _fixture(tmp_path: Path) -> tuple[Path, SourceCatalog]:
    root_a, root_b = _roots(tmp_path)
    catalog = _scan(tmp_path, root_a, root_b)
    config_path = _config(tmp_path, root_a, root_b)
    return config_path, catalog


def _no_physical_leak(payload: dict, *physical: Path) -> None:
    text = json.dumps(payload, ensure_ascii=False)
    for path in physical:
        assert str(path) not in text
    for token in ("lake_a", "lake_b", "relative_path", "absolute_path",
                  "root_id", "location_id", "manifest_json"):
        assert token not in text
    for key in _keys(payload):
        lowered = key.lower()
        assert "path" not in lowered
        assert "root" not in lowered
        assert "location" not in lowered


def _keys(value: object) -> set[str]:
    found: set[str] = set()
    if isinstance(value, dict):
        for key, child in value.items():
            found.add(str(key))
            found |= _keys(child)
    elif isinstance(value, list):
        for child in value:
            found |= _keys(child)
    return found


def test_wire_fixture_is_the_frozen_contract():
    frozen = json.loads(WIRE_FIXTURE.read_text(encoding="utf-8"))
    assert frozen["schema_version"] == "company-wiki-company-source-index/1"
    assert frozen["request_schema_version"] == (
        "company-wiki-company-source-index-request/1"
    )
    assert frozen["ordering"] == ["published_date:desc", "document_id:asc"]
    assert set(frozen["statuses"]) == {
        "ok", "not_found", "ambiguous", "unavailable", "blocked",
    }
    assert set(frozen["availability_values"]) == {
        "available", "unreadable", "retired",
    }


def test_company_index_enumerates_every_kind_across_two_roots(tmp_path: Path):
    config_path, catalog = _fixture(tmp_path)
    root_a = tmp_path / "lake_a" / "amec"
    root_b = tmp_path / "lake_b" / "mirror"
    try:
        frozen = json.loads(WIRE_FIXTURE.read_text(encoding="utf-8"))
        result = _ok(config_path, _request(), tmp_path)
        assert result["status"] == "ok"
        assert result["reason"] == ""
        assert set(result) == set(frozen["response_fields"])
        assert set(result["page"]) == set(frozen["page_fields"])
        assert set(result["company"]) == set(frozen["company_fields"])
        for entry in result["sources"]:
            assert set(entry) == set(frozen["source_fields"])
            assert set(entry["source_ref"]) == set(frozen["source_ref_fields"])
        # Diagnostics never become company source facts: the response has no
        # extension channel, so adding one breaks this assertion on purpose.
        assert not {"extensions", "diagnostics", "warnings", "notes"} & set(result)
        _no_physical_leak(result, root_a, root_b, tmp_path)

        kinds = sorted(entry["document_kind"] for entry in result["sources"])
        assert kinds == [
            "annual_report", "broker_research", "quarterly_report",
            "semi_annual_report",
        ]
        # Newest first, document_id ascending inside one publication date.
        published = [entry["published_date"] for entry in result["sources"]]
        assert published == sorted(published, reverse=True)

        annual = next(
            entry for entry in result["sources"]
            if entry["document_kind"] == "annual_report"
        )
        assert annual["copies"] == 2
        assert annual["availability"] == "available"
        assert annual["market"] == AMEC_MARKET
        assert annual["security_id"] == AMEC_SECURITY
        assert annual["fiscal_year"] == 2025
        assert annual["fiscal_period"] == "FY"
        assert annual["language"] == "zh"
        assert len(annual["source_ref"]["content_sha256"]) == 64
        assert annual["source_ref"]["mime_type"] == "text/markdown"
        assert annual["source_ref"]["byte_size"] > 0
        assert annual["source_ref"]["schema_version"] == "2.0"

        # The other issuer in the same root is never listed.
        assert all(entry["security_id"] == AMEC_SECURITY for entry in result["sources"])
    finally:
        catalog.close()


def test_paged_concatenation_equals_unpaged_set(tmp_path: Path):
    config_path, catalog = _fixture(tmp_path)
    try:
        unpaged = _ok(config_path, _request(), tmp_path)
        pages, collected = _walk_pages(config_path, _request(page_size=1), tmp_path)
        assert [len(page["sources"]) for page in pages] == [1, 1, 1, 1]
        assert [page["page"]["has_more"] for page in pages] == [True, True, True, False]
        assert collected == unpaged["sources"]
        # A page cursor is opaque and never a physical coordinate.
        for page in pages[:-1]:
            assert isinstance(page["page"]["next_cursor"], str)
            assert page["page"]["next_cursor"]
            _no_physical_leak({"cursor": page["page"]["next_cursor"]})
    finally:
        catalog.close()


def test_as_of_and_document_kind_filters_are_explicit(tmp_path: Path):
    config_path, catalog = _fixture(tmp_path)
    try:
        early = _ok(config_path, _request(as_of_date="2026-03-31"), tmp_path)
        assert [entry["document_kind"] for entry in early["sources"]] == [
            "annual_report", "semi_annual_report",
        ]
        only_q = _ok(
            config_path, _request(document_kinds=["quarterly_report"]), tmp_path,
        )
        assert [entry["document_kind"] for entry in only_q["sources"]] == [
            "quarterly_report",
        ]
        none_yet = _ok(
            config_path, _request(document_kinds=["prospectus"]), tmp_path,
        )
        assert none_yet["status"] == "ok"
        assert none_yet["sources"] == []
        assert none_yet["page"]["has_more"] is False
    finally:
        catalog.close()


def test_root_migration_keeps_logical_identity(tmp_path: Path):
    config_path, catalog = _fixture(tmp_path)
    try:
        before = _ok(config_path, _request(), tmp_path)
        annual_before = next(
            entry for entry in before["sources"]
            if entry["document_kind"] == "annual_report"
        )
    finally:
        catalog.close()

    moved = tmp_path / "relocated" / "amec_lake"
    moved.parent.mkdir(parents=True)
    shutil.copytree(tmp_path / "lake_a" / "amec", moved)
    mirror = tmp_path / "relocated" / "mirror_lake"
    shutil.copytree(tmp_path / "lake_b" / "mirror", mirror)
    catalog_dir = tmp_path / "catalog_moved"
    moved_config = _config(
        tmp_path, moved, mirror, catalog_dir=catalog_dir,
    )
    # A fresh catalog: same root ids and relative paths, different physical roots.
    catalog2 = SourceCatalog(CatalogConfig(
        project_root=tmp_path, catalog_dir=catalog_dir,
        roots=(
            RootSpec("lake_a", moved, "directory", priority=10,
                     adapter_id="sidecar_filing_v1", read_only=True,
                     reusable_for_filing=True),
            RootSpec("lake_b", mirror, "directory", priority=20,
                     adapter_id="sidecar_filing_v1", read_only=True,
                     reusable_for_filing=True),
        ),
        reusable_root_kinds=("directory",),
    ))
    catalog2.scan()
    try:
        after = _ok(moved_config, _request(), tmp_path)
        annual_after = next(
            entry for entry in after["sources"]
            if entry["document_kind"] == "annual_report"
        )
        assert annual_after["source_ref"] == annual_before["source_ref"]
        assert annual_after["copies"] == annual_before["copies"] == 2
        assert [entry["source_ref"] for entry in after["sources"]] == [
            entry["source_ref"] for entry in before["sources"]
        ]
        _no_physical_leak(after, moved, mirror)
    finally:
        catalog2.close()


def test_same_path_new_bytes_is_a_new_source_version(tmp_path: Path):
    root_a, root_b = _roots(tmp_path)
    catalog = _scan(tmp_path, root_a, root_b)
    config_path = _config(tmp_path, root_a, root_b)
    try:
        before = _ok(config_path, _request(), tmp_path)
        annual_before = next(
            entry for entry in before["sources"]
            if entry["document_kind"] == "annual_report"
        )
    finally:
        catalog.close()

    replacement = _body("amec annual 2025 restated")
    for root, name in (
        (root_a, "2026-03-20_annual.md"),
        (root_b, "copy_2026-03-20_annual.md"),
    ):
        _write(root, name, replacement, _sidecar(
            entity=AMEC_ENTITY, display=AMEC_NAME, market=AMEC_MARKET,
            security_id=AMEC_SECURITY, kind="annual_report", fiscal_year=2025,
            fiscal_period="FY", period_end="2025-12-31", published="2026-03-20",
            body=replacement, provider_doc="amec-annual-2025-restated",
        ))
    catalog2 = _scan(tmp_path, root_a, root_b)
    try:
        after = _ok(config_path, _request(), tmp_path)
        annual = [
            entry for entry in after["sources"]
            if entry["document_kind"] == "annual_report"
        ]
        available = [entry for entry in annual if entry["availability"] == "available"]
        assert len(available) == 1, "exactly one live version carries the new bytes"
        annual_after = available[0]
        assert (
            annual_after["source_ref"]["content_sha256"]
            != annual_before["source_ref"]["content_sha256"]
        )
        assert (
            annual_after["source_ref"]["source_id"]
            != annual_before["source_ref"]["source_id"]
        )
        assert annual_after["source_ref"] != annual_before["source_ref"]
        assert annual_after["copies"] == 2
        # A replaced version may stay indexed as history, but it may never
        # claim to be readable.
        assert all(
            entry["availability"] != "available"
            for entry in annual if entry is not annual_after
        )
    finally:
        catalog2.close()


def test_undated_version_is_listed_last_instead_of_dropped(tmp_path: Path):
    """An unknown publication date is missing information, not a future date."""
    root_a, root_b = _roots(tmp_path)
    undated = _body("amec undated announcement")
    _write(root_a, "announcement.md", undated, _sidecar(
        entity=AMEC_ENTITY, display=AMEC_NAME, market=AMEC_MARKET,
        security_id=AMEC_SECURITY, kind="regulatory_filing", fiscal_year=2026,
        fiscal_period="", period_end="2026-06-30", published="",
        body=undated, provider_doc="amec-announcement",
    ))
    catalog = _scan(tmp_path, root_a, root_b)
    config_path = _config(tmp_path, root_a, root_b)
    try:
        result = _ok(config_path, _request(), tmp_path)
        kinds = [entry["document_kind"] for entry in result["sources"]]
        assert "regulatory_filing" in kinds, "an undated version must still be listed"
        assert result["sources"][-1]["document_kind"] == "regulatory_filing"
        assert result["sources"][-1]["published_date"] is None
        dated = [entry["published_date"] for entry in result["sources"][:-1]]
        assert dated == sorted(dated, reverse=True)
        # Pagination keeps the same total order across the unknown-date boundary.
        pages, collected = _walk_pages(config_path, _request(page_size=2), tmp_path)
        assert collected == result["sources"]
        assert len(pages) == 3
    finally:
        catalog.close()


def test_cursor_survives_the_canonical_copy_moving(tmp_path: Path):
    """Retiring one copy moves the canonical ref; the page must not repeat it."""
    root_a = tmp_path / "lake_a"
    root_b = tmp_path / "lake_b"
    root_a.mkdir()
    root_b.mkdir()
    duplicate = _body("amec duplicated notice")
    for root, name in ((root_a, "2026-05-10_notice.md"),
                       (root_b, "copy_2026-05-10_notice.md")):
        _write(root, name, duplicate, _sidecar(
            entity=AMEC_ENTITY, display=AMEC_NAME, market=AMEC_MARKET,
            security_id=AMEC_SECURITY, kind="regulatory_filing", fiscal_year=2026,
            fiscal_period="", period_end="2026-05-10", published="2026-05-10",
            body=duplicate, provider_doc="amec-notice",
        ))
    older = _body("amec older notice")
    _write(root_a, "2026-04-01_notice.md", older, _sidecar(
        entity=AMEC_ENTITY, display=AMEC_NAME, market=AMEC_MARKET,
        security_id=AMEC_SECURITY, kind="regulatory_filing", fiscal_year=2026,
        fiscal_period="", period_end="2026-04-01", published="2026-04-01",
        body=older, provider_doc="amec-notice-older",
    ))
    catalog = _scan(tmp_path, root_a, root_b)
    config_path = _config(tmp_path, root_a, root_b)
    try:
        first = _ok(config_path, _request(page_size=1), tmp_path)
        assert first["page"]["has_more"] is True
        cursor = first["page"]["next_cursor"]
        delivered = first["sources"][0]
        assert delivered["copies"] == 2
        canonical = delivered["source_ref"]["document_id"]
        # Drop the copy that was chosen as canonical: the other copy of the
        # same bytes becomes canonical, so the cursor's document_id disappears.
        retire_document(
            catalog.store, document_id=canonical,
            reason="fixture copy withdrawn", created_by="contract-test",
        )
        catalog.close()

        second = _ok(config_path, _request(page_size=1, cursor=cursor), tmp_path)
        assert second["status"] == "ok"
        assert second["sources"], "a moved canonical copy must not empty the page"
        assert (
            second["sources"][0]["source_ref"]["source_id"]
            != delivered["source_ref"]["source_id"]
        ), "an already delivered version must not repeat"
        assert second["page"]["has_more"] is False
    finally:
        pass


def test_unknown_company_is_not_found_not_an_empty_page(tmp_path: Path):
    config_path, catalog = _fixture(tmp_path)
    try:
        result = _ok(
            config_path,
            _request(company={"entity": "No Such Issuer", "market": None,
                              "security_id": None}),
            tmp_path,
        )
        assert result["status"] == "not_found"
        assert result["reason"] == "company_not_indexed"
        assert result["sources"] == []
        assert result["page"]["has_more"] is False
        assert result["page"]["next_cursor"] is None
    finally:
        catalog.close()


def test_identity_ambiguity_is_reported_when_market_is_missing(tmp_path: Path):
    root_a, root_b = _roots(tmp_path)
    twin = _body("amec h-share listing notice")
    _write(root_a, "2026-02-01_hk_notice.md", twin, _sidecar(
        entity="ent-amec-hk", display=AMEC_NAME, market="HKEX",
        security_id="0688.HK", kind="regulatory_filing", fiscal_year=2026,
        fiscal_period="", period_end="2026-02-01", published="2026-02-01",
        body=twin, provider_doc="amec-hk-1",
    ))
    catalog = _scan(tmp_path, root_a, root_b)
    config_path = _config(tmp_path, root_a, root_b)
    try:
        ambiguous = _ok(
            config_path,
            _request(company={"entity": AMEC_NAME, "market": None,
                              "security_id": None}),
            tmp_path,
        )
        assert ambiguous["status"] == "ambiguous"
        assert ambiguous["reason"] == "company_identity_ambiguous"
        assert ambiguous["sources"] == []

        narrowed = _ok(config_path, _request(), tmp_path)
        assert narrowed["status"] == "ok"
        assert all(
            entry["security_id"] == AMEC_SECURITY for entry in narrowed["sources"]
        )
    finally:
        catalog.close()


def test_retired_and_missing_originals_are_reported_not_dropped(tmp_path: Path):
    config_path, catalog = _fixture(tmp_path)
    try:
        listed = _ok(config_path, _request(), tmp_path)
        research = next(
            entry for entry in listed["sources"]
            if entry["document_kind"] == "broker_research"
        )
        retire_document(
            catalog.store, document_id=research["source_ref"]["document_id"],
            reason="fixture withdrawal", created_by="contract-test",
        )
        catalog.close()

        catalog2 = SourceCatalog(CatalogConfig(
            project_root=tmp_path, catalog_dir=tmp_path / ".source_catalog",
            roots=(
                RootSpec("lake_a", tmp_path / "lake_a" / "amec", "directory",
                         priority=10, adapter_id="sidecar_filing_v1",
                         read_only=True, reusable_for_filing=True),
                RootSpec("lake_b", tmp_path / "lake_b" / "mirror", "directory",
                         priority=20, adapter_id="sidecar_filing_v1",
                         read_only=True, reusable_for_filing=True),
            ),
            reusable_root_kinds=("directory",),
        ))
        after = _ok(config_path, _request(), tmp_path)
        retired = next(
            entry for entry in after["sources"]
            if entry["source_ref"]["source_id"] == research["source_ref"]["source_id"]
        )
        assert retired["availability"] == "retired"
        assert after["status"] == "ok"

        # Remove the physical bytes of the quarterly filing without touching
        # the catalog: the entry stays listed but is honestly unreadable.
        (tmp_path / "lake_a" / "amec" / "2026-04-28_q1.md").unlink()
        unreadable = _ok(config_path, _request(), tmp_path)
        q1 = next(
            entry for entry in unreadable["sources"]
            if entry["document_kind"] == "quarterly_report"
        )
        assert q1["availability"] == "unreadable"
        catalog2.close()
    finally:
        pass


@pytest.mark.parametrize(
    "request_payload",
    [
        {"schema_version": "company-wiki-company-source-index-request/9"},
        {"company": {"entity": "", "market": None, "security_id": None}},
        {"page_size": 0},
        {"page_size": 101},
        {"page_size": True},
        {"as_of_date": "2026-13-01"},
        {"document_kinds": ["annual_report", "annual_report"]},
        {"document_kinds": ["not_a_kind"]},
        {"cursor": "not-a-cursor"},
        {"unexpected": 1},
    ],
)
def test_invalid_requests_are_blocked_without_success_stdout(
    tmp_path: Path, request_payload: dict,
):
    config_path, catalog = _fixture(tmp_path)
    try:
        payload = {**_request(), **request_payload}
        proc = _run_cli(config_path, payload, tmp_path)
        assert proc.returncode == 2
        assert proc.stdout == b""
        diagnostic = json.loads(proc.stderr.decode("utf-8"))
        assert diagnostic["schema_version"] == "company-wiki-company-source-index/1"
        assert diagnostic["status"] == "blocked"
        assert diagnostic["reason"] == "invalid_request"
        assert str(tmp_path) not in proc.stderr.decode("utf-8")
    finally:
        catalog.close()


def test_unavailable_catalog_is_named_not_empty(tmp_path: Path):
    config_path, catalog = _fixture(tmp_path)
    catalog.close()
    (tmp_path / ".source_catalog" / "catalog.sqlite3").unlink()
    proc = _run_cli(config_path, _request(), tmp_path)
    assert proc.returncode == 2
    assert proc.stdout == b""
    diagnostic = json.loads(proc.stderr.decode("utf-8"))
    assert diagnostic["status"] == "unavailable"
    assert diagnostic["reason"] == "catalog_unavailable"


def test_every_listed_ref_is_readable_through_the_public_read_port(tmp_path: Path):
    """The index hands out SourceRefs; the existing reader must open them."""
    config_path, catalog = _fixture(tmp_path)
    try:
        listed = _ok(config_path, _request(), tmp_path)
        entries = [
            entry for entry in listed["sources"]
            if entry["availability"] == "available"
        ]
        assert entries, "the fixture has readable versions"
    finally:
        catalog.close()

    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src") + os.pathsep + env.get("PYTHONPATH", "")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    for entry in entries:
        ref = entry["source_ref"]
        proc = subprocess.run(
            [
                sys.executable, "-m", "company_wiki.source_catalog.source_reader_cli",
                "--config", str(config_path),
                "--document-id", ref["document_id"],
                "--source-id", ref["source_id"],
                "--content-sha256", ref["content_sha256"],
                "--purpose", "source_export",
            ],
            cwd=tmp_path, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            check=False, timeout=60,
        )
        assert proc.returncode == 0, proc.stderr.decode("utf-8", "replace")
        assert len(proc.stdout) == ref["byte_size"]
        assert hashlib.sha256(proc.stdout).hexdigest() == ref["content_sha256"]
        receipt = json.loads(proc.stderr.decode("utf-8").splitlines()[-1])
        assert receipt["status"] == "ok"
        assert receipt["document_id"] == ref["document_id"]
        assert receipt["source_id"] == ref["source_id"]
        assert str(tmp_path) not in proc.stderr.decode("utf-8")
