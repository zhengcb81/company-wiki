"""Bounded, zero-write public transport for legacy source-key resolution."""

from __future__ import annotations
import argparse
import json
from pathlib import Path
import sqlite3
import sys
from typing import Any

from .config import CatalogConfigError, load_catalog_config
from .public_legacy_source_link import (
    LegacyLinkError,
    RESPONSE_SCHEMA,
    resolve_legacy_source,
)
from .reader import CatalogReaderUnavailable
from .service import SourceCatalog

MAX_REQUEST_BYTES = 8192


def _pairs(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("duplicate_key")
        value[key] = item
    return value


def _nonfinite(value):
    raise ValueError("nonfinite_number")


def _emit(value: dict[str, Any], stream) -> None:
    stream.write(
        json.dumps(
            value,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    )


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    catalog = None
    try:
        args = parser.parse_args(argv)
        raw = sys.stdin.buffer.read(MAX_REQUEST_BYTES + 1)
        if len(raw) > MAX_REQUEST_BYTES:
            raise LegacyLinkError("input_too_large")
        request = json.loads(
            raw.decode("utf-8"), object_pairs_hook=_pairs, parse_constant=_nonfinite
        )
        catalog = SourceCatalog(load_catalog_config(args.config))
        _emit(resolve_legacy_source(catalog, request), sys.stdout)
        return 0
    except LegacyLinkError as exc:
        _emit(
            {
                "schema_version": RESPONSE_SCHEMA,
                "state": "blocked",
                "reason": exc.reason,
            },
            sys.stderr,
        )
        return 2
    except (UnicodeError, ValueError, TypeError, RecursionError):
        _emit(
            {
                "schema_version": RESPONSE_SCHEMA,
                "state": "blocked",
                "reason": "invalid_request",
            },
            sys.stderr,
        )
        return 2
    except (CatalogConfigError, CatalogReaderUnavailable, sqlite3.Error, OSError):
        _emit(
            {
                "schema_version": RESPONSE_SCHEMA,
                "state": "unavailable",
                "reason": "legacy_link_unavailable",
            },
            sys.stderr,
        )
        return 2
    finally:
        if catalog is not None:
            catalog.close()


if __name__ == "__main__":
    raise SystemExit(main())
