"""Application service for one authorized transcript raw admission."""

from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from .acquisition import DownloadCandidate, DownloadReceipt
from .authorization import DownloadAuthorization
from .canonical_writer import CanonicalImportResult, CanonicalSourceWriter
from .provider_use_policy import ProviderUsePolicy
from .resolver import SourceRequest
from .transcript_fetch_admission import TranscriptFetchAdmission
from .transcript_fetch_validation import validate_transcript_fetch_result
from .transcript_material import (
    TranscriptMaterial,
    TranscriptMaterialError,
    extract_transcript_material,
)
from .transcript_tool_contract import (
    TranscriptToolContractError,
    ValidatedTranscriptPayload,
    parse_transcript_tool_result,
)


class TranscriptAdmissionError(ValueError):
    """The authorized result could not be admitted as canonical raw."""


@dataclass(frozen=True)
class TranscriptAdmissionResult:
    canonical_import: CanonicalImportResult
    material: TranscriptMaterial
    rights_policy_sha256: str
    download_authorization_hash: str
    provider_payload_sha256: str
    provider_extraction_version: str


def _preflight_issue(
    admission: object,
    request: SourceRequest,
    candidate: DownloadCandidate,
    authorization: DownloadAuthorization,
) -> str | None:
    if not isinstance(admission, TranscriptFetchAdmission):
        return "missing pre-fetch authorization evidence"
    if (
        not admission.allowed
        or admission.request_id != request.request_id
        or admission.candidate_id != candidate.candidate_id
        or admission.download_authorization_hash != authorization.receipt_hash
        or not admission.rights_policy_sha256
    ):
        return "pre-fetch authorization does not bind this candidate"
    return None


def _stage_original(
    writer: CanonicalSourceWriter, payload: ValidatedTranscriptPayload
) -> Path:
    root = writer.staging_root
    root.mkdir(parents=True, exist_ok=True)
    if not root.is_dir() or root.is_symlink():
        raise TranscriptAdmissionError("allocated staging root is unsafe")
    suffix = ".html" if payload.mime_type != "text/plain" else ".txt"
    fd, path_text = tempfile.mkstemp(prefix="transcript-", suffix=suffix, dir=root)
    with open(fd, "wb", closefd=True) as stream:
        stream.write(payload.original)
        stream.flush()
    return Path(path_text)


def _receipt(
    payload: ValidatedTranscriptPayload,
    candidate: DownloadCandidate,
    staged: Path,
) -> DownloadReceipt:
    return DownloadReceipt(
        candidate_id=candidate.candidate_id,
        provider=candidate.provider,
        provider_document_id=candidate.provider_document_id,
        source_url=candidate.source_url,
        staged_path=str(staged),
        content_sha256=payload.provider_payload_sha256,
        byte_size=len(payload.original),
        mime_type=payload.mime_type,
        retrieved_at=payload.retrieved_at,
        http_status=payload.http_status,
        adapter_name=payload.adapter_name,
        adapter_version=payload.adapter_version,
        etag=candidate.etag,
        last_modified=candidate.last_modified,
    )


def _validate_material_claims(
    material: TranscriptMaterial, payload: ValidatedTranscriptPayload
) -> None:
    if material.text_sha256 != payload.canonical_content_sha256:
        raise TranscriptAdmissionError("canonical transcript text SHA-256 mismatch")
    if material.text_byte_size != payload.content_bytes:
        raise TranscriptAdmissionError("canonical transcript text byte size mismatch")


def _audit_extension(
    payload: ValidatedTranscriptPayload,
    material: TranscriptMaterial,
    rights_policy_sha256: str | None,
    authorization: DownloadAuthorization,
) -> dict[str, object]:
    return {
        "transcript_acquisition": {
            "schema_version": "transcript-acquisition-audit/1",
            "provider_payload_sha256": payload.provider_payload_sha256,
            "provider_extraction_version": payload.extraction_version,
            "effective_url": payload.effective_url,
            "http_status": payload.http_status,
            "retrieved_at": payload.retrieved_at,
            "rights_policy_sha256": rights_policy_sha256,
            "download_authorization_hash": authorization.receipt_hash,
            "validated_actions": [
                "automated_fetch",
                "retain_original",
                "derive_text",
            ],
            "derived_extractor_version": material.extractor_version,
        }
    }


