"""FC-902 RED/acceptance tests: SourceBundle enters the resolver production
response.

``query_source_bundle`` stops being a test/CLI island: the production resolve
path attaches a snapshot-consistent SourceBundle to the ResolutionEnvelope
whenever the resolution reused a document. Core invariants:

- the bundle is built from the SAME document bytes the handle claims
  (expected_content_sha256 fail-closed — a hash drift means NO bundle);
- the envelope keeps the request-pinned policy_hash/activation_epoch;
- an artifact with an unknown artifact_role fails closed
  (invalid handle, reason artifact_role_unknown), never a valid handle.

RED phase: `GENERATOR_REGISTRY` / the role gate / the envelope bundle fields
do not exist yet.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from company_wiki.source_catalog.models import RootSpec  # noqa: E402
from company_wiki.source_catalog.source_bundle import (  # noqa: E402  (RED: import fails)
    GENERATOR_REGISTRY,
)


def _seed_company(tmp_path: Path, company: str, pdoc: str, kind: str,
                  *, fy: int = 2024) -> Path:
    raw = tmp_path / "companies" / company / "raw" / "financial_reports" / "annual"
    raw.mkdir(parents=True, exist_ok=True)
    (raw / f"{pdoc}.pdf").write_bytes(
        b"%PDF-1.4 " + company.encode("utf-8") + pdoc.encode("utf-8"))
    (raw / f"{pdoc}.pdf.source.json").write_text(json.dumps({
        "market": "CN", "security_id": "601899",
        "source_title": f"{company} {fy}", "fiscal_year": fy,
        "filing_date": f"{fy + 1}-03-20", "form_type": kind,
        "document_kind": kind, "provider": "cninfo",
        "provider_document_id": pdoc,
        "source_url": f"https://provider.example/{pdoc}",
    }, ensure_ascii=False), encoding="utf-8")
    return tmp_path / "companies"


def _catalog(tmp_path: Path, tree: Path):
    from company_wiki.source_catalog import CatalogConfig, SourceCatalog

    return SourceCatalog(
        CatalogConfig(
            project_root=tmp_path,
            catalog_dir=tmp_path / ".source_catalog",
            reusable_root_kinds=("company_raw",),
            roots=(RootSpec("company_raw", tree, "company_raw",
                            priority=10, adapter_id="company_raw_v1",
                            read_only=False, reusable_for_filing=True,
                            canonical_write_target="companies"),),
        )
    )


def _resolve(catalog, *, entity="Acme", security="601899", fy=2024,
             kind="annual_report", pdoc=None, mode="exact"):
    from company_wiki.source_catalog import SourceRequest, SourceResolver

    return SourceResolver(catalog).resolve(SourceRequest(
        entity=entity, market="CN", security_id=security,
        document_kind=kind, form_type=kind, fiscal_year=fy,
        provider="cninfo", provider_document_id=pdoc,
        as_of_date="2026-08-11", mode=mode,
    ))


def _doc_row(catalog) -> dict:
    con = sqlite3.connect(catalog.config.database_path)
    try:
        row = con.execute(
            """SELECT d.document_id, d.primary_source_id, s.content_sha256
               FROM documents d JOIN sources s ON s.source_id = d.primary_source_id
               WHERE d.source_status='active' LIMIT 1""").fetchone()
    finally:
        con.close()
    return {"document_id": row[0], "source_id": row[1], "source_sha": row[2]}


def _add_artifact(catalog, tree, *, doc, role="normalized",
                  generator_name="source_catalog_normalizer",
                  generator_version="1.0.0",
                  body=b"# normalized body",
                  status="completed") -> str:
    """Insert a valid artifact row + its file under the allowed root."""
    art_dir = tree / "Acme" / "processed"
    art_dir.mkdir(parents=True, exist_ok=True)
    path = art_dir / f"{role}.md"
    path.write_bytes(body)
    content_sha = hashlib.sha256(body).hexdigest()
    artifact_id = f"art-{role}"
    con = sqlite3.connect(catalog.config.database_path)
    con.execute(
        """INSERT OR REPLACE INTO artifacts
        (artifact_id, document_id, source_id, artifact_role, path,
         content_sha256, byte_size, mime_type, generator_name,
         generator_version, status, error, metadata_json, created_at,
         schema_version, source_sha256)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (artifact_id, doc["document_id"], doc["source_id"], role, str(path),
         content_sha, len(body), "text/markdown", generator_name,
         generator_version, status, None,
         json.dumps({"schema_version": "1.0",
                     "source_sha256": doc["source_sha"]}),
         "2026-08-01T00:00:00Z", "1.0", doc["source_sha"]),
    )
    con.commit()
    con.close()
    return artifact_id


