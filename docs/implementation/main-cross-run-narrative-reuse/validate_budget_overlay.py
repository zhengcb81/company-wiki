"""Integrate MAIN's one authorized budget module, always restoring owned bytes."""

from __future__ import annotations
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
PACKAGE = Path(__file__).resolve().parent
BUDGET_PATH = "src/company_wiki/automation/narrative_run_store.py"
SOURCE_COMMIT = "ce116dddb07184d99fe8fa9661171d2bc4aa88cc"


def main():
    target = ROOT / BUDGET_PATH
    original = target.read_bytes()
    overlay = subprocess.check_output(
        ["git", "show", f"{SOURCE_COMMIT}:{BUDGET_PATH}"], cwd=ROOT
    )
    receipt = {
        "source_commit": SOURCE_COMMIT,
        "path": BUDGET_PATH,
        "old_sha256": hashlib.sha256(original).hexdigest(),
        "overlay_sha256": hashlib.sha256(overlay).hexdigest(),
        "temporary_authorization": "MAIN explicitly authorized this one-budget-module integration overlay; no overlay commit",
        "supplier_requests": 0,
    }
    try:
        target.write_bytes(overlay)
        result = subprocess.run(
            [
                sys.executable,
                "-X",
                "utf8",
                "-B",
                str(PACKAGE / "validate.py"),
                "GREEN-integrated-kill-recovery-final",
                "-m",
                "pytest",
                "tests/integration/test_narrative_batch_recovery_e2e.py",
                "-q",
            ],
            cwd=ROOT,
        )
        receipt["exit_code"] = result.returncode
    finally:
        target.write_bytes(original)
        receipt["restored_sha256"] = hashlib.sha256(target.read_bytes()).hexdigest()
        assert receipt["restored_sha256"] == receipt["old_sha256"]
        (PACKAGE / "budget-overlay-receipt.json").write_text(
            json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    print(json.dumps(receipt, ensure_ascii=False))
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
