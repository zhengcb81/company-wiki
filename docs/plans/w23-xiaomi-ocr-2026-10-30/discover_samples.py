"""W23 read-only sample discovery over the CWP source catalog.

Loads the ROOT catalog config (project_root=ROOT) but runs the worktree's
baseline code. Zero writes: SourceCatalog.reader is the ZR-203 read-only
model and this script never touches the writable store.
"""
import json
import sys
from pathlib import Path

ROOT = Path(r"C:/Users/郑曾波/Projects/company-wiki")
WT = Path(r"C:/Users/郑曾波/Projects/company-wiki-w23-xiaomi-ocr")
sys.path.insert(0, str(WT / "src"))

from company_wiki.source_catalog.config import load_catalog_config
from company_wiki.source_catalog.service import SourceCatalog
from company_wiki.source_catalog.metadata_observation import observe_metadata

cfg = load_catalog_config(ROOT / "config" / "source_catalog.yaml", project_root=ROOT)
print("catalog_dir:", cfg.catalog_dir, "exists:", cfg.catalog_dir.is_dir())
cat = SourceCatalog(cfg)

KINDS = [
    "annual_report", "semi_annual_report", "quarterly_report",
    "investor_call_transcript", "investor_relations", "prospectus",
    "equity_offering_prospectus", "broker_research",
]
summary = {}
for kind in KINDS:
    try:
        docs = cat.query_filing_candidates(
            document_kind=kind, source_statuses=("active",), limit=500
        )
    except Exception as exc:  # noqa: BLE001 - discovery reports, does not raise
        summary[kind] = {"error": f"{type(exc).__name__}: {exc}"}
        continue
    rows = []
    for d in docs:
        obs = observe_metadata(d.get("metadata_json")).metadata
        rows.append({
            "document_id": d.get("document_id"),
            "source_id": d.get("source_id"),
            "sha": (d.get("content_sha256") or "")[:12],
            "bytes": d.get("byte_size"),
            "mime": d.get("mime_type"),
            "market": obs.get("market"),
            "language": obs.get("language"),
            "fy": obs.get("fiscal_year"),
            "fp": obs.get("fiscal_period"),
            "title": (obs.get("source_title") or "")[:70],
            "entity": obs.get("display_name") or obs.get("canonical_entity_id"),
        })
    summary[kind] = {"count": len(rows), "rows": rows}

# Compact market/language distribution per kind
for kind, entry in summary.items():
    if "error" in entry:
        print(kind, "ERROR", entry["error"])
        continue
    dist = {}
    for r in entry["rows"]:
        key = (r["market"], r["language"])
        dist[str(key)] = dist.get(str(key), 0) + 1
    print(f"== {kind}: n={entry['count']} dist={dist}")

out = Path(__file__).parent / "discovered_candidates.json"
out.write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
print("WROTE", out)
cat.close()
