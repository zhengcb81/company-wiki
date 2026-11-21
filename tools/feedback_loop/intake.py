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
from .local_host import LocalHost, host_path
from .observations import read_batch


_ROOT = Path(__file__).resolve().parents[2]
_MARKER = re.compile(r"feedback-[a-f0-9]{32}\.(?:pending|ready)")
_PACKET = re.compile(r"feedback-[a-f0-9]{32}\.jsonl")
_SETTLED = {"expected", "external", "needs_evidence", "reconciled", "verified", "regressed"}


def _recovery_dir(settings: Path) -> Path:
    return settings.parent / ".intake-recovery"


def _observation_dirs(settings: Path, owners: dict, selected: set[str] | None):
    for owner, route in owners.items():
        if selected is not None and owner not in selected:
            continue
        target = route.get("observation_dir")
        if isinstance(target, str) and target:
            yield owner, settings.parent / target, False
        native = route.get("native_observation_dirs", [])
        if not isinstance(native, list):
            raise ValueError(f"invalid native_observation_dirs for {owner}")
        for path in native:
            if not isinstance(path, str) or not path.strip():
                raise ValueError(f"invalid native observation path for {owner}")
            yield owner, settings.parent / path, True
    yield min(selected) if selected else "company-wiki", _recovery_dir(settings), False


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


def _file_version(path: Path) -> tuple[int, int]:
    stat = path.stat()
    return stat.st_size, stat.st_mtime_ns


def _receive_native(packet, marker, context, owners, host, known, rpc, wait_seconds):
    """Finish a directly published occurrence, including death between its two atomic writes."""
    try:
        version = _file_version(packet)
        if marker is None and known.get(packet.name) == version:
            return 0, 0, []
        with packet.open("rb") as stream:
            if not version[0]:
                return 0, 1, [{"code": "native_observation_missing"}]
            stream.seek(-1, os.SEEK_END)
            if stream.read(1) != b"\n":
                return 0, 1, [{"code": "native_observation_incomplete"}]
    except FileNotFoundError:
        return 0, int(marker is not None), [{"code": "native_observation_missing"}] if marker is not None else []
    batch = read_batch([packet])
    if batch.diagnostics or not batch.observations:
        return 0, 1, batch.diagnostics or [{"code": "native_observation_missing"}]
    for row in batch.observations.values():
        producing_owners = {row["origin_owner"], row["owner"]}
        if (not owners.intersection(producing_owners)
                or ("owner" in context and context["owner"] not in producing_owners)
                or any(row[key] != context[key] for key in ("run_id", "attempt_id", "step_id") if key in context)):
            return 0, 1, [{"code": "native_observation_mismatch"}]
    result = settle(batch, rpc, wait_seconds)
    count = len(result["observations"])
    if result["diagnostics"] or any(r["status"] not in _SETTLED for r in result["observations"]):
        return count, 1, result["diagnostics"]
    if _file_version(packet) != version:
        return count, 1, [{"code": "native_observation_changed"}]
    host.confirm_native_delivery(packet, version)
    known[packet.name] = version
    if marker is not None:
        marker.unlink(missing_ok=True)
    return count, 0, []


