"""Dump native PDF text layer per frozen sample page as CANDIDATE transcripts.

Candidates are never gold: each is visually verified against the 200-DPI page
render before entering gold.json.  Output goes to .w23_cache/gold_candidates/.
"""
import json
from pathlib import Path

import pypdfium2 as pdfium

WT = Path(r"C:/Users/郑曾波/Projects/company-wiki-w23-xiaomi-ocr")
PLAN = WT / "docs" / "plans" / "w23-xiaomi-ocr-2026-10-30"
OUT = WT / ".w23_cache" / "gold_candidates"
OUT.mkdir(parents=True, exist_ok=True)

manifest = json.loads((PLAN / "sample_manifest.json").read_text(encoding="utf-8"))

import sqlite3
ROOT = Path(r"C:/Users/郑曾波/Projects/company-wiki")
DAYU = ROOT.parent / "dayu-agent" / "workspace" / "portfolio"

con = sqlite3.connect(
    f"file:{ROOT.as_posix()}/.source_catalog/catalog.sqlite3?mode=ro", uri=True
)


def phys_for(rel, root_id):
    if root_id == "company_raw":
        return ROOT / "companies" / rel
    if root_id == "dayu_portfolio":
        return DAYU / rel
    raise ValueError(root_id)


seen_docs = {}
for page in manifest["pages"]:
    doc = manifest["documents"][page["doc"]]
    key = page["doc"]
    if key not in seen_docs:
        phys = phys_for(doc["relative_path"], doc["root_id"])
        seen_docs[key] = pdfium.PdfDocument(str(phys))
    pdf = seen_docs[key]
    idx = page["pdf_page_index"]
    txt = pdf[idx].get_textpage().get_text_bounded() or ""
    (OUT / f"{page['page_id']}.txt").write_text(txt, encoding="utf-8")
    print(f"{page['page_id']}: {len(txt)} chars native")

for pdf in seen_docs.values():
    pdf.close()
print("candidates at", OUT)
