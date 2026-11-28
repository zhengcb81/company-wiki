"""Optional wake-up at the end of an operator-owned scenario."""

from collections import Counter
import json
import logging
from pathlib import Path
import sys

from company_wiki import runtime_feedback
from company_wiki.diagnostic_logging import log_exception

from .coordinator import settle
from .diagnostics import launch_background, run_background
from .host import process_host, read_hosts
from .observations import read_batch


_logger = logging.getLogger(__name__)


def after_observations(sidecar: Path, env) -> dict | None:
    config = env.get("RESEARCH_FEEDBACK_HOSTS")
    if not config:
        return None
    try:
        host = process_host(read_hosts(Path(config)))
        wait_seconds = int(env.get("RESEARCH_FEEDBACK_WAIT_SECONDS", "0"))
        if wait_seconds < 0:
            raise ValueError("negative follow-up window")
    except (OSError, ValueError, RecursionError) as exc:
        runtime_feedback.record_optional_failure("host_config_unavailable", exc)
        return {"status": "host_config_unavailable"}
    result = settle(read_batch([sidecar]), host, wait_seconds)
    observations = result["observations"]
    summary = {"status": "tick_completed", "states": dict(Counter(row["status"] for row in observations)),
               "dispositions": dict(Counter(row["disposition"] for row in observations)),
               "diagnostics": result["diagnostics"]}
    reviews = [{"occurrence_id": row["occurrence_id"], **row["gate_review"]}
               for row in observations if "gate_review" in row]
    if reviews:
        summary["gate_reviews"] = reviews
    return summary


def wake(sidecar: Path, config: str, output: Path, *, wait_seconds: str = "0") -> dict:
    """Start the finite control tick outside the completed business process."""
    destination = output.with_suffix(".stderr.log")
    try:
        with output.open("xb") as stream:
            child = launch_background(
                "tools.feedback_loop.hook", destination, str(sidecar.resolve()),
                str(Path(config).resolve()), wait_seconds, cwd=Path(__file__).resolve().parents[2], stdout=stream,
            )
    except FileExistsError:
        return {"status": "previous_wake_receipt", "resume": "tick"}
    except (OSError, ValueError) as exc:
        log_exception(_logger, logging.WARNING, "Feedback hook wake could not start", exc)
        return {"status": "wake_unavailable", "error_type": type(exc).__name__, "resume": "tick"}
    return {"status": "scheduled", "pid": child.pid}


@runtime_feedback.entry("feedback-hook", local_only=True, quiet_success=True)
def _main() -> int:
    env = {"RESEARCH_FEEDBACK_HOSTS": sys.argv[2], "RESEARCH_FEEDBACK_WAIT_SECONDS": sys.argv[3] if len(sys.argv) > 3 else "0"}
    print(json.dumps(after_observations(Path(sys.argv[1]), env)))
    return 0


if __name__ == "__main__":
    raise SystemExit(run_background(_main))
