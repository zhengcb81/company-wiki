"""W23 page locating: use the text layer only to FIND business pages, then
render candidates as PNG thumbnails for visual selection. Text is never gold.
"""
import json
import sqlite3
from pathlib import Path

import pypdfium2 as pdfium

ROOT = Path(r"C:/Users/郑曾波/Projects/company-wiki")
DAYU = ROOT.parent / "dayu-agent" / "workspace" / "portfolio"
PROBE = Path(r"C:/Users/郑曾波/Projects/company-wiki-w23-xiaomi-ocr/.w23_cache/render_probe")
PROBE.mkdir(parents=True, exist_ok=True)

con = sqlite3.connect(
    f"file:{ROOT.as_posix()}/.source_catalog/catalog.sqlite3?mode=ro", uri=True
)
con.row_factory = sqlite3.Row


def resolve(sha_prefix):
    rows = con.execute(
        """
        SELECT l.root_id, l.relative_path FROM locations l
        JOIN sources s ON s.source_id = l.source_id
        WHERE s.content_sha256 LIKE ? AND s.mime_type = 'application/pdf'
        LIMIT 4
        """,
        (sha_prefix + "%",),
    ).fetchall()
    for r in rows:
        if r["root_id"] == "company_raw":
            p = ROOT / "companies" / r["relative_path"]
        elif r["root_id"] == "dayu_portfolio":
            p = DAYU / r["relative_path"]
        elif r["root_id"] == "dropbox_stock":
            import os
            p = Path(os.environ["USERPROFILE"]) / "Dropbox" / "Stock" / r["relative_path"]
        else:
            continue
        if p.is_file():
            return p
    return None


DOCS = {
    "BYD_AR2024": "e9c2d7fdd088",
    "ZIJIN_AR2024": "004f733e709b",
    "AMEC_H1_2026": "182e2062fed9",
    "MEITUAN_AR2024": "36eae4d03971",
    "ANTA_AR2025": "1297bbbca740",
    "KSY_Q1_2026": "37f0eb13fc97",
    "BILI_CALL_EN": None,  # by path
    "HRJP_CB": None,
    "IR_WRN_20241104": None,
}
PATHS = {
    "BILI_CALL_EN": ROOT / "companies/哔哩哔哩/raw/research/bilibili-4q-2022-conference-call-script.pdf",
    "HRJP_CB": ROOT / "companies/华锐精密/raw/research/华锐精密：向不特定对象发行可转换公司债券证券募集说明书.PDF",
    "IR_WRN_20241104": ROOT / "companies/万润股份/raw/research/万润股份：投资者关系活动记录表20241104.pdf",
}

KEYWORDS = {
    "zh": ["业务简介", "主要业务", "主营业务", "经营情况讨论", "管理层讨论", "业务概要",
           "核心竞争力", "行业情况", "主要产品", "客户", "产能", "问答", "投资者关系"],
    "en": ["Business", "Overview", "Products", "Customers", "Capacity"],
}

report = {}
for tag, sha in DOCS.items():
    phys = PATHS.get(tag) or (resolve(sha) if sha else None)
    if phys is None or not phys.is_file():
        report[tag] = {"error": "unresolved"}
        continue
    pdf = pdfium.PdfDocument(str(phys))
    n = len(pdf)
    hits = []
    for i in range(min(n, 80)):
        try:
            txt = pdf[i].get_textpage().get_text_bounded() or ""
        except Exception:  # noqa: BLE001
            txt = ""
        flat = txt.replace("\r\n", " ").replace("\n", " ")
        matched = [k for kws in KEYWORDS.values() for k in kws if k in flat]
        if matched:
            hits.append({"page": i, "kw": matched[:4], "head": flat[:60]})
    report[tag] = {"path": str(phys), "pages": n, "hits": hits[:14]}
    pdf.close()

out = PROBE / "locate_report.json"
out.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
for tag, e in report.items():
    if "error" in e:
        print(tag, e)
        continue
    print(f"== {tag} pages={e['pages']}")
    for h in e["hits"][:8]:
        print(f"   p{h['page']} {h['kw']} | {h['head']}")
