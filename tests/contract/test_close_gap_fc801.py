"""FC-801 RED/acceptance tests: CloseGap transaction contract.
SCENARIO: DL-02 DL-03 DL-07 DL-09 LT-10

The transaction binds request_id + gap hash + policy hash + provider +
allowed accessions + caps + expiry, and walks the FIXED steps
(rediscover/validate -> fetch staging -> validate -> canonical commit ->
re-resolve).  Scenarios: DL-02 (expired/wrong authorization -> fetch=0),
DL-03 (stale gap/policy hash -> fetch=0), DL-07 (invalid staging -> no
commit + cleanup), DL-09 (idempotent recovery), LT-10 (partial failure
never reports complete).
"""
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))


def _catalog(tmp_path: Path):
    from company_wiki.source_catalog import CatalogConfig, SourceCatalog
    from company_wiki.source_catalog.models import RootSpec

    project = tmp_path / "project"
    companies = project / "companies"
    (companies / "ACME" / "raw").mkdir(parents=True)
    return SourceCatalog(
        CatalogConfig(
            project_root=project,
            catalog_dir=project / ".source_catalog",
            roots=(RootSpec("company_raw", companies, "company_raw", priority=10,
                            adapter_id="company_raw_v1", read_only=False,
                            reusable_for_filing=True,
                            canonical_write_target="companies"),),
            reusable_root_kinds=("company_raw",),
        )
    )


def _policy_file(catalog, policy_hash: str) -> None:
    from company_wiki.source_catalog.runtime_policy import snapshot_hash

    policy = {
        "schema_version": "1.0",
        "policy_hash": policy_hash,
        "flags": {"v2_resolve_active": False, "legacy_bridge_enabled": True,
                  "v2_bundle_active": False, "v2_persist_assertions": False,
                  "v2_resolve_shadow": False, "v2_scan_shadow": False},
        "current_epoch": "epoch-1",
        "active_cohorts": ["cohort-1"],
        "updated_at": "2026-08-11T00:00:00Z",
    }
    policy["snapshot_sha256"] = snapshot_hash(policy)
    catalog.config.catalog_dir.mkdir(parents=True, exist_ok=True)
    (catalog.config.catalog_dir / "runtime_policy.json").write_text(
        json.dumps(policy, ensure_ascii=False), encoding="utf-8")


def _binding(gap_hash: str, *, policy_hash: str, request_id: str = "req-1",
             expires_at: str = "2099-01-01T00:00:00Z"):
    from company_wiki.source_catalog.close_gap import CloseGapBinding

    return CloseGapBinding(
        request_id=request_id,
        gap_plan_hash=gap_hash,
        policy_hash=policy_hash,
        provider="sec",
        allowed_accessions=("acc-2025",),
        max_items=1,
        max_bytes=5_000_000,
        expires_at=expires_at,
    )


class _FakeAdapter:
    name = "fake"
    version = "1.0.0"

    def __init__(self, *, fetch_error: Exception | None = None,
                 corrupt_receipt: bool = False):
        self.fetch_calls = 0
        self.fetch_error = fetch_error
        self.corrupt_receipt = corrupt_receipt

    def discover(self, request):
        from company_wiki.source_catalog import DownloadCandidate

        return (DownloadCandidate(
            candidate_id="c-2025", provider="sec",
            provider_document_id="acc-2025", market="US", entity="ACME",
            title="ACME 2025 annual",
            source_url="https://www.sec.gov/x/2025.pdf",
            document_kind="annual_report", form_type="annual_report",
            filing_date="2026-04-15", fiscal_year=2025,
        ),)

    def fetch(self, candidate, staging_dir):
        self.fetch_calls += 1
        if self.fetch_error is not None:
            raise self.fetch_error
        staging_dir.mkdir(parents=True, exist_ok=True)
        path = staging_dir / "annual.pdf"
        body = b"%PDF-2025"
        path.write_bytes(body)
        from company_wiki.source_catalog import DownloadReceipt

        digest = hashlib.sha256(body).hexdigest()
        if self.corrupt_receipt:
            digest = "0" * 64  # lies about the bytes
        return DownloadReceipt(
            candidate_id=candidate.candidate_id,
            provider=candidate.provider,
            provider_document_id=candidate.provider_document_id,
            source_url=candidate.source_url,
            staged_path=str(path),
            content_sha256=digest,
            byte_size=len(body),
            mime_type="application/pdf",
            retrieved_at="2026-08-08T12:00:00Z",
            http_status=200,
            adapter_name="fake",
            adapter_version="1.0.0",
        )


