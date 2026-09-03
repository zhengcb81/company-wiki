"""WU-1500 + FC-705: legacy observation period reporter — read-only.

Runs a read-only resolver pass over the production catalog with an
observer attached, reporting legacy_bridge_hits for the current
observation period.  Period bookkeeping (started_at, hits, freeze gate
status, close-gate verdict) is recorded to a JSON file next to the
catalog; the production catalog and real roots are never written.

FC-705 adds the REAL resolver seam: the canary request matrix resolves
through SourceResolver with the pinned RuntimePolicySnapshot, so the
bridge-hit count comes from actual request resolution (v2-first),
not a bespoke sampling query.

Usage: python scripts/legacy_observer.py --catalog <catalog.sqlite3> \
       --config <source_catalog.yaml> --period <n> --period-file \
       <periods.json> --read-only [--canary-matrix]
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from company_wiki.source_catalog.observability import MetricsCollector  # noqa: E402
from company_wiki.source_catalog.resolver import (  # noqa: E402
    _source_metadata,
    resolver_visibility,
)
from company_wiki.source_catalog.service import SourceCatalog  # noqa: E402


def observe(
    catalog: Path,
    *,
    sample_limit: int = 2000,
) -> dict:
    """Read-only legacy bridge observation over active documents.

    Mirrors the production resolver path: the observer is attached to a
    v2-first read WITH the catalog store, so documents that now resolve
    through active v2 assertions do NOT record legacy_bridge_hits.

    Snapshot-gated (GP-008): a pinned runtime-policy snapshot governs
    reader / epoch / cohorts / legacy_bridge_allowed exactly like
    SourceResolver — absent snapshot keeps the pre-FC-201 production
    default (bridge on, v1 reader).  Under the production snapshot
    (bridge disabled) no container read is allowed, so a zero-hit window
    reflects real production semantics instead of legacy-default
    over-counting.
    """
    con = sqlite3.connect(f"file:{catalog}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA query_only = ON")
    collector = MetricsCollector()

    snapshot = _load_policy(catalog.parent)
    if snapshot is None:
        # pre-FC-201 production default (mirrors SourceResolver)
        reader: str = "v1"
        epoch: str | None = None
        cohorts: tuple[str, ...] = ()
        bridge = True
        policy_hash = None
    else:
        reader, epoch, cohorts, bridge = resolver_visibility(snapshot)
        policy_hash = snapshot.get("policy_hash")

    class _StoreFacade:
        def __init__(self, connection):
            self._connection = connection

        def fetchone(self, sql, params=()):
            return self._connection.execute(sql, tuple(params)).fetchone()

        def fetchall(self, sql, params=()):
            return self._connection.execute(sql, tuple(params)).fetchall()

    store = _StoreFacade(con)
    rows = con.execute(
        """SELECT d.document_id, d.metadata_json, d.primary_source_id
           FROM documents d
           WHERE d.source_type='regulatory_filing'
             AND d.source_status='active'
             AND d.metadata_json LIKE '%acquisition%'
           LIMIT ?""",
        (sample_limit,),
    ).fetchall()
    for row in rows:
        try:
            metadata = json.loads(row["metadata_json"] or "{}")
        except json.JSONDecodeError:
            metadata = {}
        _source_metadata({"source_id": row["primary_source_id"],
                          "metadata": metadata}, store=store,
                         observer=collector, reader=reader,
                         current_epoch=epoch, active_cohorts=cohorts,
                         legacy_bridge_allowed=bridge)
    con.close()
    report = collector.snapshot()
    return {
        "sampled_documents": len(rows),
        "legacy_bridge_hits": report.legacy_bridge_hits,
        "shadow_diffs": report.shadow_diffs,
        "reasons": report.aggregate("reason"),
        "mode": "sample",
        "reader": reader,
        "legacy_bridge_enabled": bridge,
        "snapshot_policy_hash": policy_hash,
    }


# FC-705 canary request matrix: the same real samples the canary cohort
# was registered with (FC-505/FC-604 matrix + the active assertions).
CANARY_REQUESTS = [
    {"name": "CN-601899-FY2024", "entity": "紫金矿业", "market": "CN",
     "security_id": "601899", "fiscal_year": 2024,
     "provider_document_id": "1222870413"},
    {"name": "CN-601899-FY2025", "entity": "紫金矿业", "market": "CN",
     "security_id": "601899", "fiscal_year": 2025,
     "provider_document_id": "1225023658"},
    {"name": "HK-03690-FY2024", "entity": "美團－Ｗ", "market": "HK",
     "security_id": "03690", "fiscal_year": 2024,
     "provider_document_id": "11645024"},
    {"name": "US-AAPL-FY2025", "entity": "Apple Inc", "market": "US",
     "security_id": "AAPL", "fiscal_year": 2025,
     "provider_document_id": "0000320193-25-000079"},
]


def _load_policy(catalog_dir: Path) -> dict | None:
    """Load the production RuntimePolicySnapshot (None when absent)."""
    from company_wiki.source_catalog.runtime_policy import (
        RuntimePolicyError,
        load_runtime_policy,
    )

    try:
        return load_runtime_policy(catalog_dir / "runtime_policy.json")
    except RuntimePolicyError:
        return None


class _ReadOnlyStore:
    """fetchone/fetchall facade over a mode=ro + query_only connection."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def fetchone(self, sql: str, params=()):
        return self._connection.execute(sql, tuple(params)).fetchone()

    def fetchall(self, sql: str, params=()):
        return self._connection.execute(sql, tuple(params)).fetchall()


