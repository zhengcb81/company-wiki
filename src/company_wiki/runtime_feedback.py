"""Durable company-wiki failure observations at the public operation boundary."""
from __future__ import annotations

import argparse
from collections.abc import Callable, Mapping
from contextlib import nullcontext
from contextvars import ContextVar
from dataclasses import dataclass, field
from functools import wraps
import json
import logging
import os
from pathlib import Path
import sys
from tempfile import NamedTemporaryFile
from typing import Any, NoReturn, ParamSpec
from uuid import uuid4

from . import runtime_journal
from .diagnostic_logging import append_diagnostic, diagnostic_log, log_exception
from .diagnostic_redaction import format_diagnostic_exception, redact_text
from .file_mutex import FileMutexLockedError, os_file_mutex, win32_filesystem_path
from .runtime_feedback_values import (
    OWNER as _OWNER,
    encode_observation as _encoded,
    freeze_worker_failure as _freeze_worker_failure,
    logical_observation_ref,
    observation_stem as _stem,
    observation_token as _token,
    prepare_observation as _prepare_observation,
)

_logger = logging.getLogger(__name__)


__all__ = [
    "ArgumentParser", "checkpoint", "document_results", "entry", "freeze_worker_failure",
    "publish_worker_failure", "record", "record_optional_failure", "refusal", "retain_local_text", "run_cli",
    "runtime_identity", "trace_reference",
]


_P = ParamSpec("_P")
_FAILED = {"failed", "error", "dead_letter", "blocked", "unavailable", "uncertain",
           "budget_exhausted", "storage_exhausted", "refused", "retry_wait", "interrupted"}


@dataclass
class _Invocation:
    operation: str
    run: str
    attempt: str
    source_file: str
    log_scope: object = field(default_factory=object)
    local_only: bool = False
    started: bool = False
    trace_available: bool = True
    recoverable_failure: bool = False
    local_log_lost: bool = False
    explained: bool = False
    reported_errors: list[BaseException] = field(default_factory=list)


_current: ContextVar[_Invocation | None] = ContextVar("cwp_feedback_invocation", default=None)


def _directory() -> Path:
    return runtime_journal.default_state_root() / "observations"


def runtime_identity() -> tuple[str, str]:
    """Keep an enclosing or injected identity, otherwise allocate a local one."""
    if caller := _current.get():
        return caller.run, caller.attempt
    run = os.getenv("RESEARCH_FEEDBACK_RUN_ID") or uuid4().hex
    return run, os.getenv("RESEARCH_FEEDBACK_ATTEMPT_ID") or run


def trace_reference() -> dict[str, str] | None:
    if caller := _current.get():
        return {"run_id": logical_observation_ref(caller.run),
                "attempt_id": logical_observation_ref(caller.attempt),
                "status": "available" if caller.trace_available and not caller.local_log_lost else "degraded"}
    return None


def _invocation_trace(caller: _Invocation, step: str, status: str, **details: Any) -> None:
    written = runtime_journal.write_event(
        caller.operation, caller.run, caller.attempt, step, status, source_file=caller.source_file, **details,
    )
    caller.trace_available = caller.trace_available and written


def _start_invocation(caller: _Invocation) -> None:
    if not caller.started:
        caller.started = True
        _invocation_trace(caller, "invocation", "started")


def checkpoint(
    step: str, *, input_path: Path | None = None, source_id: str | None = None,
    related_run_id: str | None = None,
) -> None:
    """Record a named operation boundary without inspecting caller arguments."""
    if caller := _current.get():
        _start_invocation(caller)
        _invocation_trace(
            caller, step, "started", source_id=source_id, related_run_id=related_run_id,
            input_ref=runtime_journal.input_reference(input_path) if input_path is not None else None,
        )


def _local_log_paths() -> tuple[Path, ...]:
    return runtime_journal.diagnostic_paths("runtime_errors.log")


def retain_local_text(text: str) -> bool:
    """Reuse every configured owner log destination in order."""
    for path in _local_log_paths():
        try:
            if append_diagnostic(path, text, warn_on_stderr=False):
                return True
        except (OSError, ValueError):
            continue
    return False


def _atomic(path: Path, data: bytes) -> None:
    path = win32_filesystem_path(path)
    with NamedTemporaryFile(dir=path.parent, delete=False) as file:
        temporary = Path(file.name)
        try:
            file.write(data)
            file.flush()
            os.fsync(file.fileno())
        except BaseException:
            file.close()
            temporary.unlink(missing_ok=True)
            raise
    try:
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def freeze_worker_failure(
    job_id: str, attempt_id: str, status: str, reason: str, *,
    message: str = "", error: BaseException | None = None,
) -> str:
    """Freeze the original, redacted diagnostic before AUTO commits the attempt."""
    try:
        return _freeze_worker_failure(
            job_id, attempt_id, status, reason, message=message, error=error,
        )
    except Exception as exc:
        log_exception(_logger, logging.WARNING, "runtime_feedback could not capture worker cause", exc)
        return _freeze_worker_failure(job_id, attempt_id, status, reason)


