"""Bounded stdin bridge for canonical import of one transcript tool result."""

from __future__ import annotations

import argparse
import json
from dataclasses import fields
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
    TranscriptImportError,
    import_transcript_tool_result,
)


REQUEST_SCHEMA = "company-wiki-transcript-import-request/2"
RESPONSE_SCHEMA = "company-wiki-transcript-import-response/2"
MAX_ENVELOPE_BYTES = MAX_TOOL_RESULT_BYTES + 128 * 1024
_ENVELOPE_FIELDS = frozenset(
    {"schema_version", "source_request", "candidate", "transcript_result"}
)


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


def _dataclass_from_object(cls: Any, value: Any, name: str) -> Any:
    expected = {item.name for item in fields(cls) if item.init}
    if not isinstance(value, dict) or set(value) != expected:
        raise TranscriptImportCliError(f"{name} fields differ from schema")
    try:
        return cls(**value)
    except (TypeError, ValueError) as exc:
        raise TranscriptImportCliError(f"{name} is invalid") from exc


def run_import(wiki_root: Path, stream: BinaryIO) -> dict[str, Any]:
    envelope = _read_envelope(stream)
    request = _dataclass_from_object(
        SourceRequest, envelope["source_request"], "source_request"
    )
    candidate = _dataclass_from_object(
        DownloadCandidate, envelope["candidate"], "candidate"
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

    root = wiki_root.resolve(strict=True)
    if not root.is_dir():
        raise TranscriptImportCliError("wiki root is not a directory")
    config = load_catalog_config(root / "config" / "source_catalog.yaml", project_root=root)
    catalog = SourceCatalog(config)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    try:
        imported = import_transcript_tool_result(
            result_bytes,
            request=request,
            candidate=candidate,
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
    args = parser.parse_args(argv)
    try:
        response = run_import(args.wiki_root, sys.stdin.buffer)
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
