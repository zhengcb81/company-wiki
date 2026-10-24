"""Run the bounded W08 natural unit package against this checkout."""

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
import uuid


ROOT = Path(__file__).resolve().parents[6]
OUT = Path(__file__).resolve().parent
SCOPES = (
    "tests/unit/document_understanding_selection",
    "tests/unit/document_understanding_structure",
    "tests/unit/document_understanding_root",
    "tests/unit/du11_production/test_native_prose_continuity.py",
    "tests/unit/test_s7_operating_fact_semantics.py",
    "tests/unit/test_shared_reading_cache_precheck.py",
    "tests/unit/test_narrative_selection_architecture.py",
    "tests/unit/test_reading_batch_version.py",
    "tests/unit/du4_operating_states",
)


def source_hashes() -> dict[str, str]:
    return {
        path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted((ROOT / "src/company_wiki").rglob("*.py"))
    }


def main() -> None:
    assert all((ROOT / scope).exists() for scope in SCOPES)
    before = source_hashes()
    env = os.environ.copy()
    env.update(
        PYTHONUTF8="1",
        PYTHONDONTWRITEBYTECODE="1",
        PYTHON_DOTENV_DISABLED="1",
        COMPANY_WIKI_REAL_LLM="0",
        COMPANY_WIKI_NETWORK="blocked",
        PYTHONPATH=os.pathsep.join((str(ROOT / "src"), str(ROOT / "tests"))),
    )
    for name in tuple(env):
        if name.endswith("_API_KEY"):
            env.pop(name, None)
    temp_root = ROOT / (".t" + uuid.uuid4().hex[:8])
    assert not temp_root.exists()
    temp_root.mkdir()
    scratch = temp_root / "b"
    env.update(TEMP=str(temp_root), TMP=str(temp_root), TMPDIR=str(temp_root))
    junit = OUT / "natural.xml"
    args = [
        sys.executable,
        "-m",
        "pytest",
        *SCOPES,
        "-q",
        "--tb=short",
        "-p",
        "no:cacheprovider",
        "--basetemp=" + str(scratch),
        "--junitxml=" + str(junit),
    ]
    result: subprocess.CompletedProcess[bytes] | None = None
    temp_root_existed = False
    cleanup_error = None
    try:
        result = subprocess.run(args, cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        (OUT / "natural.txt").write_bytes(result.stdout)
    finally:
        after = source_hashes()
        temp_root_existed = temp_root.exists()
        try:
            assert scratch.parent == temp_root and temp_root.parent == ROOT
            if temp_root.exists():
                shutil.rmtree(temp_root)
        except OSError as exc:
            cleanup_error = f"{type(exc).__name__}: {exc}"
        stats = ET.parse(junit).find("testsuite").attrib if junit.exists() else None
        receipt = {
            "schema_version": "w08-annual14-v3-natural-suite/1",
            "at_utc": datetime.now(timezone.utc).isoformat(),
            "repo": str(ROOT),
            "args": args,
            "python": sys.version,
            "exit_code": None if result is None else result.returncode,
            "junit": stats,
            "source_before": before,
            "source_after": after,
            "source_stable": before == after,
            "temp_cleanup": {
                "path": str(temp_root),
                "created_for_this_run": True,
                "existed_after": temp_root.exists(),
                "existed_before_cleanup": temp_root_existed,
                "error": cleanup_error,
            },
            "external_calls": 0,
            "paid_model_calls": 0,
            "original_downloads": 0,
        }
        (OUT / "natural-receipt.json").write_text(
            json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    assert before == after, "Source changed during the natural W08 unit package"
    assert cleanup_error is None, cleanup_error
    raise SystemExit(result.returncode if result is not None else 1)


if __name__ == "__main__":
    main()
