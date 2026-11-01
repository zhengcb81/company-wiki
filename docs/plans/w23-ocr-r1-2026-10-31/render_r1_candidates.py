"""R1 (HISTORICAL): initial candidate renderer. The frozen renders are what the gold review used; this script records how they were produced. Superseded by render_pages on r1_sample_manifest.json which enforces the recorded SHAs.

Page selection is by measured content, not file name.  The rendered PNGs and
their SHA-256 form the frozen input the independent gold reviewer checks.
"""
import hashlib
import json
import os
from pathlib import Path

import pypdfium2 as pdfium
from PIL import Image

ROOT = Path(r"C:/Users/郑曾波/Projects/company-wiki")
DAYU = ROOT.parent / "dayu-agent" / "workspace" / "portfolio"
OUT = Path(r"C:/Users/郑曾波/Projects/company-wiki-w23-xiaomi-ocr-r1/.w23_cache/r1_pages")
OUT.mkdir(parents=True, exist_ok=True)

CANDIDATES = [
    {
        "page_id": "r1_amec_ar2025_p029",
        "label": "中微公司 2025 年年度报告",
        "phys": ROOT / "companies/中微公司/raw/financial_reports/中微公司：2025年年度报告.pdf",
        "page": 29,
        "market": "CN", "language": "zh-CN", "genre": "annual_report",
        "sha_prefix": "d64c410832f2",
        "why": "行业情况+产能+客户句群，简中业务描述与数字",
    },
    {
        "page_id": "r1_wuxi_ar2022_p010",
        "label": "药明康德 2022 年年度报告",
        "phys": ROOT / "companies/药明康德/raw/financial_reports/药明康德：2022年年度报告.pdf",
        "page": 10,
        "market": "CN", "language": "zh-CN", "genre": "annual_report",
        "sha_prefix": "f7d5c0e5",  # corrected: 2022 report, not the 2020 one
        "why": "管理层讨论与分析开头，客户数与外包比例数字",
    },
    {
        "page_id": "r1_ksy_fy2025_results_p003",
        "label": "金山雲 截至二零二五年十二月三十一日止財年未經審計財務業績",
        "phys": ROOT / "companies/金山雲/raw/financial_reports/quarterly/2026-03-25_hkexnews_12067362_內幕消息 截至二零二五年十二月三十一日止三個月及財年的未經審計財務業績.pdf",
        "page": 3,
        "market": "HK", "language": "zh", "genre": "annual_results_announcement",
        "sha_prefix": "9f35944bcca5",
        "why": "繁中年度业绩正文，第四季度收入与同比数字密集",
    },
    {
        "page_id": "r1_ksy_fy2025_income_p012",
        "label": "金山雲 截至二零二五年十二月三十一日止財年未經審計財務業績(綜合虧損表)",
        "phys": ROOT / "companies/金山雲/raw/financial_reports/quarterly/2026-03-25_hkexnews_12067362_內幕消息 截至二零二五年十二月三十一日止三個月及財年的未經審計財務業績.pdf",
        "page": 12,
        "market": "HK", "language": "zh", "genre": "annual_results_announcement",
        "sha_prefix": "9f35944bcca5",
        "why": "真实业务表格(未經審計簡明合併綜合虧損表)，多栏多行读序与千分位数字",
    },
    {
        "page_id": "r1_biren_ar2025_p030",
        "label": "壁仞科技 2025 年度報告",
        "phys": ROOT / "companies/壁仞科技/raw/financial_reports/annual/2026-04-22_hkexnews_12114765_2025年度報告.pdf",
        "page": 30,
        "market": "HK", "language": "zh", "genre": "annual_report",
        "sha_prefix": "7de30b0fb295",
        "why": "不同原件的繁中年报业务页",
    },
    {
        "page_id": "r1_brk2007_p001",
        "label": "Berkshire Hathaway 2007 Annual Report",
        "phys": Path(os.environ.get("USERPROFILE", "")) / "Dropbox/Stock/berkshire2007.pdf",
        "page": 1,
        "market": "US", "language": "en", "genre": "annual_report",
        "sha_prefix": "a914b0ad67df",
        "why": "英文年报 Business Activities 段，多分部业务描述",
    },
    {
        "page_id": "r1_brk2007_p005",
        "label": "Berkshire Hathaway 2007 Annual Report",
        "phys": Path(os.environ.get("USERPROFILE", "")) / "Dropbox/Stock/berkshire2007.pdf",
        "page": 5,
        "market": "US", "language": "en", "genre": "annual_report",
        "sha_prefix": "a914b0ad67df",
        "why": "英文致股东信，管理层与员工数字叙述",
    },
]

records = []
for cand in CANDIDATES:
    phys = cand["phys"]
    if not phys.is_file():
        print("MISSING", cand["page_id"], phys)
        continue
    pdf = pdfium.PdfDocument(str(phys))
    image = pdf[cand["page"]].render(scale=200 / 72).to_pil().convert("RGB")
    target = OUT / f"{cand['page_id']}.png"
    image.save(target)
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    text = pdf[cand["page"]].get_textpage().get_text_bounded() or ""
    pdf.close()
    records.append({
        "page_id": cand["page_id"], "label": cand["label"],
        "pdf": str(phys), "pdf_sha_prefix": cand["sha_prefix"],
        "pdf_page_index": cand["page"], "why": cand["why"],
        "market": cand["market"], "language": cand["language"], "genre": cand["genre"],
        "png": str(target), "png_sha256": digest, "png_px": list(image.size),
        "native_text_layer_chars": len(text),
    })
    print(cand["page_id"], "rendered", image.size, digest[:12], "text_chars", len(text))

manifest = {
    "schema_version": "cwp-ocr-r1-sample-manifest/1",
    "plan_id": "w23-ocr-r1-2026-10-31",
    "render": {"renderer": "pypdfium2", "dpi": 200, "color": "RGB"},
    "pages": records,
    "excluded_from_old_sample": "seven pages come from five documents not used by the 2026-10-30 experiment (amec AR2025, wuxi AR2022, ksy FY2025 results, biren AR2025, berkshire2007)",
}
out = Path("docs/plans/w23-ocr-r1-2026-10-31/r1_sample_manifest.json")
out.write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
print("WROTE", out)
