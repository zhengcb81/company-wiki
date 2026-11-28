"""Bounded owner-side lifecycle events, separate from F4 observations."""
from __future__ import annotations


from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone
from functools import lru_cache
from hashlib import sha256
import json
import os
from pathlib import Path
import re
from typing import Any

from . import __version__
from .diagnostic_logging import append_diagnostic
from .diagnostic_redaction import redact_text
from .file_mutex import win32_filesystem_path
from .runtime_feedback_values import OWNER, logical_observation_ref

__all__ = [
    "default_state_root", "delivery_overrides", "diagnostic_paths", "implementation_digest", "input_reference",
    "isolated_state", "read_trace", "subprocess_environment", "write_event",
]

_PREFIX = "runtime-event "
_DIAGNOSTIC = re.compile(r"feedback-[a-f0-9]{32}\.diagnostic\.json")
_REFERENCE_FIELDS = frozenset({"run_id", "attempt_id", "related_run_id", "input_ref", "source_id"})


_isolated_root: ContextVar[Path | None] = ContextVar("cwp_isolated_runtime_root", default=None)


@contextmanager
def isolated_state(root: Path) -> Iterator[None]:
    """Keep one isolated invocation's diagnostics within its assigned state directory."""
    token = _isolated_root.set(root)
    try:
        yield
    finally:
        _isolated_root.reset(token)


def delivery_overrides() -> tuple[Path | None, Path | None]:
    """Return the sidecar and inbox for the current invocation."""
    root = _isolated_root.get()
    if root is not None:
        return None, root / "observations"
    sidecar = os.getenv("RESEARCH_FEEDBACK_OUT")
    inbox = os.getenv("RESEARCH_FEEDBACK_DIR")
    return Path(sidecar) if sidecar else None, Path(inbox) if inbox else None


def subprocess_environment() -> dict[str, str]:
    """Propagate isolated diagnostics at process launch without modifying the parent."""
    environment = dict(os.environ)
    root = _isolated_root.get()
    if root is not None:
        environment.update(
            LOCALAPPDATA=str(root), XDG_STATE_HOME=str(root),
            RESEARCH_FEEDBACK_DIR=str(root / "observations"),
        )
        environment.pop("RESEARCH_FEEDBACK_OUT", None)
    return environment


def default_state_root() -> Path:
    root = _isolated_root.get()
    if root is not None:
        return root / OWNER
    state = os.getenv("LOCALAPPDATA") if os.name == "nt" else os.getenv("XDG_STATE_HOME")
    return (Path(state) if state else Path.home() / ".local" / "state") / OWNER


def diagnostic_paths(filename: str) -> tuple[Path, ...]:
    """Select the configured owner paths in write and cold-read order."""
    roots = [path.parent for path in delivery_overrides() if path is not None]
    try:
        roots.append(default_state_root())
    except (OSError, RuntimeError, ValueError):
        pass
    return tuple(dict.fromkeys(win32_filesystem_path(root / "logs" / filename) for root in roots))


def _trace_paths() -> tuple[Path, ...]:
    return diagnostic_paths("runtime_events.log")


@lru_cache(maxsize=128)
def implementation_digest(source_file: str) -> str | None:
    try:
        return sha256(Path(source_file).read_bytes()).hexdigest()
    except (OSError, ValueError):
        return None


def input_reference(value: Path) -> str | None:
    """Record a stable file reference without storing an input path or contents."""
    try:
        return "sha256:" + sha256(os.fsencode(value.absolute())).hexdigest()
    except (OSError, ValueError):
        return None


