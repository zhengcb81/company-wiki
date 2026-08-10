"""FC-503 RED/acceptance tests: Dropbox 历史候选治理 (read-only inventory).

The governance inventory walks a Dropbox root through the production
adapter dispatch, classifies every candidate into the FC-402 buckets,
reports missing fields and location sets duplicated into companies, and
keeps 中国平安-style weak-identity samples unprovable.  The inventory
NEVER writes: the report embeds a per-file fingerprint so a second run
proves zero writes, and companies copies are never touched (no deletion
to fabricate Dropbox-only proof).
"""
import hashlib
import json
import sqlite3
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import pytest  # noqa: E402

from company_wiki.source_catalog.models import RootSpec  # noqa: E402


def _dropbox_root(tmp_path: Path) -> RootSpec:
    root_dir = tmp_path / "Dropbox" / "Stock"
    root_dir.mkdir(parents=True)
    return RootSpec(
        root_id="dropbox_stock",
        path=root_dir,
        kind="directory",
        adapter_id="sidecar_filing_v1",
        admission_profile_id="financial_evidence_v1",
        read_only=True,
        reusable_for_filing=True,
        allowed_document_kinds=("annual_report",),
        symlink_policy="reject",
        priority=30,
        cohort="dropbox-cohort",
        canonical_write_target=None,
    )


def _sidecar_for(name: str, body: bytes, **overrides) -> dict:
    payload = {
        "schema_version": "1.0",
        "canonical_entity_id": "ent-moutai",
        "display_name": "贵州茅台",
        "market": "CN",
        "security_id": "600519",
        "document_kind": "annual_report",
        "fiscal_year": 2025,
        "period_end": "2025-12-31",
        "provider": "example-filing",
        "provider_document_id": "acc-2025",
        "source_url": "https://www.example-filing.com/600519/2025",
        "content_sha256": hashlib.sha256(body).hexdigest(),
    }
    payload.update(overrides)
    return payload


def _write_sidecar(root: Path, name: str, body: bytes, **overrides):
    (root / name).write_bytes(body)
    (root / (name + ".source.json")).write_text(
        json.dumps(_sidecar_for(name, body, **overrides), ensure_ascii=False),
        encoding="utf-8",
    )


def _mini_catalog(tmp_path: Path, *rows) -> Path:
    """Minimal read-only catalog fixture (documents/locations/sources)."""
    db = tmp_path / "catalog.sqlite3"
    con = sqlite3.connect(db)
    con.executescript(
        """
        CREATE TABLE documents (
          document_id TEXT PRIMARY KEY, primary_source_id TEXT,
          title TEXT, source_status TEXT);
        CREATE TABLE sources (
          source_id TEXT PRIMARY KEY, content_sha256 TEXT,
          byte_size INTEGER, mime_type TEXT);
        CREATE TABLE locations (
          location_id TEXT PRIMARY KEY, root_id TEXT, relative_path TEXT,
          absolute_path TEXT, source_id TEXT, document_id TEXT,
          role TEXT, location_status TEXT);
        """
    )
    con.executemany(
        "INSERT INTO sources VALUES (?,?,?,?)", rows[0]["sources"]
    )
    con.executemany(
        "INSERT INTO documents VALUES (?,?,?,?)", rows[0]["documents"]
    )
    con.executemany(
        "INSERT INTO locations VALUES (?,?,?,?,?,?,?,?)",
        rows[0]["locations"],
    )
    con.commit()
    con.close()
    return db


# --- eligible filing inventoried --------------------------------------------


def test_fc503_complete_sidecar_inventoried_as_filing(tmp_path):
    """A complete sidecar candidate is inventoried as an eligible filing
    and the report embeds its per-file fingerprint."""
    from company_wiki.source_catalog.dropbox_governance import inventory_dropbox

    root = _dropbox_root(tmp_path)
    body = b"%PDF-1.4 moutai"
    _write_sidecar(root.path, "2025年报.pdf", body)
    report = inventory_dropbox(root)
    assert report["candidates_total"] == 1
    assert report["by_role"]["original_primary"] == 1
    assert report["buckets"]["eligible"] == 1
    assert report["pingan"]["eligible"] == 0
    assert report["writes"] == 0
    fp = report["fingerprint"]
    assert "2025年报.pdf" in fp
    assert fp["2025年报.pdf"][2] == hashlib.sha256(body).hexdigest()


