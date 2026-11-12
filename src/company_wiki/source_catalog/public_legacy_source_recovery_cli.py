"""Explicit exact-target admin recovery; preview is the safe default."""

from __future__ import annotations
import argparse
import json
from pathlib import Path
import sqlite3
import sys
from .config import CatalogConfigError, load_catalog_config
from .cn_primary_issuer import PrimaryIssuerUnavailable
from .public_legacy_source_link_cli import _emit, _nonfinite, _pairs
from .public_legacy_source_recovery import (
    RESPONSE_SCHEMA,
    recover_legacy_source,
    validate_request,
)
from .reader import CatalogReaderUnavailable
from .service import SourceCatalog
from .source_reader import SourceReadError


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--operation", choices=("preview", "apply"), default="preview")
    catalog = None
    try:
        args = parser.parse_args(argv)
        raw = sys.stdin.buffer.read(32769)
        if len(raw) > 32768:
            raise SourceReadError("blocked", "recovery_request_limit")
        request = json.loads(
            raw.decode("utf-8"), object_pairs_hook=_pairs, parse_constant=_nonfinite
        )
        validate_request(request)
        catalog = SourceCatalog(load_catalog_config(args.config))
        _emit(
            recover_legacy_source(catalog, request, operation=args.operation),
            sys.stdout,
        )
        return 0
    except (SourceReadError, PrimaryIssuerUnavailable) as exc:
        _emit(
            {
                "schema_version": RESPONSE_SCHEMA,
                "status": getattr(exc, "status", "blocked"),
                "reason": exc.reason,
            },
            sys.stderr,
        )
        return 2
    except (CatalogConfigError, CatalogReaderUnavailable, sqlite3.Error, OSError):
        _emit(
            {
                "schema_version": RESPONSE_SCHEMA,
                "status": "unavailable",
                "reason": "recovery_unavailable",
            },
            sys.stderr,
        )
        return 2
    except (UnicodeError, ValueError, TypeError, RecursionError, KeyError):
        _emit(
            {
                "schema_version": RESPONSE_SCHEMA,
                "status": "blocked",
                "reason": "recovery_request_invalid",
            },
            sys.stderr,
        )
        return 2
    finally:
        if catalog is not None:
            catalog.close()


if __name__ == "__main__":
    raise SystemExit(main())