def _feedback_folders() -> tuple[Path, ...]:
    override = os.getenv("RESEARCH_FEEDBACK_DIR")
    folders = [Path(override)] if override else []
    try:
        folders.append(_directory())
    except (OSError, RuntimeError, ValueError):
        pass
    return tuple(dict.fromkeys(win32_filesystem_path(folder) for folder in folders))


def _read_if_present(path: Path) -> bytes | None:
    try:
        return path.read_bytes()
    except FileNotFoundError:
        return None


def publish_worker_failure(payload: str, *, job_id: str, attempt_id: str) -> bool:
    """Publish one frozen AUTO observation without updating existing packet bytes."""
    try:
        packet = json.loads(payload)
        row, details = packet["row"], packet["details"]
        context = {"owner": _OWNER, "run_id": logical_observation_ref(job_id),
                   "attempt_id": logical_observation_ref(attempt_id), "step_id": "worker"}
        if any(row[key] != value for key, value in context.items()):
            raise ValueError("worker observation does not match the original job and attempt")
        stem = _stem(context["run_id"], context["attempt_id"], context["step_id"], row["actual"])
        details_name = stem + ".diagnostic.json"
        if row["details_ref"] != details_name or any(details[key] != value for key, value in context.items()):
            raise ValueError("worker observation details do not match the row")
        row_data, details_data = _encoded(row), _encoded(details)
    except (TypeError, ValueError, KeyError) as exc:
        log_exception(_logger, logging.WARNING, "runtime_feedback invalid pending worker observation", exc)
        return False

    # Prefer existing durable bytes, including a prior fallback publication.
    # A supervised append sidecar is not an acknowledgment of an AUTO outcome.
    folders = _feedback_folders()
    try:
        folders = tuple(sorted(folders, key=lambda folder: not (folder / (stem + ".jsonl")).is_file()))
    except OSError:
        pass
    last_error: Exception | None = None
    for folder in folders:
        try:
            folder.mkdir(parents=True, exist_ok=True)
            with os_file_mutex(folder / ".worker-observation.lock", timeout_seconds=0.2):
                data_path = folder / (stem + ".jsonl")
                details_path = folder / details_name
                existing_row = _read_if_present(data_path)
                existing_details = _read_if_present(details_path)
                if existing_details is not None and existing_details != details_data:
                    _logger.warning("runtime_feedback worker diagnostic differs from its frozen payload")
                    return False
                if existing_row is not None:
                    if existing_row == row_data and existing_details == details_data:
                        # F4 accepts the exact atomically written unmarked file
                        # if an earlier process died or already consumed .ready.
                        return True
                    _logger.warning("runtime_feedback worker observation packet differs from its frozen payload")
                    return False
                if existing_details is None:
                    _atomic(details_path, details_data)
                _atomic(data_path, row_data)
                try:
                    _atomic(folder / (stem + ".ready"), _encoded(context))
                except OSError as exc:
                    log_exception(_logger, logging.WARNING, "runtime_feedback worker observation marker pending", exc)
                    return False
                return True
        except FileMutexLockedError:
            return False
        except OSError as exc:
            last_error = exc
    _logger.warning("runtime_feedback worker observation remains pending\n%s",
                    format_diagnostic_exception(last_error) if last_error else "")
    return False


