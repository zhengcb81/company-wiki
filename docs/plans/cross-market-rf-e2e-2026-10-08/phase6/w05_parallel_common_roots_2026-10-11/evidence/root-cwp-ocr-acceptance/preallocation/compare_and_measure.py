"""Compare frozen legal rasters and quantify one small ROI source scan."""
from pathlib import Path
import hashlib
import json
import sys
import time

tree = Path(r"C:\Users\郑曾波\Projects\_harness_worktrees\w05\cwp-ocr-root")
sys.dont_write_bytecode = True
sys.path.insert(0, str(tree / "src"))
sys.path.insert(0, str(tree / "tests/document_normalization"))
from company_wiki.document_normalization import ocr_region_recovery as rr
from test_ocr_region_recovery import strip_png
from PIL import Image
import io

folder = Path(__file__).parent
before = json.loads((folder/"before.json").read_text(encoding="utf-8"))
after = json.loads((folder/"after.json").read_text(encoding="utf-8"))
assert before == after, [(k, before[k], after[k]) for k in before if before[k] != after[k]]

source = Image.open(io.BytesIO(strip_png(width=3200, height=200))).convert("RGB")
window = (10, 15, 3190, 185)
width, height = window[2]-window[0], window[3]-window[1]

def original_reference():
    gray = source.crop(window).convert("L")
    pixels = gray.load()
    return [sum(pixels[x,y] < rr.DARK_THRESHOLD for y in range(0,height,2)) for x in range(width)]

durations = {"original_reference": [], "read_only_source_scan": []}
for _ in range(2):
    start = time.perf_counter()
    old = original_reference()
    durations["original_reference"].append(time.perf_counter()-start)
    start = time.perf_counter()
    new = rr._column_dark_counts(source, window=window)
    durations["read_only_source_scan"].append(time.perf_counter()-start)
    assert new == old

payload = {
    "schema": "root-w05-ocr-preallocation-acceptance/1",
    "legal_before_after_equal": True,
    "cases": len(before),
    "legal_png_sha_count": sum("sha256" in v for v in before.values()),
    "unchanged_existing_error_count": sum("error" in v for v in before.values()),
    "roi_size": [width,height],
    "sampled_pixels_per_scan": width*((height+1)//2),
    "scan_seconds": durations,
    "source_sha256": {p: hashlib.sha256((tree/p).read_bytes()).hexdigest() for p in (
        "src/company_wiki/document_normalization/ocr_region_recovery.py",
        "tests/document_normalization/test_ocr_region_recovery.py")},
    "provider_calls": 0, "raw_opened": 0, "fee_usd": 0,
}
(folder/"freeze.json").write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(payload,ensure_ascii=False))
