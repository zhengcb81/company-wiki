from pathlib import Path

path = Path(r"C:\Users\郑曾波\Projects\_harness_worktrees\w05\cwp-ocr-root\src\company_wiki\document_normalization\ocr_region_recovery.py")
text = path.read_text(encoding="utf-8")
old = '''            center_x = (original[0] + original[2]) / 2
            center_y = (original[1] + original[3]) / 2
            if (region_box[0] <= center_x <= region_box[2]
                    and region_box[1] <= center_y <= region_box[3]):
'''
new = '''            # Any unread fragment intersecting the source ROI prevents a
            # whole-region claim. A wholly external neighbor stays unrelated.
            if box_iou(original, region_box) > 0:
'''
assert text.count(old) == 1
path.write_text(text.replace(old, new), encoding="utf-8")