def _build_envelope(resolution, *, bundle=None, policy_snapshot=None):
    from company_wiki.source_catalog.resolver import build_resolution_envelope

    return build_resolution_envelope(
        resolution, policy_snapshot=policy_snapshot, bundle=bundle)


# --- B-01: real bundle rides on the reuse envelope ----------------------------


def test_b01_available_bundle_on_reuse(tmp_path):
    """A reused document with a verified artifact yields
    bundle_status='available', a bundle_hash, and a bundle dict carrying the
    source + valid handle."""
    from company_wiki.source_catalog import ResolutionStatus

    tree = _seed_company(tmp_path, "Acme", "doc-a", "annual_report")
    catalog = _catalog(tmp_path, tree)
    catalog.scan()
    doc = _doc_row(catalog)
    _add_artifact(catalog, tree, doc=doc)
    result = _resolve(catalog)
    assert result.status in (ResolutionStatus.REUSED_EXACT,
                                 ResolutionStatus.REUSED_EQUIVALENT)
    # explicit registry path (the default inside bundle_for_resolution is the
    # same GENERATOR_REGISTRY — both paths are covered across the suite)
    bundle = catalog.bundle_for_resolution(result, registry=GENERATOR_REGISTRY)
    assert bundle is not None
    assert bundle["bundle_hash"]
    envelope = _build_envelope(result, bundle=bundle)
    assert envelope.bundle_status == "available"
    assert envelope.bundle_hash == bundle["bundle_hash"]
    assert envelope.bundle is not None
    assert "normalized" in envelope.bundle["valid_handles"]
    assert envelope.bundle["source"]["document_id"] == doc["document_id"]


# --- B-02: unavailable is preserved when no bundle can be built ---------------


def test_b02_unavailable_without_bundle(tmp_path):
    """Without a bundle the envelope keeps the FC-704 honest 'unavailable'
    (bundle_hash/bundle are None — never a faked empty-green)."""
    from company_wiki.source_catalog import ResolutionStatus

    tree = _seed_company(tmp_path, "Acme", "doc-a", "annual_report")
    catalog = _catalog(tmp_path, tree)
    catalog.scan()
    result = _resolve(catalog)
    assert result.status in (ResolutionStatus.REUSED_EXACT,
                                 ResolutionStatus.REUSED_EQUIVALENT)
    envelope = _build_envelope(result)          # no bundle passed
    assert envelope.bundle_status == "unavailable"
    assert envelope.bundle_hash is None
    assert envelope.bundle is None


# --- B-03: snapshot consistency — hash drift fails closed ---------------------


def test_b03_snapshot_consistency_fail_closed(tmp_path):
    """If the catalog source bytes differ from the hash the handle claims,
    NO bundle is served — a bundle built from different bytes would be a
    stale/forged derivation."""
    from company_wiki.source_catalog import ResolutionStatus

    tree = _seed_company(tmp_path, "Acme", "doc-a", "annual_report")
    catalog = _catalog(tmp_path, tree)
    catalog.scan()
    doc = _doc_row(catalog)
    _add_artifact(catalog, tree, doc=doc)
    result = _resolve(catalog)
    assert result.status in (ResolutionStatus.REUSED_EXACT,
                                 ResolutionStatus.REUSED_EQUIVALENT)
    # drift the catalog source bytes AFTER the resolve (the handle keeps the
    # original hash)
    con = sqlite3.connect(catalog.config.database_path)
    con.execute("UPDATE sources SET content_sha256=? WHERE source_id=?",
                ("c" * 64, doc["source_id"]))
    con.commit()
    con.close()
    assert catalog.bundle_for_resolution(result) is None  # fail closed
    envelope = _build_envelope(result)
    assert envelope.bundle_status == "unavailable"


