"""R1 candidate probe: page count, per-page script mix, and text-layer size.

Language is measured from the actual page content (CJK vs Latin character
counts), never from the file name.
"""
import json
import os
import sqlite3
import sys
from pathlib import Path

import pypdfium2 as pdfium

ROOT = Path(r"C:/Users/郑曾波/Projects/company-wiki")
DAYU = ROOT.parent / "dayu-agent" / "workspace" / "portfolio"


def resolve(rel, root_id):
    if root_id == "company_raw":
        return ROOT / "companies" / rel
    if root_id == "dayu_portfolio":
        return DAYU / rel
    if root_id == "dropbox_stock":
        return Path(os.environ.get("USERPROFILE", "")) / "Dropbox" / "Stock" / rel
    return None


def script_mix(text: str) -> dict:
    cjk = sum(1 for c in text if "一" <= c <= "鿿")
    latin = sum(1 for c in text if ("a" <= c <= "z") or ("A" <= c <= "Z"))
    total = cjk + latin
    return {"cjk": cjk, "latin": latin,
            "cjk_ratio": round(cjk / total, 3) if total else None,
            "chars": len(text)}


def probe(path: Path, pages: int = 6) -> dict:
    pdf = pdfium.PdfDocument(str(path))
    out = {"pages": len(pdf), "sample": []}
    for i in range(min(pages, len(pdf))):
        text = pdf[i].get_textpage().get_text_bounded() or ""
        entry = {"page": i, **script_mix(text)}
        entry["head"] = " ".join(text.split())[:70]
        out["sample"].append(entry)
    pdf.close()
    return out


if __name__ == "__main__":
    con = sqlite3.connect(
        f"file:{ROOT.as_posix()}/.source_catalog/catalog.sqlite3?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    rows = con.execute("""
        SELECT s.content_sha256 AS sha, s.byte_size AS size, l.relative_path AS rel,
               l.root_id AS root, d.document_kind AS kind
        FROM sources s JOIN locations l ON l.source_id = s.source_id
        JOIN documents d ON d.document_id = l.document_id
        WHERE s.mime_type = 'application/pdf' AND d.source_status = 'active'
        """).fetchall()
    seen = {}
    for r in rows:
        seen.setdefault(r["sha"], r)
    wanted = set(sys.argv[1:])
    results = []
    for sha, r in seen.items():
        if wanted and sha[:12] not in wanted:
            continue
        phys = resolve(r["rel"], r["root"])
        if phys is None or not phys.is_file():
            continue
        try:
            info = probe(phys)
        except Exception as exc:  # noqa: BLE001
            info = {"error": f"{type(exc).__name__}: {exc}"}
        info.update({"sha": sha, "kind": r["kind"], "rel": r["rel"], "root": r["root"]})
        results.append(info)
    print(json.dumps(results, ensure_ascii=False, indent=1))