def record(operation: str, status: str, *, reason: str = "", error: BaseException | None = None,
           run: str = "", attempt: str = "", item: str = "", source_id: str = "",
           expected: bool = False, message: str = "", include_error_messages: bool = True,
           explains_invocation: bool = True, publish_issue: bool = True) -> None:
    """Keep native diagnostic facts. Omit messages at boundaries carrying opaque inputs."""
    caller = _current.get()
    try:
        run = run or (caller.run if caller else "") or os.getenv("RESEARCH_FEEDBACK_RUN_ID") or uuid4().hex
        attempt = attempt or (caller.attempt if caller else "") or os.getenv("RESEARCH_FEEDBACK_ATTEMPT_ID") or run
        stem, context, row, details = _prepare_observation(
            operation, status, run=run, attempt=attempt, reason=reason, error=error,
            item=item, source_id=source_id, expected=expected, message=message,
            include_error_messages=include_error_messages,
        )
        if caller is not None:
            _start_invocation(caller)
            caller.explained = caller.explained or explains_invocation
            if error is not None:
                caller.reported_errors.append(error)

        if error is not None or status in _FAILED or status.startswith("exit:"):
            failure = f"operation outcome {row['actual']} {json.dumps(details, ensure_ascii=True)}"
            retained = retain_local_text(failure)
            if caller is not None:
                caller.recoverable_failure |= retained
                caller.local_log_lost |= not retained
                _invocation_trace(
                    caller, "failure", status, related_run_id=run if caller.run != run else None,
                    details_ref=row["details_ref"], source_id=source_id,
                )
            else:
                runtime_journal.write_event(
                    operation, run, attempt, "failure", status, source_file=__file__,
                    details_ref=row["details_ref"], source_id=source_id,
                )
        details_name = row["details_ref"]

        def recorded() -> None:
            if caller is not None:
                caller.recoverable_failure = True

        explicit = os.getenv("RESEARCH_FEEDBACK_OUT")
        local_only = not publish_issue or (caller is not None and caller.local_only)
        if explicit and not local_only:
            sidecar = win32_filesystem_path(Path(explicit))
            try:
                sidecar.parent.mkdir(parents=True, exist_ok=True)
                with os_file_mutex(sidecar.with_suffix(sidecar.suffix + ".lock"), timeout_seconds=0.25):
                    _atomic(sidecar.parent / details_name, _encoded(details))
                    with sidecar.open("a+b") as stream:
                        needs_separator = False
                        if stream.seek(0, os.SEEK_END):
                            stream.seek(-1, os.SEEK_END)
                            needs_separator = stream.read(1) != b"\n"
                        stream.write((b"\n" if needs_separator else b"") + _encoded(row))
                        stream.flush()
                        os.fsync(stream.fileno())
            except (OSError, FileMutexLockedError):
                # The owner observations directory is the existing fallback.
                pass
            else:
                recorded()
                return
        last_error: OSError | None = None
        folders = _feedback_folders()
        if local_only and explicit:
            folders = (win32_filesystem_path(Path(explicit).parent), *folders)
        for folder in dict.fromkeys(folders):
            try:
                folder.mkdir(parents=True, exist_ok=True)
                _atomic(folder / details_name, _encoded(details))
                if not local_only:
                    _atomic(folder / (stem + ".jsonl"), _encoded(row))
                    _atomic(folder / (stem + ".ready"), _encoded(context))
            except OSError as exc:
                last_error = exc
                continue
            recorded()
            break
        else:
            if caller is not None:
                caller.trace_available = False
            else:
                _logger.warning("runtime_feedback failed to persist observation across all fallback directories\n%s",
                                format_diagnostic_exception(last_error) if last_error else "")
    except Exception as exc:
        # The source catalog and worker retain their own authoritative result.
        if caller is not None:
            caller.trace_available = False
        else:
            log_exception(_logger, logging.WARNING, "runtime_feedback unexpected persistence failure", exc)


def record_optional_failure(reason: str, error: BaseException) -> None:
    """Preserve why an optional operation degraded without generating work or changing its result."""
    if caller := _current.get():
        record(caller.operation, "unavailable", reason=reason, item=reason, error=error,
               include_error_messages=False, explains_invocation=False, publish_issue=False)


def _owns_local_log(scope: object) -> bool:
    active = _current.get()
    return active is not None and active.log_scope is scope


def _note_local_log_loss() -> None:
    if caller := _current.get():
        caller.local_log_lost = True
        _start_invocation(caller)
        _invocation_trace(caller, "local-diagnostic", "unavailable")


def _warn_if_unrecoverable(context: _Invocation) -> None:
    trace_unavailable = not context.trace_available and not context.recoverable_failure
    if sys.stderr is None or not (context.local_log_lost or trace_unavailable):
        return
    try:
        print("company-wiki diagnostic could not be retained", file=sys.stderr)
    except (OSError, ValueError):
        # A closed diagnostic stream does not replace the authoritative result.
        return


def run_cli(main: Callable[[], int], *, machine_stderr: bool = False) -> int:
    """Render unhandled terminal failures without exposing native exception text on the wire."""
    try:
        return main()
    except Exception as exc:
        if not machine_stderr and sys.stderr is not None:
            try:
                print(format_diagnostic_exception(exc), file=sys.stderr)
            except (OSError, ValueError):
                # Diagnostic output cannot replace the process failure.
                pass
        return 1


class ArgumentParser(argparse.ArgumentParser):
    """Keep argparse's exit and message shape, with an owned redacted cause."""

    def error(self, message: str) -> NoReturn:
        safe = redact_text(message)
        if caller := _current.get():
            record(caller.operation, "blocked", reason="invalid_arguments",
                   error=sys.exc_info()[1], message=safe, include_error_messages=False)
        super().error(safe)


