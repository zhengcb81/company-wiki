"""Finite JSON trees without a product-specific size or depth permission.

Traversal is iterative. Cycles, non-finite values and invalid JSON types remain
errors; shared acyclic subtrees are ordinary JSON, not cycles. Serialization
still belongs to the standard-library JSON implementation.
"""
from __future__ import annotations

from collections.abc import Callable, Iterator, Mapping
from enum import Enum
import hashlib
import json
import math
from types import MappingProxyType
from typing import Any, NoReturn


def _scalar(value: Any) -> None:
    if value is None or isinstance(value, (str, bool, int)):
        return
    if isinstance(value, float):
        if math.isfinite(value):
            return
        raise ValueError("JSON contains a non-finite number")
    raise TypeError(f"unsupported JSON type {type(value).__name__}")


def walk_json(value: Any) -> Iterator[Any]:
    """Yield each node; explicitly detect ancestor cycles without a depth cap."""
    for _context, current in walk_json_context(value):
        yield current


def walk_json_context(value: Any, *, context: Any = None,
                      child_context: Callable[[Any, str | int], Any] | None = None) -> Iterator[tuple[Any, Any]]:
    """Carry an owner's finite field state using the same JSON/cycle checks.

    Context is per edge, never inferred from string values or object identity.
    No full ancestor paths are copied, so traversal remains linear in nodes.
    """
    active: set[int] = set()
    pending: list[tuple[bool, Any, Any]] = [(False, value, context)]
    while pending:
        leaving, current, state = pending.pop()
        if leaving:
            active.remove(id(current))
            continue
        if isinstance(current, (Mapping, list, tuple)):
            if id(current) in active:
                raise ValueError("JSON contains a circular reference")
            active.add(id(current))
            pending.append((True, current, state))
            if isinstance(current, Mapping):
                if any(not isinstance(key, str) for key in current):
                    raise TypeError("JSON object keys must be strings")
                entries = tuple(current.items())
            else:
                entries = tuple(enumerate(current))
            pending.extend((False, child, child_context(state, key) if child_context else state)
                           for key, child in reversed(entries))
        else:
            _scalar(current)
        yield state, current


def copy_json(value: Any, *, freeze: bool = False,
              transform: Callable[[Any], Any] | None = None) -> Any:
    """Copy/freeze one tree, keeping its original values and order intact."""
    result: list[Any] = [None]
    active: set[int] = set()
    pending: list[tuple[bool, Any, Any, Any, Any]] = [(False, value, result, 0, None)]
    while pending:
        leaving, current, parent, key, output = pending.pop()
        if leaving:
            active.remove(id(current))
            parent[key] = (MappingProxyType(output) if isinstance(output, dict) else tuple(output)) if freeze else output
            continue
        current = transform(current) if transform is not None else current
        if isinstance(current, (Mapping, list, tuple)):
            if id(current) in active:
                raise ValueError("JSON contains a circular reference")
            active.add(id(current))
            mapping = isinstance(current, Mapping)
            if mapping and any(not isinstance(name, str) for name in current):
                raise TypeError("JSON object keys must be strings")
            output = {} if mapping else [None] * len(current)
            pending.append((True, current, parent, key, output))
            entries = tuple(current.items()) if isinstance(current, Mapping) else tuple(enumerate(current))
            pending.extend((False, child, output, name, None) for name, child in reversed(entries))
        else:
            _scalar(current)
            parent[key] = current
    return result[0]


def _validate_json_value(value: Any, path: str = "$") -> None:
    for item in walk_json(value):
        if isinstance(item, tuple) or (isinstance(item, Mapping) and not isinstance(item, dict)):
            raise TypeError(f"{path} contains a non-JSON container")


def canonical_json(value: Any) -> str:
    """Serialize a JSON value deterministically without ASCII escaping."""
    _validate_json_value(value)
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def canonical_json_hash(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_non_finite(_literal: str) -> NoReturn:
    raise ValueError("JSON contains a non-finite number")


def _parse_finite_float(literal: str) -> float:
    value = float(literal)
    if not math.isfinite(value):
        _reject_non_finite(literal)
    return value


def parse_json(value: str) -> Any:
    """Decode JSON with unique keys and finite numbers, allowing ordinary formatting."""
    if not isinstance(value, str):
        raise TypeError("JSON must be text")
    try:
        return json.loads(
            value,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_non_finite,
            parse_float=_parse_finite_float,
        )
    except RecursionError as exc:
        raise ValueError("JSON decoder exceeded the runtime stack") from exc


def parse_canonical_json(value: str) -> Any:
    """Return the decoded value after checking the persisted wire encoding."""
    if not isinstance(value, str):
        raise TypeError("canonical JSON must be text")
    try:
        decoded = parse_json(value)
    except ValueError as exc:
        raise ValueError(f"invalid canonical JSON: {exc}") from exc
    if canonical_json(decoded) != value:
        raise ValueError("JSON text is not canonical")
    return decoded


def require_canonical_json(value: str) -> str:
    """Check the encoding and return the original text for existing callers."""
    parse_canonical_json(value)
    return value


def freeze_json(value: Any) -> Any:
    return copy_json(value, freeze=True)


def plain_json(value: Any) -> Any:
    return copy_json(value, transform=lambda item: item.value if isinstance(item, Enum) else item)


def encoding_sha256(*, universal_newlines: bool = False) -> str:
    from .implementation_identity import code_sha256

    return code_sha256(__file__, universal_newlines=universal_newlines)


__all__ = [
    "canonical_json", "canonical_json_hash", "copy_json", "encoding_sha256",
    "freeze_json", "parse_canonical_json", "parse_json", "plain_json", "require_canonical_json", "walk_json", "walk_json_context",
]
