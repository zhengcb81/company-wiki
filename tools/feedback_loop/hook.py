"""Optional wake-up at the end of an operator-owned scenario."""

from collections import Counter
import json
import os
from pathlib import Path
import subprocess
import sys

from .coordinator import advance
from .host import process_host, read_hosts
from .observations import read_batch


def after_observations(sidecar: Path, env) -> dict | None:
    config = env.get("RESEARCH_FEEDBACK_HOSTS")
    if not config:
        return None
    try:
        host = process_host(read_hosts(Path(config)))
    except (OSError, ValueError, RecursionError):
        return {"status": "host_config_unavailable"}
    result = advance(read_batch([sidecar]), host)
    return {"status": "tick_completed", "states": dict(Counter(row["status"] for row in result["observations"])),
            "dispositions": dict(Counter(row["disposition"] for row in result["observations"])),
            "diagnostics": result["diagnostics"]}


def wake(sidecar: Path, config: str, output: Path) -> dict:
    """Start the finite control tick outside the completed business process."""
    try:
        with output.open("xb") as stream:
            child = subprocess.Popen(
                [sys.executable, "-B", "-m", "tools.feedback_loop.hook", str(sidecar.resolve()), str(Path(config).resolve())],
                cwd=Path(__file__).resolve().parents[2], stdin=subprocess.DEVNULL, stdout=stream, stderr=subprocess.DEVNULL,
                start_new_session=os.name != "nt", creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
    except FileExistsError:
        return {"status": "previous_wake_receipt", "resume": "tick"}
    except (OSError, ValueError) as exc:
        return {"status": "wake_unavailable", "error_type": type(exc).__name__, "resume": "tick"}
    return {"status": "scheduled", "pid": child.pid}


if __name__ == "__main__":
    print(json.dumps(after_observations(Path(sys.argv[1]), {"RESEARCH_FEEDBACK_HOSTS": sys.argv[2]})))
