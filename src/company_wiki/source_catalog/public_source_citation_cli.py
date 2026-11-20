"""Read-only replay of a native citation on one exact registered original."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sqlite3
import sys

from ..wire_json import parse_json
from .config import CatalogConfigError, load_catalog_config
from .public_source_citation import RESPONSE_SCHEMA, resolve_source_citation
from .reader import CatalogReaderUnavailable
from .service import SourceCatalog

_REQUEST_BYTES = 65_536


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args(argv)
    catalog = None
    try:
        body = sys.stdin.buffer.read(_REQUEST_BYTES + 1)
        if len(body) > _REQUEST_BYTES:
            raise ValueError("citation request exceeds transport bound")
        request = parse_json(body.decode("utf-8"))
        catalog = SourceCatalog(load_catalog_config(args.config))
        response = resolve_source_citation(catalog, request)
        print(json.dumps(response, ensure_ascii=True, allow_nan=False, separators=(",", ":")))
        return 0
    except (CatalogConfigError, CatalogReaderUnavailable, sqlite3.Error, OSError):
        state, reason = "unavailable", "source_citation_unavailable"
    except (ValueError, TypeError, RecursionError):
        state, reason = "blocked", "invalid_request"
    finally:
        if catalog is not None:
            catalog.close()
    print(json.dumps({"schema_version": RESPONSE_SCHEMA, "state": state, "reason": reason}), file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
