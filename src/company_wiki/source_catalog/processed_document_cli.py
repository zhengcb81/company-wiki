"""Serve one pathless processed-document read over stdin/stdout JSON.

Request (stdin, one JSON object)::

    {"schema_version": "company-wiki-processed-document/1",
     "source_ref": {"schema_version": "2.0", "document_id": ..., "source_id": ...,
                    "content_sha256": ..., "byte_size": ..., "mime_type": ...},
     "options": {"max_units": 200, "continuation": "<opaque cursor>"}}

``options`` is optional.  Success: one canonical JSON line on stdout holding
the ``company-wiki-processed-document/1`` envelope.  Refusal: one JSON line on
stderr ``{"schema_version", "status", "reason"}`` and exit 2.  The response and
errors never contain an original path, storage root or catalogue interior.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any, NoReturn, Sequence

from .config import CatalogConfigError, load_catalog_config
from .processed_document import PROCESSED_DOCUMENT_SCHEMA_VERSION, read_processed_document
from .reader import CatalogReaderUnavailable
from .service import SourceCatalog
from .source_reader import SourceReadError, SourceVersionReader


class _JsonArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise ValueError(message)


def _unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _read_request() -> Any:
    raw = sys.stdin.buffer.read()
    return json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_pairs)


def _write_json_line(stream: Any, value: dict[str, Any]) -> None:
    payload = (
        json.dumps(
            value, ensure_ascii=True, sort_keys=True, separators=(",", ":"),
        )
        + "\n"
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
            "schema_version": PROCESSED_DOCUMENT_SCHEMA_VERSION,
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
        request = _read_request()
        catalog = SourceCatalog(load_catalog_config(args.config))
        envelope = read_processed_document(SourceVersionReader(catalog).as_version_port(), request)
        _write_json_line(sys.stdout, envelope)
        return 0
    except SourceReadError as exc:
        _emit_error(exc.status, exc.reason)
        return 2
    except (CatalogConfigError, CatalogReaderUnavailable, OSError, sqlite3.Error):
        _emit_error("unavailable", "processed_document_unavailable")
        return 2
    except (TypeError, UnicodeError, ValueError):
        _emit_error("blocked", "invalid_request")
        return 2
    finally:
        if catalog is not None:
            catalog.close()


if __name__ == "__main__":
    raise SystemExit(main())
