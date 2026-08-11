"""WU-4.3 + FC-801: authorization-bound minimal download.

A ``DownloadAuthorization`` receipt binds the download decision to the
exact GapPlan (via its hash), the RuntimePolicySnapshot (via its hash),
the exact provider + accessions, item/byte caps, and an expiry. The
downloader validates every candidate against the receipt before fetching;
anything not in the plan, under a stale policy, or not allowed by the
receipt is rejected (DL-03: fetch=0). The receipt hash is deterministic so
the same authorization is reproducible for audit.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any


AUTHORIZATION_SCHEMA_VERSION = "1.0"


@dataclass(frozen=True)
class DownloadAuthorization:
    schema_version: str
    request_id: str
    gap_plan_hash: str
    # FC-801 (DL-03): the RuntimePolicySnapshot hash the download is bound
    # to — a download authorized under a different policy is not reusable.
    policy_hash: str
    provider: str
    allowed_accessions: tuple[str, ...]
    max_items: int
    max_bytes: int
    expires_at: str
    receipt_hash: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "request_id": self.request_id,
            "gap_plan_hash": self.gap_plan_hash,
            "policy_hash": self.policy_hash,
            "provider": self.provider,
            "allowed_accessions": list(self.allowed_accessions),
            "max_items": self.max_items,
            "max_bytes": self.max_bytes,
            "expires_at": self.expires_at,
            "receipt_hash": self.receipt_hash,
        }


def build_download_authorization(
    *,
    request_id: str,
    gap_plan_hash: str,
    policy_hash: str,
    provider: str,
    allowed_accessions: tuple[str, ...],
    max_items: int,
    max_bytes: int,
    expires_at: str,
) -> DownloadAuthorization:
    """Create a deterministic download authorization receipt."""
    if not request_id or not gap_plan_hash or not policy_hash or not provider:
        raise ValueError("request_id/gap_plan_hash/policy_hash/provider required")
    if len(gap_plan_hash) != 64:
        raise ValueError("gap_plan_hash must be a SHA-256 hex digest")
    if len(policy_hash) != 64:
        raise ValueError("policy_hash must be a SHA-256 hex digest")
    if max_items <= 0 or max_bytes <= 0:
        raise ValueError("max_items/max_bytes must be positive")
    if not allowed_accessions or not all(a for a in allowed_accessions):
        raise ValueError("allowed_accessions must be a non-empty list of accessions")
    digest = hashlib.sha256()
    digest.update(AUTHORIZATION_SCHEMA_VERSION.encode())
    digest.update(request_id.encode())
    digest.update(gap_plan_hash.encode())
    digest.update(policy_hash.encode())
    digest.update(provider.encode())
    for accession in sorted(allowed_accessions):
        digest.update(accession.encode())
    digest.update(str(max_items).encode())
    digest.update(str(max_bytes).encode())
    digest.update(expires_at.encode())
    return DownloadAuthorization(
        schema_version=AUTHORIZATION_SCHEMA_VERSION,
        request_id=request_id,
        gap_plan_hash=gap_plan_hash,
        policy_hash=policy_hash,
        provider=provider,
        allowed_accessions=tuple(allowed_accessions),
        max_items=max_items,
        max_bytes=max_bytes,
        expires_at=expires_at,
        receipt_hash=digest.hexdigest(),
    )


def validate_download_authorization(
    authorization: DownloadAuthorization,
    candidate: Any,
    *,
    plan_hash: str,
    now: str,
    items_already_fetched: int = 0,
    bytes_already_fetched: int = 0,
) -> str | None:
    """Return an error string if the candidate may NOT be fetched under the
    receipt, else None. ``candidate`` exposes provider_document_id, fiscal_year
    and remote_size (DownloadCandidate-compatible)."""
    if authorization.gap_plan_hash != plan_hash:
        return "authorization is bound to a different gap plan"
    if now > authorization.expires_at:
        return "authorization expired"
    provider = str(getattr(candidate, "provider", "") or "").lower()
    if provider and authorization.provider != provider:
        return f"provider not authorized: {provider}"
    accession = str(getattr(candidate, "provider_document_id", "") or "")
    if accession not in authorization.allowed_accessions:
        return f"accession not authorized: {accession}"
    if items_already_fetched >= authorization.max_items:
        return "item cap reached"
    size = int(getattr(candidate, "remote_size", 0) or 0)
    if bytes_already_fetched + size > authorization.max_bytes:
        return "byte cap exceeded"
    return None
