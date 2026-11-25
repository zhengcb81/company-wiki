"""Pure projection of native failure observations before persistence."""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any
from uuid import NAMESPACE_URL, uuid5

from . import __version__
from .diagnostic_redaction import redact_text


__all__ = [
    "OWNER", "encode_observation", "freeze_worker_failure", "logical_observation_ref", "observation_stem",
    "observation_token", "prepare_observation",
]

OWNER = "company-wiki"
_CODE = re.compile(r"[A-Za-z0-9_.:/-]+")


def encode_observation(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, ensure_ascii=True) + "\n").encode("ascii")


def _exceptions(exc: BaseException | None, *, include_messages: bool) -> list[dict]:
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
        values = vars(BaseException)["args"].__get__(item) if include_messages else ()
        message = [redact_text(value) for value in values if type(value) is str]
        detail: dict[str, Any] = {"type": type(item).__name__, "locations": locations, "messages": message}
        if isinstance(item, OSError):
            errno = vars(OSError)["errno"].__get__(item)
            if type(errno) is int:
                detail["errno"] = errno
        if isinstance(item, json.JSONDecodeError):
            attributes = vars(BaseException)["__dict__"].__get__(item)
            for source, field_name in (("lineno", "line"), ("colno", "column")):
                if type(attributes.get(source)) is int:
                    detail[field_name] = attributes[source]
        output.append(detail)
        for edge in (vars(BaseException)["__context__"], vars(BaseException)["__cause__"]):
            child = edge.__get__(item)
            if isinstance(child, BaseException):
                pending.append(child)
    return output


def observation_token(value: object) -> str:
    return value if isinstance(value, str) and _CODE.fullmatch(value) else ""


def observation_stem(run: str, attempt: str, step: str, status: str) -> str:
    identity = json.dumps([OWNER, run, attempt, step, status], ensure_ascii=True)
    return "feedback-" + uuid5(NAMESPACE_URL, identity).hex


def logical_observation_ref(value: str) -> str:
    # Correlate unparsed request IDs without preserving arbitrary raw text.
    if isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9_:.@-]+", value):
        return value
    return "ref-" + sha256(str(value).encode("utf-8", errors="replace")).hexdigest()


def prepare_observation(
    operation: str,
    status: str,
    *,
    run: str,
    attempt: str,
    reason: str,
    error: BaseException | None = None,
    item: str = "",
    source_id: str = "",
    expected: bool = False,
    message: str = "",
    include_error_messages: bool = True,
) -> tuple[str, dict, dict, dict]:
    run, attempt = logical_observation_ref(run), logical_observation_ref(attempt)
    if source_id:
        source_id = logical_observation_ref(source_id)
    step = operation + ("/" + logical_observation_ref(item) if item else "")
    stem = observation_stem(run, attempt, step, status)
    details_name = stem + ".diagnostic.json"
    context = {"owner": OWNER, "run_id": run, "attempt_id": attempt, "step_id": step}
    row = {**context, "schema_version": "feedback-observation/1", "check_id": "operation-outcome",
           "expected": status if expected else "completed", "actual": status,
           "disposition": "expected" if expected else "deviation", "details_ref": details_name}
    if source_id:
        row["evidence_ref"] = source_id
    if status in {"refused", "blocked"} and observation_token(reason):
        row["refusal_code"] = reason.lower()
    details = {**context, "package_version": __version__, "reason": observation_token(reason) or status,
               "exceptions": _exceptions(error, include_messages=include_error_messages)}
    if message:
        details["message"] = redact_text(message)
    if source_id:
        details["source_id"] = source_id
    return stem, context, row, details


def freeze_worker_failure(
    job_id: str, attempt_id: str, status: str, reason: str, *,
    message: str = "", error: BaseException | None = None,
) -> str:
    """Return one serialized, redacted original worker observation."""
    _, _, row, details = prepare_observation(
        "worker", status, run=job_id, attempt=attempt_id, reason=reason,
        message=message, error=error,
    )
    return encode_observation({"row": row, "details": details}).decode("ascii")
