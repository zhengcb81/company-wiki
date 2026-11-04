"""Bounded stdin bridge for canonical import of one transcript tool result.

The inbound JSON is a *public, versioned wire*, not a serialization of the
company-wiki owner models.  ``REQUEST_SCHEMA`` plus the projections below are
the whole contract: the accepted field set is listed here and is deliberately
independent of ``dataclasses.fields(SourceRequest)`` /
``dataclasses.fields(DownloadCandidate)``.  Owner-side refactoring may add
internal fields (with defaults) without silently making them required wire
fields for an already released producer.  The ``/3`` response is versioned
public wire too, so its ``source_ref`` object is emitted through an explicit
projection as well instead of re-serializing the owner dataclass.  Every owner
check that matters - source identity, period/as-of, original bytes and SHA,
byte budget - still runs after decoding, on the owner types.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
import sys
from typing import Any, BinaryIO

from .acquisition import DownloadCandidate
from .canonical_writer import CanonicalSourceWriter
from .config import load_catalog_config
from .resolver import SourceRequest
from .service import SourceCatalog
from .transcript_import import (
    MAX_TOOL_RESULT_BYTES,
    MAX_PROVIDER_PAYLOAD_BYTES,
    TranscriptImportError,
    import_transcript_tool_result,
)


REQUEST_SCHEMA = "company-wiki-transcript-import-request/2"
RESPONSE_SCHEMA = "company-wiki-transcript-import-response/3"
MAX_ENVELOPE_BYTES = MAX_TOOL_RESULT_BYTES + 128 * 1024
_ENVELOPE_FIELDS = frozenset(
    {"schema_version", "source_request", "candidate", "transcript_result"}
)

# Wire field -> owner attribute.  The wire name is what the producer sends; the
# owner name is what the current model calls it.  They coincide today, and the
# pairs stay explicit so a rename inside company-wiki cannot move a public
# field by accident.  Adding a field to either side of this table is a wire
# change and therefore a ``REQUEST_SCHEMA`` change.
_SOURCE_REQUEST_WIRE: tuple[tuple[str, str], ...] = (
    ("schema_version", "schema_version"),
    ("entity", "entity"),
    ("market", "market"),
    ("security_id", "security_id"),
    ("document_kind", "document_kind"),
    ("form_type", "form_type"),
    ("fiscal_year", "fiscal_year"),
    ("fiscal_period", "fiscal_period"),
    ("language", "language"),
    ("provider", "provider"),
    ("provider_document_id", "provider_document_id"),
    ("as_of_date", "as_of_date"),
    ("mode", "mode"),
    ("allow_download", "allow_download"),
)
_CANDIDATE_WIRE: tuple[tuple[str, str], ...] = (
    ("candidate_id", "candidate_id"),
    ("provider", "provider"),
    ("provider_document_id", "provider_document_id"),
    ("market", "market"),
    ("entity", "entity"),
    ("title", "title"),
    ("source_url", "source_url"),
    ("document_kind", "document_kind"),
    ("filing_date", "filing_date"),
    ("fiscal_year", "fiscal_year"),
    ("form_type", "form_type"),
    ("fiscal_period", "fiscal_period"),
    ("language", "language"),
    ("amended", "amended"),
    ("etag", "etag"),
    ("last_modified", "last_modified"),
    ("remote_size", "remote_size"),
    ("adapter_payload_json", "adapter_payload_json"),
    ("schema_version", "schema_version"),
)

SOURCE_REQUEST_WIRE_FIELDS = frozenset(name for name, _ in _SOURCE_REQUEST_WIRE)
CANDIDATE_WIRE_FIELDS = frozenset(name for name, _ in _CANDIDATE_WIRE)

# The /3 response is public wire too, so its ``source_ref`` object is emitted
# through this explicit projection instead of re-serializing the owner
# dataclass.  A ``SourceRef`` refactor therefore cannot silently move a
# published field; adding one to this table is a ``RESPONSE_SCHEMA`` change.
_SOURCE_REF_RESPONSE_WIRE: tuple[tuple[str, str], ...] = (
    ("document_id", "document_id"),
    ("source_id", "source_id"),
    ("content_sha256", "content_sha256"),
    ("byte_size", "byte_size"),
    ("mime_type", "mime_type"),
    ("schema_version", "schema_version"),
)
SOURCE_REF_RESPONSE_FIELDS = frozenset(name for name, _ in _SOURCE_REF_RESPONSE_WIRE)


class TranscriptImportCliError(ValueError):
    """The bounded import request is invalid."""


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise TranscriptImportCliError("duplicate JSON object key")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise TranscriptImportCliError(f"invalid JSON constant: {value}")


def _read_envelope(stream: BinaryIO, *, max_bytes: int | None = None) -> dict[str, Any]:
    if max_bytes is not None and (type(max_bytes) is not int or max_bytes <= 0):
        raise TranscriptImportCliError("invalid envelope allocation")
    raw = stream.read() if max_bytes is None else stream.read(max_bytes + 1)
    if not raw or (max_bytes is not None and len(raw) > max_bytes):
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


def _project(
    cls: Any, value: Any, name: str, wire: tuple[tuple[str, str], ...]
) -> Any:
    """Decode one pinned wire object onto the current owner type.

    Only the fields named in ``wire`` may appear.  Anything else - including an
    internal owner field that was never published - is a wire violation, and a
    missing published field is one too.  Owner fields outside ``wire`` take
    their own declared defaults; a required one is an internal bug and fails
    here as an invalid request rather than being invented by the decoder.
    """
    if not isinstance(value, dict) or set(value) != {field for field, _ in wire}:
        raise TranscriptImportCliError(f"{name} fields differ from schema")
    try:
        return cls(**{attribute: value[field] for field, attribute in wire})
    except (TypeError, ValueError) as exc:
        raise TranscriptImportCliError(f"{name} is invalid") from exc


def run_import(wiki_root: Path, stream: BinaryIO, *,
    max_original_bytes: int = MAX_PROVIDER_PAYLOAD_BYTES,
    max_envelope_bytes: int | None = None,
) -> dict[str, Any]:
    envelope = _read_envelope(stream, max_bytes=max_envelope_bytes)
    request = _project(
        SourceRequest, envelope["source_request"], "source_request", _SOURCE_REQUEST_WIRE
    )
    candidate = _project(
        DownloadCandidate, envelope["candidate"], "candidate", _CANDIDATE_WIRE
    )
    if not isinstance(envelope["transcript_result"], dict):
        raise TranscriptImportCliError("transcript_result must be an object")
    result_bytes = json.dumps(
        envelope["transcript_result"],
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")

    root = wiki_root.resolve(strict=True)
    if not root.is_dir():
        raise TranscriptImportCliError("wiki root is not a directory")
    config = load_catalog_config(root / "config" / "source_catalog.yaml", project_root=root)
    catalog = SourceCatalog(config)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    writer = CanonicalSourceWriter(catalog)
    try:
        imported = import_transcript_tool_result(
            result_bytes,
            request=request,
            candidate=candidate,
            writer=writer,
            now=now,
            max_original_bytes=max_original_bytes,
        )
        source_ref = writer.source_ref_for_import(
            request, candidate, imported.provider_payload_sha256
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
        "source_ref": {
            field: getattr(source_ref, attribute)
            for field, attribute in _SOURCE_REF_RESPONSE_WIRE
        },
        "provider_payload_sha256": imported.provider_payload_sha256,
        "line_count": len(imported.material.lines),
        "extractor_version": imported.material.extractor_version,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--wiki-root",
        type=Path,
        required=True,
        help="company-wiki root containing config/source_catalog.yaml",
    )
    parser.add_argument("--max-original-bytes", type=int, default=MAX_PROVIDER_PAYLOAD_BYTES)
    parser.add_argument("--max-envelope-bytes", type=int, default=None)
    args = parser.parse_args(argv)
    try:
        response = run_import(args.wiki_root, sys.stdin.buffer,
            max_original_bytes=args.max_original_bytes, max_envelope_bytes=args.max_envelope_bytes)
    except (
        OSError,
        TypeError,
        ValueError,
        TranscriptImportError,
    ) as exc:
        response = {
            "schema_version": RESPONSE_SCHEMA,
            "status": "rejected",
            "reason": "invalid_or_failed_import",
        }
        sys.stderr.write(f"transcript import rejected ({type(exc).__name__})\n")
        exit_code = 2
    except Exception as exc:  # noqa: BLE001 - provide a bounded machine-readable failure
        response = {
            "schema_version": RESPONSE_SCHEMA,
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
