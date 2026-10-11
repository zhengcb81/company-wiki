"""Route only review traces to the new receipt; leave frozen failures untouched."""
from pathlib import Path
import socket
import pytest


@pytest.fixture(autouse=True)
def isolated_review_trace_and_network(monkeypatch, request):
    if hasattr(request.module, "TRACE"):
        monkeypatch.setattr(request.module, "TRACE", Path(__file__).with_name("trace.jsonl"))
    def denied(*args, **kwargs):
        raise AssertionError("cutoff retest has no network")
    monkeypatch.setattr(socket.socket, "connect", denied)
    monkeypatch.setattr(socket, "getaddrinfo", denied)
    monkeypatch.setattr(socket, "create_connection", denied)