# --- B-04: unknown artifact role fails closed ---------------------------------


def test_b04_unknown_role_fail_closed(tmp_path):
    """An artifact whose role is not in the frozen known set becomes an
    invalid handle with reason artifact_role_unknown — it never appears as a
    valid handle and is never silently dropped."""
    from company_wiki.source_catalog import ResolutionStatus

    tree = _seed_company(tmp_path, "Acme", "doc-a", "annual_report")
    catalog = _catalog(tmp_path, tree)
    catalog.scan()
    doc = _doc_row(catalog)
    _add_artifact(catalog, tree, doc=doc, role="normalized")
    _add_artifact(catalog, tree, doc=doc, role="random_role",
                  body=b"# rogue body")
    result = _resolve(catalog)
    assert result.status in (ResolutionStatus.REUSED_EXACT,
                                 ResolutionStatus.REUSED_EQUIVALENT)
    bundle = catalog.bundle_for_resolution(result)
    assert bundle is not None
    valid = bundle["valid_handles"]
    assert "normalized" in valid
    assert "random_role" not in valid
    invalid = bundle["invalid"]
    assert "random_role" in invalid
    assert invalid["random_role"]["reason"] == "artifact_role_unknown"


# --- B-05: policy/epoch stay shared with the bundle ---------------------------


def test_b05_policy_epoch_shared_with_bundle(tmp_path):
    """The request-pinned policy_hash/activation_epoch ride the envelope
    together with the bundle — bundle and handle share that context."""
    from company_wiki.source_catalog import ResolutionStatus

    tree = _seed_company(tmp_path, "Acme", "doc-a", "annual_report")
    catalog = _catalog(tmp_path, tree)
    catalog.scan()
    doc = _doc_row(catalog)
    _add_artifact(catalog, tree, doc=doc)
    result = _resolve(catalog)
    assert result.status in (ResolutionStatus.REUSED_EXACT,
                                 ResolutionStatus.REUSED_EQUIVALENT)
    bundle = catalog.bundle_for_resolution(result)
    envelope = _build_envelope(result, bundle=bundle, policy_snapshot={
        "policy_hash": "a" * 64, "current_epoch": "epoch-7",
        "flags": {}, "roots": [], "active_cohorts": [],
    })
    assert envelope.bundle_status == "available"
    assert envelope.policy_hash == "a" * 64
    assert envelope.activation_epoch == "epoch-7"


# --- B-06: no bundle for non-reuse outcomes -----------------------------------


def test_b06_no_bundle_for_missing(tmp_path):
    """A non-reuse resolution (unknown entity) has no matches ->
    bundle_for_resolution returns None -> the envelope stays 'unavailable'."""
    from company_wiki.source_catalog import ResolutionStatus

    tree = _seed_company(tmp_path, "Acme", "doc-a", "annual_report")
    catalog = _catalog(tmp_path, tree)
    catalog.scan()
    result = _resolve(catalog, entity="GhostCo", security="999999")
    assert result.status not in (ResolutionStatus.REUSED_EXACT,
                                 ResolutionStatus.REUSED_EQUIVALENT)
    assert not result.matches
    assert catalog.bundle_for_resolution(result) is None
    envelope = _build_envelope(result)
    assert envelope.bundle_status == "unavailable"


# --- B-07: deterministic bundle -----------------------------------------------


def test_b07_bundle_deterministic(tmp_path):
    """The same catalog queried twice yields the identical bundle_hash —
    consumers can compare bundle hashes across calls."""
    from company_wiki.source_catalog import ResolutionStatus

    tree = _seed_company(tmp_path, "Acme", "doc-a", "annual_report")
    catalog = _catalog(tmp_path, tree)
    catalog.scan()
    doc = _doc_row(catalog)
    _add_artifact(catalog, tree, doc=doc)
    result = _resolve(catalog)
    assert result.status in (ResolutionStatus.REUSED_EXACT,
                                 ResolutionStatus.REUSED_EQUIVALENT)
    b1 = catalog.bundle_for_resolution(result)
    b2 = catalog.bundle_for_resolution(result)
    assert b1 == b2
    assert b1["bundle_hash"] == b2["bundle_hash"]
