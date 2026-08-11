"""WU-4.3: authorization-bound minimal download (RED first).

The download authorization receipt binds:
- request_id + gap_plan hash (the plan being authorized),
- the exact provider + accessions allowed,
- item/byte caps,
- an expiry timestamp.

The downloader may only fetch items inside the plan AND allowed by the
receipt. Tampering with the accession, an expired plan, or exceeding caps
must be rejected. RED phase: the module does not exist (ImportError).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest


WIKI_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WIKI_ROOT / "src"))

from company_wiki.source_catalog.authorization import (  # noqa: E402
    DownloadAuthorization,
    build_download_authorization,
    validate_download_authorization,
)


def _plan_hash() -> str:
    return "a" * 64


def _policy_hash() -> str:
    return "b" * 64


class _Candidate:
    def __init__(self, accession: str, fiscal_year: int, size: int = 1_000_000):
        self.provider = "sec"
        self.provider_document_id = accession
        self.fiscal_year = fiscal_year
        self.remote_size = size

    def to_dict(self):
        return {"provider_document_id": self.provider_document_id,
                "fiscal_year": self.fiscal_year, "remote_size": self.remote_size}


def _auth(**overrides):
    base = dict(
        request_id="req-1",
        gap_plan_hash=_plan_hash(),
        policy_hash=_policy_hash(),
        provider="sec",
        allowed_accessions=("acc-2025",),
        max_items=1,
        max_bytes=5_000_000,
        expires_at="2026-08-08T23:59:59Z",
    )
    base.update(overrides)
    return build_download_authorization(**base)


def test_build_creates_receipt(tmp_path):
    auth = _auth()
    assert isinstance(auth, DownloadAuthorization)
    assert auth.provider == "sec"
    assert auth.allowed_accessions == ("acc-2025",)
    assert auth.max_items == 1


def test_receipt_hash_deterministic(tmp_path):
    a1 = _auth()
    a2 = _auth()
    assert a1.receipt_hash == a2.receipt_hash
    assert len(a1.receipt_hash) == 64


def test_validate_ok_for_allowed_candidate(tmp_path):
    auth = _auth()
    candidate = _Candidate("acc-2025", 2025)
    error = validate_download_authorization(
        auth, candidate, plan_hash=_plan_hash(), now="2026-08-08T12:00:00Z"
    )
    assert error is None


def test_validate_rejects_plan_hash_mismatch(tmp_path):
    auth = _auth()
    candidate = _Candidate("acc-2025", 2025)
    error = validate_download_authorization(
        auth, candidate, plan_hash="b" * 64, now="2026-08-08T12:00:00Z"
    )
    assert error is not None
    assert "plan" in error


def test_validate_rejects_unknown_accession(tmp_path):
    auth = _auth()
    candidate = _Candidate("acc-9999", 2025)
    error = validate_download_authorization(
        auth, candidate, plan_hash=_plan_hash(), now="2026-08-08T12:00:00Z"
    )
    assert error is not None
    assert "accession" in error


def test_validate_rejects_other_provider(tmp_path):
    """Reviewer finding: a candidate whose provider differs from the receipt
    must be rejected even when the accession collides."""
    auth = _auth()
    candidate = _Candidate("acc-2025", 2025)
    candidate.provider = "hkexnews"  # receipt says "sec"
    error = validate_download_authorization(
        auth, candidate, plan_hash=_plan_hash(), now="2026-08-08T12:00:00Z"
    )
    assert error is not None
    assert "provider" in error


def test_validate_rejects_expired(tmp_path):
    auth = _auth(expires_at="2026-08-08T10:00:00Z")
    candidate = _Candidate("acc-2025", 2025)
    error = validate_download_authorization(
        auth, candidate, plan_hash=_plan_hash(), now="2026-08-08T12:00:00Z"
    )
    assert error is not None
    assert "expired" in error


def test_validate_rejects_over_item_cap(tmp_path):
    auth = _auth(max_items=1)
    candidate = _Candidate("acc-2025", 2025)
    # simulated by the caller having already fetched 1 item
    error = validate_download_authorization(
        auth, candidate, plan_hash=_plan_hash(), now="2026-08-08T12:00:00Z",
        items_already_fetched=1,
    )
    assert error is not None
    assert "item" in error


def test_validate_rejects_over_byte_cap(tmp_path):
    auth = _auth(max_bytes=500_000)
    candidate = _Candidate("acc-2025", 2025, size=600_000)
    error = validate_download_authorization(
        auth, candidate, plan_hash=_plan_hash(), now="2026-08-08T12:00:00Z",
        bytes_already_fetched=100_000,
    )
    assert error is not None
    assert "byte" in error


def test_coordinator_authorized_download_proceeds(tmp_path):
    """An exact+allow_download request with a valid authorization for the
    discovered accession proceeds to staging (fetch=1)."""
    from company_wiki.source_catalog import (
        AcquisitionCoordinator,
        AcquisitionStatus,
        AdapterRegistry,
        CatalogConfig,
        DownloadCandidate,
        RootSpec,
        SourceCatalog,
        SourceRequest,
    )
    from company_wiki.source_catalog.authorization import build_download_authorization

    project = tmp_path / "project"
    companies = project / "companies"
    (companies / "ACME" / "raw").mkdir(parents=True)
    catalog = SourceCatalog(
        CatalogConfig(
            project_root=project,
            catalog_dir=project / ".source_catalog",
            roots=(RootSpec("company_raw", companies, "company_raw", priority=10),),
            reusable_root_kinds=("company_raw",),
        )
    )
    catalog.store.status()

    class FakeAdapter:
        name = "fake"
        version = "1.0.0"

        def discover(self, request):
            return (DownloadCandidate(
                candidate_id="c-2025", provider="sec",
                provider_document_id="acc-2025", market="US", entity="ACME",
                title="ACME 2025 annual",
                source_url="https://www.sec.gov/x/2025.pdf",
                document_kind="annual_report", filing_date="2026-04-15",
                fiscal_year=2025,
            ),)

        def fetch(self, candidate, staging_dir):
            staging_dir.mkdir(parents=True, exist_ok=True)
            path = staging_dir / "annual.pdf"
            body = b"%PDF-2025"
            path.write_bytes(body)
            import hashlib

            from company_wiki.source_catalog import DownloadReceipt

            return DownloadReceipt(
                candidate_id=candidate.candidate_id,
                provider=candidate.provider,
                provider_document_id=candidate.provider_document_id,
                source_url=candidate.source_url,
                staged_path=str(path),
                content_sha256=hashlib.sha256(body).hexdigest(),
                byte_size=len(body),
                mime_type="application/pdf",
                retrieved_at="2026-08-08T12:00:00Z",
                http_status=200,
                adapter_name="fake",
                adapter_version="1.0.0",
            )

    coordinator = AcquisitionCoordinator(
        catalog=catalog,
        adapters=AdapterRegistry(cn=FakeAdapter(), hk=FakeAdapter(), us=FakeAdapter()),
        staging_root=tmp_path / "staging",
    )
    auth = build_download_authorization(
        request_id="req-1",
        gap_plan_hash=_plan_hash(),
        policy_hash=_policy_hash(),
        provider="sec",
        allowed_accessions=("acc-2025",),
        max_items=1,
        max_bytes=5_000_000,
        expires_at="2099-01-01T00:00:00Z",
    )
    request = SourceRequest(
        entity="ACME", market="US", security_id="ACME",
        document_kind="annual_report", as_of_date="2026-07-31",
        allow_download=True,
    )
    result = coordinator.resolve_or_stage(request, authorization=auth)
    assert result.status is AcquisitionStatus.STAGED, result


def test_coordinator_rejects_unauthorized_accession(tmp_path):
    """An exact+allow_download request whose discovered accession is NOT in
    the receipt must fail closed (no fetch, no staging)."""
    from company_wiki.source_catalog import (
        AcquisitionCoordinator,
        AdapterRegistry,
        CatalogConfig,
        DownloadCandidate,
        RootSpec,
        SourceCatalog,
        SourceRequest,
    )
    from company_wiki.source_catalog.authorization import build_download_authorization

    project = tmp_path / "project"
    companies = project / "companies"
    (companies / "ACME" / "raw").mkdir(parents=True)
    catalog = SourceCatalog(
        CatalogConfig(
            project_root=project,
            catalog_dir=project / ".source_catalog",
            roots=(RootSpec("company_raw", companies, "company_raw", priority=10),),
            reusable_root_kinds=("company_raw",),
        )
    )
    catalog.store.status()

    class FakeAdapter:
        name = "fake"
        version = "1.0.0"

        def discover(self, request):
            return (DownloadCandidate(
                candidate_id="c-2025", provider="sec",
                provider_document_id="acc-2025", market="US", entity="ACME",
                title="ACME 2025 annual",
                source_url="https://www.sec.gov/x/2025.pdf",
                document_kind="annual_report", filing_date="2026-04-15",
                fiscal_year=2025,
            ),)

        def fetch(self, candidate, staging_dir):
            raise AssertionError("fetch must not be called")

    coordinator = AcquisitionCoordinator(
        catalog=catalog,
        adapters=AdapterRegistry(cn=FakeAdapter(), hk=FakeAdapter(), us=FakeAdapter()),
        staging_root=tmp_path / "staging",
    )
    auth = build_download_authorization(
        request_id="req-1",
        gap_plan_hash=_plan_hash(),
        policy_hash=_policy_hash(),
        provider="sec",
        allowed_accessions=("acc-9999",),  # NOT the discovered one
        max_items=1,
        max_bytes=5_000_000,
        expires_at="2099-01-01T00:00:00Z",
    )
    request = SourceRequest(
        entity="ACME", market="US", security_id="ACME",
        document_kind="annual_report", as_of_date="2026-07-31",
        allow_download=True,
    )
    from company_wiki.source_catalog.acquisition import AcquisitionError

    with pytest.raises(AcquisitionError) as exc:
        coordinator.resolve_or_stage(request, authorization=auth)
    assert "not authorized" in str(exc.value)
    assert not (tmp_path / "staging").exists()


def test_receipt_hash_binds_policy_hash():
    """FC-801 (CG-08): the receipt hash binds the policy_hash — a download
    authorized under a different policy has a different receipt."""
    a1 = _auth()
    a2 = _auth(policy_hash="c" * 64)
    assert a1.receipt_hash != a2.receipt_hash
    assert a2.policy_hash == "c" * 64


def test_build_requires_policy_hash():
    """FC-801: policy_hash is mandatory — a receipt without it is invalid."""
    import pytest

    with pytest.raises(ValueError, match="policy_hash"):
        build_download_authorization(
            request_id="req-1",
            gap_plan_hash=_plan_hash(),
            policy_hash="",
            provider="sec",
            allowed_accessions=("acc",),
            max_items=1,
            max_bytes=1_000_000,
            expires_at="2099-01-01T00:00:00Z",
        )
