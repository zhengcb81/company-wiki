"""W23 freeze the comparison sample: canonical 200-DPI page renders + manifest.

Run BEFORE any engine output is generated or inspected.  The manifest records
catalog identity (document_id/source_id/sha256/bytes), page numbers, selection
reasons, render identity, and the SHA-256 of every rendered page PNG.  Page
PNGs live only under .w23_cache (never committed; deleted at cleanup); the
committed manifest plus tools/ocr_comparison/render_pages.py reproduce them.
"""
import hashlib
import json
import sqlite3
from pathlib import Path

import pypdfium2 as pdfium
from PIL import Image

ROOT = Path(r"C:/Users/郑曾波/Projects/company-wiki")
DAYU = ROOT.parent / "dayu-agent" / "workspace" / "portfolio"
WT = Path(r"C:/Users/郑曾波/Projects/company-wiki-w23-xiaomi-ocr")
PAGES_DIR = WT / ".w23_cache" / "frozen_pages"
PAGES_DIR.mkdir(parents=True, exist_ok=True)
PLAN = WT / "docs" / "plans" / "w23-xiaomi-ocr-2026-10-30"

con = sqlite3.connect(
    f"file:{ROOT.as_posix()}/.source_catalog/catalog.sqlite3?mode=ro", uri=True
)
con.row_factory = sqlite3.Row


def catalog_facts(sha_prefix):
    rows = con.execute(
        """
        SELECT d.document_id, s.source_id, s.content_sha256, s.byte_size,
               l.root_id, l.relative_path, d.document_kind, d.published_date
        FROM locations l
        JOIN sources s ON s.source_id = l.source_id
        JOIN documents d ON d.document_id = l.document_id
        WHERE s.content_sha256 = ? AND s.mime_type = 'application/pdf'
        """,
        (sha_prefix,),
    ).fetchall()
    facts = None
    phys = None
    for r in rows:
        if r["root_id"] == "company_raw":
            p = ROOT / "companies" / r["relative_path"]
        elif r["root_id"] == "dayu_portfolio":
            p = DAYU / r["relative_path"]
        else:
            continue
        if p.is_file():
            facts = dict(r)
            phys = p
            break
    return facts, phys


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


DOCS = {
    "byd_ar_2024": {
        "sha": "e9c2d7fdd088e151ccb6c8ad3d95587b2b014b10f2c9731508d23ce07fde4de3",
        "label": "比亚迪2024年年度报告",
        "market": "CN", "language": "zh-CN", "genre": "annual_report",
        "pages": [
            {"page": 21, "role": "eval",
             "reason": "简中业务描述(消费电子/客户)+整车产销数字表开头"},
            {"page": 22, "role": "holdout",
             "reason": "分车型产销多行数字表+多个勾选行(适用/不适用)"},
        ],
    },
    "amec_h1_2026": {
        "sha": "182e2062fed950cd32310099cdf47f392c791440ce251f5e3bab7137dbc932fe",
        "label": "中微公司2026年半年度报告",
        "market": "CN", "language": "zh-CN", "genre": "semi_annual_report",
        "pages": [
            {"page": 9, "role": "eval",
             "reason": "业务描述+内嵌营销图(图内艺术字,编造负对照)"},
            {"page": 11, "role": "eval",
             "reason": "采购/生产/营销模式跨段条件+勾选行"},
        ],
    },
    "meituan_ar_2024": {
        "sha": "36eae4d0397187bef187286e394b7d85421eac75f7380d1a95de9f1bfa25e70a",
        "label": "美團2024年年度報告(繁中)",
        "market": "HK", "language": "zh", "genre": "annual_report",
        "pages": [
            {"page": 0, "role": "holdout",
             "reason": "纯图像封面:繁中文字烧录在图内,大量装饰图形(编造负对照)"},
            {"page": 11, "role": "eval",
             "reason": "主席報告繁中密集正文+数字(人民幣10億元/7個試點省市)"},
        ],
    },
    "ksy_q1_2026": {
        "sha": "37f0eb13fc9748d6f2f56e76e9a586bcee7cc9482dd77cdceb7a37fc0890ba2f",
        "label": "金山雲2026年第一季度未經審計財務業績公告(繁中)",
        "market": "HK", "language": "zh", "genre": "quarterly_report",
        "pages": [
            {"page": 2, "role": "eval",
             "reason": "繁中数字密集业绩页(2,703.7百萬/37.2%/匯率6.8980)"},
            {"page": 2, "role": "eval_degraded",
             "reason": "同页synthetic_degradation:低清+倾斜,非真实扫描",
             "degradation": {"scale": 0.55, "rotate_deg": 1.3, "resample": "lanczos",
                              "note": "synthetic_degradation,不代表真实扫描覆盖"}},
        ],
    },
    "ir_wanrun_20241104": {
        "sha": "6abdef50aecf03f85e5c5b10299abc4c6442c4d8f1ffe356ba72a421b64f97fc",
        "label": "万润股份投资者关系活动记录表20241104",
        "market": "CN", "language": "zh-CN", "genre": "investor_relations",
        "pages": [
            {"page": 0, "role": "eval",
             "reason": "IR问答:勾选框+活动信息表+问答跨段"},
            {"page": 2, "role": "holdout",
             "reason": "IR问答后续:问7/答与新能源材料进展"},
        ],
    },
    "hrjp_cb_prospectus": {
        "sha": "c6ed566631e123f159abf2697c157f1868f8e994ccf8e3352132046a6c5ca0a1",
        "label": "华锐精密向不特定对象发行可转换公司债券募集说明书",
        "market": "CN", "language": "zh-CN", "genre": "prospectus_convertible_bond",
        "pages": [
            {"page": 6, "role": "eval",
             "reason": "竞争对手/原材料供应条件句(如果...将...)+产能数字(6,300万片/50万件/140万支)"},
            {"page": 37, "role": "holdout",
             "reason": "核心竞争力/行业对比段落"},
        ],
    },
    "bili_call_4q22_en": {
        "sha": "55d3581c9b6e6b4be5793c80d65894a6d998194ba9f5027493d167f84e48d168",
        "label": "Bilibili 4Q2022 earnings call script (English, US-listed)",
        "market": "US", "language": "en", "genre": "investor_call_transcript",
        "pages": [
            {"page": 1, "role": "eval",
             "reason": "English business remarks with dense numerals (93 million DAUs, RMB 21.9 billion)"},
            {"page": 3, "role": "holdout",
             "reason": "English VAS/advertising segment with dense numerals + inline Chinese title"},
        ],
    },
}

