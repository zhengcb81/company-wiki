"""Finite JSON trees without a product-specific size or depth permission.

Traversal is iterative. Cycles, non-finite values and invalid JSON types remain
errors; shared acyclic subtrees are ordinary JSON, not cycles. Serialization
still belongs to the standard-library JSON implementation.
"""
from __future__ import annotations

from collections.abc import Callable, Iterator, Mapping
import math
from types import MappingProxyType
from typing import Any


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
