"""Optional wake-up at the end of an operator-owned scenario."""

from collections import Counter
import json
import os
from pathlib import Path
import subprocess
import sys

from .coordinator import settle
from .host import process_host, read_hosts
from .observations import read_batch


def after_observations(sidecar: Path, env) -> dict | None:
    config = env.get("RESEARCH_FEEDBACK_HOSTS")
    if not config:
        return None
    try:
        host = process_host(read_hosts(Path(config)))
        wait_seconds = int(env.get("RESEARCH_FEEDBACK_WAIT_SECONDS", "0"))
        if wait_seconds < 0:
            raise ValueError("negative follow-up window")
    except (OSError, ValueError, RecursionError):
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
    try:
        with output.open("xb") as stream:
            child = subprocess.Popen(
                [sys.executable, "-B", "-m", "tools.feedback_loop.hook", str(sidecar.resolve()),
                 str(Path(config).resolve()), wait_seconds],
                cwd=Path(__file__).resolve().parents[2], stdin=subprocess.DEVNULL, stdout=stream, stderr=subprocess.DEVNULL,
                start_new_session=os.name != "nt", creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
    except FileExistsError:
        return {"status": "previous_wake_receipt", "resume": "tick"}
    except (OSError, ValueError) as exc:
        return {"status": "wake_unavailable", "error_type": type(exc).__name__, "resume": "tick"}
    return {"status": "scheduled", "pid": child.pid}


if __name__ == "__main__":
    env = {"RESEARCH_FEEDBACK_HOSTS": sys.argv[2], "RESEARCH_FEEDBACK_WAIT_SECONDS": sys.argv[3] if len(sys.argv) > 3 else "0"}
    print(json.dumps(after_observations(Path(sys.argv[1]), env)))