# --- 中国平安-style weak identity stays unprovable ---------------------------


def test_fc503_pingan_weak_identity_stays_unprovable(tmp_path):
    """A 中国平安-style display-name security_id never classifies as an
    eligible filing through the full inventory chain."""
    from company_wiki.source_catalog.dropbox_governance import inventory_dropbox

    root = _dropbox_root(tmp_path)
    pingan = root.path / "金融" / "保险" / "中国平安"
    pingan.mkdir(parents=True)
    body = b"%PDF-1.4 pingan"
    _write_sidecar(
        pingan, "中国平安：2017年年度报告.pdf", body,
        display_name="中国平安", security_id="中国平安",
        canonical_entity_id="中国平安",
    )
    report = inventory_dropbox(root)
    assert report["pingan"]["path_candidates"] == 1
    assert report["pingan"]["unprovable"] == 1
    assert report["pingan"]["eligible"] == 0
    assert report["buckets"]["unprovable"] == 1
    assert report["buckets"]["eligible"] == 0
    assert "security_id" in report["missing_fields"]


def test_fc503_filename_hint_never_upgrades_pingan(tmp_path):
    """A 601318 filename hint must never supply the identity: a sidecar
    complete except security_id stays unprovable — the inventory never
    guesses identity from the name."""
    from company_wiki.source_catalog.dropbox_governance import inventory_dropbox

    root = _dropbox_root(tmp_path)
    pingan = root.path / "金融" / "保险" / "中国平安"
    pingan.mkdir(parents=True)
    body = b"%PDF-1.4 pingan"
    _write_sidecar(
        pingan, "20190429-长江证券-中国平安-601318-深度报告：解密高ROE.pdf",
        body, security_id=None,
    )
    report = inventory_dropbox(root)
    assert report["pingan"]["path_candidates"] == 1
    assert report["pingan"]["unprovable"] == 1
    assert report["pingan"]["eligible"] == 0
    assert report["buckets"]["unprovable"] == 1
    # the strong-looking ticker never made it capture-ready
    assert "601318" not in json.dumps(report["missing_fields"])


def test_fc503_pingan_guard_blocks_unreviewed_promotion(tmp_path):
    """A 中国平安-path candidate must not become eligible from on-disk
    sidecar evidence alone — eligibility requires reviewer-completed
    evidence (FC-403 remediation), so the inventory fails closed."""
    from company_wiki.source_catalog.dropbox_governance import (
        GovernanceError,
        inventory_dropbox,
    )

    root = _dropbox_root(tmp_path)
    pingan = root.path / "金融" / "保险" / "中国平安"
    pingan.mkdir(parents=True)
    body = b"%PDF-1.4 pingan"
    # complete-looking sidecar (strong ticker + all fields) on a
    # 中国平安-path candidate — unreviewed evidence must NOT promote it
    _write_sidecar(
        pingan, "20190429-中国平安-601318-深度报告.pdf", body,
        display_name="中国平安", security_id="601318",
        canonical_entity_id="中国平安",
    )
    with pytest.raises(GovernanceError):
        inventory_dropbox(root)


# --- missing fields reported per bucket -------------------------------------


def test_fc503_missing_fields_reported_per_bucket(tmp_path):
    """No-sidecar files are unprovable with missing fields; a sidecar
    missing only the period is needs_review."""
    from company_wiki.source_catalog.dropbox_governance import inventory_dropbox

    root = _dropbox_root(tmp_path)
    body = b"%PDF-1.4 moutai"
    _write_sidecar(root.path, "2025年报.pdf", body, period_end=None)
    (root.path / "研究.pdf").write_bytes(b"%PDF-1.4 research")  # no sidecar
    report = inventory_dropbox(root)
    assert report["candidates_total"] == 2
    assert report["buckets"]["needs_review"] == 1
    assert report["buckets"]["unprovable"] == 1
    assert report["missing_fields"]["period_end"] == 1
    assert report["missing_fields"]["security_id"] >= 1


