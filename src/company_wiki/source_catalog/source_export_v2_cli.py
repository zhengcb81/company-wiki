"""Publish a verified, pathless SourceExport v2 bundle from catalog refs."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from dataclasses import fields
from pathlib import Path
from typing import Any, Sequence

from company_wiki.source_contract import EvidenceSpan, SourceExportBundleV2

from .config import CatalogConfigError, load_catalog_config
from .reader import CatalogReaderUnavailable
from .service import SourceCatalog
from .source_reader import (
    SOURCE_REF_SCHEMA_VERSION,
    SourceReadError,
    SourceRef,
    SourceVersionReader,
)


_MAX_REQUEST_BYTES = 16 * 1024 * 1024
_REQUEST_FIELDS = frozenset({"schema_version", "source_refs", "evidence_spans"})
_REF_FIELDS = frozenset(field.name for field in fields(SourceRef))


class _JsonArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise ValueError(message)


def _unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _read_request() -> tuple[tuple[SourceRef, ...], tuple[EvidenceSpan, ...]]:
    raw = sys.stdin.buffer.read(_MAX_REQUEST_BYTES + 1)
    if len(raw) > _MAX_REQUEST_BYTES:
        raise ValueError("request exceeds limit")
    request = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_pairs)
    if not isinstance(request, dict) or set(request) != _REQUEST_FIELDS:
        raise ValueError("request fields are not exact")
    if request["schema_version"] != SOURCE_REF_SCHEMA_VERSION:
        raise ValueError("unsupported request version")
    raw_refs = request["source_refs"]
    raw_spans = request["evidence_spans"]
    if not isinstance(raw_refs, list) or not isinstance(raw_spans, list):
        raise ValueError("source_refs and evidence_spans must be arrays")
    if any(not isinstance(item, dict) or set(item) != _REF_FIELDS
           for item in raw_refs):
        raise ValueError("source ref fields are not exact")
    refs = tuple(SourceRef(**item) for item in raw_refs)
    spans = tuple(EvidenceSpan.from_dict(item) for item in raw_spans)
    return refs, spans


def _write_json_line(stream: Any, value: dict[str, Any]) -> None:
    payload = (
        json.dumps(
            value, ensure_ascii=True, sort_keys=True, separators=(",", ":"),
        ) + "\n"
    ).encode("utf-8")
    binary_stream = getattr(stream, "buffer", None)
    if binary_stream is None:
        stream.write(payload.decode("utf-8"))
    else:
        binary_stream.write(payload)
    stream.flush()


def _emit_error(status: str, reason: str) -> None:
    _write_json_line(
        sys.stderr,
        {
            "schema_version": SOURCE_REF_SCHEMA_VERSION,
            "status": status,
            "reason": reason,
        },
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = _JsonArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    catalog: SourceCatalog | None = None
    try:
        args = parser.parse_args(argv)
        refs, spans = _read_request()
        catalog = SourceCatalog(load_catalog_config(args.config))
        bundle = SourceExportBundleV2.build(
            source_reader=SourceVersionReader(catalog),
            refs=refs,
            evidence_spans=spans,
        )
        _write_json_line(sys.stdout, bundle.to_dict())
        return 0
    except SourceReadError as exc:
        _emit_error(exc.status, exc.reason)
        return 2
    except (CatalogConfigError, CatalogReaderUnavailable, OSError, sqlite3.Error):
        _emit_error("unavailable", "export_unavailable")
        return 2
    except (TypeError, UnicodeError, ValueError):
        _emit_error("blocked", "invalid_request")
        return 2
    finally:
        if catalog is not None:
            catalog.close()


if __name__ == "__main__":
    raise SystemExit(main())
