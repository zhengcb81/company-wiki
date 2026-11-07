"""Local, zero-acquisition transport for the public document browse.

Reads one JSON request from stdin (browse or exact version reopen), writes
one compact JSON response line to stdout.  Read-only: no download, OCR or
summary is triggered.  Transport failures emit a single JSON error line on
stderr (``unavailable``) and exit 2; malformed requests are ``blocked``.
In-band browse states (``available`` / ``empty`` / ``partial`` / ``stale``,
reopen ``not_found``) are successful responses on stdout with exit 0.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any, NoReturn, Sequence

from .config import CatalogConfigError, load_catalog_config
from .public_document_browser import (
    BROWSE_REQUEST_SCHEMA,
    BROWSE_RESPONSE_SCHEMA,
    REOPEN_REQUEST_SCHEMA,
    PublicBrowseError,
    PublicDocumentBrowser,
)
from .reader import CatalogReaderUnavailable
from .service import SourceCatalog


_MAX_REQUEST_BYTES = 65_536


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


def _read_request() -> dict[str, Any]:
    raw = sys.stdin.buffer.read(_MAX_REQUEST_BYTES + 1)
    if len(raw) > _MAX_REQUEST_BYTES:
        raise ValueError("request exceeds limit")
    request = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_pairs)
    if not isinstance(request, dict):
        raise ValueError("request must be an object")
    if request.get("schema_version") not in {
        BROWSE_REQUEST_SCHEMA, REOPEN_REQUEST_SCHEMA,
    }:
        raise ValueError("unsupported request version")
    return request


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


def _emit_error(state: str, reason: str) -> None:
    _write_json_line(
        sys.stderr,
        {"schema_version": BROWSE_RESPONSE_SCHEMA,
         "state": state, "reason": reason},
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = _JsonArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    catalog: SourceCatalog | None = None
    try:
        args = parser.parse_args(argv)
        request = _read_request()
        catalog = SourceCatalog(load_catalog_config(args.config))
        browser = PublicDocumentBrowser(catalog)
        if request["schema_version"] == BROWSE_REQUEST_SCHEMA:
            response = browser.browse(request)
        else:
            response = browser.reopen_document_version(request)
        _write_json_line(sys.stdout, response)
        return 0
    except PublicBrowseError as exc:
        _emit_error("blocked", exc.reason)
        return 2
    except (CatalogConfigError, CatalogReaderUnavailable, OSError, sqlite3.Error):
        _emit_error("unavailable", "browse_unavailable")
        return 2
    except (TypeError, UnicodeError, ValueError):
        _emit_error("blocked", "invalid_request")
        return 2
    finally:
        if catalog is not None:
            catalog.close()


if __name__ == "__main__":
    raise SystemExit(main())