def write_event(
    operation: str, run: str, attempt: str, step: str, status: str, *,
    source_file: str,
    input_ref: str | None = None,
    source_id: str | None = None,
    related_run_id: str | None = None,
    details_ref: str | None = None,
    exit_code: int | None = None,
) -> bool:
    """Append a safe owner event without projecting normal work into the F4 inbox."""
    event: dict[str, Any] = {
        "at_utc": datetime.now(timezone.utc).isoformat(timespec="microseconds"),
        "owner": OWNER, "run_id": logical_observation_ref(run),
        "attempt_id": logical_observation_ref(attempt),
        "operation": operation, "step": step, "status": status,
        "package_version": __version__, "implementation_sha256": implementation_digest(source_file),
    }
    optional = {
        "input_ref": input_ref, "source_id": source_id,
        "related_run_id": related_run_id, "details_ref": details_ref,
    }
    event.update({key: logical_observation_ref(value) for key, value in optional.items() if value})
    if exit_code is not None:
        event["exit_code"] = exit_code
    text = _PREFIX + json.dumps(event, sort_keys=True, ensure_ascii=True)
    for path in _trace_paths():
        try:
            if append_diagnostic(path, text, warn_on_stderr=False):
                return True
        except (OSError, ValueError):
            continue
    return False


def _diagnostic_value(value: Any) -> Any:
    if isinstance(value, dict):
        return _safe_record(value)
    if isinstance(value, list):
        return [_diagnostic_value(item) for item in value]
    return redact_text(value)


def _safe_record(record: dict[str, Any]) -> dict[str, Any]:
    # Canonicalize the same coordinates used by new writers and by the
    # reader's selector. The historical file and its detail locator stay put.
    return {
        key: logical_observation_ref(value)
        if key in _REFERENCE_FIELDS and isinstance(value, str) else _diagnostic_value(value)
        for key, value in record.items()
    }


def _retained_events(path: Path) -> list[dict[str, Any]]:
    items = []
    with path.open(encoding="utf-8", errors="replace") as trace:
        for line in trace:
            _, marker, data = line.partition(_PREFIX)
            if not marker:
                continue
            try:
                event = json.loads(data)
            except (ValueError, RecursionError):
                continue
            if (isinstance(event, dict) and event.get("owner") == OWNER
                    and all(isinstance(event.get(key), str)
                            for key in ("at_utc", "run_id", "attempt_id", "operation", "step", "status"))):
                items.append(_safe_record(event))
    return items


def _details(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    references = {ref for event in events if isinstance(ref := event.get("details_ref"), str)
                  and _DIAGNOSTIC.fullmatch(ref)}
    paths: list[Path] = []
    sidecar, inbox = delivery_overrides()
    if sidecar is not None:
        paths.append(sidecar.parent)
    if inbox is not None:
        paths.append(inbox)
    try:
        paths.append(default_state_root() / "observations")
    except (OSError, RuntimeError, ValueError):
        pass
    details = []
    for ref in sorted(references):
        for path in paths:
            try:
                packet = json.loads(win32_filesystem_path(path / ref).read_bytes())
                if isinstance(packet, dict) and packet.get("owner") == OWNER:
                    details.append(_safe_record(packet))
                    break
            except (OSError, ValueError, RecursionError):
                continue
    return details


def read_trace(run_id: str, *, attempt_id: str | None = None) -> dict[str, Any]:
    """Cold-read retained events by original correlation or related business run."""
    run_id = logical_observation_ref(run_id)
    attempt_id = logical_observation_ref(attempt_id) if attempt_id is not None else None
    records: list[dict[str, Any]] = []
    unreachable = 0
    for current in _trace_paths():
        for path in (current.with_name(current.name + ".1"), current):
            try:
                records.extend(_retained_events(path))
            except FileNotFoundError:
                continue
            except OSError:
                unreachable += 1
    related = {(record.get("run_id"), record.get("attempt_id")) for record in records
               if record.get("related_run_id") == run_id or record.get("run_id") == run_id}
    events = [record for record in records
              if (record.get("run_id"), record.get("attempt_id")) in related
              and (attempt_id is None or record.get("attempt_id") == attempt_id)]
    events.sort(key=lambda record: record["at_utc"])
    return {
        "status": "available" if events else "unavailable" if unreachable else "not_found",
        "run_id": run_id, "attempt_id": attempt_id, "events": events, "diagnostics": _details(events),
    }
