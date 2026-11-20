"""Launch an ordinary owner command with a recoverable observation sidecar."""

from __future__ import annotations

import argparse
from contextlib import suppress
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from uuid import uuid4

from .coordinator import settle
from .host import process_host, read_hosts
from .local_host import LocalHost
from .observations import read_batch


_ROOT = Path(__file__).resolve().parents[2]
_MARKER = re.compile(r"feedback-[a-f0-9]{32}\.(?:pending|ready)")
_SETTLED = {"expected", "external", "needs_evidence", "reconciled", "verified", "regressed"}


def _observation_dirs(settings: Path, owners: dict, selected: str | None):
    for owner, route in owners.items():
        if selected is not None and owner != selected:
            continue
        target = route.get("observation_dir")
        if isinstance(target, str) and target:
            yield owner, settings.parent / target


def drain(settings: Path, hosts_file: Path, *, owner: str | None, wait_seconds: int) -> dict:
    """Resume host work, then consume only markers from the configured inboxes."""
    host = LocalHost(settings)
    rpc = process_host(read_hosts(hosts_file))
    woken = len(host.recover())
    processed = remaining = 0
    diagnostics = []
    visited = set()
    for name, directory in _observation_dirs(settings, host.owners, owner):
        if directory in visited:
            continue
        visited.add(directory)
        try:
            markers = sorted(directory.iterdir())
        except FileNotFoundError:
            continue
        except OSError:
            diagnostics.append({"owner": name, "code": "observation_inbox_unreadable"})
            continue
        for marker in markers:
            if not _MARKER.fullmatch(marker.name) or not marker.is_file():
                continue
            sidecar = marker.with_suffix(".jsonl")
            if not sidecar.exists() and marker.suffix == ".pending":
                remaining += 1
                continue
            # A completed business command need not have any observations.
            batch = read_batch([sidecar] if sidecar.exists() else [])
            result = settle(batch, rpc, wait_seconds)
            processed += len(result["observations"])
            diagnostics.extend({"owner": name, **row} for row in result["diagnostics"])
            if (marker.suffix == ".ready" and not result["diagnostics"]
                    and all(row["status"] in _SETTLED for row in result["observations"])):
                try:
                    marker.unlink(missing_ok=True)
                except OSError:
                    remaining += 1
                    diagnostics.append({"owner": name, "code": "observation_marker_unwritable"})
            else:
                remaining += 1
    return {"woken": woken, "processed": processed, "remaining": remaining, "diagnostics": diagnostics}


def wake(settings: Path, hosts_file: Path, *, owner: str | None = None, wait_seconds: int = 0):
    scope = [] if owner is None else ["--owner", owner]
    subprocess.Popen(
        [sys.executable, "-B", "-m", "tools.feedback_loop.intake", "--settings", str(settings),
         "--hosts", str(hosts_file), "--wait-seconds", str(wait_seconds), "drain", *scope],
        cwd=_ROOT, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        start_new_session=os.name != "nt", creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )


def run_observed(settings: Path, hosts_file: Path, owner: str, command: list[str], wait_seconds: int) -> int:
    """The command and standard streams belong to the original business caller."""
    cwd, marker = None, None
    env = os.environ.copy()
    try:
        owners = read_hosts(settings)["owners"]
        route = owners[owner]
        configured_cwd = route.get("cwd")
        if isinstance(configured_cwd, str) and configured_cwd:
            cwd = settings.parent / configured_cwd
        business_env = route.get("business_env", {})
        if isinstance(business_env, dict):
            env.update({key: value for key, value in business_env.items()
                        if isinstance(key, str) and isinstance(value, str)})
        paths = dict(_observation_dirs(settings, owners, owner))
        directory = paths.get(owner)
        if directory is not None:
            directory.mkdir(parents=True, exist_ok=True)
            token = "feedback-" + uuid4().hex
            pending = directory / (token + ".pending")
            pending.touch(exist_ok=False)
            marker = pending
            env["RESEARCH_FEEDBACK_OUT"] = str(marker.with_suffix(".jsonl"))
            env.setdefault("RESEARCH_FEEDBACK_RUN_ID", token)
            env.setdefault("RESEARCH_FEEDBACK_ATTEMPT_ID", token)
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        # Feedback is optional for the native business command.
        pass

    try:
        result = subprocess.run(command, cwd=cwd, env=env, check=False)
    except OSError:
        if marker is not None and not marker.with_suffix(".jsonl").exists():
            with suppress(OSError):
                marker.unlink(missing_ok=True)
                marker = None
        return 127
    else:
        if marker is not None:
            with suppress(OSError):
                marker.replace(marker.with_suffix(".ready"))
        return result.returncode
    finally:
        if marker is not None:
            with suppress(OSError):
                wake(settings, hosts_file, owner=owner, wait_seconds=wait_seconds)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--settings", required=True, type=Path)
    parser.add_argument("--hosts", required=True, type=Path)
    parser.add_argument("--wait-seconds", default=15, type=int)
    modes = parser.add_subparsers(dest="mode", required=True)
    run = modes.add_parser("run", help="run an existing business command and wake feedback")
    run.add_argument("--owner", required=True)
    run.add_argument("command", nargs=argparse.REMAINDER)
    modes.add_parser("drain", help="resume the configured observation inboxes").add_argument("--owner")
    args = parser.parse_args(argv)
    settings, hosts_file = args.settings.resolve(), args.hosts.resolve()
    if args.wait_seconds < 0:
        parser.error("--wait-seconds must be nonnegative")
    if args.mode == "run":
        command = args.command[1:] if args.command and args.command[0] == "--" else args.command
        if not command:
            parser.error("run requires the original command")
        return run_observed(settings, hosts_file, args.owner, command, args.wait_seconds)
    summary = drain(settings, hosts_file, owner=args.owner, wait_seconds=args.wait_seconds)
    print(json.dumps(summary, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
