"""Read retained runtime events for an original invocation."""

from __future__ import annotations

import json

from . import runtime_feedback
from .runtime_journal import (
    default_state_root,
    diagnostic_paths,
    implementation_digest,
    input_reference,
    read_trace,
    write_event,
)

__all__ = [
    "default_state_root", "diagnostic_paths", "implementation_digest",
    "input_reference", "read_trace", "write_event",
]


@runtime_feedback.entry("runtime-trace", local_only=True, quiet_success=True)
def main(argv: list[str] | None = None) -> int:
    parser = runtime_feedback.ArgumentParser(description="Read retained company-wiki runtime events by original run")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--attempt-id")
    args = parser.parse_args(argv)
    result = read_trace(args.run_id, attempt_id=args.attempt_id)
    if result["status"] == "unavailable":
        runtime_feedback.record("runtime-trace", "unavailable", reason="runtime_history_unavailable")
    print(json.dumps(result, ensure_ascii=True, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(runtime_feedback.run_cli(main))
