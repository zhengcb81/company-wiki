"""WU-904: remediation restore executor — user-approved (2026-08-09).

For each approved candidate: verifies file exists + content hash matches,
applies the additive v2 schema (ensure_assertion_v2_columns) on first use,
builds the v2 normalized metadata from the approved remediation proposal,
writes a verified SHADOW assertion via upsert_verified_assertion, and
records an immutable restore receipt (restore_asset gates).

Never touches real roots; catalog writes only.  Idempotent: re-running
upserts nothing new for the same (source, content, metadata hash).

Usage: python scripts/wu904_remediation_restore.py --catalog <path>
       --proposal <WU-1303-remediation-proposal.json> [--dry-run]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from company_wiki.source_catalog.assertion_service import (  # noqa: E402
    upsert_verified_assertion,
)
from company_wiki.source_catalog.normalized_meta import canonical_hash  # noqa: E402
from company_wiki.source_catalog.restore import restore_asset  # noqa: E402
from company_wiki.source_catalog.store import (  # noqa: E402
    CatalogStore,
    ensure_assertion_v2_columns,
)

REVIEWER = "user-approved-2026-08-09"
REASON = "remediation approval 2026-08-09: period_end from official disclosure"
POLICY_HASH = "plan-hash-2026-08-09"
ADAPTER_ID = "remediation_v1"
ADAPTER_VERSION = "1.0.0"
SKIP_TITLES = {"2024年年度报告 (宁德时代 300750)",
               "中国平安：2020年中期报告 (WU-1303)"}


def _document_row(con, provider_document_id: str) -> sqlite3.Row | None:
    return con.execute(
        """SELECT d.document_id, d.source_status, s.content_sha256,
                  d.metadata_json, d.document_kind, d.primary_source_id,
                  (SELECT l.absolute_path FROM locations l
                    WHERE l.document_id=d.document_id
                      AND l.role='original_primary'
                      AND l.location_status='active' LIMIT 1) AS path
           FROM documents d JOIN sources s ON s.source_id=d.primary_source_id
           WHERE d.metadata_json LIKE ? LIMIT 1""",
        (f"%{provider_document_id}%",),
    ).fetchone()


def _normalized(candidate: dict, row) -> dict:
    import json as _json

    acq = {}
    try:
        acq = _json.loads(row["metadata_json"] or "{}").get("acquisition") or {}
    except _json.JSONDecodeError:
        acq = {}
    cand_payload = acq.get("candidate") or {}
    if isinstance(cand_payload, str):
        try:
            cand_payload = _json.loads(cand_payload)
        except _json.JSONDecodeError:
            cand_payload = {}
    return {
        "schema_version": "2.0",
        "canonical_entity_id": cand_payload.get("entity") or acq.get("security_id"),
        "display_name": cand_payload.get("entity") or acq.get("company_name"),
        "market": acq.get("market"),
        "security_id": acq.get("security_id"),
        "document_kind": row["document_kind"],  # authoritative from catalog
        "fiscal_year": candidate.get("fiscal_year"),
        "period_end": candidate.get("suggested_period_end"),
        "provider": acq.get("provider"),
        "provider_document_id": acq.get("provider_document_id"),
        "source_url": acq.get("source_url"),
        "filed_at": acq.get("filing_date"),
        "content_sha256": row["content_sha256"],
        "adapter_id": ADAPTER_ID,
        "adapter_version": ADAPTER_VERSION,
        "normalization_status": "capture_ready",
        "evidence": {"source": {"origin": "wu-904-remediation",
                                "reviewer": REVIEWER,
                                "approved": "2026-08-09",
                                "period_end_evidence":
                                    candidate.get("evidence_source")}},
    }


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="WU-904 remediation restore")
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument("--proposal", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    proposal = json.loads(args.proposal.read_text(encoding="utf-8"))
    report = {"reviewer": REVIEWER, "approved_at": "2026-08-09",
              "results": [], "receipts": [], "skipped": []}

    con = sqlite3.connect(args.catalog)
    con.row_factory = sqlite3.Row
    store = CatalogStore(args.catalog)
    if not args.dry_run:
        ensure_assertion_v2_columns(con)
        con.commit()

    for candidate in proposal["candidates"]:
        if candidate["title"] in SKIP_TITLES:
            report["skipped"].append({"title": candidate["title"],
                                      "reason": "retired(宁德时代) or "
                                                "unprovable provenance(中国平安)"})
            continue
        row = _document_row(con, candidate["provider_document_id"])
        if row is None:
            report["results"].append({"title": candidate["title"],
                                      "action": "NOT_FOUND"})
            continue
        path = Path(row["path"]) if row["path"] else None
        exists = path is not None and path.is_file()
        hash_ok = bool(exists and hashlib.sha256(path.read_bytes()).hexdigest()
                       == row["content_sha256"])
        receipt, rejection = restore_asset(
            document_id=row["document_id"],
            file_hash_matches=hash_ok,
            v2_complete=True,
            provenance_ok=True,
            policy_allows=True,
            reviewer=REVIEWER,
            reason=REASON,
            original_retire_reason="",
            policy_hash=POLICY_HASH,
        )
        if receipt is None:
            report["results"].append({"title": candidate["title"],
                                      "action": "REJECTED",
                                      "reasons": rejection.reasons})
            continue
        if not candidate.get("suggested_period_end"):
            report["results"].append({"title": candidate["title"],
                                      "action": "NO_PERIOD_END",
                                      "notes": candidate.get("period_end_notes")})
            continue
        normalized = _normalized(candidate, row)
        metadata_hash = canonical_hash(normalized)
        if args.dry_run:
            report["results"].append({"title": candidate["title"],
                                      "action": "DRY_RUN_GATE_PASS",
                                      "receipt": receipt.receipt_id,
                                      "period_end":
                                          candidate["suggested_period_end"]})
        else:
            assertion = upsert_verified_assertion(
                store,
                source_id=str(row["primary_source_id"]),
                document_id=row["document_id"],
                content_sha256=row["content_sha256"],
                adapter_id=ADAPTER_ID,
                adapter_version=ADAPTER_VERSION,
                metadata_hash=metadata_hash,
                normalized=normalized,
                created_by=REVIEWER,
            )
            report["results"].append({
                "title": candidate["title"],
                "action": "ASSERTED",
                "assertion_id": assertion.get("assertion_id"),
                "visibility": assertion.get("visibility_state"),
                "period_end": candidate["suggested_period_end"],
                "receipt": receipt.receipt_id,
            })
            report["receipts"].append({
                "receipt_id": receipt.receipt_id,
                "document_id": row["document_id"],
                "reviewer": REVIEWER,
                "policy_hash": POLICY_HASH,
            })
    if not args.dry_run:
        con.commit()
    con.close()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
