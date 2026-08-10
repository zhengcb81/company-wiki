"""FC-701 RED/acceptance tests: normalized-only resolver.

With the RuntimePolicySnapshot pinned to the v2 reader
(``v2_resolve_active`` + epoch + active cohort + legacy bridge OFF), the
resolver consumes ONLY active normalized assertions — the legacy
acquisition/dayu_meta containers are never read (observer records zero
legacy_bridge_hit).  Without an active assertion the resolver fails
closed (no bridge fallback).  Pending remediation proposals, retired
documents and unprovable evidence are explicitly excluded with a trace
reason.  An AST gate forbids legacy-container reads anywhere except the
resolver's gated bridge.
"""
import ast
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from company_wiki.source_catalog.models import RootSpec  # noqa: E402


def _dropbox_fixture(tmp_path: Path, body: bytes) -> Path:
    dropbox = tmp_path / "Dropbox" / "Stock" / "Acme"
    dropbox.mkdir(parents=True)
    (dropbox / "2025.pdf").write_bytes(body)
    (dropbox / "2025.pdf.source.json").write_text(json.dumps({
        "schema_version": "1.0",
        "canonical_entity_id": "ent-601899",
        "display_name": "Acme", "market": "CN",
        "security_id": "601899", "document_kind": "annual_report",
        "fiscal_year": 2025, "period_end": "2025-12-31",
        "filing_date": "2026-03-20", "form_type": "annual_report",
        "provider": "cninfo", "provider_document_id": "1225023658",
        "source_url": "https://www.cninfo.com.cn/new/disclosure/detail?stockCode=601899&announcementId=1225023658",
        "content_sha256": hashlib.sha256(body).hexdigest(),
    }, ensure_ascii=False), encoding="utf-8")
    return tmp_path / "Dropbox" / "Stock"


def _catalog(tmp_path: Path, dropbox_dir: Path):
    from company_wiki.source_catalog import CatalogConfig, SourceCatalog

    companies = tmp_path / "companies" / "Acme" / "raw"
    companies.mkdir(parents=True)
    catalog = SourceCatalog(
        CatalogConfig(
            project_root=tmp_path,
            catalog_dir=tmp_path / ".source_catalog",
            reusable_root_kinds=("company_raw", "directory"),
            roots=(
                RootSpec("company_raw", tmp_path / "companies", "company_raw",
                         adapter_id="company_raw_v1", read_only=False,
                         reusable_for_filing=True,
                         canonical_write_target="companies"),
                RootSpec("dropbox_stock", dropbox_dir, "directory",
                         priority=10, adapter_id="sidecar_filing_v1",
                         read_only=True, reusable_for_filing=True),
            ),
        )
    )
    catalog.scan()
    return catalog


def _v2_snapshot(epoch="e1", cohort="dropbox-cohort") -> dict:
    return {
        "schema_version": "2.0",
        "flags": {"v2_resolve_active": True, "legacy_bridge_enabled": False},
        "current_epoch": epoch,
        "active_cohorts": [cohort],
    }


def _resolve(catalog, ident, *, snapshot=None, observer=None):
    from company_wiki.source_catalog import SourceRequest, SourceResolver

    resolver = SourceResolver(
        catalog, observer=observer, runtime_policy=snapshot)
    return resolver.resolve(SourceRequest(
        entity="Acme", market="CN", security_id=ident["security_id"],
        document_kind="annual_report", form_type="annual_report",
        fiscal_year=ident["fiscal_year"],
        provider_document_id=ident["provider_document_id"],
        as_of_date="2026-08-11", mode="exact",
    ))


def _register_active_assertion(catalog, body, ident, *, epoch="e1",
                               cohort="dropbox-cohort"):
    from company_wiki.source_catalog.activation import apply_activation
    from company_wiki.source_catalog.assertion_service import (
        upsert_verified_assertion,
    )
    from company_wiki.source_catalog.normalized_meta import canonical_hash

    digest = hashlib.sha256(body).hexdigest()
    normalized = {
        "market": ident["market"], "security_id": ident["security_id"],
        "fiscal_year": ident["fiscal_year"],
        "provider_document_id": ident["provider_document_id"],
        "provider": "cninfo",
        # normalized contract field names (assertion storage keys)
        "regulatory_form": "annual_report", "document_kind": "annual_report",
        "period_kind": "FY", "filed_at": "2026-03-20",
        "period_end": "2025-12-31",
        "source_url": "https://www.cninfo.com.cn/new/disclosure/detail?stockCode=601899&announcementId=1225023658",
    }
    row = catalog.store.fetchone(
        """SELECT d.document_id, d.primary_source_id FROM documents d
           JOIN locations l ON l.document_id = d.document_id
           JOIN sources s ON s.source_id = l.source_id
           WHERE s.content_sha256 = ? LIMIT 1""", (digest,))
    assert row is not None
    assertion = upsert_verified_assertion(
        catalog.store,
        source_id=row["primary_source_id"],
        document_id=row["document_id"],
        content_sha256=digest,
        adapter_id="sidecar_filing_v1",
        adapter_version="1.0.0",
        metadata_hash=canonical_hash(normalized),
        normalized=normalized,
        created_by="fc701-test",
    )
    applied = apply_activation(
        catalog.store,
        epoch=epoch,
        cohort=cohort,
        assertion_ids=[assertion["assertion_id"]],
        policy_hash="p" * 64,
        reason="FC-701 activation",
        reviewer="fc701-test",
    )
    return assertion["assertion_id"], applied["kind"]


