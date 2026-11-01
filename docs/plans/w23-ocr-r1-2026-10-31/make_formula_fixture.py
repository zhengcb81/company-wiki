"""R1 synthetic formula-symbol control fixture.

The frozen real sample contains no formula (independently confirmed by the gold
reviewer), so the card's minimal formula-symbol control is met with a declared
synthetic image: a few symbols and one numeric value on plain white.  It is a
control page, never counted as real-document coverage.
"""
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path(r"C:/Users/郑曾波/Projects/company-wiki-w23-xiaomi-ocr-r1/.w23_cache/r1_pages")
OUT.mkdir(parents=True, exist_ok=True)

texts = [
    "E = mc²",
    "ΔG = ΔH − TΔS",
    "f(x) = ax² + bx + c",
    "P/E = 23.7 ×",
]
font = None
for candidate in (
    "C:/Windows/Fonts/segoeui.ttf",
    "C:/Windows/Fonts/arial.ttf",
    "C:/Windows/Fonts/calibri.ttf",
):
    if Path(candidate).is_file():
        font = ImageFont.truetype(candidate, 64)
        break
if font is None:
    font = ImageFont.load_default()

image = Image.new("RGB", (1654, 2339), (255, 255, 255))
draw = ImageDraw.Draw(image)
y = 300
for line in texts:
    draw.text((180, y), line, fill=(20, 20, 20), font=font)
    y += 200
# a small decorative rule to act as a non-text negative control
draw.rectangle([180, 1150, 1470, 1160], fill=(120, 120, 120))

target = OUT / "r1_formula_control.png"
image.save(target)
digest = hashlib.sha256(target.read_bytes()).hexdigest()
record = {
    "page_id": "r1_formula_control",
    "label": "synthetic formula-symbol control (declared, not real-document coverage)",
    "pdf": None,
    "pdf_page_index": None,
    "png": str(target),
    "png_sha256": digest,
    "png_px": list(image.size),
    "market": None,
    "language": "symbols",
    "genre": "synthetic_formula_control",
    "native_text_layer_chars": 0,
    "synthetic_degradation": True,
    "why": "card C: at least one small formula-symbol control from a synthetic fixture, since the frozen real pages contain no formula",
    "expected_symbols": ["=", "²", "Δ", "−", "×", "f(x)", "E", "mc", "TΔS", "23.7"],
}
manifest = {
    "schema_version": "cwp-ocr-r1-control-manifest/1",
    "plan_id": "w23-ocr-r1-2026-10-31",
    "render": {"renderer": "PIL", "dpi": "n/a", "color": "RGB"},
    "pages": [record],
    "note": "control page only; excluded from every real-document denominator",
}
out = Path("docs/plans/w23-ocr-r1-2026-10-31/r1_control_manifest.json")
out.write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps(record, ensure_ascii=False, indent=1))
print("WROTE", out)
