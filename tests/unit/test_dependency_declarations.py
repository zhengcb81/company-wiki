"""The fast commit check detects dependency drift without importing installed packages."""
from pathlib import Path
import subprocess
import sys
import re
import yaml

from tools.check_dependencies import missing_dependencies


def test_declarations_do_not_depend_on_host_installed_httpx(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        '[project]\ndependencies = ["httpx>=0.27,<1", "requests>=2"]\n', encoding="utf-8")
    (tmp_path / "requirements.txt").write_text("requests>=2\n", encoding="utf-8")
    assert missing_dependencies(tmp_path) == ["httpx>=0.27,<1"]
    (tmp_path / "requirements.txt").write_text("httpx>=0.27,<1 # direct\nrequests>=2\n", encoding="utf-8")
    assert missing_dependencies(tmp_path) == []


def test_checker_cli_exits_nonzero_for_missing_direct_dependency(tmp_path):
    (tmp_path / "pyproject.toml").write_text('[project]\ndependencies=["missing>=1"]\n', encoding="utf-8")
    (tmp_path / "requirements.txt").write_text("", encoding="utf-8")
    script = Path(__file__).resolve().parents[2] / "tools/check_dependencies.py"
    call = subprocess.run([sys.executable, str(script), "--root", str(tmp_path)],
                          capture_output=True, text=True, timeout=10)
    assert call.returncode == 1
    assert "missing>=1" in call.stdout


def test_commit_triggers_only_declaration_files_without_pytest():
    root = Path(__file__).resolve().parents[2]
    config = yaml.safe_load((root / ".pre-commit-config.yaml").read_text(encoding="utf-8"))
    hook = next(h for repo in config["repos"] for h in repo["hooks"] if h["id"] == "dependency-declarations")
    pattern = re.compile(hook["files"])
    assert all(pattern.search(p) for p in ("pyproject.toml", "requirements.txt", "requirements-test.txt", "tools/check_dependencies.py"))
    assert not any(pattern.search(p) for p in ("README.md", "src/company_wiki/automation/worker.py"))
    assert "pytest" not in hook["entry"]
