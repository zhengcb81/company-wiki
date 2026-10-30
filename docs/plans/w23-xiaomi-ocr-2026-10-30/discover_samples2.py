"""W23 read-only sample discovery, second pass: full metadata + locations."""
import json
import sqlite3
from pathlib import Path

ROOT = Path(r"C:/Users/郑曾波/Projects/company-wiki")
OUT = Path(__file__).parent / "discovered_candidates2.json"

con = sqlite3.connect(
    f"file:{ROOT.as_posix()}/.source_catalog/catalog.sqlite3?mode=ro", uri=True
)
con.row_factory = sqlite3.Row

rows = con.execute(
    """
    SELECT d.document_id, d.primary_source_id, d.document_kind, d.published_date,
           d.source_status, d.metadata_json,
           s.source_id, s.content_sha256, s.byte_size, s.mime_type
    FROM documents d JOIN sources s ON s.source_id = d.primary_source_id
    WHERE d.source_status = 'active'
    ORDER BY d.document_kind, d.published_date
    """
).fetchall()

KINDS = {
    "annual_report", "semi_annual_report", "quarterly_report",
    "investor_call_transcript", "investor_relations", "prospectus",
    "equity_offering_prospectus", "convertible_bond_prospectus",
    "broker_research",
}
out = {}
for r in rows:
    kind = r["document_kind"]
    if kind not in KINDS:
        continue
    md = json.loads(r["metadata_json"] or "{}")
    cand = (md.get("acquisition") or {}).get("candidate") or {}
    entry = {
        "document_id": r["document_id"],
        "source_id": r["source_id"],
        "sha256": r["content_sha256"],
        "byte_size": r["byte_size"],
        "mime": r["mime_type"],
        "published": r["published_date"],
        "market": cand.get("market"),
        "language": cand.get("language"),
        "entity": cand.get("entity"),
        "fy": cand.get("fiscal_year"),
        "fp": cand.get("fiscal_period"),
        "form_type": cand.get("form_type"),
        "provider": cand.get("provider"),
        "title": (cand.get("source_url") or cand.get("primary_filename") or "")[:90],
    }
    out.setdefault(kind, []).append(entry)

for kind in sorted(out):
    entries = out[kind]
    dist = {}
    for e in entries:
        key = (e["market"], e["language"])
        dist[str(key)] = dist.get(str(key), 0) + 1
    print(f"== {kind}: n={len(entries)} dist={dist}")

OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print("WROTE", OUT)
