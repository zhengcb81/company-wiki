"""Fail-closed stdin bridge for importing one authorized transcript result.

This command is a post-fetch importer. Its trusted parent must perform source
discovery and exact candidate authorization before starting the transcript
provider process. The CLI independently rechecks the current runtime and
rights policies before committing any bytes.
"""

from __future__ import annotations

import argparse
from dataclasses import fields
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any, BinaryIO, TypeVar

from .acquisition import DownloadCandidate
from .authorization import build_download_authorization
from .canonical_writer import CanonicalSourceWriter
from .config import load_catalog_config
from .provider_use_policy import (
    ProviderUsePolicyError,
    TranscriptFetchAdmission,
    authorize_transcript_fetch,
    load_provider_use_policy,
)
from .resolver import SourceRequest
from .runtime_policy import RuntimePolicyError, load_runtime_policy
from .service import SourceCatalog
from .transcript_import import (
    MAX_TOOL_RESULT_BYTES,
    TranscriptImportError,
    import_transcript_tool_result,
)


REQUEST_SCHEMA = "company-wiki-transcript-import-request/1"
RESPONSE_SCHEMA = "company-wiki-transcript-import-response/1"
DISCOVERY_PREFLIGHT_REQUEST = "company-wiki-transcript-discovery-preflight-request/1"
DISCOVERY_PREFLIGHT_RESPONSE = "company-wiki-transcript-discovery-preflight-response/1"
CANDIDATE_PREFLIGHT_REQUEST = "company-wiki-transcript-candidate-preflight-request/1"
CANDIDATE_PREFLIGHT_RESPONSE = "company-wiki-transcript-candidate-preflight-response/1"
MAX_ENVELOPE_BYTES = MAX_TOOL_RESULT_BYTES + 128 * 1024
MAX_PREFLIGHT_BYTES = 128 * 1024
MAX_PROVIDER_PAYLOAD_BYTES = 16 * 1024 * 1024
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_ENVELOPE_FIELDS = frozenset(
    {
        "schema_version",
        "source_request",
        "candidate",
        "download_authorization",
        "preflight_admission",
        "plan_hash",
        "transcript_result",
    }
)
_AUTHORIZATION_FIELDS = frozenset(
    {
        "schema_version",
        "request_id",
        "gap_plan_hash",
        "policy_hash",
        "provider",
        "allowed_accessions",
        "max_items",
        "max_bytes",
        "expires_at",
        "receipt_hash",
    }
)
_ADMISSION_FIELDS = frozenset(
    {
        "allowed",
        "reason",
        "rights_policy_sha256",
        "download_authorization_hash",
        "request_id",
        "candidate_id",
    }
)
_T = TypeVar("_T")


class TranscriptImportCliError(ValueError):
    """Input is invalid or lacks current authorization for import."""


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise TranscriptImportCliError("duplicate JSON object key")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise TranscriptImportCliError(f"invalid JSON constant: {value}")


