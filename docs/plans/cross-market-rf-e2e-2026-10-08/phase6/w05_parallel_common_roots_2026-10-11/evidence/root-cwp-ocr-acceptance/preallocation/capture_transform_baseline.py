"""Small deterministic rasters; no real OCR or original document access."""
from pathlib import Path
import hashlib
import json
import sys

tree = Path(r"C:\Users\郑曾波\Projects\_harness_worktrees\w05\cwp-ocr-root")
sys.dont_write_bytecode = True
sys.path.insert(0, str(tree / "src"))
sys.path.insert(0, str(tree / "tests/document_normalization"))
from company_wiki.document_normalization import ocr_region_recovery as rr
from test_ocr_region_recovery import strip_png
from PIL import Image
import io

out = {}
for mode in ("RGB", "L", "RGBA", "P", "CMYK"):
    image = Image.open(io.BytesIO(strip_png())).convert(mode)
    for name in ("build_margin_crop", "build_split_stack", "build_upscale"):
        try:
            png, transform = getattr(rr, name)(image, (10., 28., 262., 48.))
            out[f"{mode}:{name}"] = {"sha256": hashlib.sha256(png).hexdigest(), "transform": transform}
        except OSError as exc:
            # Existing CMYK margin/upscale cannot encode PNG; retain this
            # limitation rather than pretending it was valid RGB behavior.
            out[f"{mode}:{name}"] = {"error": type(exc).__name__, "detail": str(exc)}
target = Path(__file__).parent / sys.argv[1]
target.write_text(json.dumps(out, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
print(f"Recorded {len(out)} deterministic mode/transform cases to {target}.")
