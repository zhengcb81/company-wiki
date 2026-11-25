"""Durable company-wiki failure observations at the public operation boundary."""
from __future__ import annotations

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
from typing import Any, ParamSpec
from uuid import uuid4

from .diagnostic_logging import append_diagnostic, diagnostic_log
from .diagnostic_redaction import format_diagnostic_exception
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


__all__ = ["document_results", "entry", "freeze_worker_failure", "publish_worker_failure", "record"]


_P = ParamSpec("_P")
_FAILED = {"failed", "error", "dead_letter", "blocked", "unavailable", "uncertain",
           "budget_exhausted", "storage_exhausted", "refused", "retry_wait", "interrupted"}


@dataclass
class _Invocation:
    operation: str
    run: str
    attempt: str
    log_path: Path | None = None
    explained: bool = False
    reported_errors: list[BaseException] = field(default_factory=list)


_current: ContextVar[_Invocation | None] = ContextVar("cwp_feedback_invocation", default=None)


def _directory() -> Path:
    state = os.getenv("LOCALAPPDATA") if os.name == "nt" else os.getenv("XDG_STATE_HOME")
    return (Path(state) if state else Path.home() / ".local" / "state") / _OWNER / "observations"


def _local_log_path() -> Path | None:
    explicit = os.getenv("RESEARCH_FEEDBACK_OUT") or os.getenv("RESEARCH_FEEDBACK_DIR")
    try:
        state = Path(explicit).parent if explicit else _directory().parent
    except (OSError, RuntimeError, ValueError):
        return None
    return state / "logs/runtime_errors.log"


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
        _logger.warning("runtime_feedback could not capture worker cause\n%s",
                        format_diagnostic_exception(exc))
        return _freeze_worker_failure(job_id, attempt_id, status, reason)


def _feedback_folders() -> tuple[Path, ...]:
    override = os.getenv("RESEARCH_FEEDBACK_DIR")
    folders = (Path(override), _directory()) if override else (_directory(),)
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
        _logger.warning("runtime_feedback invalid pending worker observation (%s)",
                        type(exc).__name__)
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
                    _logger.warning("runtime_feedback worker observation marker pending\n%s",
                                    format_diagnostic_exception(exc))
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
           explains_invocation: bool = True) -> None:
    """Keep native diagnostic facts. Omit messages at boundaries carrying opaque inputs."""
    try:
        caller = _current.get()
        run = run or (caller.run if caller else "") or os.getenv("RESEARCH_FEEDBACK_RUN_ID") or uuid4().hex
        attempt = attempt or (caller.attempt if caller else "") or os.getenv("RESEARCH_FEEDBACK_ATTEMPT_ID") or run
        stem, context, row, details = _prepare_observation(
            operation, status, run=run, attempt=attempt, reason=reason, error=error,
            item=item, source_id=source_id, expected=expected, message=message,
            include_error_messages=include_error_messages,
        )
        if caller is not None and caller.log_path is not None and (
            error is not None or status in _FAILED or status.startswith("exit:")
        ):
            append_diagnostic(
                caller.log_path, f"operation outcome {row['actual']} {json.dumps(details, ensure_ascii=True)}",
                warn_on_stderr=False,
            )
        details_name = row["details_ref"]

        def recorded() -> None:
            if caller is not None:
                caller.explained = caller.explained or explains_invocation
                if error is not None:
                    caller.reported_errors.append(error)

        explicit = os.getenv("RESEARCH_FEEDBACK_OUT")
        if explicit:
            sidecar = win32_filesystem_path(Path(explicit))
            try:
                sidecar.parent.mkdir(parents=True, exist_ok=True)
                _atomic(sidecar.parent / details_name, _encoded(details))
                with sidecar.open("a+b") as stream:
                    needs_separator = False
                    if stream.seek(0, os.SEEK_END):
                        stream.seek(-1, os.SEEK_END)
                        needs_separator = stream.read(1) != b"\n"
                    stream.write((b"\n" if needs_separator else b"") + _encoded(row))
                    stream.flush()
                    os.fsync(stream.fileno())
            except OSError as exc:
                _logger.warning("runtime_feedback explicit sidecar write failed\n%s",
                                format_diagnostic_exception(exc))
            else:
                recorded()
                return
        last_error: OSError | None = None
        for folder in _feedback_folders():
            try:
                folder.mkdir(parents=True, exist_ok=True)
                _atomic(folder / details_name, _encoded(details))
                _atomic(folder / (stem + ".jsonl"), _encoded(row))
                _atomic(folder / (stem + ".ready"), _encoded(context))
            except OSError as exc:
                last_error = exc
                continue
            recorded()
            break
        else:
            _logger.warning("runtime_feedback failed to persist observation across all fallback directories\n%s",
                            format_diagnostic_exception(last_error) if last_error else "")
    except Exception as exc:
        # The source catalog and worker retain their own authoritative result.
        _logger.warning("runtime_feedback unexpected persistence failure\n%s", format_diagnostic_exception(exc))
        return


def entry(operation: str) -> Callable[[Callable[_P, int]], Callable[_P, int]]:
    """Bind a run before CLI parsing, while preserving byte streams and exit semantics."""
    def decorate(main: Callable[_P, int]) -> Callable[_P, int]:
        @wraps(main)
        def invoke(*args: _P.args, **kwargs: _P.kwargs) -> int:
            parent = _current.get()
            run = (parent.run if parent else None) or os.getenv("RESEARCH_FEEDBACK_RUN_ID") or uuid4().hex
            attempt = (parent.attempt if parent else None) or os.getenv("RESEARCH_FEEDBACK_ATTEMPT_ID") or run
            context = _Invocation(
                operation, run, attempt, parent.log_path if parent else _local_log_path(),
                reported_errors=parent.reported_errors if parent else [],
            )
            token = _current.set(context)
            try:
                log_scope = (
                    diagnostic_log(logging.getLogger("company_wiki"), context.log_path, warn_on_stderr=False)
                    if parent is None and context.log_path is not None else nullcontext()
                )
                with log_scope:
                    try:
                        result = main(*args, **kwargs)
                        if result and not context.explained:
                            record(operation, f"exit:{result}")
                        return result
                    except (Exception, SystemExit, KeyboardInterrupt) as exc:
                        already_recorded = any(exc is previous for previous in context.reported_errors)
                        if not already_recorded and (not isinstance(exc, SystemExit) or
                                                     (not context.explained and exc.code not in (0, None))):
                            record(operation, "interrupted" if isinstance(exc, KeyboardInterrupt) else "failed",
                                   error=exc)
                        raise
            finally:
                if parent and context.explained:
                    parent.explained = True
                _current.reset(token)
        return invoke
    return decorate


def document_results(operation: str, payload: Mapping[str, Any]) -> None:
    """Read each native result including failures inside a successful request."""
    status = payload.get("status")
    run = _token(payload.get("run_id")) or _token(payload.get("request_id"))
    attempt = _token(payload.get("attempt_id"))
    if isinstance(status, str) and status in _FAILED:
        record(operation, status, run=run, attempt=attempt, reason=payload.get("reason") or payload.get("error") or "",
               error=sys.exc_info()[1])
    members = payload.get("items", payload.get("documents"))
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
        item = member.get("item_key") or source or member.get("document_id") or member.get("candidate_id") or ""
        reasons = member.get("reason_codes") or member.get("errors")
        if not isinstance(reasons, (list, tuple)):
            reasons = []
        record(operation, state, run=run, attempt=_token(member.get("attempt_id")) or attempt,
               item=str(item), source_id=source,
               reason=next((code for code in reasons if _token(code)), ""))
