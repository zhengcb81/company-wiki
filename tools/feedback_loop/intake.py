"""Launch an ordinary owner command with a recoverable observation sidecar."""

from __future__ import annotations

import argparse
from hashlib import file_digest
import json
import logging
import os
from pathlib import Path
import re
import sqlite3
import subprocess
from uuid import uuid4

from .coordinator import settle
from .diagnostics import background_command, background_environment, format_diagnostic_exception, redact_text, run_background
from .host import process_host, read_hosts
from .local_host import LocalHost, host_path
from .observations import Batch, IDENTITY, decode_observation, digest, read_batch, unique_fields
from .process_history import ProcessHistory, implementation, utc_now

_logger = logging.getLogger(__name__)


_ROOT = Path(__file__).resolve().parents[2]
_MARKER = re.compile(r"feedback-[a-f0-9]{32}\.(?:pending|ready)")
_PACKET = re.compile(r"feedback-[a-f0-9]{32}\.jsonl")
_BUNDLE = "feedback-delivery-ready/1"
_SETTLED = {"expected", "external", "needs_evidence", "reconciled", "verified", "regressed"}
_TERMINAL = {"succeeded", "failed", "cancelled", "interrupted"}


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


def _process_failure(marker: Path | None, context: dict, token: str, actual: str, os_error: dict) -> dict | None:
    """Project the OS outcome unless the owner already covered this same process."""
    observations = read_batch([marker.with_suffix(".jsonl")]).observations.values() if marker is not None else ()
    # A sibling failure, even on the same owner, run and attempt, cannot
    # account for the exit of this particular process.
    if any(row["owner"] == row["origin_owner"] == context["owner"]
           and (row["run_id"], row["attempt_id"]) == (context["run_id"], context["attempt_id"])
           and row.get("parent_step_id") == context["step_id"] and row["step_id"] != context["step_id"]
           and row["check_id"] == "process-outcome" and row["actual"] == actual
           and (row["disposition"] == "deviation" or "refusal_code" in row)
           for row in observations):
        return None
    return {**context, "schema_version": "feedback-observation/1", "check_id": "process-outcome",
            "expected": "exit:0", "actual": actual, "disposition": "deviation",
            "evidence_ref": "intake-process/1/" + token, **os_error}


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


def _restore_history_marker(marker: Path, context: dict, history: ProcessHistory) -> None:
    entry = context.get("host_process")
    if entry is None:
        return
    keys = ("owner", "run_id", "attempt_id", "step_id")
    if (context.get("step_id") != "intake/" + marker.stem or not isinstance(entry, dict)
            or any(context[key] != entry[key] for key in keys)):
        raise ValueError("process marker identity mismatch")
    observation = context.get("host_observation")
    if observation is not None:
        if (not isinstance(observation, dict) or observation.get("check_id") != "process-outcome"
                or any(context[key] != observation[key] for key in keys)):
            raise ValueError("process marker observation mismatch")
    history.save(entry, observation)


def _file_version(path: Path) -> tuple[int, int]:
    stat = path.stat()
    return stat.st_size, stat.st_mtime_ns


def _bundle_details_present(path: Path, declared: int, references: set[str]) -> bool:
    try:
        with path.open("rb") as stream:
            ids = set()
            for line in stream:
                if not line.endswith(b"\n"):
                    return False
                item = json.loads(line, object_pairs_hook=unique_fields)
                key = item.get("details_id") if isinstance(item, dict) else None
                if not isinstance(key, str) or not key or key in ids:
                    return False
                ids.add(key)
    except (OSError, ValueError, RecursionError):
        return False
    return len(ids) == declared and references <= ids


def _matches_digest(path: Path, expected: str) -> bool:
    with path.open("rb") as stream:
        return file_digest(stream, "sha256").hexdigest() == expected


def _acknowledgeable(result: dict, *, bundle: bool) -> bool:
    if result["status"] in _SETTLED:
        return True
    # A final bundle can be delivered while a separate billing fact is unknown.
    # The coordinator only supplies this shape after a bound, read-only lookup.
    return (bundle and result["status"] == "unknown" and result.get("step") == "reconcile"
            and result.get("job_status") in _TERMINAL and result.get("cost_state") == "unknown"
            and bool(result.get("evidence_ref")))


