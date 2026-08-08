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


WIKI_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WIKI_ROOT / "src"))

from company_wiki.source_catalog.authorization import (  # noqa: E402
    DownloadAuthorization,
    build_download_authorization,
    validate_download_authorization,
)


def _plan_hash() -> str:
    return "a" * 64


class _Candidate:
    def __init__(self, accession: str, fiscal_year: int, size: int = 1_000_000):
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
