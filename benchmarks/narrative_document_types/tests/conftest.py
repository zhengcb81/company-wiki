"""Test bootstrap for the N5-DOCSET benchmark package.

pytest loads this conftest for everything under ``benchmarks/narrative_document_types``
(the repository-root conftest is also loaded for the short-basetemp convention),
but ``tests/conftest.py`` does not apply here, so the two things that one file
provides for the ordinary suite are re-provided locally: ``src`` on ``sys.path``
and a hermetic socket block.
"""

from __future__ import annotations

import os
from pathlib import Path
import socket
import sys

import pytest


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PACKAGE_ROOT.parents[1]

for _entry in (REPO_ROOT / "src", PACKAGE_ROOT):
    entry = str(_entry)
    if entry not in sys.path:
        sys.path.insert(0, entry)

os.environ.setdefault("PYTHON_DOTENV_DISABLED", "1")
os.environ.setdefault("COMPANY_WIKI_NETWORK", "blocked")
os.environ.setdefault("COMPANY_WIKI_REAL_LLM", "0")


@pytest.fixture(autouse=True)
def hermetic_sockets(monkeypatch):
    def blocked(*_args, **_kwargs):
        raise RuntimeError(
            "HERMETIC NETWORK BLOCKED: benchmark tests cannot open sockets"
        )

    monkeypatch.setattr(socket.socket, "connect", blocked)
    monkeypatch.setattr(socket, "create_connection", blocked)
