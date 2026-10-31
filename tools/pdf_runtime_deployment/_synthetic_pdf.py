"""Shared synthetic-PDF fixture for real-entry deployment verification.

One deterministic two-page wrapped-prose document. Each page carries one
genuine fracture (line 1 ends mid-sentence without terminal punctuation), so
the native triage demands enhancement and the real SDK proposals must pass the
existing alignment. The CJK text is drawn with an embedded system font that
carries a proper ToUnicode CMap: pymupdf's built-in ``china-s`` font has none
and docling's pdfminer backend then extracts mojibake (observed honestly in
this card's first E2E: SDK items were garbage, alignment rejected them all).
A fixture font without ToUnicode would mis-audit the deployment, not the
runtime.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import sys

_FONT_CANDIDATES = ("C:/Windows/Fonts/simhei.ttf", "C:/Windows/Fonts/simsun.ttc",
                    "C:/Windows/Fonts/msyh.ttc", "C:/Windows/Fonts/Deng.ttf")


def find_cjk_font() -> str:
    for candidate in _FONT_CANDIDATES:
        if Path(candidate).is_file():
            return candidate
    raise RuntimeError("no CJK-capable system font found for the synthetic fixture; "
                       f"looked in: {', '.join(_FONT_CANDIDATES)}")


def build_two_page_wrapped_prose_pdf(path: Path) -> tuple[bytes, str]:
    import pymupdf as fitz

    fontfile = find_cjk_font()
    document = fitz.open()
    for index in range(2):
        page = document.new_page(width=600, height=800)
        page.insert_font(fontname="cjk", fontfile=fontfile)
        page.insert_text((60, 100),
                         f"报告期内，公司第{index + 1}季度的新型自动化产线已进入安装调试阶段，并在期末前完成联动试车并获得",
                         fontsize=9, fontname="cjk")
        page.insert_text((83, 114), "客户的最终验收确认，但尚未转入大规模量产。",
                         fontsize=9, fontname="cjk")
    data = document.tobytes()
    document.close()
    path.write_bytes(data)
    return data, sha256(data).hexdigest()


if __name__ == "__main__":
    data, digest = build_two_page_wrapped_prose_pdf(Path(sys.argv[1] if len(sys.argv) > 1 else "synthetic.pdf"))
    print(sha256(data).hexdigest(), len(data))
