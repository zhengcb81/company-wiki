"""Pre-network admission for one exact transcript candidate."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime

from .acquisition import DownloadCandidate
from .authorization import DownloadAuthorization, validate_download_authorization
from .provider_use_policy import ProviderUsePolicy
from .resolver import SourceRequest
from .transcript_use_policy import authorize_transcript_actions


_FETCH_ACTIONS = ("automated_fetch", "retain_original", "derive_text")


@dataclass(frozen=True)
class TranscriptFetchAdmission:
    """Pre-network decision; an allowed result still requires post-fetch checks."""

    allowed: bool
    reason: str
    rights_policy_sha256: str | None
    download_authorization_hash: str | None
    request_id: str | None = None
    candidate_id: str | None = None


def _exact_transcript_request(request: SourceRequest) -> bool:
    return (
        request.market == "US"
        and request.document_kind == "investor_call_transcript"
        and request.fiscal_year is not None
        and request.fiscal_period in {"Q1", "Q2", "Q3", "Q4"}
        and request.security_id is not None
        and request.mode in (None, "exact")
    )


def _candidate_matches(request: SourceRequest, candidate: DownloadCandidate) -> bool:
    return (
        candidate.market == request.market
        and candidate.document_kind == request.document_kind
        and candidate.entity == request.entity
        and candidate.fiscal_year == request.fiscal_year
        and candidate.fiscal_period == request.fiscal_period
        and candidate.filing_date <= request.as_of_date
        and request.provider in (None, candidate.provider)
        and request.provider_document_id in (None, candidate.provider_document_id)
    )


def _candidate_security_matches(
    request: SourceRequest, candidate: DownloadCandidate
) -> bool:
    try:
        identity = json.loads(candidate.adapter_payload_json or "null")
    except json.JSONDecodeError:
        return False
    return (
        isinstance(identity, dict)
        and identity.get("security_id") == request.security_id
        and identity.get("market") == request.market
    )


def _canonical_timestamp(value: str) -> bool:
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except (TypeError, ValueError):
        return False
    return parsed.strftime("%Y-%m-%dT%H:%M:%SZ") == value


def _rights_reason(action: str | None, reason: str) -> str:
    if action is None or action == "automated_fetch":
        return "provider_rights_" + reason
    return "provider_rights_" + action + "_" + reason


def _request_candidate_issue(
    request: object, candidate: object, now: str
) -> str | None:
    if not isinstance(request, SourceRequest) or not isinstance(
        candidate, DownloadCandidate
    ):
        return "invalid_request_or_candidate"
    if not request.allow_download:
        return "download_not_authorized"
    if not _exact_transcript_request(request):
        return "request_not_exact_us_transcript"
    if not _candidate_matches(request, candidate):
        return "candidate_identity_mismatch"
    if not _candidate_security_matches(request, candidate):
        return "candidate_security_identity_missing"
    return None if _canonical_timestamp(now) else "invalid_now"


def _authorization_issue(
    authorization: object,
    *,
    request: SourceRequest,
    candidate: DownloadCandidate,
    plan_hash: str,
    runtime_policy_hash: str,
    now: str,
) -> str | None:
    if not isinstance(authorization, DownloadAuthorization):
        return "missing_download_authorization"
    if authorization.request_id != request.request_id:
        return "authorization_request_mismatch"
    if authorization.policy_hash != runtime_policy_hash:
        return "runtime_policy_hash_mismatch"
    issue = validate_download_authorization(
        authorization, candidate, plan_hash=plan_hash, now=now
    )
    return "download_authorization_rejected" if issue is not None else None


def authorize_transcript_fetch(
    *,
    request: SourceRequest,
    candidate: DownloadCandidate,
    authorization: DownloadAuthorization | None,
    plan_hash: str,
    runtime_policy_hash: str,
    rights_policy: ProviderUsePolicy | None,
    now: str,
) -> TranscriptFetchAdmission:
    """Bind user, exact-download and provider-use authorization before fetch."""
    rights_hash = (
        rights_policy.policy_sha256
        if isinstance(rights_policy, ProviderUsePolicy)
        else None
    )
    auth_hash = (
        authorization.receipt_hash
        if isinstance(authorization, DownloadAuthorization)
        else None
    )

    def deny(reason: str) -> TranscriptFetchAdmission:
        return TranscriptFetchAdmission(
            False,
            reason,
            rights_hash,
            auth_hash,
            request.request_id if isinstance(request, SourceRequest) else None,
            (
                candidate.candidate_id
                if isinstance(candidate, DownloadCandidate)
                else None
            ),
        )

    issue = _request_candidate_issue(request, candidate, now)
    if issue is not None:
        return deny(issue)
    assert isinstance(request, SourceRequest)
    assert isinstance(candidate, DownloadCandidate)
    issue = _authorization_issue(
        authorization,
        request=request,
        candidate=candidate,
        plan_hash=plan_hash,
        runtime_policy_hash=runtime_policy_hash,
        now=now,
    )
    if issue is not None:
        return deny(issue)
    assert isinstance(authorization, DownloadAuthorization)
    rights = authorize_transcript_actions(
        rights_policy=rights_policy,
        provider_id=candidate.provider,
        source_url=candidate.source_url,
        actions=_FETCH_ACTIONS,
        on_date=now[:10],
    )
    if not rights.allowed:
        if rights.reason == "missing_provider_use_policy":
            return deny(rights.reason)
        return deny(_rights_reason(rights.failed_action, rights.reason))
    return TranscriptFetchAdmission(
        True,
        "permitted",
        rights_hash,
        auth_hash,
        request.request_id,
        candidate.candidate_id,
    )
