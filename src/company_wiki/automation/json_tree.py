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
    active: set[int] = set()
    pending: list[tuple[bool, Any]] = [(False, value)]
    while pending:
        leaving, current = pending.pop()
        if leaving:
            active.remove(id(current))
            continue
        if isinstance(current, (Mapping, list, tuple)):
            if id(current) in active:
                raise ValueError("JSON contains a circular reference")
            active.add(id(current))
            pending.append((True, current))
            if isinstance(current, Mapping):
                if any(not isinstance(key, str) for key in current):
                    raise TypeError("JSON object keys must be strings")
                pending.extend((False, child) for child in reversed(tuple(current.values())))
            else:
                pending.extend((False, child) for child in reversed(current))
        else:
            _scalar(current)
        yield current


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
