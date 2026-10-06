"""Hermetic pytest setup for the N5-RAW-DUP read-only duplicate audit tests.

The lane write set is limited to ``tools/raw_duplicate_audit/``; this package
therefore carries its own conftest instead of reusing ``tests/conftest.py``.
"""

from __future__ import annotations

import os
import socket
import sys
from pathlib import Path

import pytest

TESTS_DIR = Path(__file__).resolve().parent
PACKAGE_DIR = TESTS_DIR.parent
TOOLS_DIR = PACKAGE_DIR.parent
REPO_ROOT = TOOLS_DIR.parent

for _path in (REPO_ROOT / "src", TOOLS_DIR, TESTS_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

for _secret_name in (
    "OPENAI_API_KEY",
    "DEEPSEEK_API_KEY",
    "MINIMAX_API_KEY",
    "MIMO_API_KEY",
    "TAVILY_API_KEY",
    "ANTHROPIC_API_KEY",
):
    os.environ.pop(_secret_name, None)
os.environ["PYTHON_DOTENV_DISABLED"] = "1"
os.environ["COMPANY_WIKI_NETWORK"] = "blocked"
os.environ["COMPANY_WIKI_REAL_LLM"] = "0"


@pytest.fixture(autouse=True)
def hermetic_runtime(monkeypatch):
    """No sockets, no provider calls, no repository secrets in this lane."""
    for secret_name in (
        "OPENAI_API_KEY",
        "DEEPSEEK_API_KEY",
        "MINIMAX_API_KEY",
        "MIMO_API_KEY",
        "TAVILY_API_KEY",
        "ANTHROPIC_API_KEY",
    ):
        monkeypatch.delenv(secret_name, raising=False)
    monkeypatch.setenv("PYTHON_DOTENV_DISABLED", "1")
    monkeypatch.setenv("COMPANY_WIKI_NETWORK", "blocked")
    monkeypatch.setenv("COMPANY_WIKI_REAL_LLM", "0")

    def blocked(*_args, **_kwargs):
        raise RuntimeError("HERMETIC NETWORK BLOCKED: N5-RAW-DUP opens no sockets")

    monkeypatch.setattr(socket.socket, "connect", blocked)
    monkeypatch.setattr(socket, "create_connection", blocked)
