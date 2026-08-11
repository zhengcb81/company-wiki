"""FC-901: legacy artifact binding migration (dry-run bucketing).

The 7712 legacy production artifacts are currently ``source-bound=0``: none can
pass the WU-5.1 ``validate_artifact`` gate.  This module classifies every legacy
artifact into exactly one bucket by reusing that single fail-closed gate as the
source of truth, then optionally writes shadow source-bindings for the provably
bindable subset.

Buckets (exactly one per artifact; first failing gate wins):

- ``bindable``         — ``validate_artifact`` returns reusable; source/document/
                         content/generator/schema are all provable.
- ``hash_mismatch``    — the artifact's OWN content_sha256 does not verify against
                         its file bytes (``artifact_hash_mismatch`` /
                         ``artifact_hash_malformed``).
- ``missing_bytes``    — the artifact file is absent (``artifact_file_missing``).
- ``unknown_generator``— generator_name/version not in the registry
                         (``artifact_generator_unregistered``).
- ``legacy_unbound``   — provenance not provable: null/unmatched source binding,
                         source_sha lineage failure, status/schema/created_at/path
                         gate.  Never guessed (MIG-05).

Modes:

- ``dry-run`` (default): pure SELECT over artifacts/documents/sources; zero writes,
  zero schema changes.  Emits a complete proposal (per-bucket counts, per-bucket
  byte capacity, and a per-bindable binding proposal) — MIG-01.
- ``apply``: ``CREATE TABLE IF NOT EXISTS artifact_bindings`` then ``INSERT OR
  IGNORE`` shadow rows for bindable artifacts only.  The legacy ``artifacts``
  table is never UPDATEd/DELETEd; reversal is ``DELETE`` of shadow rows.

Idempotency (MIG-03): the result JSON is deterministic (ordered by artifact_id),
so re-running over an unchanged catalog yields a byte-identical ``result_hash``;
``INSERT OR IGNORE`` on the UNIQUE(artifact_id) binding makes a second apply a
no-op skip rather than a duplicate.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .artifact_handle import ArtifactHandle, validate_artifact

ARTIFACT_BINDING_SCHEMA_VERSION = "1.0"
ARTIFACT_BINDING_EVIDENCE_BASIS = "legacy-artifact-backfill"
ARTIFACT_BINDING_CREATED_BY = "fc-901"

_BINDINGS_DDL = """
CREATE TABLE IF NOT EXISTS artifact_bindings (
    binding_id TEXT PRIMARY KEY,
    artifact_id TEXT NOT NULL UNIQUE,
    source_id TEXT NOT NULL,
    document_id TEXT NOT NULL,
    content_sha256 TEXT NOT NULL,
    generator_name TEXT NOT NULL,
    generator_version TEXT NOT NULL,
    bundle_hash TEXT NOT NULL,
    evidence_basis TEXT NOT NULL,
    visibility_state TEXT NOT NULL,
    schema_version TEXT NOT NULL,
    created_at TEXT NOT NULL,
    created_by TEXT NOT NULL
);
"""

# validate_artifact reason -> FC-901 bucket.  Every reusable artifact is
# `bindable`; the rest map by the failing gate.  Anything not explicitly
# hash/file/generator-related is a provenance failure -> legacy_unbound (MIG-05).
_REASON_TO_BUCKET: dict[str, str] = {
    "artifact_hash_mismatch": "hash_mismatch",
    "artifact_hash_malformed": "hash_mismatch",
    "artifact_file_missing": "missing_bytes",
    "artifact_generator_unregistered": "unknown_generator",
}
_LEGACY_UNBOUND = "legacy_unbound"


@dataclass
class ArtifactBackfillResult:
    input: int = 0
    bindable: int = 0
    hash_mismatch: int = 0
    missing_bytes: int = 0
    unknown_generator: int = 0
    legacy_unbound: int = 0
    rows: list[dict[str, Any]] = field(default_factory=list)
    proposals: dict[str, dict[str, Any]] = field(default_factory=dict)
    capacity: dict[str, int] = field(default_factory=dict)
    created: list[str] = field(default_factory=list)
    skipped_already_bound: int = 0

    def _bucket_total(self, bucket: str) -> int:
        return sum(1 for r in self.rows if r["bucket"] == bucket)

    @property
    def closed(self) -> bool:
        return self.input == (self.bindable + self.hash_mismatch
                              + self.missing_bytes + self.unknown_generator
                              + self.legacy_unbound)

    def as_dict(self) -> dict[str, Any]:
        # Deterministic: rows ordered by artifact_id, proposals likewise.
        rows = sorted(self.rows, key=lambda r: str(r.get("artifact_id") or ""))
        proposals = {k: self.proposals[k] for k in sorted(self.proposals)}
        return {
            "input": self.input,
            "buckets": {
                "bindable": self._bucket_total("bindable"),
                "hash_mismatch": self._bucket_total("hash_mismatch"),
                "missing_bytes": self._bucket_total("missing_bytes"),
                "unknown_generator": self._bucket_total("unknown_generator"),
                "legacy_unbound": self._bucket_total("legacy_unbound"),
            },
            "capacity": dict(sorted(self.capacity.items())),
            "proposals": proposals,
            "closed": self.closed,
            "created_bindings": sorted(self.created),
            "skipped_already_bound": self.skipped_already_bound,
            "rows": rows,
        }

    @property
    def result_hash(self) -> str:
        """Stable sha256 over the canonical result JSON (MIG-03 idempotency)."""
        payload = json.dumps(self.as_dict(), sort_keys=True,
                             ensure_ascii=False).encode()
        return hashlib.sha256(payload).hexdigest()


def _connect(path: Path) -> sqlite3.Connection:
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    return con


def _bundle_hash(artifact_id: str, source_id: str, content_sha256: str,
                 generator_name: str, generator_version: str) -> str:
    digest = hashlib.sha256()
    digest.update(ARTIFACT_BINDING_SCHEMA_VERSION.encode())
    digest.update(artifact_id.encode())
    digest.update(source_id.encode())
    digest.update(content_sha256.encode())
    digest.update(generator_name.encode())
    digest.update(generator_version.encode())
    return digest.hexdigest()


def _classify(row: sqlite3.Row, *, registry: dict[str, set[str]],
              allowed_roots: tuple[Path, ...], now: str) -> tuple[str, str]:
    """Return (bucket, reason) for one artifact row.

    Reuses validate_artifact as the single source of truth.  If the source
    lineage cannot even be assembled (no document / primary source / source row),
    the artifact is legacy_unbound without guessing.
    """
    artifact_id = str(row["artifact_id"])
    artifact = {
        "artifact_id": artifact_id,
        "document_id": str(row["document_id"] or ""),
        "source_id": str(row["source_id"] or ""),
        "artifact_role": str(row["artifact_role"] or ""),
        "path": str(row["path"] or ""),
        "content_sha256": str(row["content_sha256"] or ""),
        "generator_name": str(row["generator_name"] or ""),
        "generator_version": str(row["generator_version"] or ""),
        "status": str(row["status"] or ""),
        "created_at": str(row["created_at"] or ""),
    }
    try:
        metadata = json.loads(row["metadata_json"] or "{}")
        if isinstance(metadata, dict):
            # schema_version + source_sha256 live in the producer metadata; the
            # artifacts table has no such columns.
            if "schema_version" in metadata:
                artifact["schema_version"] = metadata["schema_version"]
            if "source_sha256" in metadata:
                artifact["source_sha256"] = metadata["source_sha256"]
    except (json.JSONDecodeError, TypeError):
        pass

    primary_source_id = str(row["primary_source_id"] or "")
    source_sha = str(row["source_content_sha256"] or "")
    if not primary_source_id or not source_sha:
        return _LEGACY_UNBOUND, "no_provable_source_lineage"

    source = {
        "document_id": artifact["document_id"],
        "primary_source_id": primary_source_id,
        "source_sha256": source_sha,
        # as_of_date is a temporal sanity gate, not a binding-provability
        # concern; the documents table has no such column, so we leave it
        # empty and validate_artifact skips that check (only fires when set).
        "as_of_date": "",
    }
    handle: ArtifactHandle = validate_artifact(
        artifact, source=source, registry=registry,
        allowed_roots=allowed_roots, now=now)
    if handle.reusable:
        return "bindable", "bindable"
    bucket = _REASON_TO_BUCKET.get(handle.reason or "", _LEGACY_UNBOUND)
    return bucket, handle.reason or "unspecified"


def run_artifact_backfill(
    catalog: Path,
    *,
    registry: dict[str, set[str]],
    allowed_roots: tuple[Path, ...],
    now: str,
    mode: str = "dry-run",
) -> ArtifactBackfillResult:
    """Classify all legacy artifacts; optionally bind the provable subset.

    mode: ``dry-run`` (zero writes, default) | ``apply`` (shadow bindings only).
    """
    if mode not in {"dry-run", "apply"}:
        raise ValueError(f"unknown mode {mode!r}")
    result = ArtifactBackfillResult()
    con = _connect(catalog)
    try:
        rows = con.execute(
            """SELECT a.artifact_id, a.document_id, a.source_id, a.artifact_role,
                      a.path, a.content_sha256, a.byte_size, a.mime_type,
                      a.generator_name, a.generator_version, a.status, a.error,
                      a.metadata_json, a.created_at,
                      d.primary_source_id,
                      s.content_sha256 AS source_content_sha256
               FROM artifacts a
               LEFT JOIN documents d ON d.document_id = a.document_id
               LEFT JOIN sources s ON s.source_id = d.primary_source_id
               ORDER BY a.artifact_id""",
        ).fetchall()
        for row in rows:
            result.input += 1
            bucket, reason = _classify(
                row, registry=registry, allowed_roots=allowed_roots, now=now)
            byte_size = int(row["byte_size"] or 0)
            result.rows.append({
                "artifact_id": str(row["artifact_id"]),
                "document_id": str(row["document_id"] or ""),
                "bucket": bucket,
                "reason": reason,
                "byte_size": byte_size,
            })
            result.capacity[bucket] = result.capacity.get(bucket, 0) + byte_size
            if bucket == "bindable":
                source_id = str(row["source_id"] or "")
                content_sha = str(row["content_sha256"] or "")
                gen_name = str(row["generator_name"] or "")
                gen_ver = str(row["generator_version"] or "")
                bundle = _bundle_hash(str(row["artifact_id"]), source_id,
                                      content_sha, gen_name, gen_ver)
                result.proposals[str(row["artifact_id"])] = {
                    "source_id": source_id,
                    "document_id": str(row["document_id"] or ""),
                    "content_sha256": content_sha,
                    "generator_name": gen_name,
                    "generator_version": gen_ver,
                    "bundle_hash": bundle,
                }
        # Derive bucket counters from rows (single source of truth).
        result.bindable = result._bucket_total("bindable")
        result.hash_mismatch = result._bucket_total("hash_mismatch")
        result.missing_bytes = result._bucket_total("missing_bytes")
        result.unknown_generator = result._bucket_total("unknown_generator")
        result.legacy_unbound = result._bucket_total(_LEGACY_UNBOUND)

        if mode == "apply" and result.proposals:
            con.executescript(_BINDINGS_DDL)
            for artifact_id, proposal in sorted(result.proposals.items()):
                existing = con.execute(
                    "SELECT 1 FROM artifact_bindings WHERE artifact_id=?",
                    (artifact_id,),
                ).fetchone()
                if existing is not None:
                    result.skipped_already_bound += 1
                    continue
                binding_id = f"abind-{artifact_id}"
                con.execute(
                    """INSERT OR IGNORE INTO artifact_bindings
                    (binding_id, artifact_id, source_id, document_id,
                     content_sha256, generator_name, generator_version,
                     bundle_hash, evidence_basis, visibility_state,
                     schema_version, created_at, created_by)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (binding_id, artifact_id, proposal["source_id"],
                     proposal["document_id"], proposal["content_sha256"],
                     proposal["generator_name"], proposal["generator_version"],
                     proposal["bundle_hash"], ARTIFACT_BINDING_EVIDENCE_BASIS,
                     "shadow", ARTIFACT_BINDING_SCHEMA_VERSION, now,
                     ARTIFACT_BINDING_CREATED_BY),
                )
                result.created.append(binding_id)
            con.commit()
    finally:
        con.close()
    return result


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="FC-901 legacy artifact binding migration (dry-run bucketing)")
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument("--mode", choices=("dry-run", "apply"), default="dry-run")
    parser.add_argument("--registry-json", type=Path, default=None,
                        help='JSON dict[str, list[str]] of generator -> versions')
    parser.add_argument("--allowed-root", action="append", type=Path,
                        dest="allowed_roots",
                        help="allowed artifact root (repeatable)")
    parser.add_argument("--now", default=None,
                        help="UTC now stamp YYYY-MM-DDTHH:MM:SSZ")
    args = parser.parse_args()

    registry: dict[str, set[str]] = {}
    if args.registry_json:
        raw = json.loads(args.registry_json.read_text(encoding="utf-8"))
        registry = {k: set(v) for k, v in raw.items()}
    allowed_roots = tuple(args.allowed_roots or ())
    now = args.now or _default_now()
    result = run_artifact_backfill(
        args.catalog, registry=registry, allowed_roots=allowed_roots,
        now=now, mode=args.mode)
    print(json.dumps(result.as_dict(), ensure_ascii=False, indent=2))
    if not result.closed:
        print("RECONCILIATION NOT CLOSED", file=__import__("sys").stderr)
        return 2
    return 0


def _default_now() -> str:
    # CLI default = real UTC wall-clock so production bindings carry an honest
    # stamp. Tests call run_artifact_backfill directly with an explicit ``now``.
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


if __name__ == "__main__":
    raise SystemExit(main())
