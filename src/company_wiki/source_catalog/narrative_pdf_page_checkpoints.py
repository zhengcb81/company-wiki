"""Pure bounded wire for source-bound, atomically completed PDF pages.

No process, filesystem, SDK, parsing engine, persistence or source rewriting.
Only newline-committed page records can survive a later failed process.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from hashlib import sha256
import json
import math
from typing import Any

from .narrative_pdf_environment import ENVIRONMENT_ALGORITHM

CHECKPOINT_PROTOCOL = "pdf-paragraph-page-checkpoints/1"
PAGE_SCHEMA = "pdf-paragraph-page-checkpoint/1"
COMPLETE_SCHEMA = "pdf-paragraph-pages-complete/1"
MAX_ITEMS = 2048
# Existing public runtime ceilings; actual request limits may be lower.
MAX_PAGES = 16
MAX_SECONDS = 300
MAX_INPUT_BYTES = 64 * 1024**2
MAX_OUTPUT_BYTES = 32 * 1024**2
MAX_MEMORY_BYTES = 8 * 1024**3
MAX_CPU_THREADS = 16
_REQUEST_FIELDS = ("schema_version", "checkpoint_protocol", "source_id", "source_sha256",
    "source_page_count", "pages", "docling_version", "model_sha256", "model_config_sha256",
    "runtime_versions", "environment_sha256", "cpu_threads", "max_seconds", "max_memory_bytes",
    "max_output_bytes")
_RUNTIME_KEYS = {"python", "docling-core", "docling-ibm-models", "torch", "pymupdf", "pypdfium2"}


def _digest(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def _request_identity(request: Mapping[str, Any]) -> dict[str, Any]:
    if (request.get("schema_version") not in {"pdf-paragraph-request/1", "pdf-paragraph-request/2"}
            or request.get("checkpoint_protocol") != CHECKPOINT_PROTOCOL):
        raise ValueError("unsupported paragraph checkpoint request")
    algorithm = request.get("environment_algorithm")
    if (request["schema_version"].endswith("/2") and algorithm != ENVIRONMENT_ALGORITHM
            or request["schema_version"].endswith("/1") and "environment_algorithm" in request):
        raise ValueError("paragraph checkpoint environment algorithm differs")
    sid = request.get("source_id")
    if not isinstance(sid, str) or not sid.strip() or len(sid) > 4096:
        raise ValueError("paragraph checkpoint requires a bounded source ID")
    for key in ("source_sha256", "model_sha256", "model_config_sha256", "environment_sha256"):
        if not _digest(request.get(key)):
            raise ValueError("paragraph checkpoint digest is invalid")
    count, pages = request.get("source_page_count"), request.get("pages")
    if (type(count) is not int or count < 1 or not isinstance(pages, list)
            or not 1 <= len(pages) <= MAX_PAGES or any(type(p) is not int or not 1 <= p <= count for p in pages)
            or len(set(pages)) != len(pages)):
        raise ValueError("paragraph checkpoint pages are invalid")
    seconds = request.get("max_seconds")
    if (not isinstance(seconds, (int, float)) or isinstance(seconds, bool)
            or not math.isfinite(seconds) or not 0 < seconds <= MAX_SECONDS):
        raise ValueError("paragraph checkpoint deadline is invalid")
    for key, maximum in (("max_memory_bytes", MAX_MEMORY_BYTES), ("max_output_bytes", MAX_OUTPUT_BYTES),
                         ("cpu_threads", MAX_CPU_THREADS)):
        value = request.get(key)
        if type(value) is not int or not 0 < value <= maximum:
            raise ValueError("paragraph checkpoint resource bound is invalid")
    versions = request.get("runtime_versions")
    if (not isinstance(versions, Mapping) or set(versions) != _RUNTIME_KEYS
            or not all(isinstance(v, str) and 0 < len(v) <= 128 for v in versions.values())
            or not isinstance(request.get("docling_version"), str) or not 0 < len(request["docling_version"]) <= 128):
        raise ValueError("paragraph checkpoint runtime binding is invalid")
    identity = {key: request[key] for key in _REQUEST_FIELDS}
    if algorithm is not None:
        identity["environment_algorithm"] = algorithm
    return identity


def request_sha256(request: Mapping[str, Any]) -> str:
    return sha256(json.dumps(_request_identity(request), sort_keys=True, ensure_ascii=False,
                             separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def validate_request(request: Mapping[str, Any]) -> None:
    if request.get("request_sha256") != request_sha256(request):
        raise ValueError("paragraph checkpoint request hash differs")


def _binding(request: Mapping[str, Any]) -> dict[str, Any]:
    validate_request(request)
    result = {key: request[key] for key in ("source_id", "source_sha256", "docling_version",
        "model_sha256", "model_config_sha256", "runtime_versions", "environment_sha256", "request_sha256")}
    if "environment_algorithm" in request:
        result["environment_algorithm"] = request["environment_algorithm"]
    return {**result, "request_schema": request["schema_version"],
            "requested_pages": request["pages"], "converter_instances": 1}


def _items(value: Any, page: int) -> list[dict[str, Any]]:
    if not isinstance(value, list) or len(value) > MAX_ITEMS:
        raise ValueError("paragraph checkpoint item count is invalid")
    for item in value:
        if (not isinstance(item, dict) or set(item) != {"label", "text", "provenance"}
                or item["label"] not in {"text", "list_item"} or not isinstance(item["text"], str)
                or not 0 < len(item["text"]) <= 16_384):
            raise ValueError("paragraph checkpoint item is invalid")
        provenance = item["provenance"]
        if not isinstance(provenance, list) or len(provenance) != 1 or not isinstance(provenance[0], dict):
            raise ValueError("paragraph checkpoint provenance is invalid")
        row = provenance[0]
        if type(row.get("page_no")) is not int or row["page_no"] != page:
            raise ValueError("paragraph checkpoint item belongs to another page")
        box = row.get("bbox")
        if (not isinstance(box, dict) or box.get("coord_origin") != "BOTTOMLEFT"
                or any(type(box.get(k)) not in (int, float) or not math.isfinite(box[k]) for k in ("l", "r", "t", "b"))
                or not 0 <= box["l"] < box["r"] or not 0 <= box["b"] < box["t"]):
            raise ValueError("paragraph checkpoint item box is invalid")
    return value


def encode_page(request: Mapping[str, Any], page: int, sequence: int, items: list[dict[str, Any]],
                peak_job_commit_bytes: int | None) -> bytes:
    binding = _binding(request)
    if (type(page) is not int or type(sequence) is not int or not 0 <= sequence < len(request["pages"])
            or request["pages"][sequence] != page):
        raise ValueError("paragraph checkpoint page order differs")
    _peak(peak_job_commit_bytes, request)
    return _encode({**binding, "schema_version": PAGE_SCHEMA, "sequence": sequence, "page": page,
                    "items": _items(items, page), "peak_job_commit_bytes": peak_job_commit_bytes})


def encode_complete(request: Mapping[str, Any], total_items: int) -> bytes:
    if type(total_items) is not int or not 0 <= total_items <= MAX_ITEMS:
        raise ValueError("paragraph checkpoint total item count is invalid")
    return _encode({**_binding(request), "schema_version": COMPLETE_SCHEMA,
        "sequence": len(request["pages"]), "completed_pages": request["pages"], "total_items": total_items})


def _encode(value: Mapping[str, Any]) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode() + b"\n"


def _peak(value: Any, request: Mapping[str, Any]) -> None:
    if value is not None and (type(value) is not int or not 0 <= value <= request["max_memory_bytes"]):
        raise ValueError("paragraph checkpoint memory observation is invalid")


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("paragraph checkpoint has duplicate JSON keys")
        result[key] = value
    return result


def _constant(value):
    raise ValueError("paragraph checkpoint has non-finite JSON")


def decode_single_json(raw: bytes) -> Any:
    """Strict JSON shared by checkpoint records and successful legacy output."""
    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=_unique, parse_constant=_constant)
    except (UnicodeError, json.JSONDecodeError, RecursionError) as error:
        raise ValueError("paragraph checkpoint is not strict JSON") from error


class _PrefixEnd(Exception):
    def __init__(self, *, in_string: bool = False):
        self.in_string = in_string


def _prefix_string(text: str, start: int) -> tuple[int, str]:
    """Read one string, distinguishing a valid unfinished escape from garbage."""
    position = start + 1
    while position < len(text):
        char = text[position]
        if char == '"':
            end = position + 1
            return end, json.loads(text[start:end])
        if ord(char) < 32:
            raise ValueError("unescaped JSON control character")
        position += 1
        if char != "\\":
            continue
        if position == len(text):
            raise _PrefixEnd()
        escape = text[position]
        position += 1
        if escape == "u":
            for _ in range(4):
                if position == len(text):
                    raise _PrefixEnd()
                if text[position] not in "0123456789abcdefABCDEF":
                    raise ValueError("invalid JSON Unicode escape")
                position += 1
        elif escape not in '"\\/bfnrt':
            raise ValueError("invalid JSON escape")
    raise _PrefixEnd(in_string=True)


def _prefix_number(text: str, position: int) -> int:
    """Consume the JSON number grammar without accepting a broken prefix."""
    if text[position] == "-":
        position += 1
        if position == len(text):
            raise _PrefixEnd()
    if text[position] == "0":
        position += 1
    elif text[position] in "123456789":
        position += 1
        while position < len(text) and text[position] in "0123456789":
            position += 1
    else:
        raise ValueError("invalid JSON number")
    for markers, signed in ((".", False), ("eE", True)):
        if position < len(text) and text[position] in markers:
            position += 1
            if signed and position < len(text) and text[position] in "+-":
                position += 1
            if position == len(text):
                raise _PrefixEnd()
            begin = position
            while position < len(text) and text[position] in "0123456789":
                position += 1
            if position == begin:
                raise ValueError("invalid JSON number fraction/exponent")
    return position


@dataclass
class _PrefixFrame:
    kind: str
    state: str
    keys: set[str]


def _truncated_object(raw: bytes) -> bool:
    """Recognize an extendable strict JSON object prefix, including unique keys.

    Each open object owns its key set. A closed duplicate key is already
    irreparable even when its value or the outer document is unfinished.
    The iterative stack also avoids Python recursion limits on partial input.
    """
    pending_utf8 = False
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as error:
        if error.reason != "unexpected end of data" or error.end != len(raw):
            return False
        text = raw[:error.start].decode("utf-8")
        pending_utf8 = True
    position = len(text) - len(text.lstrip(" \t\r\n"))
    if position == len(text) or text[position] != "{":
        return False
    stack = [_PrefixFrame("object", "key_or_end", set())]
    position += 1
    try:
        while stack:
            while position < len(text) and text[position] in " \t\r\n":
                position += 1
            if position == len(text):
                return not pending_utf8
            frame, char = stack[-1], text[position]
            if frame.state in {"key", "key_or_end"}:
                if char == "}" and frame.state == "key_or_end":
                    stack.pop()
                    position += 1
                    continue
                if char != '"':
                    return False
                position, key = _prefix_string(text, position)
                if key in frame.keys:
                    return False
                frame.keys.add(key)
                frame.state = "colon"
            elif frame.state == "colon":
                if char != ":":
                    return False
                frame.state = "value"
                position += 1
            elif frame.state == "comma_or_end":
                if char == ("}" if frame.kind == "object" else "]"):
                    stack.pop()
                elif char == ",":
                    frame.state = "key" if frame.kind == "object" else "value"
                else:
                    return False
                position += 1
            else:
                if char == "]" and frame.state == "value_or_end":
                    stack.pop()
                    position += 1
                    continue
                frame.state = "comma_or_end"
                if char in "{[":
                    stack.append(_PrefixFrame("object" if char == "{" else "array",
                        "key_or_end" if char == "{" else "value_or_end", set()))
                    position += 1
                elif char == '"':
                    position, _ = _prefix_string(text, position)
                elif char in "-0123456789":
                    position = _prefix_number(text, position)
                else:
                    literal = next((word for word in ("true", "false", "null") if word.startswith(char)), None)
                    if literal is None:
                        return False
                    available = text[position:position + len(literal)]
                    if not literal.startswith(available):
                        return False
                    if len(available) < len(literal):
                        raise _PrefixEnd()
                    position += len(literal)
    except _PrefixEnd as unfinished:
        return not pending_utf8 or unfinished.in_string
    except (ValueError, RecursionError):
        return False
    # A complete root object, with or without trailing garbage, is no checkpoint.
    return False


@dataclass(frozen=True)
class CompletedPages:
    items: tuple[dict[str, Any], ...]
    pages: tuple[int, ...]
    complete: bool
    truncated_final_record: bool
    peak_job_commit_bytes: int | None


def decode_output(raw: bytes, request: Mapping[str, Any], *, process_failed: bool) -> CompletedPages:
    binding = _binding(request)
    if not isinstance(raw, bytes) or len(raw) > request["max_output_bytes"]:
        raise ValueError("paragraph checkpoint output byte bound exceeded")
    records = raw.split(b"\n", len(request["pages"]) + 1)
    tail = records.pop()
    truncated = bool(tail)
    if tail and (not process_failed or not _truncated_object(tail)):
        raise ValueError("paragraph checkpoint final record is not committed")
    completed: list[int] = []
    items: list[dict[str, Any]] = []
    terminal = False
    peak: int | None = None
    for line in records:
        record = decode_single_json(line)
        if not isinstance(record, dict) or terminal:
            raise ValueError("paragraph checkpoint record order is invalid")
        if _encode({key: record.get(key) for key in binding}) != _encode(binding):
            raise ValueError("paragraph checkpoint source/runtime/request binding differs")
        if record.get("schema_version") == COMPLETE_SCHEMA:
            if (set(record) != set(binding) | {"schema_version", "sequence", "completed_pages", "total_items"}
                    or type(record["sequence"]) is not int or record["sequence"] != len(request["pages"])
                    or completed != request["pages"] or record["completed_pages"] != completed
                    or not isinstance(record["completed_pages"], list)
                    or any(type(page) is not int for page in record["completed_pages"])
                    or type(record["total_items"]) is not int or record["total_items"] != len(items)):
                raise ValueError("paragraph checkpoint completion differs")
            terminal = True
            continue
        if (set(record) != set(binding) | {"schema_version", "sequence", "page", "items", "peak_job_commit_bytes"}
                or record.get("schema_version") != PAGE_SCHEMA or type(record.get("sequence")) is not int
                or record["sequence"] != len(completed) or len(completed) >= len(request["pages"])
                or type(record.get("page")) is not int or record["page"] != request["pages"][len(completed)]):
            raise ValueError("paragraph checkpoint page order is invalid")
        page_items = _items(record["items"], record["page"])
        if len(items) + len(page_items) > MAX_ITEMS:
            raise ValueError("paragraph checkpoint aggregate item count exceeded")
        _peak(record["peak_job_commit_bytes"], request)
        observed = record["peak_job_commit_bytes"]
        if observed is not None:
            peak = max(peak or 0, observed)
        items.extend(page_items)
        completed.append(record["page"])
    if (terminal and tail) or (not process_failed and not terminal):
        raise ValueError("paragraph checkpoint stream is incomplete")
    return CompletedPages(tuple(items), tuple(completed), terminal and not process_failed, truncated, peak)
