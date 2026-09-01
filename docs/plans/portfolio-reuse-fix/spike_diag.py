# ruff: noqa: E402
"""Diagnostic: why does resolve not return REUSED_EXACT after the spike import?"""
from __future__ import annotations
import json
import sys
from pathlib import Path
CW_ROOT = Path(r"C:\Users\郑曾波\Projects\company-wiki")
sys.path.insert(0, str(CW_ROOT / "src"))
from company_wiki.source_catalog.config import load_catalog_config
from company_wiki.source_catalog.service import SourceCatalog
from company_wiki.source_catalog.resolver import SourceRequest, SourceResolver

SHA = "efe2ccd923b744eb69166aebf5f9b32ab7560efe3f6c44f2c6bcf4672fec1fa8"
config = load_catalog_config(CW_ROOT / "config" / "source_catalog.yaml", project_root=CW_ROOT)
catalog = SourceCatalog(config)

# 1) find the document + its metadata + locations
rows = catalog.store.fetchall(
    """SELECT d.document_id, d.title, d.document_kind, d.source_status, d.metadata_json,
              l.root_id, l.role, l.location_status, l.relative_path, l.absolute_path
       FROM sources s
       JOIN locations l ON l.source_id=s.source_id
       JOIN documents d ON d.document_id=l.document_id
       WHERE s.content_sha256=?""", (SHA,))
print(f"=== {len(rows)} rows for content_sha256 {SHA[:12]} ===")
roots_seen = set()
for r in rows:
    roots_seen.add(r["root_id"])
    md = json.loads(r["metadata_json"]) if r["metadata_json"] else {}
    print(f"\n-- loc root={r['root_id']} role={r['role']} status={r['location_status']}")
    print(f"   rel_path={r['relative_path']}")
    print(f"   title={r['title']!r} kind={r['document_kind']} status={r['source_status']}")
    print(f"   metadata TOP KEYS: {list(md.keys())}")
    for k in ("acquisition", "dayu_meta"):
        v = md.get(k)
        if isinstance(v, dict):
            print(f"   metadata[{k}] KEYS: {list(v.keys())}")
            print(f"     provider={v.get('provider')} pdid={v.get('provider_document_id')} market={v.get('market')} secid={v.get('security_id')} fy={v.get('fiscal_year')} form={v.get('form_type')} lang={v.get('language')}")
        else:
            print(f"   metadata[{k}] = {v!r}")
print(f"\nroots_seen for this content: {roots_seen}")

# 2) resolve the same request and print trace
req = SourceRequest(entity="金山雲", market="HK", security_id="3896",
    document_kind="annual_report", form_type="FY", fiscal_year=2025, fiscal_period="FY",
    language="zh", provider="hkexnews", provider_document_id="12118317",
    as_of_date="2026-08-02", allow_download=False)
res = SourceResolver(catalog).resolve(req)
print(f"\n=== resolve status={res.status.value} reason={res.reason} ===")
print(f"matches={len(res.matches)} download_required={res.download_required}")
print("debug_trace:")
for t in res.debug_trace:
    print("  ", t)