def _txn(tmp_path, adapter=None, catalog=None):
    from company_wiki.source_catalog import (
        AcquisitionCoordinator,
        AdapterRegistry,
    )
    from company_wiki.source_catalog.acquisition_journal import AcquisitionJournal
    from company_wiki.source_catalog.canonical_writer import CanonicalSourceWriter
    from company_wiki.source_catalog.close_gap import CloseGapTransaction

    if catalog is None:
        catalog = _catalog(tmp_path)
    adapter = adapter or _FakeAdapter()
    coordinator = AcquisitionCoordinator(
        catalog=catalog,
        adapters=AdapterRegistry(cn=adapter, hk=adapter, us=adapter),
        staging_root=tmp_path / "staging",
    )
    writer = CanonicalSourceWriter(
        catalog, staging_root=tmp_path / "staging")
    return CloseGapTransaction(
        catalog=catalog,
        coordinator=coordinator,
        writer=writer,
        journal=AcquisitionJournal(catalog.config.catalog_dir),
    )


def _request():
    from company_wiki.source_catalog import SourceRequest

    return SourceRequest(
        entity="ACME", market="US", security_id="ACME",
        document_kind="annual_report", form_type="annual_report",
        fiscal_year=2025, as_of_date="2026-07-31", mode="exact",
    )


def _current_gap_hash(catalog, adapter):
    """Rediscover and build the current gap plan (metadata only)."""
    from company_wiki.source_catalog import (
        AcquisitionCoordinator,
        AdapterRegistry,
        SourceRequest,
    )

    coordinator = AcquisitionCoordinator(
        catalog=catalog,
        adapters=AdapterRegistry(cn=adapter, hk=adapter, us=adapter),
        staging_root=Path(str(catalog.config.catalog_dir) + "-staging"),
    )
    result = coordinator.resolve_or_stage(
        SourceRequest(
            entity="ACME", market="US", security_id="ACME",
            document_kind="annual_report", form_type="annual_report",
            fiscal_year=2025, as_of_date="2026-07-31", mode="latest_as_of",
        ))
    return result.gap_plan.gap_hash, result


# --- DL-03: stale policy / gap hash -------------------------------------------


def test_cg01_stale_policy_hash_fetch_zero(tmp_path):
    """DL-03: a download bound to a different policy hash is rejected with
    fetch=0 — old authorizations are never reusable."""
    catalog = _catalog(tmp_path)
    _policy_file(catalog, "a" * 64)
    adapter = _FakeAdapter()
    txn = _txn(tmp_path, adapter, catalog)
    result = txn.execute(
        _binding("1" * 64, policy_hash="b" * 64), _request())
    assert result.status == "rejected"
    assert result.reason == "stale_policy_hash"
    assert result.fetch_events == 0
    assert adapter.fetch_calls == 0


def test_cg02_stale_gap_hash_fetch_zero(tmp_path):
    """DL-03: the authorized gap hash no longer matches the rediscovered
    plan (provider state changed) -> rejected, fetch=0."""
    catalog = _catalog(tmp_path)
    _policy_file(catalog, "a" * 64)
    adapter = _FakeAdapter()
    txn = _txn(tmp_path, adapter, catalog)
    result = txn.execute(
        _binding("d" * 64, policy_hash="a" * 64), _request())
    assert result.status == "rejected"
    assert result.reason == "stale_gap_hash"
    assert result.fetch_events == 0
    assert adapter.fetch_calls == 0


# --- DL-02: expired / wrong authorization -------------------------------------


def test_cg03_expired_authorization_fetch_zero(tmp_path):
    """DL-02: an expired authorization is rejected with a precise reason
    and zero fetches."""
    catalog = _catalog(tmp_path)
    _policy_file(catalog, "a" * 64)
    adapter = _FakeAdapter()
    gap_hash, _ = _current_gap_hash(catalog, adapter)
    txn = _txn(tmp_path, adapter, catalog)
    result = txn.execute(
        _binding(gap_hash, policy_hash="a" * 64,
                  request_id=_request().request_id,
                 expires_at="2020-01-01T00:00:00Z"),
        _request())
    assert result.status == "rejected"
    assert "expired" in result.reason
    assert result.fetch_events == 0
    assert adapter.fetch_calls == 0