def _remove_staged(staged: Path | None, root: Path) -> None:
    if staged is None or not staged.exists():
        return
    if staged.is_symlink():
        raise TranscriptAdmissionError("refusing to remove unsafe staged path")
    try:
        resolved = staged.resolve(strict=True)
        resolved.relative_to(root.resolve(strict=True))
    except (OSError, ValueError) as exc:
        raise TranscriptAdmissionError(
            "refusing to remove staged path outside allocated root"
        ) from exc
    resolved.unlink()


def _validate_inputs(
    *,
    request: object,
    candidate: object,
    authorization: object,
    preflight_admission: object,
    current_rights_policy: object,
    writer: object,
) -> None:
    if not all(
        (
            isinstance(request, SourceRequest),
            isinstance(candidate, DownloadCandidate),
            isinstance(authorization, DownloadAuthorization),
            isinstance(writer, CanonicalSourceWriter),
        )
    ):
        raise TranscriptAdmissionError(
            "request, candidate, authorization and writer are required"
        )
    typed_request = cast(SourceRequest, request)
    typed_candidate = cast(DownloadCandidate, candidate)
    typed_authorization = cast(DownloadAuthorization, authorization)
    if (
        typed_authorization.max_bytes <= 0
        or typed_authorization.request_id != typed_request.request_id
    ):
        raise TranscriptAdmissionError(
            "download authorization does not bind this request"
        )
    issue = _preflight_issue(
        preflight_admission,
        typed_request,
        typed_candidate,
        typed_authorization,
    )
    if issue is not None:
        raise TranscriptAdmissionError(issue)
    if not isinstance(current_rights_policy, ProviderUsePolicy):
        raise TranscriptAdmissionError("current rights policy is unavailable")
    typed_admission = cast(TranscriptFetchAdmission, preflight_admission)
    if current_rights_policy.policy_sha256 != typed_admission.rights_policy_sha256:
        raise TranscriptAdmissionError("provider-use policy changed during fetch")


def _payload_and_material(
    raw_result: bytes | str,
    *,
    request: SourceRequest,
    candidate: DownloadCandidate,
    authorization: DownloadAuthorization,
) -> tuple[ValidatedTranscriptPayload, TranscriptMaterial]:
    try:
        payload = parse_transcript_tool_result(
            raw_result,
            request=request,
            candidate=candidate,
            authorization=authorization,
        )
    except TranscriptToolContractError as exc:
        raise TranscriptAdmissionError(str(exc)) from exc
    try:
        material = extract_transcript_material(
            payload.original, mime_type=payload.mime_type
        )
    except TranscriptMaterialError as exc:
        raise TranscriptAdmissionError(str(exc)) from exc
    _validate_material_claims(material, payload)
    return payload, material


def admit_transcript_tool_result(
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
) -> TranscriptAdmissionResult:
    _validate_inputs(
        request=request,
        candidate=candidate,
        authorization=authorization,
        preflight_admission=preflight_admission,
        current_rights_policy=current_rights_policy,
        writer=writer,
    )
    payload, material = _payload_and_material(
        raw_result,
        request=request,
        candidate=candidate,
        authorization=authorization,
    )
    rights_policy_sha256 = preflight_admission.rights_policy_sha256
    if not rights_policy_sha256:
        raise TranscriptAdmissionError("pre-fetch policy pin is missing")
    staged: Path | None = None
    try:
        staged = _stage_original(writer, payload)
        receipt = _receipt(payload, candidate, staged)
        validation = validate_transcript_fetch_result(
            request=request,
            candidate=candidate,
            receipt=receipt,
            authorization=authorization,
            plan_hash=plan_hash,
            runtime_policy_hash=runtime_policy_hash,
            pinned_rights_policy_sha256=rights_policy_sha256,
            current_rights_policy=current_rights_policy,
            final_url=payload.effective_url,
            staging_root=writer.staging_root,
            now=now,
        )
        if not validation.allowed:
            raise TranscriptAdmissionError(
                "post-fetch validation denied: " + validation.reason
            )
        imported = writer.import_staged(
            request,
            candidate,
            receipt,
            provenance_extensions=_audit_extension(
                payload,
                material,
                validation.rights_policy_sha256,
                authorization,
            ),
        )
        if imported.source_id != material.original_source_id:
            raise TranscriptAdmissionError(
                "canonical source identity differs from transcript material"
            )
        return TranscriptAdmissionResult(
            canonical_import=imported,
            material=material,
            rights_policy_sha256=validation.rights_policy_sha256 or "",
            download_authorization_hash=authorization.receipt_hash,
            provider_payload_sha256=payload.provider_payload_sha256,
            provider_extraction_version=payload.extraction_version,
        )
    finally:
        _remove_staged(staged, writer.staging_root)
