"""Bounded owner-side lifecycle events, separate from F4 observations."""
from __future__ import annotations

import argparse
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
from .file_mutex import win32_filesystem_path
from .runtime_feedback_values import OWNER, logical_observation_ref

__all__ = ["default_state_root", "implementation_digest", "input_reference", "read_trace", "write_event"]

_PREFIX = "runtime-event "
_DIAGNOSTIC = re.compile(r"feedback-[a-f0-9]{32}\.diagnostic\.json")


def default_state_root() -> Path:
    state = os.getenv("LOCALAPPDATA") if os.name == "nt" else os.getenv("XDG_STATE_HOME")
    return (Path(state) if state else Path.home() / ".local" / "state") / OWNER


def _trace_paths() -> tuple[Path, ...]:
    roots: list[Path] = []
    explicit = os.getenv("RESEARCH_FEEDBACK_OUT") or os.getenv("RESEARCH_FEEDBACK_DIR")
    if explicit:
        roots.append(Path(explicit).parent)
    try:
        roots.append(default_state_root())
    except (OSError, RuntimeError, ValueError):
        pass
    return tuple(dict.fromkeys(win32_filesystem_path(root / "logs/runtime_events.log") for root in roots))


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


def _retained_events(path: Path) -> list[dict[str, Any]]:
    items = []
    with path.open(encoding="utf-8", errors="replace") as trace:
        for line in trace:
            _, marker, data = line.partition(_PREFIX)
            if not marker:
                continue
            try:
                event = json.loads(data)
            except ValueError:
                continue
            if (isinstance(event, dict) and event.get("owner") == OWNER
                    and all(isinstance(event.get(key), str)
                            for key in ("at_utc", "run_id", "attempt_id", "operation", "step", "status"))):
                items.append(event)
    return items


def _details(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    references = {ref for event in events if isinstance(ref := event.get("details_ref"), str)
                  and _DIAGNOSTIC.fullmatch(ref)}
    paths: list[Path] = []
    if explicit := os.getenv("RESEARCH_FEEDBACK_OUT"):
        paths.append(Path(explicit).parent)
    if explicit := os.getenv("RESEARCH_FEEDBACK_DIR"):
        paths.append(Path(explicit))
    try:
        paths.append(default_state_root() / "observations")
    except (OSError, RuntimeError, ValueError):
        pass
    details = []
    for ref in sorted(references):
        for path in paths:
            try:
                packet = json.loads(win32_filesystem_path(path / ref).read_bytes())
            except (OSError, ValueError):
                continue
            if isinstance(packet, dict) and packet.get("owner") == OWNER:
                details.append(packet)
                break
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read retained company-wiki runtime events by original run")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--attempt-id")
    args = parser.parse_args(argv)
    print(json.dumps(read_trace(args.run_id, attempt_id=args.attempt_id), ensure_ascii=True, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
