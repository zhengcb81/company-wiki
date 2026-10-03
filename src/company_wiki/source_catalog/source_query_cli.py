"""Local, zero-acquisition query transport for path-independent source refs."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
import sqlite3
import sys
from pathlib import Path
from typing import NoReturn, Sequence

from .config import CatalogConfigError, load_catalog_config
from .reader import CatalogReaderUnavailable
from .resolver import SourceRequest
from .service import SourceCatalog
from .source_reader import SOURCE_REF_SCHEMA_VERSION, SourceReadError, SourceVersionReader


_MAX_REQUEST_BYTES = 65_536
_TRANSCRIPT_LOOKUP_SCHEMA = "company-wiki-transcript-import-lookup-request/1"


class _JsonArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise ValueError(message)


def _emit(payload: dict[str, object]) -> None:
    sys.stdout.write(
        json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
        + "\n"
    )
    sys.stdout.flush()


def main(argv: Sequence[str] | None = None) -> int:
    parser = _JsonArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    catalog: SourceCatalog | None = None
    try:
        args = parser.parse_args(argv)
        raw = sys.stdin.buffer.read(_MAX_REQUEST_BYTES + 1)
        if len(raw) > _MAX_REQUEST_BYTES:
            raise ValueError("request too large")
        request_data = json.loads(raw.decode("utf-8"))
        if not isinstance(request_data, dict):
            raise ValueError("request must be an object")
        transcript_lookup = request_data.get("schema_version") == _TRANSCRIPT_LOOKUP_SCHEMA
        if transcript_lookup:
            if set(request_data) != {"schema_version", "source_request"}:
                raise ValueError("transcript lookup fields differ from schema")
            request_data = request_data["source_request"]
            if not isinstance(request_data, dict):
                raise ValueError("source_request must be an object")
        request = SourceRequest(**request_data)
        config = load_catalog_config(args.config)
        catalog = SourceCatalog(config)
        reader = SourceVersionReader(catalog)
        result = (
            reader.lookup_transcript_import(request)
            if transcript_lookup
            else reader.query_local(request)
        )
        _emit({
            **asdict(result),
            "request_id": request.request_id,
            "candidates": [
                reader.describe_candidate(ref) for ref in result.matches
            ] if result.status in {"found", "unknown_publication"} else [],
            "source_read_policy_sha256": reader.read_policy_sha256(),
        })
        return 0
    except SourceReadError as exc:
        _emit(
            {
                "schema_version": SOURCE_REF_SCHEMA_VERSION,
                "status": exc.status,
                "reason": exc.reason,
                "matches": [],
                "candidates": [],
            }
        )
        return 2
    except (CatalogConfigError, CatalogReaderUnavailable, OSError, sqlite3.Error):
        _emit(
            {
                "schema_version": SOURCE_REF_SCHEMA_VERSION,
                "status": "unavailable",
                "reason": "reader_unavailable",
                "matches": [],
                "candidates": [],
            }
        )
        return 2
    except (TypeError, UnicodeError, ValueError):
        _emit(
            {
                "schema_version": SOURCE_REF_SCHEMA_VERSION,
                "status": "blocked",
                "reason": "invalid_request",
                "matches": [],
                "candidates": [],
            }
        )
        return 2
    finally:
        if catalog is not None:
            catalog.close()


if __name__ == "__main__":
    raise SystemExit(main())
