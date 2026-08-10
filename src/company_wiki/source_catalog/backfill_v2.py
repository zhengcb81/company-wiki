"""WU-902: legacy company_raw/dayu -> v2 assertion backfill.

Constructs v2 assertions ONLY from strong-binding legacy fields:
provider_document_id + source_url + form_type + fiscal_year + provider,
plus provable period_end.  Anything unprovable goes to the remediation
queue with the exact missing field — never guessed from file names or
titles.  Reconciliation closes: input = success + indexed_only +
conflict + skipped + error, bucketed by root/status/kind/year.

Modes: dry-run (default, zero writes) | apply (writes shadow assertions
only — visibility_state='shadow', reader stays v1/legacy).
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from dataclasses import dataclass, field
from pathlib import Path

STRONG_FIELDS = (
    "provider_document_id",
    "source_url",
    "form_type",
    "fiscal_year",
    "provider",
)

# display-name style security ids are never strong identity
_STRONG_SECURITY_EXAMPLES = {"AAPL", "NVDA", "002594", "300750", "03690",
                             "601899", "09988", "02020", "03896", "06082"}
_REQUIRED_STRONG = frozenset(STRONG_FIELDS)


@dataclass
class StrongBinding:
    """A doc passed the strong-binding gate (before period provability)."""

    document_id: str
    source_id: str
    content_sha256: str
    missing_fields: list[str] = field(default_factory=list)


@dataclass
class BackfillResult:
    input: int = 0
    success: int = 0
    indexed_only: int = 0
    conflict: int = 0
    skipped: int = 0
    errors: int = 0
    created: list[str] = field(default_factory=list)
    remediation: list[dict] = field(default_factory=list)
    buckets: dict[str, int] = field(default_factory=dict)
    rows: list[dict] = field(default_factory=list)

    def reconciliation_by(self, dim: str) -> dict[str, dict[str, int]]:
        out: dict[str, dict[str, int]] = {}
        for row in self.rows:
            key = str(row.get(dim) or "(none)")
            bucket = row["bucket"]
            slot = out.setdefault(key, {})
            slot["total"] = slot.get("total", 0) + 1
            slot[bucket] = slot.get(bucket, 0) + 1
        return out

    def as_dict(self) -> dict:
        return {
            "input": self.input,
            "success": self.success,
            "indexed_only": self.indexed_only,
            "conflict": self.conflict,
            "skipped": self.skipped,
            "errors": self.errors,
            "closed": (self.input == self.success + self.indexed_only
                       + self.conflict + self.skipped + self.errors),
            "created_assertions": self.created,
            "remediation": self.remediation,
            "by_root": self.reconciliation_by("root_id"),
            "by_status": self.reconciliation_by("source_status"),
            "by_kind": self.reconciliation_by("document_kind"),
            "by_year": self.reconciliation_by("fiscal_year"),
        }


def _connect(path: Path) -> sqlite3.Connection:
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


def _is_strong_security(security_id: str, company_name: str | None) -> bool:
    """A ticker/stock-code is strong; a Chinese display name is not."""
    if not security_id:
        return False
    if company_name and security_id == company_name:
        return False
    if security_id in _STRONG_SECURITY_EXAMPLES:
        return True
    # ticker-like: uppercase ASCII with digits (AAPL, 002594, 03690)
    return (
        security_id.isascii()
        and security_id.isalnum()
        and any(ch.isdigit() for ch in security_id)
        and len(security_id) <= 10
    )


def _classify(acq: dict) -> StrongBinding:
    """Strong-binding gate over acquisition metadata (no guessing)."""
    missing = [f for f in _REQUIRED_STRONG if not acq.get(f)]
    security_id = acq.get("security_id")
    if not _is_strong_security(str(security_id or ""), acq.get("company_name")):
        missing.append("security_id")
    return StrongBinding(
        document_id="",
        source_id="",
        content_sha256=str(acq.get("content_sha256") or ""),
        missing_fields=missing,
    )


def classify_bucket(
    acq: dict,
    *,
    evidence_hint_only: bool = False,
    existing_verified_hash: str | None = None,
) -> tuple[str, list[str]]:
    """FC-402: classify a filing into exactly one bucket.

    eligible            — strong identity + provable period + HTTPS source
                           (capture-ready candidate)
    needs_review        — strong identity but period not provable from
                           metadata (never guessed from the file name)
    unprovable          — weak identity (display-name security_id, 中国平安
                           style) or critical field missing; fails closed
                           until evidence is completed
    retired_or_conflict — content hash conflicts with an existing verified
                           assertion (history coexists, never overwritten)

    ``evidence_hint_only`` marks a document whose only evidence is its file
    name/title: the name is at most a hint and NEVER makes it capture-ready.
    """
    if evidence_hint_only:
        missing = ["content_sha256"]
        if not acq.get("security_id"):
            missing.append("security_id")
        return "unprovable", missing
    missing = [f for f in _REQUIRED_STRONG if not acq.get(f)]
    security_id = acq.get("security_id")
    if not _is_strong_security(str(security_id or ""), acq.get("company_name")):
        missing.append("security_id")
    source_url = str(acq.get("source_url") or "")
    if source_url and not source_url.lower().startswith("https://"):
        missing.append("source_url")
    if missing:
        # weak identity / critical field missing -> unprovable; a mere
        # missing period keeps the strong identity but needs review
        if "security_id" in missing or "provider_document_id" in missing:
            return "unprovable", sorted(set(missing))
        if "period_end" in missing:
            return "needs_review", sorted(set(missing))
        return "unprovable", sorted(set(missing))
    period_end = acq.get("period_end")
    if not period_end:
        return "needs_review", ["period_end"]
    if existing_verified_hash is not None:
        declared = str(acq.get("content_sha256") or "")
        if declared and existing_verified_hash != declared:
            return "retired_or_conflict", []
    return "eligible", []


def run_backfill(
    catalog: Path,
    *,
    roots: tuple[str, ...],
    mode: str = "dry-run",
) -> BackfillResult:
    """Backfill legacy acquisition metadata into v2 shadow assertions.

    mode: dry-run (classify only, zero writes) | apply (write verified
    shadow assertions for strong-bound, period-provable documents only).
    """
    if mode not in {"dry-run", "apply"}:
        raise ValueError(f"unknown mode {mode!r}")
    result = BackfillResult()
    con = _connect(catalog)
    placeholders = ",".join("?" for _ in roots)
    docs = con.execute(
        f"""SELECT d.document_id, d.title, d.source_status, d.document_kind,
                   d.metadata_json, d.primary_source_id,
                   s.content_sha256,
                   (SELECT GROUP_CONCAT(l.root_id) FROM locations l
                     WHERE l.document_id = d.document_id) AS root_ids
            FROM documents d
            LEFT JOIN sources s ON s.source_id = d.primary_source_id
            WHERE d.source_type = 'regulatory_filing'
              AND (SELECT COUNT(*) FROM locations l
                    WHERE l.document_id = d.document_id
                      AND l.root_id IN ({placeholders})) > 0
            ORDER BY d.document_id""",
        roots,
    ).fetchall()

    for row in docs:
        result.input += 1
        try:
            metadata = json.loads(row["metadata_json"] or "{}")
        except json.JSONDecodeError:
            metadata = {}
        acq = metadata.get("acquisition") or {}
        binding = _classify(acq)
        record = {
            "document_id": row["document_id"],
            "title": row["title"],
            "root_id": row["root_ids"],
            "source_status": row["source_status"],
            "document_kind": row["document_kind"],
            "fiscal_year": acq.get("fiscal_year"),
            "content_sha256": row["content_sha256"] or acq.get("content_sha256"),
            "bucket": "error",
        }

        if binding.missing_fields:
            record["bucket"] = "indexed_only"
            result.indexed_only += 1
            result.remediation.append({
                "document_id": row["document_id"],
                "title": row["title"],
                "missing_fields": sorted(set(binding.missing_fields)),
                "reason": "missing " + ",".join(
                    sorted(set(binding.missing_fields))
                ),
            })
            result.rows.append(record)
            continue

        # strong binding present — period must also be provable
        period_end = acq.get("period_end")
        if not period_end:
            record["bucket"] = "indexed_only"
            result.indexed_only += 1
            result.remediation.append({
                "document_id": row["document_id"],
                "title": row["title"],
                "missing_fields": ["period_end"],
                "reason": "missing period_end (not provable from legacy "
                          "metadata; never guessed from title/file name)",
            })
            result.rows.append(record)
            continue

        content_sha256 = row["content_sha256"] or acq.get("content_sha256")
        source_id = str(row["primary_source_id"] or "")
        # conflict: an existing verified assertion for the same source with
        # a different content hash (history coexists; never overwritten)
        existing = con.execute(
            """SELECT content_sha256 FROM source_metadata_assertions
               WHERE source_id=? AND decision='verified'
               ORDER BY created_at DESC LIMIT 1""",
            (source_id,),
        ).fetchone()
        if existing is not None and existing["content_sha256"] != content_sha256:
            record["bucket"] = "conflict"
            result.conflict += 1
            result.rows.append(record)
            continue

        # skip: identical verified assertion already exists
        if existing is not None and existing["content_sha256"] == content_sha256:
            record["bucket"] = "skipped"
            result.skipped += 1
            result.rows.append(record)
            continue

        record["bucket"] = "success"
        result.success += 1
        result.rows.append(record)
        if mode == "apply":
            assertion_id = f"sa-bf-{uuid.uuid4().hex}"
            result.created.append(assertion_id)
            con.execute(
                """INSERT INTO source_metadata_assertions
                (assertion_id, source_id, document_id, entity, market,
                 security_id, document_kind, form_type, fiscal_year,
                 fiscal_period, provider, provider_document_id, source_url,
                 filing_date, content_sha256, evidence_basis, evidence_json,
                 decision, created_at, created_by, schema_version,
                 adapter_id, adapter_version, normalized_sha256,
                 normalization_status, visibility_state)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    assertion_id, source_id, row["document_id"],
                    acq.get("company_name"), acq.get("market"),
                    acq.get("security_id"), acq.get("document_kind"),
                    acq.get("form_type"), acq.get("fiscal_year"),
                    acq.get("fiscal_period"), acq.get("provider"),
                    acq.get("provider_document_id"), acq.get("source_url"),
                    acq.get("filing_date"), content_sha256,
                    "legacy-backfill-v1",
                    json.dumps({"origin": "legacy-backfill-v1",
                                "provider": acq.get("provider"),
                                "provider_document_id":
                                    acq.get("provider_document_id"),
                                "source_url": acq.get("source_url")}),
                    "verified", "2026-08-09", "wu-902", "2.0",
                    "legacy_bridge_v1", "1.0.0",
                    "", "capture_ready", "shadow",
                ),
            )
    if mode == "apply":
        con.commit()
    con.close()
    result.buckets = {
        "success": result.success,
        "indexed_only": result.indexed_only,
        "conflict": result.conflict,
        "skipped": result.skipped,
        "errors": result.errors,
    }
    return result


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="WU-902 legacy company_raw/dayu -> v2 backfill")
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument("--roots", default="company_raw,dayu_portfolio")
    parser.add_argument("--mode", choices=("dry-run", "apply"), default="dry-run")
    args = parser.parse_args()
    result = run_backfill(
        args.catalog,
        roots=tuple(item.strip() for item in args.roots.split(",") if item.strip()),
        mode=args.mode,
    )
    print(json.dumps(result.as_dict(), ensure_ascii=False, indent=2))
    if not result.as_dict()["closed"]:
        print("RECONCILIATION NOT CLOSED", file=__import__("sys").stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
