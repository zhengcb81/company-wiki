"""Zero-network guard for the whole P4 session (card 5.5.5).

``socket.socket.connect`` (and the sibling entry points that can reach the
network) raise ``AssertionError`` for the entire session.  Any code that catches
it is recorded as ``p4_network_attempted``; the guard is never uninstalled.
"""

from __future__ import annotations

import socket
import threading
from typing import Any


class NetworkAttempted(AssertionError):
    """Raised by the guard; an ``AssertionError`` so no ``except Exception`` is needed."""


_FORBIDDEN = (
    "socket.socket.connect",
    "socket.socket.connect_ex",
    "socket.create_connection",
)

_lock = threading.Lock()
_attempts: list[str] = []
_installed: set[str] = set()
_originals: dict[str, Any] = {}


def _record(name: str) -> None:
    with _lock:
        _attempts.append(name)


def record_attempt(name: str) -> None:
    """Record a network attempt observed by a test-local probe."""
    _record(name)


def attempts() -> tuple[str, ...]:
    with _lock:
        return tuple(_attempts)


def network_attempted() -> bool:
    return bool(attempts())


def _guard(name: str):
    def forbidden(*_args: Any, **_kwargs: Any):
        _record(name)
        raise NetworkAttempted(
            f"{name} reached by P4 lane; the lane must never touch the network "
            "(card section 8)"
        )

    return forbidden


def guard(name: str):
    """The forbidden callable for ``name``; tests may install it under monkeypatch.

    ``tests/conftest.py``'s hermetic fixture re-patches ``socket`` per test, so a
    test that wants to prove the lane guard raises must restore this guard for
    the duration of its own probe.
    """
    return _guard(name)


def install() -> None:
    """Forbid every network entry point for the rest of the session.

    Safe to call repeatedly: ``tests/conftest.py`` (outside this card's write
    set) installs its own per-test hermetic socket patch, and monkeypatch
    restores whatever it displaced.  Re-installing here reclaims the patch for
    the lane so the recording guard - not the silent one - is the one that
    fires, both between and during tests.
    """
    with _lock:
        socket.socket.connect = _guard("socket.socket.connect")  # type: ignore[method-assign]
        socket.socket.connect_ex = _guard("socket.socket.connect_ex")  # type: ignore[method-assign]
        socket.create_connection = _guard("socket.create_connection")
        _installed.update(_FORBIDDEN)


def is_installed() -> bool:
    with _lock:
        return bool(_installed)


def reset_for_test() -> None:
    """Clear recorded attempts only; the guard itself stays installed."""
    with _lock:
        _attempts.clear()
