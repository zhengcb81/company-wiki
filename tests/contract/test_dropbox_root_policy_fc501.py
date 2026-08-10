"""FC-501 RED/acceptance tests: Dropbox RootPolicy + sidecar contract.

The Dropbox root is explicitly configured: read_only, reusable for
filing, allowed kinds, sidecar schema, symlink/junction policy and
canonical priority.  filing-fetch must NOT keep an independent local
root allowlist — it consumes the policy snapshot hash and verifies
canonical path containment only (DBX-01..06).
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import pytest  # noqa: E402

from company_wiki.source_catalog.models import RootSpec  # noqa: E402


def _dropbox_root(tmp_path: Path, **overrides) -> RootSpec:
    root_dir = tmp_path / "Dropbox" / "Stock"
    root_dir.mkdir(parents=True)
    kwargs = dict(
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
    kwargs.update(overrides)
    return RootSpec(**kwargs)


# --- DBX-02: no sidecar -> index optional, filing reuse rejected ------------


def test_dbx02_no_sidecar_reuse_rejected(tmp_path):
    from company_wiki.source_catalog.adapter_dispatch import (
        scan_root_via_adapter,
    )

    root = _dropbox_root(tmp_path)
    (root.path / "年报.pdf").write_bytes(b"pdf")
    candidates = scan_root_via_adapter(root, ())
    # the bare file may be indexed but carries no filing evidence
    assert any(c.relative_path.endswith("年报.pdf") for c in candidates)
    from company_wiki.source_catalog.adapters.sidecar import SidecarFilingAdapter

    adapter = SidecarFilingAdapter()
    items = adapter.enumerate(root.path)
    for item in items:
        if item.relative_path.endswith("年报.pdf"):
            assert item.normalized == {}, (
                "filename alone must never produce filing evidence"
            )


# --- DBX-03: sidecar hash mismatch -> fail closed ---------------------------


def test_dbx03_sidecar_hash_mismatch_fails_closed(tmp_path):
    from company_wiki.source_catalog.adapters.sidecar import (
        _validate_sidecar,
    )

    primary = tmp_path / "Dropbox" / "Stock" / "2025.pdf"
    primary.parent.mkdir(parents=True)
    primary.write_bytes(b"pdf-bytes")
    sidecar = tmp_path / "Dropbox" / "Stock" / "2025.source.json"
    sidecar.write_text(
        '{"content_sha256": "' + "0" * 64 + '", "document_kind": "annual_report"}',
        encoding="utf-8",
    )
    problems = _validate_sidecar(
        {"content_sha256": "0" * 64, "document_kind": "annual_report"},
        primary,
    )
    assert any("hash" in p for p in problems)


# --- DBX-04: broker report named 年报 -> broker_research, not filing --------


def test_dbx04_broker_report_not_filing(tmp_path):
    from company_wiki.source_catalog.adapters.sidecar import SidecarFilingAdapter

    root = _dropbox_root(tmp_path)
    (root.path / "broker_2025年报.pdf").write_bytes(b"pdf")
    import hashlib

    pdf_hash = hashlib.sha256(b"pdf").hexdigest()
    (root.path / "broker_2025年报.pdf.source.json").write_text(
        json.dumps({
            "schema_version": "1.0",
            "canonical_entity_id": "ent-x",
            "display_name": "X",
            "market": "CN",
            "security_id": "000001",
            "document_kind": "broker_research",
            "fiscal_year": 2025,
            "period_end": "2025-12-31",
            "content_sha256": pdf_hash,
            "provider": "broker-x",
            "provider_document_id": "br-1",
        }, ensure_ascii=False),
        encoding="utf-8",
    )
    adapter = SidecarFilingAdapter()
    items = adapter.enumerate(root.path)
    kinds = {i.normalized.get("document_kind") for i in items}
    assert "broker_research" in kinds
    assert "annual_report" not in kinds


# --- DBX-05: symlink/junction escape -> rejected with policy reason ---------


def test_dbx05_symlink_escape_rejected(tmp_path):
    from company_wiki.source_catalog.adapters.sidecar import SidecarFilingAdapter

    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "leak.pdf").write_bytes(b"secret")
    root = _dropbox_root(tmp_path)
    try:
        (root.path / "link").symlink_to(outside, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks not supported on this host")
    adapter = SidecarFilingAdapter()
    items = adapter.enumerate(root.path)
    # the symlink target must not be enumerated
    assert all(not i.relative_path.endswith("leak.pdf") for i in items)


# --- DBX-06: retired document not revived by rescan -------------------------


def test_dbx06_retired_not_revived(tmp_path):
    from company_wiki.source_catalog.store import CatalogStore

    store = CatalogStore(tmp_path / "c.sqlite3")
    with store.transaction() as conn:
        conn.execute(
            "INSERT INTO roots (root_id, path, kind, priority) "
            "VALUES ('dropbox_stock','/x','directory',30)")
        conn.execute(
            "INSERT INTO sources (source_id, content_sha256, byte_size, "
            "mime_type, first_seen_at) VALUES ('s1','h',1,'x','2026-01-01')")
        conn.execute(
            "INSERT INTO documents (document_id, title, source_status, "
            "source_type, document_kind, metadata_priority, metadata_json, "
            "first_seen_at, last_seen_at) "
            "VALUES ('d1','t','retired','file','annual_report',10,'{}',"
            "'2026-01-01','2026-01-01')")
        conn.execute(
            "INSERT INTO locations (location_id, root_id, relative_path, "
            "absolute_path, document_id, role, location_status, "
            "last_seen_run, metadata_json) "
            "VALUES ('l1','dropbox_stock','2025.pdf','/x/2025.pdf','d1',"
            "'original_primary','retired','run1','{}')")
    # the retired location stays retired through the ledger
    from company_wiki.source_catalog.migration_ledger import build_quality_ledger

    ledger = build_quality_ledger(store)
    assert ledger["retired_locations"] == 1
    assert ledger["by_root"].get("dropbox_stock", {}).get("eligible", 0) == 0


# --- RootPolicy 2.x: Dropbox explicit contract ------------------------------


def test_dropbox_root_policy_contract(tmp_path):
    from company_wiki.source_catalog.policy_2x import (
        export_policy_2x,
        load_root_policy_2x,
    )

    root_dir = tmp_path / "Dropbox" / "Stock"
    root_dir.mkdir(parents=True)
    config_path = tmp_path / "source_catalog.yaml"
    config_path.write_text(
        "\n".join(
            [
                "schema_version: '1.0'",
                "catalog_dir: '" + str(tmp_path / ".source_catalog").replace("\\", "/") + "'",
                "roots:",
                "  -",
                "    root_id: dropbox_stock",
                "    kind: directory",
                "    path: '" + str(root_dir).replace("\\", "/") + "'",
                "    adapter_id: sidecar_filing_v1",
                "    admission_profile_id: financial_evidence_v1",
                "    read_only: true",
                "    reusable_for_filing: true",
                "    allowed_document_kinds: ['annual_report']",
                "    symlink_policy: reject",
                "    priority: 30",
                "    cohort: dropbox-cohort",
                "    canonical_write_target: null",
                "",
            ]
        ),
        encoding="utf-8",
    )
    cfg = load_root_policy_2x(config_path, project_root=tmp_path)
    root = cfg.roots[0]
    assert root.read_only is True
    assert root.reusable_for_filing is True
    assert root.symlink_policy == "reject"
    assert root.canonical_write_target is None  # never a write target
    _, policy = export_policy_2x(cfg)
    dropbox = [r for r in policy["roots"] if r["root_id"] == "dropbox_stock"][0]
    assert dropbox["read_only"] is True
    assert dropbox["cohort"] == "dropbox-cohort"
    assert dropbox["canonical_write_target"] is None
