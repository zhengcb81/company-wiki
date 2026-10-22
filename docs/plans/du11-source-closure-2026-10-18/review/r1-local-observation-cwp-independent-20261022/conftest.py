"""Only owned source/catalog fixtures; disable credentials and sockets."""

import os
import socket
import pytest

for name in (
    "OPENAI_API_KEY",
    "DEEPSEEK_API_KEY",
    "MINIMAX_API_KEY",
    "MIMO_API_KEY",
    "FMP_API_KEY",
):
    os.environ.pop(name, None)
os.environ["PYTHON_DOTENV_DISABLED"] = "1"
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def refuse(*_args, **_kwargs):
        raise AssertionError("CWP_LOCAL_OBSERVATION_REVIEW_OFFLINE")

    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)
