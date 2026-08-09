"""WU-1001: atomic SourceBundle CLI — one query, one snapshot, exit codes.

stdout carries ONLY the protocol (bundle JSON); diagnostics go to stderr.
Exit codes: 0 = bundle produced; 1 = NOT_FOUND; 2 = NOT_ADMISSIBLE;
3 = AMBIGUOUS; 4 = STALE_BUNDLE; 5 = INTERNAL.  The catalog is opened
read-only (mode=ro + query_only); no parser/LLM/network/write.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

_ARTIFACT_ROLES = {"normalized", "markdown", "summary", "sections",
                   "consumer_analysis"}


def _open_readonly(catalog: Path) -> sqlite3.Connection:
    con = sqlite3.connect(f"file:{catalog}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA query_only = ON")
    return con


def _fail(code: int, message: str, document_id: str) -> None:
    sys.stderr.write(json.dumps({"error_code": code, "error": message,
                                 "document_id": document_id}))
    sys.stderr.write("\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Atomic SourceBundle resolve")
    parser.add_argument("--document-id", required=True)
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument("--allowed-root", action="append", default=[])
    args = parser.parse_args(argv)

    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")

    if not args.catalog.is_file():
        _fail(5, "catalog missing", args.document_id)
        return 5

    from company_wiki.source_catalog.source_bundle import build_source_bundle

    con = _open_readonly(args.catalog)
    try:
        row = con.execute(
            "SELECT * FROM documents WHERE document_id=?",
            (args.document_id,),
        ).fetchone()
        if row is None:
            _fail(1, "NOT_FOUND", args.document_id)
            return 1
        document = dict(row)
        source = {
            "document_id": document["document_id"],
            "primary_source_id": document.get("primary_source_id") or "",
            "source_sha256": "",
            "as_of_date": document.get("published_date") or "",
        }
        if document.get("primary_source_id"):
            src = con.execute(
                "SELECT content_sha256 FROM sources WHERE source_id=?",
                (document["primary_source_id"],),
            ).fetchone()
            if src is not None:
                source["source_sha256"] = src["content_sha256"]
        artifacts = [
            dict(a) for a in con.execute(
                """SELECT artifact_id,artifact_role,source_id,path,content_sha256,
                          byte_size,mime_type,generator_name,generator_version,status,
                          error,schema_version,source_sha256,created_at
                   FROM artifacts WHERE document_id=?
                   ORDER BY artifact_role,created_at,artifact_id""",
                (args.document_id,),
            ).fetchall()
        ]
        registry = {role: {"required": False} for role in _ARTIFACT_ROLES}
        allowed = tuple(Path(p) for p in args.allowed_root) or (args.catalog.parent,)
        bundle = build_source_bundle(
            source=source, artifacts=artifacts, registry=registry,
            allowed_roots=allowed, now="2099-01-01",
        )
        payload = bundle.to_dict()
        payload["catalog_snapshot"] = {"catalog": str(args.catalog)}
        sys.stdout.write(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        sys.stdout.write("\n")
        return 0
    except Exception as exc:  # noqa: BLE001 - report and exit INTERNAL
        _fail(5, f"INTERNAL: {exc}", args.document_id)
        return 5
    finally:
        con.close()


if __name__ == "__main__":
    raise SystemExit(main())
