from pathlib import Path
import hashlib
import json

tree = Path(r"C:\Users\郑曾波\Projects\_harness_worktrees\w05\cwp-ocr-root")
paths = (
    "src/company_wiki/document_normalization/ocr_region_recovery.py",
    "src/company_wiki/document_normalization/ocr_composition.py",
    "src/company_wiki/document_normalization/local_ocr.py",
    "tests/document_normalization/test_ocr_region_recovery.py",
    "tests/document_normalization/test_ocr_region_composition.py",
)
payload = {
    "schema": "root-w05-ocr-recovery-fix-freeze/1",
    "tree": str(tree),
    "source_sha256": {p: hashlib.sha256((tree/p).read_bytes()).hexdigest() for p in paths},
    "all_owned_files_released_to_root": True,
    "formal_red": "9 FAIL plus 1 overlapping-source-fragment FAIL; original logs preserved",
    "green": "38 PASS / 3.38s",
    "provider_calls": 0,
    "raw_opened": 0,
    "raw_modified": 0,
    "new_fee_usd": 0,
    "committed": False,
    "note": "Composition released earlier for ROOT hard-deadline seam; no further subagent mutations.",
}
target = Path(__file__).parent / "source-freeze.json"
target.write_text(json.dumps(payload, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
print(json.dumps(payload, ensure_ascii=False))
