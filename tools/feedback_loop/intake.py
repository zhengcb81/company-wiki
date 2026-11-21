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


def _publish_marker(path: Path, value: dict) -> None:
    temporary = path.with_suffix(path.suffix + "-tmp")
    with temporary.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(value, ensure_ascii=True) + "\n")
    temporary.replace(path)


def _process_failure(marker: Path, context: dict, actual: str, os_error: dict) -> None:
    """Preserve the OS outcome separately from the owner's streams and accounting."""
    native = marker.with_suffix(".jsonl")
    observations = read_batch([native]).observations.values() if native.exists() else ()
    # A sibling failure, even on the same owner, run and attempt, cannot
    # account for the exit of this particular process.
    if any(row["owner"] == row["origin_owner"] == context["owner"]
           and (row["run_id"], row["attempt_id"]) == (context["run_id"], context["attempt_id"])
           and row.get("parent_step_id") == context["step_id"] and row["step_id"] != context["step_id"]
           and row["check_id"] == "process-outcome" and row["actual"] == actual
           and (row["disposition"] == "deviation" or "refusal_code" in row)
           for row in observations):
        return
    row = {**context, "schema_version": "feedback-observation/1", "check_id": "process-outcome",
           "expected": "exit:0", "actual": actual, "disposition": "deviation",
           "evidence_ref": "intake-process/1/" + marker.stem, **os_error}
    # The native producer owns .jsonl; some producers require it to be initially
    # absent. A separate atomic record also survives an interrupted ready rename.
    _publish_marker(marker.with_suffix(".process"), row)


def _restore_process_receipt(marker: Path, original: dict, receipt: Path) -> None:
    temporary = receipt.with_suffix(".process-tmp")
    if receipt.exists() or not temporary.is_file():
        return
    with temporary.open("rb") as stream:
        content = stream.read()
    # Readers may see the writer before it closes the file. Leave incomplete
    # bytes in place; a later drain can finish the same publication.
    if not content.endswith(b"\n"):
        return
    value = json.loads(content)
    if (isinstance(value, dict) and all(value.get(key) == item for key, item in original.items())
            and value.get("schema_version") == "feedback-observation/1"
            and value.get("check_id") == "process-outcome"
            and value.get("evidence_ref") == "intake-process/1/" + marker.stem):
        temporary.replace(receipt)


def drain(settings: Path, hosts_file: Path, *, owner: str | None, wait_seconds: int) -> dict:
    """Resume host work, then consume only markers from the configured inboxes."""
    host = LocalHost(settings)
    rpc = process_host(read_hosts(hosts_file))
    woken = len(host.recover())
    processed = remaining = 0
    diagnostics = []
    unconfirmed = []
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
            process_receipt = marker.with_suffix(".process")
            if marker.suffix == ".pending" and not process_receipt.exists():
                try:
                    # Legacy empty markers do not identify the original run.
                    content = marker.read_bytes()
                    if content:
                        marker_data = json.loads(content)
                        original = {key: marker_data[key] for key in ("owner", "run_id", "attempt_id", "step_id")}
                        _restore_process_receipt(marker, original, process_receipt)
                        if marker.exists() and not process_receipt.exists():
                            unconfirmed.append(original)
                except FileNotFoundError:
                    pass  # Another reader or the supervisor has finished publishing.
                except (OSError, ValueError, TypeError, KeyError, RecursionError):
                    diagnostics.append({"owner": name, "code": "unreadable_process_marker"})
            sources = [path for path in (sidecar, process_receipt) if path.exists()]
            if not sources and marker.suffix == ".pending":
                remaining += 1
                continue
            # A completed business command need not have any observations.
            batch = read_batch(sources)
            result = settle(batch, rpc, wait_seconds)
            processed += len(result["observations"])
            diagnostics.extend({"owner": name, **row} for row in result["diagnostics"])
            if ((marker.suffix == ".ready" or process_receipt.is_file()) and not result["diagnostics"]
                    and all(row["status"] in _SETTLED for row in result["observations"])):
                try:
                    marker.unlink(missing_ok=True)
                except OSError:
                    remaining += 1
                    diagnostics.append({"owner": name, "code": "observation_marker_unwritable"})
            else:
                remaining += 1
    return {"woken": woken, "processed": processed, "remaining": remaining, "diagnostics": diagnostics,
            "unconfirmed": unconfirmed}


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
    context = {}
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
            for key in ("RESEARCH_FEEDBACK_RUN_ID", "RESEARCH_FEEDBACK_ATTEMPT_ID"):
                if not env.get(key, "").strip():
                    env[key] = token
            context = {"owner": owner, "run_id": env["RESEARCH_FEEDBACK_RUN_ID"],
                       "attempt_id": env["RESEARCH_FEEDBACK_ATTEMPT_ID"], "step_id": "intake/" + token}
            _publish_marker(pending, context)
            marker = pending
            env["RESEARCH_FEEDBACK_OUT"] = str(marker.with_suffix(".jsonl"))
            env["RESEARCH_FEEDBACK_PROCESS_STEP_ID"] = context["step_id"]
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        # Feedback is optional for the native business command.
        pass

    os_error = {}
    try:
        code = subprocess.run(command, cwd=cwd, env=env, check=False).returncode
        failure = f"exit:{code}" if code else None
    except OSError as exc:
        code = 127
        failure = "launch:" + type(exc).__name__
        os_error = {name: value for name in ("errno", "winerror")
                    if (value := getattr(exc, name, None)) is not None}
    if marker is not None:
        with suppress(OSError):
            if failure is not None:
                _process_failure(marker, context, failure, os_error)
            marker.replace(marker.with_suffix(".ready"))
        with suppress(OSError):
            wake(settings, hosts_file, owner=owner, wait_seconds=wait_seconds)
    return code


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