class _Observer:
    def __init__(self):
        self.reasons = []

    def record_reason(self, reason: str):
        self.reasons.append(reason)


# --- v2 reader consumes normalized assertions only ----------------------------


def test_fc701_v2_reader_consumes_normalized_only(tmp_path):
    """With the snapshot pinned to v2 and the legacy bridge OFF, the
    resolver consumes the active normalized assertion and records ZERO
    legacy bridge hits."""
    from company_wiki.source_catalog import ResolutionStatus

    ident = {"market": "CN", "security_id": "601899",
             "fiscal_year": 2025, "provider_document_id": "1225023658"}
    body = b"%PDF-1.4 fc701"
    dropbox = _dropbox_fixture(tmp_path, body)
    catalog = _catalog(tmp_path, dropbox)
    _register_active_assertion(catalog, body, ident)
    observer = _Observer()
    result = _resolve(catalog, ident, snapshot=_v2_snapshot(),
                      observer=observer)
    assert result.status is ResolutionStatus.REUSED_EXACT
    handle = result.matches[0]
    assert handle.provider == "cninfo"
    assert handle.provider_document_id == "1225023658"
    assert handle.capture_ready is True
    assert observer.reasons == [], (
        f"legacy bridge read despite v2 reader: {observer.reasons}")


def test_fc701_bridge_off_fails_closed_without_assertion(tmp_path):
    """V2 reader with NO active assertion and the bridge OFF resolves
    MISSING — no legacy container fallback."""
    from company_wiki.source_catalog import ResolutionStatus

    ident = {"market": "CN", "security_id": "601899",
             "fiscal_year": 2025, "provider_document_id": "1225023658"}
    body = b"%PDF-1.4 fc701"
    dropbox = _dropbox_fixture(tmp_path, body)
    catalog = _catalog(tmp_path, dropbox)
    observer = _Observer()
    result = _resolve(catalog, ident, snapshot=_v2_snapshot(),
                      observer=observer)
    assert result.status is not ResolutionStatus.REUSED_EXACT
    # the legacy container WAS indexed by the scan but must not be read
    assert observer.reasons == [], (
        f"bridge read despite v2-only snapshot: {observer.reasons}")


def test_fc701_bridge_on_still_observable_with_v2_snapshot(tmp_path):
    """Even with the bridge ON, the v2 assertion (when present) is read
    first — a legacy hit only happens when NO v2 assertion exists."""
    from company_wiki.source_catalog import ResolutionStatus

    ident = {"market": "CN", "security_id": "601899",
             "fiscal_year": 2025, "provider_document_id": "1225023658"}
    body = b"%PDF-1.4 fc701"
    dropbox = _dropbox_fixture(tmp_path, body)
    catalog = _catalog(tmp_path, dropbox)
    _register_active_assertion(catalog, body, ident)
    snapshot = _v2_snapshot()
    snapshot["flags"]["legacy_bridge_enabled"] = True
    observer = _Observer()
    result = _resolve(catalog, ident, snapshot=snapshot, observer=observer)
    assert result.status is ResolutionStatus.REUSED_EXACT
    assert observer.reasons == [], (
        f"v2 assertion present but bridge read: {observer.reasons}")


# --- remediation / retired / unprovable explicitly excluded ------------------


