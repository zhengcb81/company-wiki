"""JSON transport for the company-level source index.

Success writes one compact JSON object to stdout.  A refusal writes one
compact JSON object to stderr and exits 2, so a consumer never mistakes an
empty page for "the company has no sources".
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any, NoReturn, Sequence

from .company_source_index import (
    RESPONSE_SCHEMA_VERSION,
    CompanySourceIndex,
    CompanySourceIndexError,
    CompanySourceIndexRequest,
)
from .config import CatalogConfigError, load_catalog_config
from .reader import CatalogReaderUnavailable
from .service import SourceCatalog


class _JsonArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise ValueError(message)


def _write_json_line(stream: Any, value: dict[str, Any]) -> None:
    payload = (
        json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")
    binary = getattr(stream, "buffer", None)
    if binary is None:
        stream.write(payload.decode("utf-8"))
    else:
        binary.write(payload)
    stream.flush()


def _emit_error(status: str, reason: str) -> None:
    _write_json_line(
        sys.stderr,
        {
            "schema_version": RESPONSE_SCHEMA_VERSION,
            "status": status,
            "reason": reason,
        },
    )


def _unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = _JsonArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    catalog: SourceCatalog | None = None
    try:
        args = parser.parse_args(argv)
        request = CompanySourceIndexRequest.from_dict(
            json.loads(
                sys.stdin.buffer.read().decode("utf-8"),
                object_pairs_hook=_unique_pairs,
            )
        )
        catalog = SourceCatalog(load_catalog_config(args.config))
        result = CompanySourceIndex(catalog).page(request)
        _write_json_line(sys.stdout, result)
        return 0
    except CompanySourceIndexError as exc:
        _emit_error(exc.status, exc.reason)
        return 2
    except (CatalogConfigError, CatalogReaderUnavailable, OSError, sqlite3.Error):
        _emit_error("unavailable", "catalog_unavailable")
        return 2
    except (TypeError, UnicodeError, ValueError):
        _emit_error("blocked", "invalid_request")
        return 2
    finally:
        if catalog is not None:
            catalog.close()


if __name__ == "__main__":
    raise SystemExit(main())
