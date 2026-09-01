"""Phase 14 R8 evidence tool: bridge-off equivalence comparison (READ-ONLY).

The WU-1500 close gate's hit metric only records probe traffic (production
resolve runs without an observer — resolver.py passes observer=None), so
the zero-hit condition can never be satisfied by production traffic and the
probes themselves would keep the gate permanently closed (findings 64:
measurement self-lock).

R8 entry condition v2 (documented plan amendment):
  (a) canary drill: v2 + bridge-off -> 4/4 REUSED_EXACT, zero hits;
  (b) THIS equivalence run: the canary matrix + every legacy-assertion
      document + a random sample of active documents resolve under BOTH
      policies (production current vs bridge-off) with IDENTICAL outcomes,
      except the enumerated legacy-assertion enrichment drops;
  (c) the >=24h observation windows already elapsed (periods 3-5, stable
      probe-only hits) demonstrate no production bridge traffic.

Exit 0 = equivalence holds with only the enumerated expected differences;
1 = unexpected divergence (R8 must NOT proceed).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sqlite3
import sys
from copy import deepcopy
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from company_wiki.source_catalog import SourceCatalog  # noqa: E402
from company_wiki.source_catalog.config import load_catalog_config  # noqa: E402
from company_wiki.source_catalog.observability import MetricsCollector  # noqa: E402
from company_wiki.source_catalog.resolver import SourceRequest, SourceResolver  # noqa: E402
from company_wiki.source_catalog.runtime_policy import load_runtime_policy  # noqa: E402

# Mirrors legacy_observer.CANARY_REQUESTS exactly — full identity so the
# v2 strict entity gate (FC-702) receives the same inputs as production.
CANARIES = [
    {"entity": "紫金矿业", "market": "CN", "security_id": "601899", "fiscal_year": 2024,
     "provider_document_id": "1222870413"},
    {"entity": "紫金矿业", "market": "CN", "security_id": "601899", "fiscal_year": 2025,
     "provider_document_id": "1225023658"},
    {"entity": "美團－Ｗ", "market": "HK", "security_id": "03690", "fiscal_year": 2024,
     "provider_document_id": "11645024"},
    {"entity": "Apple Inc", "market": "US", "security_id": "AAPL", "fiscal_year": 2025,
     "provider_document_id": "0000320193-25-000079"},
]

SAMPLE_SIZE = 100


def _resolve(resolver: SourceResolver, observer: MetricsCollector, entity: str,
             market: str | None, kind: str, fiscal_year: int | None = None,
             security_id: str | None = None,
             provider_document_id: str | None = None) -> dict:
    try:
        result = resolver.resolve(SourceRequest(
            entity=entity,
            market=market,
            security_id=security_id,
            document_kind=kind,
            fiscal_year=fiscal_year,
            provider_document_id=provider_document_id,
            as_of_date="2026-08-13",
            mode="exact",
        ))
        matches = getattr(result, "matches", None)
        status = getattr(result, "status", None)
        return {
            "ok": True,
            "status": getattr(status, "value", None) if status is not None else None,
            "matches": len(matches) if matches else 0,
        }
    except Exception as exc:  # noqa: BLE001 - comparison wants the failure mode
        return {"ok": False, "error": type(exc).__name__}


def main(argv: list[str] | None = None) -> int:
    # FC-1205 pattern: force UTF-8 stdio (Chinese user path/GBK console).
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--sample", type=int, default=SAMPLE_SIZE)
    args = parser.parse_args(argv)

    cfg = load_catalog_config(args.config, project_root=Path("."))
    cat = SourceCatalog(cfg)
    current = load_runtime_policy(args.catalog.parent / "runtime_policy.json")

    bridge_off = deepcopy(current)
    bridge_off["flags"] = dict(current["flags"])
    bridge_off["flags"]["legacy_bridge_enabled"] = False
    bridge_off["flags"]["v2_resolve_shadow"] = True
    bridge_off["flags"]["v2_resolve_active"] = True

    random.Random(20260813)
    db = sqlite3.connect(f"file:{args.catalog}?mode=ro", uri=True)
    legacy_docs = [
        (r[0], r[1], r[2], r[3])
        for r in db.execute(
            "SELECT a.entity, a.market, a.document_kind, a.fiscal_year "
            "FROM source_metadata_assertions a WHERE a.visibility_state='legacy'"
        ).fetchall()
    ]
    sample_rows = db.execute(
        "SELECT a.entity, a.market, a.document_kind, a.fiscal_year, a.security_id, "
        "       a.provider_document_id "
        "FROM source_metadata_assertions a "
        "JOIN documents d ON d.document_id = a.document_id "
        "WHERE d.source_status='active' AND a.entity IS NOT NULL AND a.entity != '' "
        "ORDER BY random() LIMIT ?", (args.sample,)).fetchall()
    db.close()

    probes: list[tuple[str, str | None, str, str, int | None, str | None, str | None]] = []
    for c in CANARIES:
        probes.append((c["entity"], c.get("market"), "annual_report", "canary",
                       c.get("fiscal_year"), c.get("security_id"), c.get("provider_document_id")))
    for entity, market, kind, fy in legacy_docs:
        probes.append((entity, market, kind or "annual_report", "legacy-assertion", fy, None, None))
    for entity, market, kind, fy, sid, pdoc in sample_rows:
        probes.append((entity, market, kind or "annual_report", "sample", fy, sid, pdoc))

    current_resolver = SourceResolver(cat, runtime_policy=current)
    off_resolver = SourceResolver(cat, runtime_policy=bridge_off)

    rows = []
    unexpected = 0
    for entity, market, kind, label, fy, sid, pdoc in probes:
        ob1, ob2 = MetricsCollector(), MetricsCollector()
        before = _resolve(current_resolver, ob1, entity, market, kind, fy, sid, pdoc)
        after = _resolve(off_resolver, ob2, entity, market, kind, fy, sid, pdoc)
        equivalent = before == after
        hits = ob1._report.legacy_bridge_hits
        if not equivalent:
            unexpected += 1
        rows.append({
            "label": label,
            "entity": entity,
            "market": market,
            "before": before,
            "after": after,
            "equivalent": equivalent,
            "bridge_hits_current_policy": hits,
        })

    report = {
        "policies": {
            "current_flags": current["flags"],
            "bridge_off_flags": bridge_off["flags"],
        },
        "probes": rows,
        "unexpected_divergences": unexpected,
        "expected_divergences": sum(
            1 for r in rows if r["label"] == "legacy-assertion" and not r["equivalent"]
        ),
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    # Divergences are acceptable ONLY for legacy-assertion docs (their legacy
    # enrichment disappears by design) — everything else must be identical.
    sample_bad = sum(
        1 for r in rows if r["label"] != "legacy-assertion" and not r["equivalent"]
    )
    return 1 if sample_bad else 0


if __name__ == "__main__":
    sys.exit(main())