def entry(
    operation: str, *, machine_stderr: bool = False, local_only: bool = False,
    quiet_success: bool = False,
) -> Callable[[Callable[_P, int]], Callable[_P, int]]:
    """Bind a run before CLI parsing, while preserving byte streams and exit semantics."""
    def decorate(main: Callable[_P, int]) -> Callable[_P, int]:
        @wraps(main)
        def invoke(*args: _P.args, **kwargs: _P.kwargs) -> int:
            argv = args[0] if args else kwargs.get("argv")
            if argv is None:
                argv = sys.argv[1:]
            help_requested = isinstance(argv, (list, tuple)) and any(
                value in {"--help", "-h"} for value in argv
            )
            parent = _current.get()
            run, attempt = runtime_identity()
            context = _Invocation(
                operation, run, attempt, main.__code__.co_filename,
                log_scope=parent.log_scope if parent else object(),
                local_only=local_only or bool(parent and parent.local_only),
                reported_errors=parent.reported_errors if parent else [],
            )
            token = _current.set(context)
            try:
                if not quiet_success and not help_requested:
                    _start_invocation(context)
                log_scope = (
                    diagnostic_log(
                        logging.getLogger("company_wiki"), _local_log_paths,
                        in_scope=lambda: _owns_local_log(context.log_scope),
                        on_loss=_note_local_log_loss,
                    ) if parent is None else nullcontext()
                )
                with log_scope:
                    try:
                        result = main(*args, **kwargs)
                        if result and not context.explained:
                            record(operation, f"exit:{result}")
                        if context.started:
                            _invocation_trace(context, "invocation", "failed" if result else "completed",
                                              exit_code=result)
                        return result
                    except (Exception, SystemExit, KeyboardInterrupt) as exc:
                        already_recorded = any(exc is previous for previous in context.reported_errors)
                        if not already_recorded and (not isinstance(exc, SystemExit) or
                                                     (not context.explained and exc.code not in (0, None))):
                            record(operation, "interrupted" if isinstance(exc, KeyboardInterrupt) else "failed",
                                   error=exc)
                        exit_code = exc.code if isinstance(exc, SystemExit) and isinstance(exc.code, int) else 1
                        status = "interrupted" if isinstance(exc, KeyboardInterrupt) else "failed"
                        if context.started:
                            _invocation_trace(context, "invocation", "completed" if exit_code == 0 else status,
                                              exit_code=exit_code)
                        raise
            finally:
                if parent is not None:
                    parent.explained |= context.explained
                    parent.trace_available &= context.trace_available
                    parent.recoverable_failure |= context.recoverable_failure
                    parent.local_log_lost |= context.local_log_lost
                elif not machine_stderr:
                    _warn_if_unrecoverable(context)
                _current.reset(token)
        return invoke
    return decorate


def document_results(
    operation: str, payload: Mapping[str, Any], *, error: BaseException | None = None,
) -> None:
    """Read each native result including failures inside a successful request."""
    status = payload.get("status")
    run = _token(payload.get("run_id")) or _token(payload.get("request_id"))
    attempt = _token(payload.get("attempt_id"))
    if isinstance(status, str) and status in _FAILED:
        record(operation, status, run=run, attempt=attempt, reason=payload.get("reason") or payload.get("error") or "",
               error=error if error is not None else sys.exc_info()[1])
    members = payload.get("items", payload.get("documents", payload.get("statements")))
    if not isinstance(members, (list, tuple)):
        return
    for member in members:
        if not isinstance(member, dict):
            continue
        state = member.get("state") or member.get("status")
        if not isinstance(state, str) or state not in _FAILED:
            continue
        ref = member.get("source_ref") or {}
        source = _token(ref.get("source_id")) if isinstance(ref, dict) else ""
        item = (member.get("item_key") or source or member.get("document_id")
                or member.get("candidate_id") or member.get("statement_type") or "")
        reasons = member.get("reason_codes") or member.get("errors")
        if not isinstance(reasons, (list, tuple)):
            reasons = []
        reason = _token(member.get("error_code")) or next((code for code in reasons if _token(code)), "")
        record(operation, state, run=run, attempt=_token(member.get("attempt_id")) or attempt,
               item=str(item), source_id=source, error=error, reason=reason)


def refusal(status: str, reason: str) -> None:
    """Trace a machine refusal at the original exception boundary, without raw inputs."""
    if caller := _current.get():
        record(caller.operation, status, reason=reason, error=sys.exc_info()[1], include_error_messages=False)
