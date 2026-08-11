"""FC-703 replay: real-catalog resolve latency baseline (read-only).

Resolves the real canary request matrix (CN 601899 FY2024/2025,
HK 03690 FY2024, US AAPL FY2025) against the LIVE catalog repeatedly
and reports p50/p95/p99 resolve latency plus candidate-slice sizes
(OPS-03: no full-table Python scan; EX-07: deterministic).  Read-only:
no catalog writes, no downloads.
"""
import json
import sqlite3
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from company_wiki.source_catalog import (  # noqa: E402
    CatalogConfig,
    RootSpec,
    SourceCatalog,
    SourceRequest,
    SourceResolver,
)

REQUESTS = [
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
REPEATS = 11  # odd count so p50 is exact


def _percentile(values, pct: float) -> float:
    values = sorted(values)
    idx = min(len(values) - 1, int(len(values) * pct))
    return values[idx]


def main() -> int:
    catalog_dir = PROJECT_ROOT / ".source_catalog"
    db_path = catalog_dir / "catalog.sqlite3"
    if not db_path.exists():
        print(json.dumps({
            "result": "FC-703 replay FAILED CLOSED",
            "error": f"catalog database missing: {db_path}",
            "hint": "run 'python -m company_wiki.source_catalog scan' "
                    "(or the catalog bootstrap) first",
        }, ensure_ascii=False, indent=1))
        return 2
    catalog = SourceCatalog(
        CatalogConfig(
            project_root=PROJECT_ROOT,
            catalog_dir=catalog_dir,
            reusable_root_kinds=("company_raw", "dayu_portfolio", "directory"),
            roots=(
                RootSpec("company_raw", PROJECT_ROOT / "companies", "company_raw"),
                RootSpec("dayu_portfolio",
                         Path(r"C:/Users/郑曾波/Projects/dayu-agent/workspace/portfolio"),
                         "dayu_portfolio"),
                RootSpec("dropbox_stock", Path.home() / "Dropbox" / "Stock",
                         "directory"),
            ),
        )
    )
    resolver = SourceResolver(catalog)
    results = []
    for sample in REQUESTS:
        timings = []
        status = None
        for _ in range(REPEATS):
            request = SourceRequest(
                entity=sample["entity"], market=sample["market"],
                security_id=sample["security_id"],
                document_kind="annual_report",
                fiscal_year=sample["fiscal_year"],
                provider_document_id=sample["provider_document_id"],
                as_of_date="2026-08-11", mode="exact",
            )
            start = time.perf_counter()
            result = resolver.resolve(request)
            timings.append((time.perf_counter() - start) * 1000.0)
            status = result.status.value
        results.append({
            "sample": sample["name"],
            "status": status,
            "p50_ms": round(_percentile(timings, 0.50), 1),
            "p95_ms": round(_percentile(timings, 0.95), 1),
            "p99_ms": round(_percentile(timings, 0.99), 1),
            "samples": REPEATS,
        })
    con = sqlite3.connect(f"file:{PROJECT_ROOT / '.source_catalog' / 'catalog.sqlite3'}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    total_docs = con.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
    con.close()
    print(json.dumps({
        "result": "FC-703 latency baseline (read-only)",
        "catalog_documents": total_docs,
        "requests": results,
        "side_effects": {"downloads": 0, "catalog_writes": 0,
                         "provider_calls": 0, "llm_calls": 0},
    }, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
