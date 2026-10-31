"""W23 render candidate pages for visual selection (view copies only)."""
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


def resolve(sha):
    for r in con.execute(
        "SELECT l.root_id, l.relative_path FROM locations l JOIN sources s ON s.source_id=l.source_id "
        "WHERE s.content_sha256 LIKE ? LIMIT 4",
        (sha + "%",),
    ):
        if r[0] == "company_raw":
            p = ROOT / "companies" / r[1]
        elif r[0] == "dayu_portfolio":
            p = DAYU / r[1]
        else:
            continue
        if p.is_file():
            return p
    return None


PAGES = {
    "BYD": (ROOT / "companies/比亚迪/raw", "e9c2d7fdd088", [12, 21, 22]),
    "ZIJIN": (None, "004f733e709b", [5, 8, 10]),
    "AMEC": (None, "182e2062fed9", [9, 10, 11]),
    "MT": (None, "36eae4d03971", [0, 6, 11]),
    "ANTA": (None, "1297bbbca740", [7, 11, 12]),
    "KSY": (None, "37f0eb13fc97", [2, 5]),
    "BILI": (ROOT / "companies/哔哩哔哩/raw/research/bilibili-4q-2022-conference-call-script.pdf", None, [1, 3]),
    "HRJP": (ROOT / "companies/华锐精密/raw/research/华锐精密：向不特定对象发行可转换公司债券证券募集说明书.PDF", None, [6, 37]),
    "IRWRN": (ROOT / "companies/万润股份/raw/research/万润股份：投资者关系活动记录表20241104.pdf", None, [0, 2]),
}

manifest = {}
for tag, (path, sha, pages) in PAGES.items():
    phys = path if path and path.is_file() else resolve(sha)
    if phys is None:
        print(tag, "UNRESOLVED")
        continue
    pdf = pdfium.PdfDocument(str(phys))
    for pno in pages:
        page = pdf[pno]
        bitmap = page.render(scale=150 / 72)
        img = bitmap.to_pil()
        out = PROBE / f"{tag}_p{pno:03d}.png"
        img.save(out)
        manifest[f"{tag}_p{pno:03d}"] = {"path": str(phys), "page": pno, "png": str(out), "size": img.size}
    pdf.close()
    print(tag, "ok", [str(p) for p in pages])

(PROBE / "render_manifest.json").write_text(
    json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8"
)
