"""FC-1001 RED/acceptance tests: unified isolated-lake fixture.

The fixture is the Phase-10 E2E bedrock: one temp directory reproducing the
real three-root production layout with sidecars, identity snapshots, v2
processed artifacts (schema_version COLUMN + metadata), producer_events
journal rows, corruption variants, and a deterministic manifest hash with NO
real paths.  RED target: the fixture module does not exist yet.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from _rf_system_paths import RF_CODE_ROOT  # noqa: E402
PROJECT_ROOT = RF_CODE_ROOT
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
sys.path.insert(0, str(PROJECT_ROOT / "tests"))
WIKI_ROOT = PROJECT_ROOT.parent / "company-wiki"
sys.path.insert(0, str(WIKI_ROOT / "src"))

import pytest  # noqa: E402

from e2e_support.isolated_lake import (  # noqa: E402
    ARTIFACT_SCHEMA_VERSION,
    IsolatedLake,
)

CN_ANNUAL = {"market": "CN", "security_id": "601899",
             "provider_document_id": "1225023658", "fiscal_year": 2025}


def test_manifest_is_deterministic(tmp_path: Path):
    m1 = IsolatedLake(tmp_path / "a", seed="fc1001").build()
    m2 = IsolatedLake(tmp_path / "b", seed="fc1001").build()
    assert m1.manifest_hash() == m2.manifest_hash()
    assert len(m1.entries) == 3  # companies + dayu + dropbox


def test_manifest_has_no_real_paths(tmp_path: Path):
    m = IsolatedLake(tmp_path, seed="fc1001").build()
    flat = "\n".join(m.relative_manifest())
    for forbidden in ("C:\\", "C:/", "/Users/", "郑曾波", "Projects", "tmp"):
        assert forbidden not in flat, f"real path leaked: {forbidden!r}"


def test_three_roots_resolve_consistently(tmp_path: Path):
    """Same request matrix hits the companies root; contract fields stable."""
    from company_wiki.source_catalog import (
        CatalogConfig,
        RootSpec,
        SourceCatalog,
        SourceRequest,
        SourceResolver,
    )
    from company_wiki.source_catalog.runtime_policy import load_runtime_policy

    m = IsolatedLake(tmp_path, seed="fc1001").build()
    assert m.catalog_path is not None
    catalog = SourceCatalog(CatalogConfig(
        project_root=tmp_path / "lake" / "project",
        catalog_dir=m.catalog_path.parent,
        roots=(
            RootSpec("company_raw", tmp_path / "lake" / "project" / "companies", "company_raw",
                     priority=10, adapter_id="company_raw_v1", read_only=False,
                     reusable_for_filing=True, canonical_write_target="companies"),
            RootSpec("dayu_portfolio", tmp_path / "lake" / "portfolio", "dayu_portfolio",
                     priority=20, adapter_id="dayu_filing_v1", read_only=True,
                     reusable_for_filing=True),
            RootSpec("dropbox_stock", tmp_path / "lake" / "Dropbox" / "Stock", "directory",
                     priority=30, adapter_id="sidecar_filing_v1", read_only=True,
                     reusable_for_filing=True),
        ),
    ))
    try:
        policy = load_runtime_policy(m.catalog_path.parent / "runtime_policy.json")
    except Exception:
        policy = None
    req = SourceRequest(entity="紫金矿业", document_kind="annual_report",
                        as_of_date="2026-08-12", market="CN", fiscal_year=2025)
    res = SourceResolver(catalog, runtime_policy=policy).resolve(req)
    assert res.status is not None
    assert res.status.value in ("reused_exact", "reused_equivalent"), res.status
    assert res.matches, "companies root must resolve the annual report"
    match = res.matches[0]
    assert match.fiscal_year == 2025
    assert match.provider_document_id == "1225023658"


def test_v2_artifacts_are_bindable(tmp_path: Path):
    from company_wiki.source_catalog.artifact_handle import validate_artifact
    from company_wiki.source_catalog.source_bundle import GENERATOR_REGISTRY

    m = IsolatedLake(tmp_path, seed="fc1001").build()
    assert m.catalog_path is not None and m.derived_root is not None
    import sqlite3

    con = sqlite3.connect(f"file:{m.catalog_path}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    rows = con.execute(
        """SELECT a.*, d.primary_source_id, s.content_sha256 AS source_sha
           FROM artifacts a JOIN documents d ON d.document_id=a.document_id
           JOIN sources s ON s.source_id=d.primary_source_id
           WHERE a.artifact_role='normalized'"""
    ).fetchall()
    con.close()
    assert len(rows) >= 2, "preset v2 artifacts missing"
    for row in rows:
        assert row["schema_version"] == ARTIFACT_SCHEMA_VERSION, (
            "column must be stamped (FC-906-d contract)"
        )
        meta = json.loads(row["metadata_json"] or "{}")
        assert meta.get("schema_version") == ARTIFACT_SCHEMA_VERSION
        artifact = {
            "artifact_id": row["artifact_id"], "document_id": row["document_id"],
            "source_id": row["source_id"], "artifact_role": row["artifact_role"],
            "path": row["path"], "content_sha256": row["content_sha256"],
            "generator_name": row["generator_name"], "generator_version": row["generator_version"],
            "status": row["status"], "created_at": row["created_at"],
            "schema_version": row["schema_version"] or meta.get("schema_version", ""),
            "source_sha256": row["source_sha256"] or meta.get("source_sha256", ""),
        }
        source = {"document_id": row["document_id"],
                  "primary_source_id": row["primary_source_id"],
                  "source_sha256": row["source_sha"] or "", "as_of_date": ""}
        handle = validate_artifact(artifact, source=source,
                                   registry=GENERATOR_REGISTRY,
                                   allowed_roots=(m.derived_root,),
                                   now="2099-12-31T23:59:59Z")
        assert handle.reusable is True, f"preset artifact not bindable: {handle.reason}"


@pytest.mark.parametrize("variant", [
    "hash_mismatch", "truncated_source",
    # KNOWN GAP, not a pass.  "A document whose identity sidecar is missing must
    # not default to a trusted filing" has NO implementation today: the resolver
    # answers from the INDEX, and the index keeps the document's location rows
    # and recorded entity rows after the sidecar FILE is deleted.  Measured six
    # ways (scan/resolve, before/after the resolver's reuse-alignment change,
    # synthetic vs production-shaped config) in the R4 phase-B run directory:
    # findings F-B01-7 and evidence/b01-fc1001_probe.py.  The assertion below is
    # deliberately kept so the requirement stays written down; strict=True turns
    # this into a FAILURE the moment the requirement is implemented, i.e. the
    # marker then has to be removed deliberately.  Carrier: B06 acceptance item
    # "identity sidecar missing => not reusable".
    pytest.param("sidecar_missing", marks=pytest.mark.xfail(
        strict=True,
        reason="F-B01-7: sidecar-missing fail-closed is unimplemented (carrier: B06)")),
    "location_inactive", "column_drop",
])
def test_corruption_variants_fail_closed(tmp_path: Path, variant: str):
    """Each corruption makes the artifact/document unusable — never silently
    trusted.  A variant that still validates is a broken corruption + broken
    fail-closed, and this test must catch it."""
    m = IsolatedLake(tmp_path, seed="fc1001").build()
    lake = IsolatedLake(tmp_path, seed="fc1001")
    lake.corrupt(variant, m)

    import sqlite3

    con = sqlite3.connect(f"file:{m.catalog_path}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    rows = con.execute(
        """SELECT a.*, d.primary_source_id, s.content_sha256 AS source_sha
           FROM artifacts a JOIN documents d ON d.document_id=a.document_id
           JOIN sources s ON s.source_id=d.primary_source_id
           WHERE a.artifact_role='normalized'"""
    ).fetchall()
    con.close()

    if variant == "location_inactive":
        # resolver must not see the dropbox document at all
        import sqlite3 as _sqlite3

        from company_wiki.source_catalog import (
            CatalogConfig,
            RootSpec,
            SourceCatalog,
            SourceRequest,
            SourceResolver,
        )

        # the document EXISTS in the catalog (location row present, just
        # quarantined) — it must be invisible to the resolver regardless
        c = _sqlite3.connect(f"file:{m.catalog_path}?mode=ro", uri=True)
        n = c.execute("SELECT COUNT(*) FROM locations WHERE root_id='dropbox_stock'"
                      " AND location_status='quarantined'").fetchone()[0]
        c.close()
        assert n >= 1, "fixture corruption did not quarantine the dropbox location"

        catalog = SourceCatalog(CatalogConfig(
            project_root=tmp_path / "lake" / "project",
            catalog_dir=m.catalog_path.parent,
            roots=(RootSpec("dropbox_stock", tmp_path / "lake" / "Dropbox" / "Stock",
                            "directory", priority=30, adapter_id="sidecar_filing_v1",
                            read_only=True, reusable_for_filing=True),),
        ))
        req = SourceRequest(entity="中国平安", document_kind="semi_annual_report",
                            as_of_date="2026-08-12", market="CN", fiscal_year=2020)
        res = SourceResolver(catalog, runtime_policy=None).resolve(req)
        assert not res.matches, "inactive location must not resolve"
        return

    if variant == "sidecar_missing":
        # Dropbox identity comes from the sidecar (FC-501) - but that is a
        # SCAN-time rule, and this corruption deletes the sidecar FILE only,
        # while the catalog row it produced stays intact (the fixture comment in
        # e2e_support/isolated_lake.py:381-386 states the same intent).  What
        # used to reject the document here was therefore NOT identity: it was
        # the resolver's old kind-only reuse set, applied to this inline
        # synthetic config whose default reusable_root_kinds is ('company_raw',)
        # while the root below is a `directory` root.  B01 aligned the resolver
        # with the exported policy (an explicit reusable_for_filing=True makes
        # this root reusable), which removed that incidental cover and exposed
        # the real gap - the assertion below is kept as a strict xfail until the
        # requirement has an implementation (F-B01-7; carrier: B06).
        from company_wiki.source_catalog import (
            CatalogConfig,
            RootSpec,
            SourceCatalog,
            SourceRequest,
            SourceResolver,
        )

        catalog = SourceCatalog(CatalogConfig(
            project_root=tmp_path / "lake" / "project",
            catalog_dir=m.catalog_path.parent,
            roots=(RootSpec("dropbox_stock", tmp_path / "lake" / "Dropbox" / "Stock",
                            "directory", priority=30, adapter_id="sidecar_filing_v1",
                            read_only=True, reusable_for_filing=True),),
        ))
        req = SourceRequest(entity="中国平安", document_kind="semi_annual_report",
                            as_of_date="2026-08-12", market="CN", fiscal_year=2020)
        res = SourceResolver(catalog, runtime_policy=None).resolve(req)
        assert not res.matches, "sidecar-missing dropbox doc must not resolve"
        return

    # Column/source corruptions fail closed at the BUNDLE layer (the validator
    # reads metadata for schema_version; the bundle reads the COLUMN — the
    # FC-906-d production path).  hash_mismatch fails at the validator layer.
    from company_wiki.source_catalog.source_bundle import GENERATOR_REGISTRY

    if variant in ("truncated_source", "column_drop"):
        from company_wiki.source_catalog import (
            CatalogConfig,
            RootSpec,
            SourceCatalog,
        )

        catalog = SourceCatalog(CatalogConfig(
            project_root=tmp_path / "lake" / "project",
            catalog_dir=m.catalog_path.parent,
            roots=(RootSpec("company_raw", tmp_path / "lake" / "project" / "companies", "company_raw",
                            priority=10, adapter_id="company_raw_v1", read_only=False,
                            reusable_for_filing=True, canonical_write_target="companies"),),
        ))
        assert m.derived_root is not None
        b = catalog.query_source_bundle(
            document_id=rows[0]["document_id"],
            registry=GENERATOR_REGISTRY,
            allowed_roots=(m.derived_root,),
            now="2099-12-31T23:59:59Z",
            expected_content_sha256=rows[0]["source_sha"],
        )
        valid = (b or {}).get("valid_handles") or {}
        assert not valid, (
            f"corruption {variant!r} must empty bundle valid_handles, "
            f"got {sorted(valid.keys())}"
        )
        return

    # hash_mismatch fails at the validator layer
    from company_wiki.source_catalog.artifact_handle import validate_artifact

    for row in rows:
        meta = json.loads(row["metadata_json"] or "{}")
        artifact = {
            "artifact_id": row["artifact_id"], "document_id": row["document_id"],
            "source_id": row["source_id"], "artifact_role": row["artifact_role"],
            "path": row["path"], "content_sha256": row["content_sha256"],
            "generator_name": row["generator_name"], "generator_version": row["generator_version"],
            "status": row["status"], "created_at": row["created_at"],
            "schema_version": row["schema_version"] or meta.get("schema_version", ""),
            "source_sha256": row["source_sha256"] or meta.get("source_sha256", ""),
        }
        source = {"document_id": row["document_id"],
                  "primary_source_id": row["primary_source_id"],
                  "source_sha256": row["source_sha"] or "", "as_of_date": ""}
        handle = validate_artifact(artifact, source=source,
                                   registry=GENERATOR_REGISTRY,
                                   allowed_roots=(m.derived_root,),
                                   now="2099-12-31T23:59:59Z")
        assert handle.reusable is False, (
            f"hash_mismatch must make artifact unusable: {handle.reason}"
        )
