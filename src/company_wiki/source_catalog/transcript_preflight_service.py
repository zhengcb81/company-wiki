"""Typed, read-only transcript discovery and candidate preflight service."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from .acquisition import DownloadCandidate
from .authorization import DownloadAuthorization, build_download_authorization
from .provider_use_policy import ProviderUsePolicy
from .resolver import SourceRequest
from .transcript_fetch_admission import (
    TranscriptFetchAdmission,
    authorize_transcript_fetch,
)
from .transcript_tool_contract import MAX_PROVIDER_PAYLOAD_BYTES


DISCOVERY_PREFLIGHT_REQUEST = "company-wiki-transcript-discovery-preflight-request/1"
DISCOVERY_PREFLIGHT_RESPONSE = "company-wiki-transcript-discovery-preflight-response/1"
CANDIDATE_PREFLIGHT_REQUEST = "company-wiki-transcript-candidate-preflight-request/1"
CANDIDATE_PREFLIGHT_RESPONSE = "company-wiki-transcript-candidate-preflight-response/1"


@dataclass(frozen=True)
class DiscoveryPreflightCommand:
    request_id: str
    provider: str
    source_url: str
    market: str
    ticker: str
    exchange: str
    fiscal_year: int
    fiscal_quarter: int
    as_of_date: str


@dataclass(frozen=True)
class DiscoveryPreflightDecision:
    command: DiscoveryPreflightCommand
    allowed: bool
    reason: str
    rights_policy_sha256: str
    rights_evidence_sha256: str | None

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": DISCOVERY_PREFLIGHT_RESPONSE,
            "status": "allowed" if self.allowed else "denied",
            "allowed": self.allowed,
            "reason": self.reason,
            **self.command.__dict__,
            "rights_policy_sha256": self.rights_policy_sha256,
            "rights_evidence_sha256": self.rights_evidence_sha256,
        }


@dataclass(frozen=True)
class CandidatePreflightCommand:
    request: SourceRequest
    candidate: DownloadCandidate
    max_bytes: int
    expires_at: str


@dataclass(frozen=True)
class CandidatePreflightDecision:
    command: CandidatePreflightCommand
    admission: TranscriptFetchAdmission
    authorization: DownloadAuthorization
    plan_hash: str

    def to_dict(self) -> dict[str, object]:
        result: dict[str, object] = {
            "schema_version": CANDIDATE_PREFLIGHT_RESPONSE,
            "status": "allowed" if self.admission.allowed else "denied",
            "allowed": self.admission.allowed,
            "reason": self.admission.reason,
            "request_id": self.command.request.request_id,
            "candidate_id": self.command.candidate.candidate_id,
            "rights_policy_sha256": self.admission.rights_policy_sha256,
        }
        if self.admission.allowed:
            result.update(
                {
                    "source_request": self.command.request.to_dict(),
                    "candidate": self.command.candidate.to_dict(),
                    "download_authorization": self.authorization.to_dict(),
                    "preflight_admission": admission_dict(self.admission),
                    "plan_hash": self.plan_hash,
                }
            )
        return result


def admission_dict(admission: TranscriptFetchAdmission) -> dict[str, object]:
    return {
        "allowed": admission.allowed,
        "reason": admission.reason,
        "rights_policy_sha256": admission.rights_policy_sha256,
        "download_authorization_hash": admission.download_authorization_hash,
        "request_id": admission.request_id,
        "candidate_id": admission.candidate_id,
    }


def evaluate_discovery_preflight(
    command: DiscoveryPreflightCommand,
    *,
    rights_policy: ProviderUsePolicy,
    now_date: str,
) -> DiscoveryPreflightDecision:
    decision = rights_policy.decide(
        provider_id=command.provider,
        source_url=command.source_url,
        content_class="earnings_call_transcript",
        action="discover_metadata",
        on_date=now_date,
    )
    return DiscoveryPreflightDecision(
        command=command,
        allowed=decision.allowed,
        reason=decision.reason,
        rights_policy_sha256=decision.policy_sha256,
        rights_evidence_sha256=decision.rule_evidence_sha256,
    )


def _download_plan(command: CandidatePreflightCommand) -> tuple[dict, str]:
    plan = {
        "schema_version": "company-wiki-transcript-download-plan/1",
        "source_request": command.request.to_dict(),
        "candidate": command.candidate.to_dict(),
        "max_bytes": command.max_bytes,
        "expires_at": command.expires_at,
    }
    encoded = json.dumps(
        plan,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return plan, hashlib.sha256(encoded).hexdigest()


def evaluate_candidate_preflight(
    command: CandidatePreflightCommand,
    *,
    runtime_policy_hash: str,
    rights_policy: ProviderUsePolicy,
    now: str,
) -> CandidatePreflightDecision:
    if not 0 < command.max_bytes <= MAX_PROVIDER_PAYLOAD_BYTES:
        raise ValueError("max_bytes is outside the provider payload limit")
    _, plan_hash = _download_plan(command)
    authorization = build_download_authorization(
        request_id=command.request.request_id,
        gap_plan_hash=plan_hash,
        policy_hash=runtime_policy_hash,
        provider=command.candidate.provider,
        allowed_accessions=(command.candidate.provider_document_id,),
        max_items=1,
        max_bytes=command.max_bytes,
        expires_at=command.expires_at,
    )
    admission = authorize_transcript_fetch(
        request=command.request,
        candidate=command.candidate,
        authorization=authorization,
        plan_hash=plan_hash,
        runtime_policy_hash=runtime_policy_hash,
        rights_policy=rights_policy,
        now=now,
    )
    return CandidatePreflightDecision(
        command=command,
        admission=admission,
        authorization=authorization,
        plan_hash=plan_hash,
    )
