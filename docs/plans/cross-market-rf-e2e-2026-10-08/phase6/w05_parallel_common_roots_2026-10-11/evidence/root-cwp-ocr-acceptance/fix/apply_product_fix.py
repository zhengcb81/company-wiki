"""One-shot bounded W05 ROOT fix; exact replacement guards prevent clobbering."""
from pathlib import Path

TREE = Path(r"C:\Users\郑曾波\Projects\_harness_worktrees\w05\cwp-ocr-root")
rec = TREE / "src/company_wiki/document_normalization/ocr_region_recovery.py"
comp = TREE / "src/company_wiki/document_normalization/ocr_composition.py"
local = TREE / "src/company_wiki/document_normalization/local_ocr.py"

def swap(text, old, new):
    assert text.count(old) == 1, old[:100]
    return text.replace(old, new)

text = rec.read_text(encoding="utf-8")
text = swap(text, '        self.total_roi_pixels = 0\n', '''        self.total_roi_pixels = 0
        self.total_pixels = 0

    def reserve_pixels(self, pixels: int, *, limits, roi: bool = False):
        """Check and charge all source/ROI pixels before backend invocation.

        Reservations remain charged after a failed backend call because the
        attempted inference still consumed resources. One composer shares this
        accumulator across all unique source media and recovery attempts.
        """
        if type(pixels) is not int or pixels <= 0:
            raise ValueError("pixels must be a positive integer")
        limits.check_deadline()
        limits.require_within("max_image_pixels", pixels)
        limits.require_within("max_total_pixels", self.total_pixels + pixels)
        self.total_pixels += pixels
        if roi:
            self.total_roi_pixels += pixels
''')
text = swap(text, '            "roi_pixels": self.total_roi_pixels,\n', '            "roi_pixels": self.total_roi_pixels,\n            "total_pixels": self.total_pixels,\n')
text = swap(text, '            return (height - y1, x0, height - y0, x1)\n', '            return (width - y1, x0, width - y0, x1)\n')
text = swap(text, '            return (y0, width - x1, y1, width - x0)\n', '            return (y0, height - x1, y1, height - x0)\n')
text = swap(text, '''        # Chunk rows are stacked top-to-bottom separated by gap rows; map the
        # box into whichever chunk's row range contains its vertical center,
        # then translate by that chunk's crop-offset delta.
        center_y = (y0 + y1) / 2
''', '''        # A box spanning chunks or padding does not represent one contiguous
        # source rectangle. Its entire extent must lie inside a real chunk.
''')
text = swap(text, '''                else float("inf")
            )
            if sy0 <= center_y < sy1:
''', '''                else transform["size"][1]
            )
            if (sx0 <= x0 and x1 <= sx0 + _cx1 - _cx0
                    and sy0 <= y0 and y1 <= sy1):
''')
text = swap(text, '''            else float("inf")
        )
        rows.append((sy0, sy1, cx0, cx1))
''', '''            else transform["size"][1]
        )
        rows.append((sy0, sy1, cx0, cx1))
''')
text = swap(text, '''    candidates = _region_candidates(crop_result, transform, region_box)
''', '''    # LocalOCRAdapter excludes filtered text from lines. A clean surviving
    # fragment therefore proves no whole-region recovery if a dropped source
    # fragment remains. Margin-neighbor text outside this region is unrelated.
    diagnostics = crop_result.region_diagnostics
    if diagnostics is not None:
        for dropped in diagnostics.dropped:
            if dropped.reason != "low_text_score" or not dropped.text.strip():
                continue
            original = map_box(transform, dropped.box)
            if original is None:
                return None, "unmappable_dropped_text"
            center_x = (original[0] + original[2]) / 2
            center_y = (original[1] + original[3]) / 2
            if (region_box[0] <= center_x <= region_box[2]
                    and region_box[1] <= center_y <= region_box[3]):
                return None, "in_region_dropped_text"
    if any(map_box(transform, line.box) is None for line in crop_result.lines):
        return None, "unmappable_region_text"
    candidates = _region_candidates(crop_result, transform, region_box)
''')
text = swap(text, '''            limits.require_within("max_image_pixels", width * height)
            budget.total_roi_pixels += width * height
''', '''            budget.reserve_pixels(width * height, limits=limits, roi=True)
''')
text = swap(text, '''            observed = tuple(
                (line.text, line.confidence) for line in crop_result.lines
            )
''', '''            observed = tuple(
                (line.text, line.confidence) for line in crop_result.lines
            ) + tuple(
                (region.text, region.confidence)
                for region in (() if crop_result.region_diagnostics is None
                               else crop_result.region_diagnostics.dropped)
            )
''')
rec.write_text(text, encoding="utf-8")

text = comp.read_text(encoding="utf-8")
text = swap(text, '    pixels = 0\n', '')
text = swap(text, '''                pixels += width * height
                ocr_limits.require_within("max_total_pixels", pixels)
''', '''                recovery_budget.reserve_pixels(width * height, limits=ocr_limits)
''')
text = swap(text, '''                    pixels += outcome.roi_pixels
                    ocr_limits.require_within("max_total_pixels", pixels)
''', '')
text = swap(text, '                "total_decoded_pixels": pixels,\n', '                "total_decoded_pixels": recovery_budget.total_pixels,\n')
comp.write_text(text, encoding="utf-8")

text = local.read_text(encoding="utf-8")
text = swap(text, '''            "region_recovery": OCR_REGION_RECOVERY_SCHEMA,
''', '''            "region_recovery": OCR_REGION_RECOVERY_SCHEMA,
            "region_recovery_algorithm": "bounded-source-roi/2",
''')
local.write_text(text, encoding="utf-8")

test = TREE / "tests/document_normalization/test_ocr_region_recovery.py"
text = test.read_text(encoding="utf-8")
text = swap(text, '''    # 90-degree rotation inside a 40x20 canvas maps (x,y)->(H-1-y, x)
''', '''    # Inverse PIL CCW rotation uses the pre-rotation width (40), not height.
''')
text = swap(text, 'pytest.approx((16.0, 0.0, 20.0, 10.0))', 'pytest.approx((36.0, 0.0, 40.0, 10.0))')
test.write_text(text, encoding="utf-8")
print("Applied shared pre-inference reservation, complete-region checks and source geometry fix.")