class _ReadOnlyCatalog(SourceCatalog):
    """SourceCatalog whose store is a read-only connection: constructing a
    CatalogStore runs WAL/DDL/migrations (a write) — the observer must never
    write the production catalog."""

    def __init__(self, config, connection: sqlite3.Connection) -> None:
        super().__init__(config)
        self._read_only_store = _ReadOnlyStore(connection)

    @property
    def store(self):  # type: ignore[override]
        return self._read_only_store


def observe_canary_matrix(
    config_path: Path,
    *,
    drill: bool = False,
) -> dict:
    """FC-705: resolve the canary matrix through the REAL resolver seam.

    ``drill=False`` uses the production snapshot as-is (honest current-state
    count).  ``drill=True`` simulates the cutover: v2_resolve_active=True,
    legacy_bridge_enabled=False, epoch/cohort pinned — proving the canary
    requests resolve REUSED_EXACT without touching the bridge.  The catalog
    is opened mode=ro + query_only: zero writes (no WAL/DDL/migration).
    """
    from company_wiki.source_catalog.config import load_catalog_config
    from company_wiki.source_catalog.resolver import (
        SourceRequest,
        SourceResolver,
    )
    config = load_catalog_config(config_path.resolve())
    connection = sqlite3.connect(
        f"file:{config.database_path}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA query_only = ON")
    catalog = _ReadOnlyCatalog(config, connection)
    snapshot = _load_policy(config.catalog_dir)
    if drill:
        flags = dict(snapshot.get("flags", {})) if snapshot else {}
        flags["v2_resolve_active"] = True
        flags["legacy_bridge_enabled"] = False
        snapshot = {
            "schema_version": (snapshot or {}).get("schema_version", "1.0"),
            "policy_hash": (snapshot or {}).get("policy_hash"),
            "flags": flags,
            "current_epoch": (snapshot or {}).get("current_epoch"),
            "active_cohorts": (snapshot or {}).get("active_cohorts"),
        }
    collector = MetricsCollector()
    resolver = SourceResolver(
        catalog, observer=collector, runtime_policy=snapshot)
    requests = []
    try:
        for sample in CANARY_REQUESTS:
            result = resolver.resolve(SourceRequest(
                entity=sample["entity"], market=sample["market"],
                security_id=sample["security_id"],
                document_kind="annual_report",
                fiscal_year=sample["fiscal_year"],
                provider_document_id=sample["provider_document_id"],
                as_of_date="2026-08-11", mode="exact",
            ))
            requests.append({
                "name": sample["name"],
                "status": result.status.value,
                "reason": result.reason,
            })
    finally:
        connection.close()
    report = collector.snapshot()
    return {
        "mode": "drill" if drill else "current",
        "snapshot_policy_hash": (snapshot or {}).get("policy_hash"),
        "requests": requests,
        "legacy_bridge_hits": report.legacy_bridge_hits,
        "shadow_diffs": report.shadow_diffs,
    }


def _load_periods(path: Path) -> dict:
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"periods": []}


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="WU-1500/FC-705 legacy observer")
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=None,
                        help="source_catalog.yaml for the canary-matrix seam "
                             "(default: <catalog_dir>/../config/source_catalog.yaml)")
    parser.add_argument("--period", type=int, required=True)
    parser.add_argument("--period-file", type=Path, required=True)
    parser.add_argument("--read-only", action="store_true", required=True)
    parser.add_argument("--sample-limit", type=int, default=2000)
    parser.add_argument("--canary-matrix", action="store_true",
                        help="FC-705: observe the canary matrix through the "
                             "real resolver seam (instead of the sample pass)")
    parser.add_argument("--drill", action="store_true",
                        help="simulate the cutover: v2 active + bridge off")
    args = parser.parse_args()
    if not args.read_only:
        print("refusing: --read-only is mandatory", file=sys.stderr)
        return 2

    if args.canary_matrix:
        config_path = args.config or (
            args.catalog.parent / "config" / "source_catalog.yaml")
        result = observe_canary_matrix(config_path, drill=args.drill)
    else:
        result = observe(args.catalog, sample_limit=args.sample_limit)

    periods = _load_periods(args.period_file)
    existing = [p for p in periods["periods"] if p["period"] == args.period]
    if existing:
        entry = existing[0]
        entry["ended_at"] = None  # still observing
        entry["legacy_bridge_hits"] = result["legacy_bridge_hits"]
        entry["mode"] = result.get("mode", "sample")
        entry["updated_at"] = _utc_now()
    else:
        # a new period closes the previous one (real timestamps, FC-705)
        if periods["periods"]:
            previous = max(periods["periods"], key=lambda p: p["period"])
            if previous.get("ended_at") is None:
                previous["ended_at"] = _utc_now()
        periods["periods"].append({
            "period": args.period,
            "started_at": _utc_now(),
            "legacy_bridge_hits": result["legacy_bridge_hits"],
            "shadow_diffs": result.get("shadow_diffs"),
            "sampled_documents": result.get("sampled_documents"),
            "mode": result.get("mode", "sample"),
            "freeze_gate": "no new callers (resolver._source_metadata only)",
            "status": "observing",
        })
    periods["periods"].sort(key=lambda p: p["period"])
    from company_wiki.source_catalog.legacy_close_gate import close_gate_allowed

    allowed, reasons = close_gate_allowed(periods["periods"])
    verdict = {
        "close_allowed": allowed,
        "reasons": reasons,
        "evaluated_at": _utc_now(),
    }
    args.period_file.parent.mkdir(parents=True, exist_ok=True)
    periods["close_gate"] = verdict
    args.period_file.write_text(
        json.dumps(periods, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    result["close_gate"] = verdict
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
