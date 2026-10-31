"""W23 probe round 2: resolve by content SHA prefix."""
import os
import sqlite3
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
    ("KSY_AR2024", "5dcfd59c9ad2"),
]

import pypdfium2 as pdfium

for tag, sha in CANDIDATES:
    rows = con.execute(
        """
        SELECT l.root_id, l.relative_path, s.byte_size, s.content_sha256
        FROM locations l
        JOIN sources s ON s.source_id = l.source_id
        WHERE s.content_sha256 LIKE ? AND s.mime_type = 'application/pdf'
        LIMIT 3
        """,
        (f"{sha}%",),
    ).fetchall()
    if not rows:
        print(f"== {tag}: NOT FOUND ({sha})")
        continue
    r = rows[0]
    if r["root_id"] == "company_raw":
        phys = ROOT / "companies" / r["relative_path"]
    elif r["root_id"] == "dropbox_stock":
        phys = Path(os.environ["USERPROFILE"]) / "Dropbox" / "Stock" / r["relative_path"]
    else:
        phys = ROOT / r["relative_path"]
    ok = phys.is_file()
    line = f"== {tag}: {r['root_id']} exists={ok} size={r['byte_size']} path={r['relative_path'][:70]}"
    if ok:
        try:
            pdf = pdfium.PdfDocument(str(phys))
            n = len(pdf)
            info = []
            for idx in (0, min(3, n - 1)):
                page = pdf[idx]
                w, h = page.get_size()
                txt = page.get_textpage().get_text_bounded() or ""
                info.append(f"p{idx}:{w:.0f}x{h:.0f}pt/tc{len(txt)}")
            line += f" pages={n} " + " ".join(info) + f" sha={r['content_sha256'][:12]}"
            pdf.close()
        except Exception as exc:  # noqa: BLE001
            line += f" PROBE_ERROR {type(exc).__name__}: {exc}"
    print(line)
