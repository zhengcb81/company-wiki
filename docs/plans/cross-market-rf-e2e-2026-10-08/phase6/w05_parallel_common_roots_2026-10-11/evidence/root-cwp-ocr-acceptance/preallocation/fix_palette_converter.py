from pathlib import Path

path = Path(r"C:\Users\郑曾波\Projects\_harness_worktrees\w05\cwp-ocr-root\src\company_wiki\document_normalization\ocr_region_recovery.py")
text = path.read_text(encoding="utf-8")
old = '''        if mode == "P":
            converter.palette = image.palette
'''
new = '''        if mode == "P" and image.palette is not None:
            # putpalette updates PIL's core palette; assigning .palette only
            # changes Python metadata and would leave the 1px lookup blank.
            converter.putpalette(image.getpalette())
'''
assert text.count(old) == 1
path.write_text(text.replace(old, new), encoding="utf-8")
