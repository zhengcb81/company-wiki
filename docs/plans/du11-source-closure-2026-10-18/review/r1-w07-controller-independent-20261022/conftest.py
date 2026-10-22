"""Owned independent-review runtime; never read real provider credentials."""
import os
import socket
import pytest

SECRET_NAMES = (
    'OPENAI_API_KEY', 'DEEPSEEK_API_KEY', 'MINIMAX_API_KEY', 'MIMO_API_KEY',
    'TAVILY_API_KEY', 'ANTHROPIC_API_KEY',
)
for name in SECRET_NAMES:
    os.environ.pop(name, None)
os.environ['PYTHON_DOTENV_DISABLED'] = '1'
os.environ['COMPANY_WIKI_NETWORK'] = 'blocked'
os.environ['COMPANY_WIKI_REAL_LLM'] = '0'


@pytest.fixture(autouse=True)
def hermetic_runtime(monkeypatch):
    for name in SECRET_NAMES:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv('PYTHON_DOTENV_DISABLED', '1')
    monkeypatch.setenv('COMPANY_WIKI_NETWORK', 'blocked')
    monkeypatch.setenv('COMPANY_WIKI_REAL_LLM', '0')

    def refuse(*_args, **_kwargs):
        raise RuntimeError('INDEPENDENT_REVIEW_EXTERNAL_SOCKET_REFUSED')

    monkeypatch.setattr(socket.socket, 'connect', refuse)
    monkeypatch.setattr(socket, 'create_connection', refuse)
