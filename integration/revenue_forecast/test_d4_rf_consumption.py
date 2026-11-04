"""ROOT D4-02: run real RF port tests from the RF checkout, without CWP imports."""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys


def test_prepared_narrative_reaches_claim_parameter_formula_and_report(
    tmp_path: Path,
) -> None:
    rf_root = Path(os.environ["RF_CODE_ROOT"]).resolve(strict=True)
    scratch = tmp_path / "rf-d4-tests"
    command = [
        sys.executable,
        "-B",
        "-m",
        "pytest",
        "-p",
        "no:cacheprovider",
        "-q",
        "--basetemp",
        str(scratch),
        "tests/test_d4_narrative_consumption_port.py::test_d4_one_consumption_reads_once_and_reaches_claim_parameter_formula_report",
        "tests/test_d4_narrative_consumption_port.py::test_d4_prepared_source_reaches_adoption_through_replaceable_ports",
    ]
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.upper().endswith(("API_KEY", "API_KEY_FILE"))
        and not key.upper().startswith("GIT_")
        and key.upper() not in {"PYTHONPATH", "CWP_V2_CODE_ROOT", "FILING_FETCH_V2_WIKI_SRC"}
    }
    env.update(
        PYTHONDONTWRITEBYTECODE="1",
        PYTEST_DISABLE_PLUGIN_AUTOLOAD="1",
        PYTHONUTF8="1",
        PYTHON_DOTENV_DISABLED="1",
        COMPANY_WIKI_NETWORK="blocked",
        COMPANY_WIKI_REAL_LLM="0",
    )
    completed = subprocess.run(
        command,
        cwd=rf_root,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=180,
        check=False,
    )
    try:
        assert completed.returncode == 0, completed.stdout + completed.stderr
        assert "2 passed" in completed.stdout, completed.stdout + completed.stderr
    finally:
        if scratch.exists():
            shutil.rmtree(scratch)
    assert not scratch.exists()
