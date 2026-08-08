"""WU-1.1: unique test symbol AST gate contract tests.

``tools/check_unique_test_symbols.py`` must exit 0 when every test file
has unique ``test_*`` names per scope, and exit 1 when a later definition
would silently override an earlier one (F-030/F-031 lesson).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory


ROOT = Path(__file__).resolve().parents[2]
GATE = ROOT / "tools" / "check_unique_test_symbols.py"


def _run_gate(paths: list[Path]) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(GATE), *(str(p) for p in paths)],
        capture_output=True,
        text=True,
        encoding="utf-8",  # child prints UTF-8; Windows GBK locale would break text=True
        timeout=60,
    )


def test_duplicate_test_definition_fails() -> None:
    with TemporaryDirectory() as td:
        path = Path(td) / "test_dup.py"
        path.write_text(
            "def test_a():\n    assert True\n\n\ndef test_a():\n    assert False\n",
            encoding="utf-8",
        )
        proc = _run_gate([path])
        assert proc.returncode == 1, proc.stdout
        assert "DUPLICATE" in proc.stdout


def test_unique_definitions_pass() -> None:
    with TemporaryDirectory() as td:
        path = Path(td) / "test_uniq.py"
        path.write_text(
            "def test_a():\n    assert True\n\n\ndef test_b():\n    assert True\n",
            encoding="utf-8",
        )
        proc = _run_gate([path])
        assert proc.returncode == 0, proc.stderr


def test_same_name_in_different_classes_is_not_duplicate() -> None:
    """Class-scope names are tracked per class: test_create in ClassA and
    ClassB are distinct pytest nodes and must NOT be reported."""
    with TemporaryDirectory() as td:
        path = Path(td) / "test_classes.py"
        path.write_text(
            "class TestA:\n"
            "    def test_create(self):\n"
            "        assert True\n"
            "\n"
            "class TestB:\n"
            "    def test_create(self):\n"
            "        assert True\n",
            encoding="utf-8",
        )
        proc = _run_gate([path])
        assert proc.returncode == 0, proc.stderr


def test_syntax_error_is_reported_as_failure() -> None:
    with TemporaryDirectory() as td:
        path = Path(td) / "test_bad.py"
        path.write_text("def test_a(:\n", encoding="utf-8")
        proc = _run_gate([path])
        assert proc.returncode == 1
        assert "SYNTAX ERROR" in proc.stderr or "SYNTAX ERROR" in proc.stdout


def test_whole_repo_passes_currently() -> None:
    proc = _run_gate([ROOT / "tests"])
    assert proc.returncode == 0, proc.stderr
