"""Local, zero-acquisition transport for the canonical issuer browse.

Reads one JSON request from stdin, writes one compact JSON response line to
stdout.  The StockWiki proof CLI deployment (interpreter, code root, trusted
workspace root) comes only from fixed operator arguments — never from the
business JSON.  Read-only: no download, refresh, OCR, parsing, registration
or backfill is triggered, and no physical path is emitted.  Transport
failures emit a single JSON error line on stderr (``unavailable``) and exit
2; malformed requests are ``blocked``.  In-band states (``available`` /
``empty`` / ``partial`` / ``stale`` / ``unsupported``) are successful
responses on stdout with exit 0.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any, NoReturn, Sequence

from .config import CatalogConfigError, load_catalog_config
from .public_canonical_browser import (
    REQUEST_SCHEMA,
    RESPONSE_SCHEMA,
    CanonicalBrowseError,
    ProofTransportError,
    PublicCanonicalBrowser,
    StockWikiProofClient,
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
    if request.get("schema_version") != REQUEST_SCHEMA:
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
        {"schema_version": RESPONSE_SCHEMA,
         "state": state, "reason": reason},
    )


def _proof_client(args: argparse.Namespace) -> StockWikiProofClient | None:
    """Build the proof client from fixed operator arguments only."""
    if args.sw_python is None and args.sw_cli is None and args.sw_root is None:
        return None
    if args.sw_python is None or args.sw_cli is None or args.sw_root is None:
        raise ValueError("incomplete stockwiki proof configuration")
    return StockWikiProofClient(
        python_executable=args.sw_python, cli_path=args.sw_cli,
        workspace_root=args.sw_root,
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = _JsonArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--sw-python", type=str, default=None)
    parser.add_argument("--sw-cli", type=str, default=None)
    parser.add_argument("--sw-root", type=str, default=None)
    catalog: SourceCatalog | None = None
    try:
        args = parser.parse_args(argv)
        request = _read_request()
        catalog = SourceCatalog(load_catalog_config(args.config))
        try:
            proof_client = _proof_client(args)
        except ProofTransportError:
            # An unusable operator configuration is reported in-band by the
            # binding (named unavailable), like a missing configuration.
            proof_client = None
        # Probe the catalog once so an unreadable catalog is the transport
        # fault it is (unavailable), even when no proof is configured and
        # the binding itself would short-circuit.
        catalog.reader.fetchone("SELECT 1")
        browser = PublicCanonicalBrowser(catalog, proof_client=proof_client)
        response = browser.browse(request)
        _write_json_line(sys.stdout, response)
        return 0
    except CanonicalBrowseError as exc:
        _emit_error("blocked", exc.reason)
        return 2
    except (CatalogConfigError, CatalogReaderUnavailable, OSError,
            sqlite3.Error):
        _emit_error("unavailable", "canonical_browse_unavailable")
        return 2
    except (TypeError, UnicodeError, ValueError):
        _emit_error("blocked", "invalid_request")
        return 2
    finally:
        if catalog is not None:
            catalog.close()


if __name__ == "__main__":
    raise SystemExit(main())