def _record_unsettled(packet, outcomes, unsettled, *, bundle=False) -> bool:
    fields = ("occurrence_id", "status", "step", "job_status", "cost_state", "code")
    waiting = [{field: row[field] for field in fields if field in row}
               for row in outcomes if not _acknowledgeable(row, bundle=bundle)]
    if waiting:
        unsettled.append({"packet_id": packet.stem, "observations": waiting})
    return bool(waiting)


def _receive_process_history(history, owners, rpc, wait_seconds, seen, unsettled, diagnostics) -> tuple[int, int]:
    """Receive original OS results even when neither file inbox survived."""
    try:
        pending = history.observations(owners)
    except (OSError, sqlite3.Error, ValueError) as exc:
        diagnostics.append({"code": "process_history_unavailable", "error_type": type(exc).__name__})
        return 0, 0
    rows = {}
    steps = {}
    remaining = 0
    for step_id, raw in pending:
        try:
            row = decode_observation(raw)
        except (ValueError, RecursionError):
            diagnostics.append({"code": "unreadable_process_history_observation", "step_id": step_id})
            remaining += 1
            continue
        key = digest([row[field] for field in IDENTITY])
        steps[key] = step_id
        if key not in seen:
            rows[key] = row
    result = settle(Batch(rows, []), rpc, wait_seconds)
    diagnostics.extend(result["diagnostics"])
    settled = [seen[key] for key in steps.keys() & seen.keys() if _acknowledgeable(seen[key], bundle=False)]
    for outcome in [*result["observations"], *settled]:
        key = outcome["occurrence_id"]
        step_id = steps[key]
        if key not in seen and _record_unsettled(Path(step_id), [outcome], unsettled):
            remaining += 1
            continue
        try:
            history.delivered(step_id)
        except (OSError, sqlite3.Error) as exc:
            diagnostics.append({"code": "process_history_confirmation_failed", "step_id": step_id,
                                "error_type": type(exc).__name__})
            remaining += 1
    return len(result["observations"]), remaining


def _receive_native(packet, marker, context, owners, host, known, rpc, wait_seconds, unsettled):
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
    bundle = context.get("schema_version") == _BUNDLE
    details_version = None
    if bundle:
        if (context.get("observations") != len(batch.observations) or
                context.get("step_ids") != sorted({row["step_id"] for row in batch.observations.values()})):
            return 0, 1, [{"code": "native_observation_mismatch"}]
        details = packet.with_name(packet.name + ".details.jsonl")
        declared = context.get("details")
        references = {row["details_ref"] for row in batch.observations.values() if "details_ref" in row}
        if type(declared) is not int or declared < len(references):
            return 0, 1, [{"code": "native_observation_mismatch"}]
        if declared or "details_sha256" in context:
            try:
                details_version = _file_version(details)
            except OSError:
                return 0, 1, [{"code": "native_observation_details_missing"}]
            if not _bundle_details_present(details, declared, references):
                return 0, 1, [{"code": "native_observation_details_incomplete"}]
        if any(field in context and not _matches_digest(path, context[field])
               for path, field in ((packet, "observations_sha256"), (details, "details_sha256"))):
            return 0, 1, [{"code": "native_observation_checksum_mismatch"}]
    if "occurrence_id" in context and tuple(batch.observations) != (context["occurrence_id"],):
        return 0, 1, [{"code": "native_observation_mismatch"}]
    for row in batch.observations.values():
        producing_owners = {row["origin_owner"], row["owner"]}
        if (not owners.intersection(producing_owners)
                or ("owner" in context and context["owner"] not in producing_owners)
                or any(row[key] != context[key] for key in
                       ("origin_owner", "run_id", "attempt_id", "step_id", "check_id") if key in context)):
            return 0, 1, [{"code": "native_observation_mismatch"}]
    result = settle(batch, rpc, wait_seconds)
    count = len(result["observations"])
    waiting = _record_unsettled(packet, result["observations"], unsettled, bundle=bundle)
    if result["diagnostics"] or waiting:
        return count, 1, result["diagnostics"]
    if _file_version(packet) != version or (details_version is not None and _file_version(details) != details_version):
        return count, 1, [{"code": "native_observation_changed"}]
    host.confirm_native_delivery(packet, version)
    known[packet.name] = version
    if marker is not None:
        if bundle:
            try:
                marker.replace(marker.with_suffix(".ack"))
            except FileNotFoundError:
                if not marker.with_suffix(".ack").is_file():
                    raise
        else:
            marker.unlink(missing_ok=True)
    return count, 0, []


