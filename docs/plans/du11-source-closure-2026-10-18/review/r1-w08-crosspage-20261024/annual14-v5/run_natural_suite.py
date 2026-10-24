"""Reproduce the W08 natural regression suite against this checked-out source tree."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET


sys.stdout.reconfigure(encoding="utf-8")
HERE = Path(__file__).resolve().parent
ROOT = next(parent for parent in HERE.parents if (parent / "pyproject.toml").exists())
SCOPES = [
    "tests/unit/document_understanding_selection",
    "tests/unit/document_understanding_structure",
    "tests/unit/document_understanding_root",
    "tests/unit/du11_production/test_native_prose_continuity.py",
    "tests/unit/test_s7_operating_fact_semantics.py",
    "tests/unit/test_shared_reading_cache_precheck.py",
    "tests/unit/test_narrative_selection_architecture.py",
    "tests/unit/test_reading_batch_version.py",
    "tests/unit/du4_operating_states",
]


def source_hashes() -> dict[str, str]:
    files = sorted((ROOT / "src/company_wiki").rglob("*.py"))
    return {
        path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in files
    }


def main() -> None:
    assert all((ROOT / scope).exists() for scope in SCOPES)
    before = source_hashes()
    owned_temp_root = ROOT / ".tmp-w08-v5-natural"
    assert not owned_temp_root.exists(), f"Refusing to reuse test temp root: {owned_temp_root}"
    owned_temp_root.mkdir()
    env = os.environ.copy()
    env.update(
        PYTHONUTF8="1",
        PYTHONDONTWRITEBYTECODE="1",
        PYTHON_DOTENV_DISABLED="1",
        COMPANY_WIKI_REAL_LLM="0",
        PYTHONPATH=str(ROOT / "src") + os.pathsep + str(ROOT / "tests"),
        TEMP=str(owned_temp_root),
        TMP=str(owned_temp_root),
        TMPDIR=str(owned_temp_root),
        CW_BASETEMP_FALLBACK_ROOT=str(owned_temp_root / "pytest-fallback"),
    )
    junit = HERE / "natural.xml"
    args = [
        sys.executable,
        "-m",
        "pytest",
        *SCOPES,
        "-q",
        "--tb=short",
        "-p",
        "no:cacheprovider",
        "--basetemp=" + str(owned_temp_root / "requested-basetemp"),
        "--junitxml=" + str(junit),
    ]
    result = None
    output = ""
    try:
        result = subprocess.run(args, cwd=ROOT, env=env, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, check=False)
        output = result.stdout.decode("utf-8", errors="replace")
        (HERE / "natural.txt").write_text(output, encoding="utf-8")
        print(output[-18000:])
    finally:
        after = source_hashes()
        suite = ET.parse(junit).find("testsuite") if junit.exists() else None
        temp_entries_before_cleanup = sorted(
            path.relative_to(owned_temp_root).as_posix()
            for path in owned_temp_root.rglob("*")
        )
        shutil.rmtree(owned_temp_root)
        receipt = {
            "schema_version": "w08-natural-suite-receipt/1",
            "at_utc": datetime.now(timezone.utc).isoformat(),
            "root": str(ROOT),
            "args": args,
            "exit_code": None if result is None else result.returncode,
            "junit": None if suite is None else suite.attrib,
            "source_before": before,
            "source_after": after,
            "source_stable": before == after,
            "temp_cleanup": {
                "path": str(owned_temp_root),
                "created_for_this_run": True,
                "existed_after": owned_temp_root.exists(),
                "entries_removed": temp_entries_before_cleanup,
            },
            "external_calls": 0,
            "paid_model_calls": 0,
            "original_downloads": 0,
        }
        (HERE / "natural-receipt.json").write_text(
            json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    assert before == after, "Source changed during the natural combined suite"
    assert result is not None and result.returncode == 0, "Natural suite failed"


if __name__ == "__main__":
    main()