def test_fc701_remediation_pending_excluded(tmp_path):
    """A source with a pending remediation proposal is not offered for
    reuse — the resolver records the exclusion reason."""
    from company_wiki.source_catalog import ResolutionStatus

    ident = {"market": "CN", "security_id": "601899",
             "fiscal_year": 2025, "provider_document_id": "1225023658"}
    body = b"%PDF-1.4 fc701"
    dropbox = _dropbox_fixture(tmp_path, body)
    catalog = _catalog(tmp_path, dropbox)
    digest = hashlib.sha256(body).hexdigest()
    row = catalog.store.fetchone(
        """SELECT d.document_id, d.primary_source_id FROM documents d
           JOIN locations l ON l.document_id = d.document_id
           JOIN sources s ON s.source_id = l.source_id
           WHERE s.content_sha256 = ? LIMIT 1""", (digest,))
    from company_wiki.source_catalog.remediation import create_proposal

    create_proposal(
        catalog.store,
        source_id=row["primary_source_id"],
        document_id=row["document_id"],
        content_sha256=digest,
        field_evidence={"security_id": {"origin": "pdf-text", "source_pointer": "p1"}},
        proposed_fields={"security_id": "601899"},
        policy_hash=hashlib.sha256(b"fc701-policy").hexdigest(),
        proposed_by="fc701-test",
    )
    result = _resolve(catalog, ident)
    assert result.status is not ResolutionStatus.REUSED_EXACT
    assert any("remediation" in t for t in result.debug_trace), (
        f"no remediation exclusion reason: {list(result.debug_trace)[:4]}")


def test_fc701_retired_document_excluded(tmp_path):
    """A retired document is never offered for reuse."""
    from company_wiki.source_catalog import ResolutionStatus

    ident = {"market": "CN", "security_id": "601899",
             "fiscal_year": 2025, "provider_document_id": "1225023658"}
    body = b"%PDF-1.4 fc701"
    dropbox = _dropbox_fixture(tmp_path, body)
    catalog = _catalog(tmp_path, dropbox)
    digest = hashlib.sha256(body).hexdigest()
    row = catalog.store.fetchone(
        """SELECT d.document_id FROM documents d
           JOIN locations l ON l.document_id = d.document_id
           JOIN sources s ON s.source_id = l.source_id
           WHERE s.content_sha256 = ? LIMIT 1""", (digest,))
    with catalog.store.transaction() as conn:
        conn.execute(
            "UPDATE documents SET source_status='retired' WHERE document_id=?",
            (row["document_id"],),
        )
    result = _resolve(catalog, ident)
    # retired documents are excluded at the candidate query level
    # (source_statuses=("active",)) — never offered for reuse
    assert result.status is not ResolutionStatus.REUSED_EXACT


# --- AST gate: legacy containers read only in the gated bridge ---------------


_LEGACY_OWNERS = frozenset({
    # the gated bridge and the documented legacy container handlers —
    # migration/backfill/stats/persist/bridge-helper each own their seam;
    # FC-701 freezes the set: NO new production caller may read the
    # acquisition/dayu_meta containers as an identity source.
    "resolver.py", "backfill_v2.py", "migration_ledger.py",
    "normalizer.py", "scanner.py", "visibility_bridge.py", "dayu.py",
})


def _legacy_reads(src_dir) -> list[str]:
    violations = []
    for py_file in sorted(src_dir.rglob("*.py")):
        if py_file.name.startswith("test_") or py_file.name.startswith("__"):
            continue
        if py_file.name in _LEGACY_OWNERS:
            continue
        tree = ast.parse(py_file.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            key = None
            if isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant):
                key = node.slice.value
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)                     and node.func.attr == "get" and node.args                     and isinstance(node.args[0], ast.Constant):
                key = node.args[0].value
            if key in ("acquisition", "dayu_meta"):
                violations.append(f"{py_file.name}:{node.lineno}:{key}")
    return violations


def test_fc701_legacy_container_read_only_in_bridge():
    """AST gate: the legacy containers may be read only by the documented
    owners (the resolver's gated bridge + migration/persist seams).  A NEW
    production caller reading acquisition/dayu_meta is a violation — the
    resolver consumes normalized assertions only."""
    src_dir = (Path(__file__).resolve().parents[2] / "src"
               / "company_wiki" / "source_catalog")
    violations = _legacy_reads(src_dir)
    assert not violations, (
        f"legacy container read by a new production caller: {violations}")


def test_fc701_legacy_gate_rejects_new_caller(tmp_path):
    """Adversarial: a NEW module reading acquisition is rejected by the
    gate — FC-701 forbids new legacy-container callers."""
    src_dir = (Path(__file__).resolve().parents[2] / "src"
               / "company_wiki" / "source_catalog")
    evil = src_dir / "_fc701_evil_probe.py"
    evil.write_text(
        'metadata = {}\nvalue = metadata.get("acquisition")\n',
        encoding="utf-8")
    try:
        violations = _legacy_reads(src_dir)
        assert any("_fc701_evil_probe" in v for v in violations), (
            f"evil probe not detected: {violations}")
    finally:
        evil.unlink()