def drain(settings: Path, hosts_file: Path, *, owner: str | list[str] | None, wait_seconds: int) -> dict:
    """Resume host work and consume the original packets in the configured inboxes."""
    selected = {owner} if isinstance(owner, str) else set(owner) if owner else None
    registry = read_hosts(host_path(hosts_file))
    host = LocalHost(settings, recovery_owners=selected, host_registry=registry)
    history = ProcessHistory(host.database_path)
    rpc = process_host(registry, local=host)
    diagnostics = host.flush_observations(owners=selected)
    woken = len(host.recover(owners=selected))
    processed = remaining = 0
    unconfirmed = []
    unsettled = []
    seen_processes = {}
    directories: dict[Path, set[str]] = {}
    native_owners: dict[Path, set[str]] = {}
    supervised = set()
    for name, directory, native in _observation_dirs(settings, host.owners, selected):
        directory = host_path(directory)
        directories.setdefault(directory, set()).add(name)
        if native:
            native_owners.setdefault(directory, set()).add(name)
        else:
            supervised.add(directory)
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
            try:
                content = b"" if unmarked else marker.read_bytes()
                context = json.loads(content, object_pairs_hook=unique_fields) if content else {}
                if not isinstance(context, dict):
                    raise ValueError("invalid observation marker")
                if selected and context.get("owner") and context["owner"] not in selected:
                    continue
                if "host_process" in context:
                    if directory not in supervised or context.get("owner") not in host.owners:
                        raise ValueError("process recovery marker outside the host's route")
                    _restore_history_marker(marker, context, history)
            except FileNotFoundError:
                continue  # A concurrent reader completed the same marker.
            except (OSError, KeyError, ValueError, RecursionError, sqlite3.Error):
                remaining += 1
                diagnostics.append({"owner": name, "code": "unreadable_process_marker"})
                continue
            if unmarked or (marker.suffix == ".ready" and native):
                try:
                    supervisor_marker = directory in supervised and context.get("step_id") == "intake/" + marker.stem
                    direct = native and not supervisor_marker
                    if direct:
                        count, pending_count, issues = _receive_native(
                            sidecar, None if unmarked else marker, context, native, host, known, rpc,
                            wait_seconds, unsettled)
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
            closed = False
            if marker.suffix == ".pending" and not process_receipt.exists():
                try:
                    # Legacy empty markers do not identify the original run.
                    if context:
                        original = {key: context[key] for key in ("owner", "run_id", "attempt_id", "step_id")}
                        _restore_process_receipt(marker, original, process_receipt)
                        if marker.exists() and not process_receipt.exists():
                            if original["step_id"] == "intake/" + marker.stem:
                                try:
                                    closed = history.completed(original)
                                except (OSError, sqlite3.Error, ValueError) as exc:
                                    diagnostics.append({"owner": name, "code": "process_history_unavailable",
                                                        "error_type": type(exc).__name__})
                            if not closed:
                                unconfirmed.append(original)
                except FileNotFoundError:
                    pass  # Another reader or the supervisor has finished publishing.
                except (OSError, ValueError, TypeError, KeyError, RecursionError):
                    diagnostics.append({"owner": name, "code": "unreadable_process_marker"})
            sources = [path for path in (sidecar, process_receipt) if path.exists()]
            if not sources and marker.suffix == ".pending" and not closed:
                remaining += 1
                continue
            # A completed business command need not have any observations.
            batch = read_batch(sources)
            result = settle(batch, rpc, wait_seconds)
            if process_receipt in sources:
                for outcome in result["observations"]:
                    key = outcome["occurrence_id"]
                    if batch.observations[key]["check_id"] == "process-outcome":
                        seen_processes[key] = outcome
            processed += len(result["observations"])
            diagnostics.extend({"owner": name, **row} for row in result["diagnostics"])
            waiting = _record_unsettled(sidecar, result["observations"], unsettled)
            if ((marker.suffix == ".ready" or process_receipt.is_file() or closed) and not result["diagnostics"]
                    and not waiting):
                try:
                    marker.unlink(missing_ok=True)
                except OSError:
                    remaining += 1
                    diagnostics.append({"owner": name, "code": "observation_marker_unwritable"})
            else:
                remaining += 1
    owners = set(host.owners) if selected is None else set(host.owners) & selected
    count, pending = _receive_process_history(
        history, owners, rpc, wait_seconds, seen_processes, unsettled, diagnostics,
    )
    processed += count
    remaining += pending
    return {"woken": woken, "processed": processed, "remaining": remaining, "diagnostics": diagnostics,
            "unconfirmed": unconfirmed, "unsettled": unsettled}


