"""Post-fetch transcript receipt and staged-byte validation."""

from __future__ import annotations

import hashlib
import stat
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .acquisition import DownloadCandidate, DownloadReceipt
from .authorization import DownloadAuthorization
from .provider_use_policy import ProviderUsePolicy
from .resolver import SourceRequest
from .transcript_fetch_admission import authorize_transcript_fetch
from .transcript_use_policy import authorize_transcript_actions


_FETCH_ACTIONS = ("automated_fetch", "retain_original", "derive_text")
_MIME_TYPES = frozenset({"text/html", "application/xhtml+xml", "text/plain"})


@dataclass(frozen=True)
class TranscriptFetchValidation:
    """Post-fetch proof before any transcript bytes become canonical raw."""

    allowed: bool
    reason: str
    rights_policy_sha256: str | None
    download_authorization_hash: str | None
    content_sha256: str | None = None
    final_url: str | None = None
    mime_type: str | None = None
    byte_size: int | None = None


def _receipt_issue(
    receipt: DownloadReceipt,
    candidate: DownloadCandidate,
    authorization: DownloadAuthorization | None,
) -> str | None:
    if not _receipt_identity_matches(receipt, candidate):
        return "download_receipt_identity_mismatch"
    if not 200 <= receipt.http_status < 300:
        return "download_receipt_http_status_not_successful"
    if receipt.mime_type not in _MIME_TYPES:
        return "unsupported_transcript_mime_type"
    if authorization is None or receipt.byte_size > authorization.max_bytes:
        return "downloaded_bytes_exceed_authorized_cap"
    return None


def _receipt_identity_matches(
    receipt: DownloadReceipt, candidate: DownloadCandidate
) -> bool:
    return not (
        receipt.candidate_id != candidate.candidate_id
        or receipt.provider != candidate.provider
        or receipt.provider_document_id != candidate.provider_document_id
        or receipt.source_url != candidate.source_url
    )


def _timestamp_issue(received: str, checked: str) -> str | None:
    try:
        received_at = datetime.strptime(received, "%Y-%m-%dT%H:%M:%SZ")
        checked_at = datetime.strptime(checked, "%Y-%m-%dT%H:%M:%SZ")
    except (TypeError, ValueError):
        return "invalid_fetch_timestamp"
    return "download_receipt_from_future" if received_at > checked_at else None


def _staged_file(
    receipt: DownloadReceipt, staging_root: Path
) -> tuple[Path | None, str | None]:
    try:
        root = staging_root.resolve(strict=True)
    except OSError:
        return None, "allocated_staging_root_unavailable"
    staged = Path(receipt.staged_path)
    try:
        resolved = staged.resolve(strict=True)
        resolved.relative_to(root)
    except (OSError, ValueError):
        return None, "staged_file_outside_allocated_root"
    try:
        file_stat = resolved.stat()
    except OSError:
        return None, "staged_file_unavailable"
    if staged.is_symlink() or not stat.S_ISREG(file_stat.st_mode):
        return None, "staged_file_not_regular"
    if file_stat.st_size != receipt.byte_size:
        return None, "staged_file_size_mismatch"
    return resolved, None


def _sha_issue(path: Path, expected: str) -> str | None:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError:
        return "staged_file_unavailable"
    return None if digest.hexdigest() == expected else "staged_file_sha256_mismatch"


def _final_rights_issue(
    policy: ProviderUsePolicy, candidate: DownloadCandidate, final_url: str, now: str
) -> str | None:
    rights = authorize_transcript_actions(
        rights_policy=policy,
        provider_id=candidate.provider,
        source_url=final_url,
        actions=_FETCH_ACTIONS,
        on_date=now[:10],
    )
    if rights.allowed:
        return None
    action = rights.failed_action or "automated_fetch"
    return "final_url_rights_" + action + "_" + rights.reason


