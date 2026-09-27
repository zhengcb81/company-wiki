"""Binary local transport for an exact, verified source version.

stdout carries only source bytes.  stderr carries one JSON receipt after a
complete successful write, or one JSON refusal with no successful receipt.
Callers must require exit code 0, the receipt and their own byte hash check.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
import sqlite3
import sys
from pathlib import Path
from typing import Sequence

from .config import CatalogConfigError, load_catalog_config
from .reader import CatalogReaderUnavailable
from .service import SourceCatalog
from .source_reader import (
    SOURCE_READ_RECEIPT_SCHEMA_VERSION,
    SourceReadError,
    SourceVersionReader,
)


class _JsonArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise ValueError(message)


def _emit_receipt(payload: dict[str, object]) -> None:
    line = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    sys.stderr.write(line + "\n")
    sys.stderr.flush()


def main(argv: Sequence[str] | None = None) -> int:
    parser = _JsonArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--document-id", required=True)
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--content-sha256", required=True)
    parser.add_argument("--purpose", default="filing_reuse")
    parser.add_argument("--expected-read-policy-sha256")
    catalog: SourceCatalog | None = None
    try:
        args = parser.parse_args(argv)
        config = load_catalog_config(args.config)
        catalog = SourceCatalog(config)
        reader = SourceVersionReader(catalog)
        ref = reader.query_ref(
            args.document_id, args.source_id, args.content_sha256
        )
        opened = reader.open_version(
            ref, purpose=args.purpose,
            expected_read_policy_sha256=args.expected_read_policy_sha256,
        )
        manifest = reader.describe_version(ref)
        sys.stdout.buffer.write(opened.data)
        sys.stdout.buffer.flush()
        _emit_receipt(
            {
                "schema_version": SOURCE_READ_RECEIPT_SCHEMA_VERSION,
                "status": "ok",
                "document_id": opened.document_id,
                "source_id": opened.source_id,
                "content_sha256": opened.content_sha256,
                "byte_size": opened.byte_size,
                "policy_sha256": opened.policy_sha256,
                "source_read_policy_sha256": opened.source_read_policy_sha256,
                "read_at": opened.read_at,
                "manifest": manifest,
                "review": asdict(opened.review) if opened.review is not None else None,
            }
        )
        return 0
    except SourceReadError as exc:
        _emit_receipt(
            {
                "schema_version": SOURCE_READ_RECEIPT_SCHEMA_VERSION,
                "status": exc.status,
                "reason": exc.reason,
            }
        )
        return 2
    except (CatalogConfigError, CatalogReaderUnavailable, OSError, sqlite3.Error, ValueError):
        _emit_receipt(
            {
                "schema_version": SOURCE_READ_RECEIPT_SCHEMA_VERSION,
                "status": "unavailable",
                "reason": "reader_unavailable",
            }
        )
        return 2
    finally:
        if catalog is not None:
            catalog.close()


if __name__ == "__main__":
    raise SystemExit(main())
