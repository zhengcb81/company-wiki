"""Executable contracts for the no-network, no-dotenv test runtime.

The environment isolation itself migrated out of the retired
``scripts/clean_env_gate.py`` into ``tests/support/isolated_environment.py``
(G5-CWP-CHECKS); these tests keep consuming it.
"""

from __future__ import annotations

import os
import socket
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from support.isolated_environment import sanitized_environment as clean_environment


def test_isolated_environment_disables_dotenv_and_strips_api_keys(monkeypatch) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "must-not-survive")
    monkeypatch.setenv("MINIMAX_API_KEY", "must-not-survive")
    monkeypatch.setenv("MIMO_API_KEY", "must-not-survive")
    monkeypatch.setenv("TAVILY_API_KEY", "must-not-survive")
    monkeypatch.setenv("CUSTOM_API_KEY", "must-not-survive")
    monkeypatch.setenv("COMPANY_WIKI_WRITE_MODE", "legacy")
    monkeypatch.setenv("COMPANY_WIKI_LEGACY_WRITERS", "allow")
    environment = clean_environment()
    assert "DEEPSEEK_API_KEY" not in environment
    assert "MINIMAX_API_KEY" not in environment
    assert "MIMO_API_KEY" not in environment
    assert "TAVILY_API_KEY" not in environment
    assert "CUSTOM_API_KEY" not in environment
    assert "COMPANY_WIKI_WRITE_MODE" not in environment
    assert "COMPANY_WIKI_LEGACY_WRITERS" not in environment
    assert environment["PYTHON_DOTENV_DISABLED"] == "1"
    assert environment["COMPANY_WIKI_NETWORK"] == "blocked"
    assert environment["COMPANY_WIKI_REAL_LLM"] == "0"
    assert environment["PIP_NO_INDEX"] == "1"
    assert environment["NO_PROXY"] == "*"


def test_config_cannot_reload_repository_dotenv_when_disabled() -> None:
    environment = os.environ.copy()
    environment.pop("DEEPSEEK_API_KEY", None)
    environment.pop("MINIMAX_API_KEY", None)
    environment.pop("MIMO_API_KEY", None)
    environment.pop("TAVILY_API_KEY", None)
    environment["PYTHON_DOTENV_DISABLED"] = "1"
    environment["COMPANY_WIKI_NETWORK"] = "blocked"
    environment["COMPANY_WIKI_REAL_LLM"] = "0"
    environment["PYTHONPATH"] = str(SCRIPTS)
    code = (
        "import os, config; config._load_dotenv(); "
        "print(int('MINIMAX_API_KEY' in os.environ), int('MIMO_API_KEY' in os.environ), "
        "int('TAVILY_API_KEY' in os.environ))"
    )
    completed = subprocess.run(
        [sys.executable, "-c", code],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=20,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip() == "0 0 0"


def test_socket_connections_are_blocked_by_default() -> None:
    with pytest.raises(RuntimeError, match="HERMETIC NETWORK BLOCKED"):
        socket.create_connection(("127.0.0.1", 9), timeout=0.05)
