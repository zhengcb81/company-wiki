"""Audit-hook sidecar loaded via PYTHONPATH for N6-FOOTPRINT E2E runs.

It records every ``open`` audit event that touches a regular file under
``N6_E2E_ROOT`` so the E2E can prove the scanner reads zero original bodies.
The flushed JSON lands at ``N6_E2E_OPEN_LOG``; both variables are test-only.
"""

from __future__ import annotations

import atexit
import json
import os
import sys
import threading

_state = threading.local()
_records: list[dict] = []
_enabled = os.environ.get("N6_E2E_OPEN_LOG")
_root = os.environ.get("N6_E2E_ROOT")


def _inside_root(text: str) -> bool:
    if not _root:
        return False
    try:
        real = os.path.normcase(os.path.realpath(text))
        root = os.path.normcase(os.path.realpath(_root))
    except OSError:
        return False
    return real == root or real.startswith(root + os.sep)


def _hook(event, args):
    if event not in ("open", "io.open"):
        return
    if getattr(_state, "busy", False):
        return
    if not args:
        return
    target = args[0]
    if not isinstance(target, (str, bytes, os.PathLike)):
        return
    try:
        text = os.fsdecode(os.fspath(target))
    except TypeError:
        return
    if not _inside_root(text):
        return
    try:
        if os.path.isdir(text):
            return
    except OSError:
        return
    mode = args[1] if len(args) > 1 else None
    _state.busy = True
    try:
        _records.append(
            {
                "event": event,
                "mode": str(mode),
                "path": os.path.relpath(
                    os.path.realpath(text), os.path.realpath(str(_root))
                ),
            }
        )
    finally:
        _state.busy = False


def _flush():
    if not _enabled:
        return
    _state.busy = True
    try:
        with open(_enabled, "w", encoding="utf-8") as handle:
            json.dump(_records, handle, ensure_ascii=False)
    except Exception:
        pass
    finally:
        _state.busy = False


if _enabled and _root:
    sys.addaudithook(_hook)
    atexit.register(_flush)