def wake(settings: Path, hosts_file: Path, *, owner: str | None = None, owners: list[str] | None = None,
         wait_seconds: int = 0):
    scope = [arg for name in (owners or ([owner] if owner else [])) for arg in ("--owner", name)]
    subprocess.Popen(
        background_command("tools.feedback_loop.intake", "--settings", str(settings),
                           "--hosts", str(hosts_file), "--wait-seconds", str(wait_seconds), "drain", *scope),
        cwd=_ROOT, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        env=background_environment(settings.resolve().parent / "logs" / "intake_drain_stderr.log"),
        start_new_session=os.name != "nt", creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )


def _process_message(entry: dict) -> str:
    return json.dumps({key: redact_text(value) if isinstance(value, str) else value
                       for key, value in entry.items() if key in {
        "owner", "run_id", "attempt_id", "step_id", "status", "exit_code", "error_type",
    }}, ensure_ascii=True)


def _save_history(history: ProcessHistory, entry: dict, pending: dict | None = None) -> bool:
    try:
        history.save(entry, pending)
    except (OSError, sqlite3.Error, UnicodeError) as exc:
        _logger.warning("Feedback process history unavailable (%s) %s",
                        type(exc).__name__, _process_message(entry))
        return False
    return True


def _capture_path(directories: tuple[Path, ...], token: str, context: dict) -> Path | None:
    for candidate in dict.fromkeys(directories):
        try:
            candidate.mkdir(parents=True, exist_ok=True)
            pending = candidate / (token + ".pending")
            _publish_marker(pending, context)
            return pending
        except OSError:
            continue
    return None


def _publish_outcome(marker: Path, observation: dict | None, recovery: dict | None) -> None:
    if recovery is not None:
        _publish_marker(marker, recovery)
    if observation is not None:
        # The native producer owns .jsonl. Keep its streams and outcome separate.
        _publish_marker(marker.with_suffix(".process"), observation)
    marker.replace(marker.with_suffix(".ready"))


def _finish_capture(marker: Path, settings: Path, token: str, context: dict, observation: dict | None,
                    recovery: dict | None) -> bool:
    try:
        _publish_outcome(marker, observation, recovery)
        return True
    except OSError:
        # The original occurrence has the same identity in the backup inbox.
        if observation is None and recovery is None:
            return False
        backup_dir = _recovery_dir(settings)
        if backup_dir == marker.parent:
            return False
        backup = _capture_path((backup_dir,), token, recovery if recovery is not None else context)
        if backup is None:
            return False
        try:
            _publish_outcome(backup, observation, None)
            return True
        except OSError:
            return False