def _read_envelope(stream: BinaryIO) -> dict[str, Any]:
    raw = stream.read(MAX_ENVELOPE_BYTES + 1)
    if not raw or len(raw) > MAX_ENVELOPE_BYTES:
        raise TranscriptImportCliError("stdin envelope is empty or oversized")
    try:
        value = json.loads(
            raw.decode("utf-8", errors="strict"),
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise TranscriptImportCliError("stdin envelope is invalid UTF-8 JSON") from exc
    if not isinstance(value, dict) or set(value) != _ENVELOPE_FIELDS:
        raise TranscriptImportCliError("stdin envelope fields differ from schema")
    if value["schema_version"] != REQUEST_SCHEMA:
        raise TranscriptImportCliError("unsupported stdin envelope schema")
    return value


def _read_preflight(stream: BinaryIO, *, expected_schema: str, fields_expected: frozenset[str]) -> dict[str, Any]:
    raw = stream.read(MAX_PREFLIGHT_BYTES + 1)
    if not raw or len(raw) > MAX_PREFLIGHT_BYTES:
        raise TranscriptImportCliError("preflight input is empty or oversized")
    try:
        value = json.loads(
            raw.decode("utf-8", errors="strict"),
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise TranscriptImportCliError("preflight input is invalid UTF-8 JSON") from exc
    if not isinstance(value, dict) or set(value) != fields_expected:
        raise TranscriptImportCliError("preflight input fields differ from schema")
    if value["schema_version"] != expected_schema:
        raise TranscriptImportCliError("unsupported preflight schema")
    return value


def _wiki_policy_context(wiki_root: Path) -> tuple[Path, Any, Any, Any]:
    root = wiki_root.resolve(strict=True)
    if not root.is_dir():
        raise TranscriptImportCliError("wiki root is not a directory")
    config = load_catalog_config(root / "config" / "source_catalog.yaml", project_root=root)
    runtime_policy = load_runtime_policy(config.catalog_dir / "runtime_policy.json")
    rights_policy = load_provider_use_policy(root / "config" / "provider_use_policy.json")
    return root, config, runtime_policy, rights_policy


def _date_text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not _DATE.fullmatch(value):
        raise TranscriptImportCliError(f"invalid {name}")
    try:
        parsed = datetime.strptime(value, "%Y-%m-%d")
    except ValueError as exc:
        raise TranscriptImportCliError(f"invalid {name}") from exc
    if parsed.strftime("%Y-%m-%d") != value:
        raise TranscriptImportCliError(f"invalid {name}")
    return value


def _admission_dict(admission: TranscriptFetchAdmission) -> dict[str, Any]:
    return {
        "allowed": admission.allowed,
        "reason": admission.reason,
        "rights_policy_sha256": admission.rights_policy_sha256,
        "download_authorization_hash": admission.download_authorization_hash,
        "request_id": admission.request_id,
        "candidate_id": admission.candidate_id,
    }


def run_discovery_preflight(wiki_root: Path, stream: BinaryIO) -> dict[str, Any]:
    fields_expected = frozenset(
        {
            "schema_version", "request_id", "provider", "source_url", "market",
            "ticker", "exchange", "fiscal_year", "fiscal_quarter", "as_of_date",
        }
    )
    value = _read_preflight(
        stream, expected_schema=DISCOVERY_PREFLIGHT_REQUEST, fields_expected=fields_expected
    )
    request_id = value["request_id"]
    provider = value["provider"]
    source_url = value["source_url"]
    if not isinstance(request_id, str) or not request_id or len(request_id) > 256:
        raise TranscriptImportCliError("invalid request_id")
    if not isinstance(provider, str) or not provider or provider != provider.strip():
        raise TranscriptImportCliError("invalid provider")
    if not isinstance(source_url, str) or not source_url:
        raise TranscriptImportCliError("invalid source_url")
    if value["market"] != "US":
        raise TranscriptImportCliError("transcript discovery requires a US security")
    if not isinstance(value["ticker"], str) or not value["ticker"]:
        raise TranscriptImportCliError("invalid ticker")
    if value["exchange"] not in {"NYSE", "NASDAQ"}:
        raise TranscriptImportCliError("exchange must be NYSE or NASDAQ")
    if type(value["fiscal_year"]) is not int or not 1900 <= value["fiscal_year"] <= 2200:
        raise TranscriptImportCliError("invalid fiscal_year")
    if type(value["fiscal_quarter"]) is not int or value["fiscal_quarter"] not in {1, 2, 3, 4}:
        raise TranscriptImportCliError("invalid fiscal_quarter")
    as_of_date = _date_text(value["as_of_date"], "as_of_date")
    _, _, _, rights_policy = _wiki_policy_context(wiki_root)
    decision = rights_policy.decide(
        provider_id=provider,
        source_url=source_url,
        content_class="earnings_call_transcript",
        action="discover_metadata",
        on_date=datetime.now(timezone.utc).date().isoformat(),
    )
    return {
        "schema_version": DISCOVERY_PREFLIGHT_RESPONSE,
        "status": "allowed" if decision.allowed else "denied",
        "allowed": decision.allowed,
        "reason": decision.reason,
        "request_id": request_id,
        "provider": provider,
        "source_url": source_url,
        "market": value["market"],
        "ticker": value["ticker"],
        "exchange": value["exchange"],
        "fiscal_year": value["fiscal_year"],
        "fiscal_quarter": value["fiscal_quarter"],
        "as_of_date": as_of_date,
        "rights_policy_sha256": decision.policy_sha256,
        "rights_evidence_sha256": decision.rule_evidence_sha256,
    }


def run_candidate_preflight(wiki_root: Path, stream: BinaryIO) -> dict[str, Any]:
    fields_expected = frozenset(
        {"schema_version", "source_request", "candidate", "max_bytes", "expires_at"}
    )
    value = _read_preflight(
        stream, expected_schema=CANDIDATE_PREFLIGHT_REQUEST, fields_expected=fields_expected
    )
    request = _dataclass_from_object(SourceRequest, value["source_request"], "source_request")
    candidate = _dataclass_from_object(DownloadCandidate, value["candidate"], "candidate")
    max_bytes = value["max_bytes"]
    if type(max_bytes) is not int or not 0 < max_bytes <= MAX_PROVIDER_PAYLOAD_BYTES:
        raise TranscriptImportCliError("max_bytes is outside the provider payload limit")
    expires_at = value["expires_at"]
    if not isinstance(expires_at, str):
        raise TranscriptImportCliError("invalid expires_at")
    try:
        expiry = datetime.strptime(expires_at, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as exc:
        raise TranscriptImportCliError("invalid expires_at") from exc
    if expiry.strftime("%Y-%m-%dT%H:%M:%SZ") != expires_at:
        raise TranscriptImportCliError("invalid expires_at")

    _, _, runtime_policy, rights_policy = _wiki_policy_context(wiki_root)
    plan = {
        "schema_version": "company-wiki-transcript-download-plan/1",
        "source_request": request.to_dict(),
        "candidate": candidate.to_dict(),
        "max_bytes": max_bytes,
        "expires_at": expires_at,
    }
    plan_bytes = json.dumps(
        plan, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    plan_hash = hashlib.sha256(plan_bytes).hexdigest()
    runtime_hash = runtime_policy["snapshot_sha256"]
    authorization = build_download_authorization(
        request_id=request.request_id,
        gap_plan_hash=plan_hash,
        policy_hash=runtime_hash,
        provider=candidate.provider,
        allowed_accessions=(candidate.provider_document_id,),
        max_items=1,
        max_bytes=max_bytes,
        expires_at=expires_at,
    )
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    admission = authorize_transcript_fetch(
        request=request,
        candidate=candidate,
        authorization=authorization,
        plan_hash=plan_hash,
        runtime_policy_hash=runtime_hash,
        rights_policy=rights_policy,
        now=now,
    )
    result: dict[str, Any] = {
        "schema_version": CANDIDATE_PREFLIGHT_RESPONSE,
        "status": "allowed" if admission.allowed else "denied",
        "allowed": admission.allowed,
        "reason": admission.reason,
        "request_id": request.request_id,
        "candidate_id": candidate.candidate_id,
        "rights_policy_sha256": admission.rights_policy_sha256,
    }
    if admission.allowed:
        result.update(
            {
                "source_request": request.to_dict(),
                "candidate": candidate.to_dict(),
                "download_authorization": authorization.to_dict(),
                "preflight_admission": _admission_dict(admission),
                "plan_hash": plan_hash,
            }
        )
    return result


def _dataclass_from_object(cls: type[_T], value: Any, name: str) -> _T:
    expected = {item.name for item in fields(cls) if item.init}
    if not isinstance(value, dict) or set(value) != expected:
        raise TranscriptImportCliError(f"{name} fields differ from schema")
    try:
        return cls(**value)
    except (TypeError, ValueError) as exc:
        raise TranscriptImportCliError(f"{name} is invalid") from exc


def _authorization_from_object(
    value: Any,
    *,
    request: SourceRequest,
    candidate: DownloadCandidate,
    plan_hash: str,
    runtime_policy_hash: str,
) -> Any:
    if not isinstance(value, dict) or set(value) != _AUTHORIZATION_FIELDS:
        raise TranscriptImportCliError("download authorization fields differ from schema")
    accessions = value["allowed_accessions"]
    if (
        not isinstance(accessions, list)
        or len(accessions) != 1
        or not all(isinstance(item, str) and item for item in accessions)
        or accessions != [candidate.provider_document_id]
        or type(value["max_items"]) is not int
        or value["max_items"] != 1
        or type(value["max_bytes"]) is not int
    ):
        raise TranscriptImportCliError("authorization is not bound to one exact candidate")
    if (
        value["request_id"] != request.request_id
        or value["gap_plan_hash"] != plan_hash
        or value["policy_hash"] != runtime_policy_hash
        or value["provider"] != candidate.provider
    ):
        raise TranscriptImportCliError("download authorization identity mismatch")
    try:
        authorization = build_download_authorization(
            request_id=value["request_id"],
            gap_plan_hash=value["gap_plan_hash"],
            policy_hash=value["policy_hash"],
            provider=value["provider"],
            allowed_accessions=tuple(accessions),
            max_items=value["max_items"],
            max_bytes=value["max_bytes"],
            expires_at=value["expires_at"],
        )
    except (TypeError, ValueError) as exc:
        raise TranscriptImportCliError("download authorization is invalid") from exc
    if authorization.to_dict() != value:
        raise TranscriptImportCliError("download authorization receipt hash mismatch")
    return authorization


def _admission_from_object(
    value: Any,
    *,
    request: SourceRequest,
    candidate: DownloadCandidate,
    authorization: Any,
    plan_hash: str,
    runtime_policy_hash: str,
    rights_policy: Any,
    now: str,
) -> TranscriptFetchAdmission:
    if not isinstance(value, dict) or set(value) != _ADMISSION_FIELDS:
        raise TranscriptImportCliError("preflight admission fields differ from schema")
    if value["allowed"] is not True or value["reason"] != "permitted":
        raise TranscriptImportCliError("preflight admission was not allowed")
    recomputed = authorize_transcript_fetch(
        request=request,
        candidate=candidate,
        authorization=authorization,
        plan_hash=plan_hash,
        runtime_policy_hash=runtime_policy_hash,
        rights_policy=rights_policy,
        now=now,
    )
    expected = {
        "allowed": recomputed.allowed,
        "reason": recomputed.reason,
        "rights_policy_sha256": recomputed.rights_policy_sha256,
        "download_authorization_hash": recomputed.download_authorization_hash,
        "request_id": recomputed.request_id,
        "candidate_id": recomputed.candidate_id,
    }
    if not recomputed.allowed or value != expected:
        raise TranscriptImportCliError("preflight admission does not match current policy")
    return recomputed


def run_import(wiki_root: Path, stream: BinaryIO) -> dict[str, Any]:
    envelope = _read_envelope(stream)
    plan_hash = envelope["plan_hash"]
    if not isinstance(plan_hash, str) or not _SHA256.fullmatch(plan_hash):
        raise TranscriptImportCliError("invalid plan_hash")

    request = _dataclass_from_object(
        SourceRequest, envelope["source_request"], "source_request"
    )
    candidate = _dataclass_from_object(
        DownloadCandidate, envelope["candidate"], "candidate"
    )
    root = wiki_root.resolve(strict=True)
    if not root.is_dir():
        raise TranscriptImportCliError("wiki root is not a directory")

    config = load_catalog_config(root / "config" / "source_catalog.yaml", project_root=root)
    runtime_policy = load_runtime_policy(config.catalog_dir / "runtime_policy.json")
    runtime_hash = runtime_policy["snapshot_sha256"]
    rights_policy = load_provider_use_policy(root / "config" / "provider_use_policy.json")
    authorization = _authorization_from_object(
        envelope["download_authorization"],
        request=request,
        candidate=candidate,
        plan_hash=plan_hash,
        runtime_policy_hash=runtime_hash,
    )
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    admission = _admission_from_object(
        envelope["preflight_admission"],
        request=request,
        candidate=candidate,
        authorization=authorization,
        plan_hash=plan_hash,
        runtime_policy_hash=runtime_hash,
        rights_policy=rights_policy,
        now=now,
    )

    if not isinstance(envelope["transcript_result"], dict):
        raise TranscriptImportCliError("transcript_result must be an object")
    result_bytes = json.dumps(
        envelope["transcript_result"],
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    if len(result_bytes) > MAX_TOOL_RESULT_BYTES:
        raise TranscriptImportCliError("transcript result exceeds byte limit")

    catalog = SourceCatalog(config)
    try:
        imported = import_transcript_tool_result(
            result_bytes,
            request=request,
            candidate=candidate,
            authorization=authorization,
            preflight_admission=admission,
            plan_hash=plan_hash,
            runtime_policy_hash=runtime_hash,
            current_rights_policy=rights_policy,
            writer=CanonicalSourceWriter(catalog),
            now=now,
        )
    finally:
        catalog.close()

    return {
        "schema_version": RESPONSE_SCHEMA,
        "status": "imported",
        "canonical_status": imported.canonical_import.status.value,
        "request_id": request.request_id,
        "source_id": imported.canonical_import.source_id,
        "content_sha256": imported.canonical_import.content_sha256,
        "provider_payload_sha256": imported.provider_payload_sha256,
        "rights_policy_sha256": imported.rights_policy_sha256,
        "line_count": len(imported.material.lines),
        "extractor_version": imported.material.extractor_version,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--operation",
        choices=("import", "preflight-discovery", "preflight-candidate"),
        default="import",
        help="Run a read-only rights preflight or import one previously authorized result.",
    )
    parser.add_argument(
        "--wiki-root",
        type=Path,
        required=True,
        help="trusted company-wiki root containing config/source_catalog.yaml",
    )
    args = parser.parse_args(argv)
    response_schema = {
        "import": RESPONSE_SCHEMA,
        "preflight-discovery": DISCOVERY_PREFLIGHT_RESPONSE,
        "preflight-candidate": CANDIDATE_PREFLIGHT_RESPONSE,
    }[args.operation]
    try:
        if args.operation == "preflight-discovery":
            response = run_discovery_preflight(args.wiki_root, sys.stdin.buffer)
        elif args.operation == "preflight-candidate":
            response = run_candidate_preflight(args.wiki_root, sys.stdin.buffer)
        else:
            response = run_import(args.wiki_root, sys.stdin.buffer)
    except (
        OSError,
        TypeError,
        ValueError,
        RuntimePolicyError,
        ProviderUsePolicyError,
        TranscriptImportError,
    ) as exc:
        response = {
            "schema_version": response_schema,
            "status": "rejected",
            "reason": "invalid_or_unauthorized_import",
        }
        sys.stderr.write(f"transcript import rejected ({type(exc).__name__})\n")
        exit_code = 2
    except Exception as exc:  # noqa: BLE001 - keep unexpected CLI failures structured
        response = {
            "schema_version": response_schema,
            "status": "rejected",
            "reason": "import_failed",
        }
        sys.stderr.write(f"transcript import failed ({type(exc).__name__})\n")
        exit_code = 2
    else:
        exit_code = 0
    sys.stdout.write(json.dumps(response, ensure_ascii=False, separators=(",", ":")) + "\n")
    return exit_code


if __name__ == "__main__":  # pragma: no cover - subprocess entrypoint
    raise SystemExit(main())