def drain(settings: Path, hosts_file: Path, *, owner: str | list[str] | None, wait_seconds: int) -> dict:
    """Resume host work and consume the original packets in the configured inboxes."""
    host = LocalHost(settings)
    rpc = process_host(read_hosts(host_path(hosts_file)), local=host)
    woken = len(host.recover())
    processed = remaining = 0
    diagnostics = []
    unconfirmed = []
    selected = {owner} if isinstance(owner, str) else set(owner) if owner else None
    directories: dict[Path, set[str]] = {}
    native_owners: dict[Path, set[str]] = {}
    for name, directory, native in _observation_dirs(settings, host.owners, selected):
        directory = host_path(directory)
        directories.setdefault(directory, set()).add(name)
        if native:
            native_owners.setdefault(directory, set()).add(name)
    for directory, names in directories.items():
        name = sorted(names)[0]
        native = native_owners.get(directory, set())
        try:
            markers = sorted(directory.iterdir())
        except FileNotFoundError:
            continue
        except OSError:
            diagnostics.append({"owner": name, "code": "observation_inbox_unreadable"})
            continue
        known = host.native_deliveries(directory) if native and markers else {}
        for marker in markers:
            unmarked = native and _PACKET.fullmatch(marker.name)
            if unmarked:
                if any(marker.with_suffix(ext).exists() for ext in (".pending", ".ready", ".process")):
                    continue
            elif not _MARKER.fullmatch(marker.name) or not marker.is_file():
                continue
            sidecar = marker.with_suffix(".jsonl")
            process_receipt = marker.with_suffix(".process")
            if unmarked or (marker.suffix == ".ready" and (native or selected)):
                try:
                    content = b"" if unmarked else marker.read_bytes()
                    context = json.loads(content) if content else {}
                    if not isinstance(context, dict):
                        raise ValueError("invalid observation marker")
                    if selected and context.get("owner") and context["owner"] not in selected:
                        continue
                    direct = native and not str(context.get("step_id", "")).startswith("intake/")
                    if direct:
                        count, pending_count, issues = _receive_native(
                            sidecar, None if unmarked else marker, context, native, host, known, rpc, wait_seconds)
                        processed += count
                        remaining += pending_count
                        diagnostics.extend({"owner": name, **row} for row in issues)
                        continue
                except FileNotFoundError:
                    continue  # A concurrent reader completed the same marker.
                except (OSError, ValueError, RecursionError):
                    remaining += 1
                    diagnostics.append({"owner": name, "code": "unreadable_process_marker"})
                    continue
            if marker.suffix == ".pending" and selected:
                try:
                    original_marker = marker.read_bytes()
                    marker_owner = json.loads(original_marker).get("owner") if original_marker else None
                    if marker_owner and marker_owner not in selected:
                        continue
                except FileNotFoundError:
                    continue
                except (AttributeError, OSError, ValueError, RecursionError):
                    remaining += 1
                    diagnostics.append({"owner": name, "code": "unreadable_process_marker"})
                    continue
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
        target = route.get("observation_dir")
        if isinstance(target, str) and target:
            directory = settings.parent / target
            token = "feedback-" + uuid4().hex
            for key in ("RESEARCH_FEEDBACK_RUN_ID", "RESEARCH_FEEDBACK_ATTEMPT_ID"):
                if not env.get(key, "").strip():
                    env[key] = token
            context = {"owner": owner, "run_id": env["RESEARCH_FEEDBACK_RUN_ID"],
                       "attempt_id": env["RESEARCH_FEEDBACK_ATTEMPT_ID"], "step_id": "intake/" + token}
            # Both locations use the same occurrence identity. An outage of
            # one owner inbox must not erase the original process outcome.
            for candidate in (directory, _recovery_dir(settings)):
                try:
                    candidate.mkdir(parents=True, exist_ok=True)
                    pending = candidate / (token + ".pending")
                    _publish_marker(pending, context)
                except OSError:
                    continue
                marker = pending
                break
        if marker is not None:
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
        try:
            if failure is not None:
                _process_failure(marker, context, failure, os_error)
            marker.replace(marker.with_suffix(".ready"))
        except OSError:
            # A writable Inbox can disappear while the child is running.
            # Persist the observed exit in the host-owned directory using the
            # original token. A later reader reconciles the same occurrence.
            if failure is not None:
                with suppress(OSError):
                    backup = _recovery_dir(settings) / marker.name
                    backup.parent.mkdir(parents=True, exist_ok=True)
                    if backup != marker:
                        _publish_marker(backup, context)
                        _process_failure(backup, context, failure, os_error)
                        backup.replace(backup.with_suffix(".ready"))
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
