"""W23 probe candidate PDFs: resolve location, page count, text-layer presence."""
import sqlite3
import sys
from pathlib import Path

ROOT = Path(r"C:/Users/郑曾波/Projects/company-wiki")

con = sqlite3.connect(
    f"file:{ROOT.as_posix()}/.source_catalog/catalog.sqlite3?mode=ro", uri=True
)
con.row_factory = sqlite3.Row

CANDIDATES = [
    ("BYD_AR2024", "e9c2d7fdd088"),
    ("ZIJIN_AR2024", "004f733e709b"),
    ("AMEC_H1", "182e2062fed9"),
    ("MEITUAN_AR2024", "36eae4d03971"),
    ("ANTA_AR2025", "1297bbbca740"),
    ("KSY_Q1_2026", "37f0eb13fc97"),
    ("BILI_CALL_EN", "bilibili"),
    ("BRK2007", "berkshire2007.pdf"),
    ("HRJP_CB_PROSPECTUS", "华锐精密"),
    ("IR_RECORD", "万润股份：投资者关系活动记录表20241104"),
]

try:
    import pypdfium2 as pdfium
except ImportError:
    print("pypdfium2 MISSING")
    sys.exit(1)

for tag, needle in CANDIDATES:
    rows = con.execute(
        """
        SELECT l.root_id, l.relative_path, s.byte_size, s.content_sha256
        FROM locations l
        JOIN documents d ON d.document_id = l.document_id
        JOIN sources s ON s.source_id = l.source_id
        WHERE l.relative_path LIKE ? AND s.mime_type = 'application/pdf'
        LIMIT 3
        """,
        (f"%{needle}%",),
    ).fetchall()
    if not rows:
        print(f"== {tag}: NOT FOUND ({needle})")
        continue
    r = rows[0]
    # company_raw root path is ROOT/companies
    if r["root_id"] == "company_raw":
        phys = ROOT / "companies" / r["relative_path"]
    elif r["root_id"] == "dropbox_stock":
        import os

        phys = Path(os.environ["USERPROFILE"]) / "Dropbox" / "Stock" / r["relative_path"]
    else:
        phys = ROOT / r["relative_path"]
    ok = phys.is_file()
    line = f"== {tag}: {r['root_id']} exists={ok} size={r['byte_size']}"
    if ok:
        try:
            pdf = pdfium.PdfDocument(str(phys))
            n = len(pdf)
            page = pdf[0]
            w, h = page.get_size()
            # text-layer check on page 0
            tp = page.get_textpage()
            txt = tp.get_text_bounded() or ""
            line += (
                f" pages={n} page0={w:.0f}x{h:.0f}pt text_chars_p0={len(txt)}"
                f" sha={r['content_sha256'][:12]}"
            )
            pdf.close()
        except Exception as exc:  # noqa: BLE001
            line += f" PROBE_ERROR {type(exc).__name__}: {exc}"
    print(line)