# --- DL-07: invalid staging -> no commit + cleanup -----------------------------


def test_cg04_invalid_staging_no_commit_cleanup(tmp_path):
    """DL-07: bytes that do not match the receipt are never committed; the
    staging directory is cleaned up and the catalog is unchanged."""
    catalog = _catalog(tmp_path)
    _policy_file(catalog, "a" * 64)
    adapter = _FakeAdapter(corrupt_receipt=True)
    gap_hash, _ = _current_gap_hash(catalog, adapter)
    txn = _txn(tmp_path, adapter, catalog)
    before = catalog.store.fetchall("SELECT COUNT(*) c FROM documents")[0]["c"]
    result = txn.execute(
        _binding(gap_hash, policy_hash="a" * 64,
                  request_id=_request().request_id),
        _request())
    assert result.status == "failed"
    assert "SHA-256" in result.reason or "receipt" in result.reason
    after = catalog.store.fetchall("SELECT COUNT(*) c FROM documents")[0]["c"]
    assert after == before, "invalid staging was committed"
    staging = tmp_path / "staging"
    leftovers = list(staging.rglob("*")) if staging.exists() else []
    assert leftovers == [], f"staging not cleaned: {leftovers}"


# --- DL-09: idempotent recovery -------------------------------------------------


def test_cg05_rerun_is_idempotent(tmp_path):
    """DL-09: after a successful close, re-running the transaction finds
    the document (reused, no duplicate, no second fetch)."""
    catalog = _catalog(tmp_path)
    _policy_file(catalog, "a" * 64)
    adapter = _FakeAdapter()
    gap_hash, _ = _current_gap_hash(catalog, adapter)
    txn = _txn(tmp_path, adapter, catalog)
    first = txn.execute(_binding(gap_hash, policy_hash="a" * 64), _request())
    assert first.status == "completed"
    assert first.fetch_events == 1
    # re-run: the gap is now closed -> reused, zero fetches
    second = txn.execute(_binding(gap_hash, policy_hash="a" * 64), _request())
    assert second.status == "completed"
    assert second.fetch_events == 0
    assert second.outcome == "reused_before_download"
    docs = catalog.store.fetchall("SELECT COUNT(*) c FROM documents")[0]["c"]
    assert docs == 1, "rerun duplicated the document"


# --- LT-10: partial failure never reports complete ------------------------------


def test_cg06_fetch_failure_is_failed_not_complete(tmp_path):
    """LT-10: a fetch exception journals failed with the txn id — the
    result never claims complete and the txn is re-runnable."""
    catalog = _catalog(tmp_path)
    _policy_file(catalog, "a" * 64)
    adapter = _FakeAdapter(fetch_error=RuntimeError("provider 500"))
    gap_hash, _ = _current_gap_hash(catalog, adapter)
    txn = _txn(tmp_path, adapter, catalog)
    result = txn.execute(
        _binding(gap_hash, policy_hash="a" * 64,
                  request_id=_request().request_id),
        _request())
    assert result.status == "failed"
    assert result.reason != "completed"
    attempts = txn.journal.read_all()
    assert any(a.request_id == _request().request_id
               and a.outcome == "failed" for a in attempts)
    assert result.txn_id  # re-runnable handle


# --- success path ---------------------------------------------------------------


def test_cg07_success_downloaded_new_envelope(tmp_path):
    """The full happy path: downloaded_new is journaled, the final
    re-resolve returns REUSED_EXACT and the FC-704 envelope reports
    outcome downloaded_new with download_events=1."""
    from company_wiki.source_catalog import ResolutionStatus

    catalog = _catalog(tmp_path)
    _policy_file(catalog, "a" * 64)
    adapter = _FakeAdapter()
    gap_hash, _ = _current_gap_hash(catalog, adapter)
    txn = _txn(tmp_path, adapter, catalog)
    result = txn.execute(
        _binding(gap_hash, policy_hash="a" * 64,
                  request_id=_request().request_id),
        _request())
    assert result.status == "completed"
    assert result.outcome == "downloaded_new"
    envelope = result.envelope
    assert envelope["outcome"] == "downloaded_new"
    assert envelope["download_events"] == 1
    assert result.resolution["status"] in (
        ResolutionStatus.REUSED_EXACT.value,
        ResolutionStatus.REUSED_EQUIVALENT.value)
