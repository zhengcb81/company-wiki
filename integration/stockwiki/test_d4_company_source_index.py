"""ROOT D4-01: merged StockWiki default entrypoints over an isolated CWP lake."""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "integration/stockwiki/d4_01_company_source_e2e.py"


def test_company_sources_run_company_enrich_and_signals_use_the_virtual_lake(
    tmp_path: Path,
) -> None:
    baseline = tuple(tmp_path.iterdir())
    cwp_root = Path(os.environ["CWP_V2_CODE_ROOT"]).resolve(strict=True)
    stockwiki_root = Path(os.environ["STOCKWIKI_CODE_ROOT"]).resolve(strict=True)
    scratch = tmp_path / "d4-01-lake"
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.upper().endswith(("API_KEY", "API_KEY_FILE"))
        and not key.upper().startswith("GIT_")
    }
    env.update(
        D401_CWP_ROOT=str(cwp_root),
        D401_STOCKWIKI_ROOT=str(stockwiki_root),
        D401_TEMP_ROOT=str(scratch),
        PYTHONDONTWRITEBYTECODE="1",
        PYTHON_DOTENV_DISABLED="1",
        COMPANY_WIKI_NETWORK="blocked",
    )
    completed = subprocess.run(
        [sys.executable, "-B", str(SCRIPT)],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=300,
        check=False,
    )
    try:
        assert completed.returncode == 0, completed.stdout + completed.stderr
        assert "RESULT PASS" in completed.stdout, completed.stdout + completed.stderr
        assert scratch.is_dir()
    finally:
        if scratch.exists():
            shutil.rmtree(scratch)
    assert not scratch.exists()
    assert tuple(tmp_path.iterdir()) == baseline