# --- duplicate location sets into companies: reported, never deleted ---------


def test_fc503_duplicate_location_sets_reported_no_delete(tmp_path):
    """A Dropbox candidate whose ACTUAL bytes also live in company_raw is
    reported as a duplicate location set (even when the sidecar declares a
    bogus hash — the on-disk bytes are the ground truth); the companies
    copy and the catalog are untouched (no deletion to fabricate
    exclusive-source proof)."""
    from company_wiki.source_catalog.dropbox_governance import inventory_dropbox

    root = _dropbox_root(tmp_path)
    body = b"%PDF-1.4 dup"
    digest = hashlib.sha256(body).hexdigest()
    # the sidecar declares a WRONG content hash — governance must still
    # match the duplicate by the actual file bytes
    _write_sidecar(root.path, "dup2025.pdf", body,
                   content_sha256="b" * 64)
    companies = tmp_path / "companies"
    companies.mkdir(parents=True)
    company_copy = companies / "dup2025.pdf"
    company_copy.write_bytes(body)
    time.sleep(0.05)
    before_copy = (company_copy.stat().st_size, company_copy.stat().st_mtime_ns)

    catalog = _mini_catalog(
        tmp_path,
        {
            "sources": [("s-dropbox", digest, len(body), "application/pdf"),
                        ("s-companies", digest, len(body), "application/pdf")],
            "documents": [("d-dropbox", "s-dropbox", "dup2025", "active"),
                          ("d-companies", "s-companies", "dup2025", "active")],
            "locations": [
                ("l-dropbox", "dropbox_stock", "dup2025.pdf", "x",
                 "s-dropbox", "d-dropbox", "original_primary", "active"),
                ("l-companies", "company_raw", "dup2025.pdf", "x",
                 "s-companies", "d-companies", "original_primary", "active"),
            ],
        },
    )
    counts_before = _catalog_counts(catalog)
    report = inventory_dropbox(root, catalog=catalog,
                              other_root_ids=("company_raw",))
    assert report["duplicate_location_sets"]["count"] == 1
    assert report["duplicate_location_sets"]["samples"][0]["root_ids"] == ["company_raw"]
    # catalog unchanged (read-only) and the companies copy still intact
    assert _catalog_counts(catalog) == counts_before
    after_copy = (company_copy.stat().st_size, company_copy.stat().st_mtime_ns)
    assert after_copy == before_copy
    assert company_copy.read_bytes() == body


def _catalog_counts(db: Path) -> tuple:
    con = sqlite3.connect(db)
    counts = tuple(
        con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        for t in ("documents", "sources", "locations")
    )
    con.close()
    return counts


# --- read-only and deterministic --------------------------------------------


def test_fc503_inventory_read_only_and_deterministic(tmp_path):
    """Two inventory runs produce identical reports and leave every real
    file (bytes and mtime) untouched."""
    from company_wiki.source_catalog.dropbox_governance import inventory_dropbox

    root = _dropbox_root(tmp_path)
    body = b"%PDF-1.4 moutai"
    _write_sidecar(root.path, "2025年报.pdf", body)
    (root.path / "研究.pdf").write_bytes(b"%PDF-1.4 research")
    time.sleep(0.05)
    files_before = {
        p.name: (p.stat().st_size, p.stat().st_mtime_ns)
        for p in root.path.iterdir()
    }
    first = inventory_dropbox(root)
    second = inventory_dropbox(root)
    assert first["fingerprint"] == second["fingerprint"]
    assert first["buckets"] == second["buckets"]
    assert first["missing_fields"] == second["missing_fields"]
    files_after = {
        p.name: (p.stat().st_size, p.stat().st_mtime_ns)
        for p in root.path.iterdir()
    }
    assert files_after == files_before
    assert first["writes"] == 0