def run_observed(settings: Path, hosts_file: Path, owner: str, command: list[str], wait_seconds: int) -> int:
    """The command and standard streams belong to the original business caller."""
    cwd, directory, history = None, None, None
    configured_owner = False
    env = os.environ.copy()
    try:
        config = read_hosts(settings)
        route = config["owners"][owner]
        configured_owner = True
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
        history = ProcessHistory(settings.parent / config["state"])
    except (OSError, ValueError, TypeError, KeyError, AttributeError) as exc:
        _logger.warning("Feedback observation capture setup failed for owner=%s\n%s",
                        redact_text(owner), format_diagnostic_exception(exc))

    token = "feedback-" + uuid4().hex
    for key in ("RESEARCH_FEEDBACK_RUN_ID", "RESEARCH_FEEDBACK_ATTEMPT_ID"):
        if not env.get(key, "").strip():
            env[key] = token
    context = {"owner": owner, "run_id": env["RESEARCH_FEEDBACK_RUN_ID"],
               "attempt_id": env["RESEARCH_FEEDBACK_ATTEMPT_ID"], "step_id": "intake/" + token}
    entry = {**context, "status": "unconfirmed", "started_at": utc_now(), "implementation": implementation()}
    env["RESEARCH_FEEDBACK_PROCESS_STEP_ID"] = context["step_id"]
    saved_start = history is not None and _save_history(history, entry)
    marker_context = context if saved_start else {**context, "host_process": entry}
    recovery_dir = _recovery_dir(settings)
    if directory is not None:
        marker = _capture_path((directory, recovery_dir), token, marker_context)
    elif configured_owner and not saved_start:
        marker = _capture_path((recovery_dir,), token, marker_context)
    else:
        marker = None
    if marker is not None and directory is not None:
        env["RESEARCH_FEEDBACK_OUT"] = str(marker.with_suffix(".jsonl"))
    elif marker is None and (directory is not None or not saved_start):
        _logger.warning("Feedback capture inboxes unavailable before launch %s", _process_message(entry))

    os_error = {}
    try:
        code = subprocess.run(command, cwd=cwd, env=env, check=False).returncode
        failure = f"exit:{code}" if code else None
        entry.update(status="exited")
    except OSError as exc:
        code = 127
        failure = "launch:" + type(exc).__name__
        os_error = {name: value for name in ("errno", "winerror")
                    if (value := getattr(exc, name, None)) is not None}
        entry.update(status="launch_failed", error_type=type(exc).__name__, **os_error)
    entry.update(exit_code=code, finished_at=utc_now())
    observation = _process_failure(marker, context, token, failure, os_error) if failure is not None else None
    saved = history is not None and _save_history(history, entry, observation)
    recovery = None if saved else {**context, "host_process": entry, "host_observation": observation}
    if recovery is not None and marker is None and configured_owner:
        marker = _capture_path((recovery_dir,), token, recovery)
    if marker is not None:
        published = _finish_capture(marker, settings, token, context, observation, recovery)
        if not published:
            _logger.warning("Feedback capture outcome publication incomplete %s", _process_message(entry))
    elif directory is not None or not saved:
        _logger.warning("Feedback capture inboxes unavailable after process %s", _process_message(entry))
    if (marker is not None and directory is not None) or (saved and observation is not None):
        try:
            wake(settings, hosts_file, owner=owner, wait_seconds=wait_seconds)
        except OSError as exc:
            _logger.warning("Feedback wake failed (%s) %s", type(exc).__name__, _process_message(entry))
    return code


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--settings", required=True, type=Path)
    parser.add_argument("--hosts", type=Path)
    parser.add_argument("--wait-seconds", default=15, type=int)
    modes = parser.add_subparsers(dest="mode", required=True)
    run = modes.add_parser("run", help="run an existing business command and wake feedback")
    run.add_argument("--owner", required=True)
    run.add_argument("command", nargs=argparse.REMAINDER)
    history = modes.add_parser("history", help="read the host's original process outcome")
    history.add_argument("--run-id", required=True)
    history.add_argument("--attempt-id")
    history.add_argument("--owner")
    modes.add_parser("drain", help="resume the configured observation inboxes").add_argument("--owner", action="append")
    args = parser.parse_args(argv)
    settings = args.settings.resolve()
    if args.mode != "history" and args.hosts is None:
        parser.error("--hosts is required for run and drain")
    hosts_file = args.hosts.resolve() if args.hosts is not None else None
    if args.wait_seconds < 0:
        parser.error("--wait-seconds must be nonnegative")
    if args.mode == "run":
        command = args.command[1:] if args.command and args.command[0] == "--" else args.command
        if not command:
            parser.error("run requires the original command")
        return run_observed(settings, hosts_file, args.owner, command, args.wait_seconds)
    if args.mode == "history":
        try:
            database = settings.parent / read_hosts(settings)["state"]
            processes = ProcessHistory(database).read(args.run_id, owner=args.owner, attempt_id=args.attempt_id)
            summary = {"status": "found" if processes else "absent", "processes": processes}
        except (OSError, sqlite3.Error, ValueError, TypeError, KeyError) as exc:
            summary = {"status": "unavailable", "processes": [], "error_type": type(exc).__name__}
    else:
        summary = drain(settings, hosts_file, owner=args.owner, wait_seconds=args.wait_seconds)
    print(json.dumps(summary, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(run_background(main))
