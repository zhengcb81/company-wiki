"""Compatibility facade for transcript-tool canonical admission."""

from __future__ import annotations

from .acquisition import DownloadCandidate
from .authorization import DownloadAuthorization
from .canonical_writer import CanonicalSourceWriter
from .provider_use_policy import ProviderUsePolicy
from .resolver import SourceRequest
from .transcript_admission_service import (
    TranscriptAdmissionError,
    TranscriptAdmissionResult,
    admit_transcript_tool_result,
)
from .transcript_fetch_admission import TranscriptFetchAdmission
from .transcript_tool_contract import (
    MAX_PROVIDER_PAYLOAD_BYTES,
    MAX_TOOL_RESULT_BYTES,
    TRANSCRIPT_RESULT_SCHEMA,
)


class TranscriptImportError(ValueError):
    """A tool result is invalid, unapproved, or cannot be safely imported."""


TranscriptImportResult = TranscriptAdmissionResult


def import_transcript_tool_result(
    raw_result: bytes | str,
    *,
    request: SourceRequest,
    candidate: DownloadCandidate,
    authorization: DownloadAuthorization,
    preflight_admission: TranscriptFetchAdmission,
    plan_hash: str,
    runtime_policy_hash: str,
    current_rights_policy: ProviderUsePolicy,
    writer: CanonicalSourceWriter,
    now: str,
) -> TranscriptImportResult:
    """Admit one provider `/2` result while preserving the public error type."""
    try:
        return admit_transcript_tool_result(
            raw_result,
            request=request,
            candidate=candidate,
            authorization=authorization,
            preflight_admission=preflight_admission,
            plan_hash=plan_hash,
            runtime_policy_hash=runtime_policy_hash,
            current_rights_policy=current_rights_policy,
            writer=writer,
            now=now,
        )
    except TranscriptAdmissionError as exc:
        raise TranscriptImportError(str(exc)) from exc


__all__ = [
    "MAX_PROVIDER_PAYLOAD_BYTES",
    "MAX_TOOL_RESULT_BYTES",
    "TRANSCRIPT_RESULT_SCHEMA",
    "TranscriptImportError",
    "TranscriptImportResult",
    "import_transcript_tool_result",
]