RENDER = {
    "renderer": "pypdfium2",
    "dpi": 200,
    "draw_scale": 200 / 72,
    "color": "RGB",
    "rotation": "none",
    "format": "png",
}

pages_out = []
for doc_id, spec in DOCS.items():
    facts, phys = catalog_facts(spec["sha"])
    assert phys is not None, doc_id
    pdf = pdfium.PdfDocument(str(phys))
    for pspec in spec["pages"]:
        page = pdf[pspec["page"]]
        img = page.render(scale=RENDER["draw_scale"]).to_pil().convert("RGB")
        if pspec["role"] == "eval_degraded":
            deg = pspec["degradation"]
            w, h = img.size
            img = img.resize((round(w * deg["scale"]), round(h * deg["scale"])), Image.Resampling.LANCZOS)
            img = img.rotate(deg["rotate_deg"], resample=Image.Resampling.BICUBIC,
                             expand=True, fillcolor=(255, 255, 255))
        pid = f"{doc_id}_p{pspec['page']:03d}"
        if pspec["role"] == "eval_degraded":
            pid += "_synthetic_degraded"
        png = PAGES_DIR / f"{pid}.png"
        img.save(png)
        pages_out.append({
            "page_id": pid,
            "doc": doc_id,
            "pdf_page_index": pspec["page"],
            "role": pspec["role"],
            "reason": pspec["reason"],
            "degradation": pspec.get("degradation"),
            "png_sha256": sha256_file(png),
            "png_px": list(img.size),
            "png_bytes": png.stat().st_size,
        })
    doc_entry = {
        "label": spec["label"],
        "market": spec["market"],
        "language": spec["language"],
        "genre": spec["genre"],
        "document_id": facts["document_id"],
        "source_id": facts["source_id"],
        "content_sha256": facts["content_sha256"],
        "byte_size": facts["byte_size"],
        "root_id": facts["root_id"],
        "relative_path": facts["relative_path"],
        "published_date": facts["published_date"],
    }
    DOCS[doc_id]["catalog"] = doc_entry
    pdf.close()
    print(doc_id, "ok pages rendered")

manifest = {
    "schema_version": "cwp-ocr-sample-manifest/1",
    "plan_id": "w23-xiaomi-ocr-2026-10-30",
    "frozen_at_note": "frozen before any engine output was generated or inspected",
    "render": RENDER,
    "pypdfium2_version": str(__import__("pypdfium2.version", fromlist=["PYPDFIUM_INFO"]).PYPDFIUM_INFO),
    "documents": {k: v["catalog"] for k, v in DOCS.items()},
    "pages": pages_out,
    "counts": {
        "documents": len(DOCS),
        "pages": len(pages_out),
        "eval": sum(1 for p in pages_out if p["role"] == "eval"),
        "holdout": sum(1 for p in pages_out if p["role"] == "holdout"),
        "synthetic_degradation": sum(1 for p in pages_out if p["role"] == "eval_degraded"),
    },
    "notes": [
        "真实扫描件在目录内缺失;ksy_q1_2026_p002_synthetic_degraded 为同页人工退化,标注 synthetic_degradation,不计真实扫描覆盖。",
        "US 市场年报在目录中为 text/html(NVIDIA/Apple 10-K),不纳入页图OCR样本;英文页由US上市电话会脚本PDF覆盖。",
    ],
}
out = PLAN / "sample_manifest.json"
out.write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
print("WROTE", out)
print("counts:", manifest["counts"])