def _prevalidation_issue(
    *,
    request: SourceRequest,
    candidate: DownloadCandidate,
    receipt: object,
    authorization: DownloadAuthorization | None,
    plan_hash: str,
    runtime_policy_hash: str,
    pinned_rights_policy_sha256: str,
    current_rights_policy: object,
    staging_root: object,
    now: str,
) -> str | None:
    if not isinstance(receipt, DownloadReceipt):
        return "invalid_download_receipt"
    if not isinstance(staging_root, Path):
        return "invalid_staging_root"
    if not isinstance(current_rights_policy, ProviderUsePolicy):
        return "missing_current_provider_use_policy"
    if current_rights_policy.policy_sha256 != pinned_rights_policy_sha256:
        return "provider_use_policy_changed_during_fetch"
    admission = authorize_transcript_fetch(
        request=request,
        candidate=candidate,
        authorization=authorization,
        plan_hash=plan_hash,
        runtime_policy_hash=runtime_policy_hash,
        rights_policy=current_rights_policy,
        now=now,
    )
    return None if admission.allowed else "post_fetch_" + admission.reason


def _receipt_and_time_issue(
    receipt: DownloadReceipt,
    candidate: DownloadCandidate,
    authorization: DownloadAuthorization | None,
    now: str,
) -> str | None:
    return _receipt_issue(receipt, candidate, authorization) or _timestamp_issue(
        receipt.retrieved_at, now
    )


def _staged_content_issue(
    receipt: DownloadReceipt, staging_root: Path
) -> str | None:
    staged, issue = _staged_file(receipt, staging_root)
    if issue or staged is None:
        return issue or "staged_file_unavailable"
    return _sha_issue(staged, receipt.content_sha256)


def validate_transcript_fetch_result(
    *,
    request: SourceRequest,
    candidate: DownloadCandidate,
    receipt: DownloadReceipt,
    authorization: DownloadAuthorization | None,
    plan_hash: str,
    runtime_policy_hash: str,
    pinned_rights_policy_sha256: str,
    current_rights_policy: ProviderUsePolicy | None,
    final_url: str,
    staging_root: Path,
    now: str,
) -> TranscriptFetchValidation:
    """Revalidate policy, response identity and exact bytes after fetch."""
    policy_hash = (
        current_rights_policy.policy_sha256
        if isinstance(current_rights_policy, ProviderUsePolicy)
        else None
    )
    auth_hash = (
        authorization.receipt_hash
        if isinstance(authorization, DownloadAuthorization)
        else None
    )

    def deny(reason: str) -> TranscriptFetchValidation:
        return TranscriptFetchValidation(
            False,
            reason,
            policy_hash,
            auth_hash,
            final_url=final_url if isinstance(final_url, str) else None,
        )

    issue = _prevalidation_issue(
        request=request,
        candidate=candidate,
        receipt=receipt,
        authorization=authorization,
        plan_hash=plan_hash,
        runtime_policy_hash=runtime_policy_hash,
        pinned_rights_policy_sha256=pinned_rights_policy_sha256,
        current_rights_policy=current_rights_policy,
        staging_root=staging_root,
        now=now,
    )
    if issue is not None:
        return deny(issue)
    assert isinstance(receipt, DownloadReceipt)
    assert isinstance(staging_root, Path)
    assert isinstance(current_rights_policy, ProviderUsePolicy)
    issue = _receipt_and_time_issue(receipt, candidate, authorization, now)
    if issue is not None:
        return deny(issue)
    issue = _staged_content_issue(receipt, staging_root)
    if issue is not None:
        return deny(issue)
    issue = _final_rights_issue(
        current_rights_policy,
        candidate,
        final_url,
        now,
    )
    if issue is not None:
        return deny(issue)
    return TranscriptFetchValidation(
        True,
        "permitted",
        policy_hash,
        auth_hash,
        receipt.content_sha256,
        final_url,
        receipt.mime_type,
        receipt.byte_size,
    )
