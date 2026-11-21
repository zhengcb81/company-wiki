"""Durable company-wiki failure observations at the public operation boundary."""
from __future__ import annotations

from collections.abc import Callable, Mapping
from contextvars import ContextVar
from dataclasses import dataclass, field
from functools import wraps
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import sys
from tempfile import NamedTemporaryFile
from typing import Any, ParamSpec
from uuid import NAMESPACE_URL, uuid4, uuid5

from .diagnostic_redaction import redact_text


__all__ = ["document_results", "entry", "record"]


_P = ParamSpec("_P")
_OWNER = "company-wiki"
_CODE = re.compile(r"[A-Za-z0-9_.:/-]+")
_FAILED = {"failed", "error", "dead_letter", "blocked", "unavailable", "uncertain",
           "budget_exhausted", "storage_exhausted", "refused", "retry_wait", "interrupted"}


@dataclass
class _Invocation:
    operation: str
    run: str
    attempt: str
    explained: bool = False
    reported_errors: list[BaseException] = field(default_factory=list)


_current: ContextVar[_Invocation | None] = ContextVar("cwp_feedback_invocation", default=None)


def _directory() -> Path:
    state = os.getenv("LOCALAPPDATA") if os.name == "nt" else os.getenv("XDG_STATE_HOME")
    return (Path(state) if state else Path.home() / ".local" / "state") / _OWNER / "observations"


def _atomic(path: Path, data: bytes) -> None:
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


def _encoded(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, ensure_ascii=True) + "\n").encode("ascii")


def _exceptions(exc: BaseException | None) -> list[dict]:
    output: list[dict] = []
    pending = [exc] if exc is not None else []
    seen: set[int] = set()
    while pending:
        item = pending.pop()
        if id(item) in seen:
            continue
        seen.add(id(item))
        locations = []
        tb = vars(BaseException)["__traceback__"].__get__(item)
        while tb is not None:
            code = tb.tb_frame.f_code
            locations.append([Path(code.co_filename).name, code.co_name, tb.tb_lineno])
            tb = tb.tb_next
        # Never call an exception's user-defined __str__ or expose arbitrary
        # object arguments. Native message strings retain the specific cause.
        values = vars(BaseException)["args"].__get__(item)
        message = [redact_text(value) for value in values if type(value) is str]
        detail: dict[str, Any] = {"type": type(item).__name__, "locations": locations, "messages": message}
        if isinstance(item, OSError) and item.errno is not None:
            detail["errno"] = item.errno
        if isinstance(item, json.JSONDecodeError):
            detail["line"], detail["column"] = item.lineno, item.colno
        output.append(detail)
        for edge in (vars(BaseException)["__context__"], vars(BaseException)["__cause__"]):
            child = edge.__get__(item)
            if isinstance(child, BaseException):
                pending.append(child)
    return output


def _token(value: object) -> str:
    return value if isinstance(value, str) and _CODE.fullmatch(value) else ""


def record(operation: str, status: str, *, reason: str = "", error: BaseException | None = None,
           run: str = "", attempt: str = "", item: str = "", source_id: str = "",
           expected: bool = False, message: str = "") -> None:
    """Project only stable native facts; diagnostic failures never replace the native outcome."""
    try:
        caller = _current.get()
        run = run or (caller.run if caller else "") or os.getenv("RESEARCH_FEEDBACK_RUN_ID") or uuid4().hex
        attempt = attempt or (caller.attempt if caller else "") or os.getenv("RESEARCH_FEEDBACK_ATTEMPT_ID") or run
        # Identifiers can originate in unparsed request arguments. An unsafe value
        # is still correlatable without preserving a raw path or arbitrary text.
        def logical(value: str) -> str:
            if isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9_:.@-]+", value):
                return value
            return "ref-" + sha256(str(value).encode("utf-8", errors="replace")).hexdigest()

        run, attempt = logical(run), logical(attempt)
        if source_id:
            source_id = logical(source_id)
        step = operation + ("/" + logical(item) if item else "")
        key = uuid5(NAMESPACE_URL, json.dumps([_OWNER, run, attempt, step, status], ensure_ascii=True)).hex
        stem = "feedback-" + key
        details_name = stem + ".diagnostic.json"
        context = {"owner": _OWNER, "run_id": run, "attempt_id": attempt, "step_id": step}
        row = {**context, "schema_version": "feedback-observation/1", "check_id": "operation-outcome",
               "expected": status if expected else "completed", "actual": status,
               "disposition": "expected" if expected else "deviation", "details_ref": details_name}
        if source_id:
            row["evidence_ref"] = source_id
        if status in {"refused", "blocked"} and _token(reason):
            row["refusal_code"] = reason.lower()
        details = {**context, "reason": _token(reason) or status, "exceptions": _exceptions(error)}
        if message:
            details["message"] = redact_text(message)
        if source_id:
            details["source_id"] = source_id
        def recorded() -> None:
            if caller is not None:
                caller.explained = True
                if error is not None:
                    caller.reported_errors.append(error)

        explicit = os.getenv("RESEARCH_FEEDBACK_OUT")
        if explicit:
            sidecar = Path(explicit)
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
            except OSError:
                pass
            else:
                recorded()
                return
        override = os.getenv("RESEARCH_FEEDBACK_DIR")
        folders = [Path(override), _directory()] if override else [_directory()]
        for folder in dict.fromkeys(folders):
            try:
                folder.mkdir(parents=True, exist_ok=True)
                _atomic(folder / details_name, _encoded(details))
                _atomic(folder / (stem + ".jsonl"), _encoded(row))
                _atomic(folder / (stem + ".ready"), _encoded(context))
            except OSError:
                continue
            recorded()
            break
    except Exception:
        # The source catalog and worker retain their own authoritative result.
        return


def entry(operation: str) -> Callable[[Callable[_P, int]], Callable[_P, int]]:
    """Bind a run before CLI parsing, while preserving byte streams and exit semantics."""
    def decorate(main: Callable[_P, int]) -> Callable[_P, int]:
        @wraps(main)
        def invoke(*args: _P.args, **kwargs: _P.kwargs) -> int:
            parent = _current.get()
            run = (parent.run if parent else None) or os.getenv("RESEARCH_FEEDBACK_RUN_ID") or uuid4().hex
            attempt = (parent.attempt if parent else None) or os.getenv("RESEARCH_FEEDBACK_ATTEMPT_ID") or run
            context = _Invocation(operation, run, attempt, reported_errors=parent.reported_errors if parent else [])
            token = _current.set(context)
            try:
                result = main(*args, **kwargs)
                if result and not context.explained:
                    record(operation, f"exit:{result}")
                return result
            except (Exception, SystemExit, KeyboardInterrupt) as exc:
                already_recorded = any(exc is previous for previous in context.reported_errors)
                if not already_recorded and (not isinstance(exc, SystemExit) or
                                             (not context.explained and exc.code not in (0, None))):
                    record(operation, "interrupted" if isinstance(exc, KeyboardInterrupt) else "failed", error=exc)
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
    if isinstance(status, str) and status in _FAILED:
        record(operation, status, run=run, reason=payload.get("reason") or payload.get("error") or "",
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
        record(operation, state, run=run, attempt=run, item=str(item), source_id=source,
               reason=next((code for code in reasons if _token(code)), ""))
