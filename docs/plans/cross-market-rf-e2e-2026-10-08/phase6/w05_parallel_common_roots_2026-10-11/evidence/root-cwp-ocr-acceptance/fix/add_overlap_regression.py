"""Reject an unread qualifier overlapping the source ROI even if its center is outside."""
from pathlib import Path

TREE = Path(r"C:\Users\郑曾波\Projects\_harness_worktrees\w05\cwp-ocr-root")
path = TREE / "tests/document_normalization/test_ocr_region_recovery.py"
text = path.read_text(encoding="utf-8")
assert "test_dropped_source_fragment_with_outside_center_stays_unrecovered" not in text
text += '''


def test_dropped_source_fragment_with_outside_center_stays_unrecovered():
    from PIL import Image

    image = strip_png()
    full = result_with([dropped(WIDE)])

    class OverlappingRemainder:
        def transcribe(self, data, *, limits):
            width, height = Image.open(io.BytesIO(data)).size
            scale = width / 290
            clean = OCRLine("Clean part of source", (1., 12*scale, 280*scale, 35*scale), .99)
            # Original crop y origin is 9: this qualifier spans y=11..23,
            # centered above the source ROI y=20..52, but its bytes overlap it.
            remainder = dropped((1., 2*scale, 100*scale, 14*scale), .3, "unread overlapping qualifier")
            return result_with([remainder], (clean,), width=width, height=height)

    got = rr.recover_regions(ocr=OverlappingRemainder(), image_bytes=image, result=full,
        limits=OCRLimits(), budget=rr.RecoveryBudget(), accept_threshold=THRESHOLD)
    assert got.recovered_lines == ()
    assert got.diagnostics.recovery[0].status == "unrecovered"
'''
path.write_text(text, encoding="utf-8")
