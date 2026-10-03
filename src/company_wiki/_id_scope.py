"""Small immutable ID scopes for parameterized, bounded batch queries."""

from __future__ import annotations


def normalize_id_scope(
    values: tuple[str, ...] | None, *, name: str,
) -> tuple[str, ...] | None:
    """Preserve unrestricted/empty scopes; bound unique IDs, not duplicates."""
    if values is None:
        return None
    if not isinstance(values, tuple):
        raise TypeError(f"{name} must be a tuple or None")
    if any(not isinstance(value, str) or not value or value.strip() != value
           for value in values):
        raise ValueError(f"{name} must contain non-empty, unpadded string IDs")
    unique = tuple(dict.fromkeys(values))
    if len(unique) > 900:
        raise ValueError(f"{name} must contain at most 900 unique IDs")
    return unique
