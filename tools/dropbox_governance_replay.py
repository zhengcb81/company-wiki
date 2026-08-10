"""FC-503 replay: real-root read-only governance inventory.

Runs ``inventory_dropbox`` over the REAL Dropbox/Stock root twice,
asserts the two reports are identical (determinism + zero writes), and
prints a compact JSON summary (no absolute paths, no file contents).
Also asserts the catalog invariants: every 中国平安 company_raw
document stays retired (weak display-name identity, never revived) and
the catalog row counts are unchanged by the inventory.
"""
import hashlib
import json
import os
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import yaml  # noqa: E402

from company_wiki.source_catalog.dropbox_governance import (  # noqa: E402
    inventory_dropbox,
)
from company_wiki.source_catalog.models import RootSpec  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "config" / "source_catalog.yaml"
CATALOG_PATH = PROJECT_ROOT / ".source_catalog" / "catalog.sqlite3"


def _dropbox_root_spec() -> tuple[RootSpec, tuple[str, ...]]:
    cfg = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    entry = next(r for r in cfg["roots"] if r["root_id"] == "dropbox_stock")
    raw = str(entry["path"])
    resolved = raw.replace("${USER_PROFILE}", os.environ.get("USERPROFILE") or "")
    root = RootSpec(root_id="dropbox_stock", path=Path(resolved), kind="directory",
                    adapter_id="sidecar_filing_v1")
    other_root_ids = tuple(
        r["root_id"] for r in cfg["roots"] if r["root_id"] != "dropbox_stock"
    )
    return root, other_root_ids


def _catalog_counts() -> tuple[int, int, int]:
    con = sqlite3.connect(f"file:{CATALOG_PATH}?mode=ro", uri=True)
    try:
        return tuple(
            con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            for t in ("documents", "sources", "locations")
        )
    finally:
        con.close()


_RESEARCH_KINDS = ("broker_research", "other")


def _pingan_retired_invariants() -> dict:
    """Every 中国平安 weak-identity document that is filing-kind must stay
    retired; any active weak-identity filing-kind doc is capture-incomplete
    (no fiscal_year — never eligible without reviewer-completed evidence).
    The inventory run must not promote or revive any."""
    con = sqlite3.connect(f"file:{CATALOG_PATH}?mode=ro", uri=True)
    try:
        rows = con.execute(
            """SELECT d.source_status, d.document_kind, COUNT(*) c
               FROM documents d
               WHERE d.title LIKE '%中国平安%'
                 AND d.metadata_json LIKE '%"security_id":"中国平安"%'
               GROUP BY d.source_status, d.document_kind"""
        ).fetchall()
        retired = sum(r[2] for r in rows if r[0] == "retired")
        active = sum(r[2] for r in rows if r[0] == "active")
        if retired < 1:
            raise SystemExit(f"FAIL: 中国平安 retired docs = {retired}, expected >= 1")
        active_filing_kind = [
            (r[1], r[2]) for r in rows
            if r[0] == "active" and r[1] not in _RESEARCH_KINDS
        ]
        capture_incomplete = con.execute(
            """SELECT COUNT(*) c FROM documents d
               WHERE d.title LIKE '%中国平安%'
                 AND d.metadata_json LIKE '%"security_id":"中国平安"%'
                 AND d.source_status = 'active'
                 AND d.metadata_json NOT LIKE '%"fiscal_year"%'"""
        ).fetchone()[0]
        if capture_incomplete != active:
            raise SystemExit(
                f"FAIL: 中国平安 active capture-incomplete = {capture_incomplete},"
                f" expected {active} (every active weak-identity doc must lack"
                f" fiscal_year)"
            )
        return {
            "pingan_retired": retired,
            "pingan_active": active,
            "active_filing_kind": active_filing_kind,
            "active_capture_incomplete": capture_incomplete,
        }
    finally:
        con.close()


def _summary(report: dict) -> dict:
    fp = report["fingerprint"]
    digest = hashlib.sha256(
        json.dumps(fp, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    return {
        "candidates_total": report["candidates_total"],
        "by_role": report["by_role"],
        "buckets": report["buckets"],
        "missing_fields_top": dict(
            sorted(report["missing_fields"].items(), key=lambda kv: -kv[1])[:8]
        ),
        "duplicate_location_sets": report["duplicate_location_sets"]["count"],
        "pingan": report["pingan"],
        "fingerprint_sha256": digest,
        "catalog_counts": report["catalog_counts"],
        "writes": report["writes"],
    }


def main() -> int:
    counts_before = _catalog_counts()
    root, other_root_ids = _dropbox_root_spec()
    first = inventory_dropbox(root, catalog=CATALOG_PATH,
                              other_root_ids=other_root_ids)
    second = inventory_dropbox(root, catalog=CATALOG_PATH,
                               other_root_ids=other_root_ids)
    if first["fingerprint"] != second["fingerprint"]:
        raise SystemExit("FAIL: fingerprint changed between two runs")
    if first["buckets"] != second["buckets"]:
        raise SystemExit("FAIL: buckets changed between two runs")
    if first["duplicate_location_sets"] != second["duplicate_location_sets"]:
        raise SystemExit("FAIL: duplicate sets changed between two runs")
    if first["catalog_counts"] != counts_before:
        raise SystemExit("FAIL: catalog row counts changed by the inventory")
    pingan = _pingan_retired_invariants()
    if first["pingan"]["eligible"] != 0:
        raise SystemExit("FAIL: 中国平安 eligible != 0")
    print(json.dumps({
        "result": "identical-across-two-runs",
        "summary": _summary(first),
        "pingan_catalog_invariants": pingan,
    }, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
