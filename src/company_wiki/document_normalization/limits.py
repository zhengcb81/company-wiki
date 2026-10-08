"""Strict finite resource limits for document normalization.

Every field is a strictly positive integer (never bool, never unbounded) or,
for ``deadline``, ``None`` or a finite ``time.monotonic()`` reading.  Exceeding
any limit raises :class:`NormalizationLimitError`; the parser never silently
truncates.  Defaults are recorded in
``docs/implementation/cmrf-format-normalization-20261008/task_plan.md`` and may
be chosen per deployment, but callers must always be able to bound the work.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
import time

from .errors import NormalizationLimitError

# Fixed safety bound for ZIP member count.  It is intentionally not
# configurable: a package with more members than this is not a plausible
# presentation and rejecting it is cheaper than iterating it.
MAX_ZIP_MEMBERS = 10_000

_POSITIVE_INT_FIELDS = (
    "max_source_bytes",
    "max_total_uncompressed_bytes",
    "max_text_output_bytes",
    "max_units",
    "max_pages",
    "max_media_bytes",
)


@dataclass(frozen=True)
class NormalizationLimits:
    """Finite resource budget for one ``normalize_document`` or replay call."""

    max_source_bytes: int = 64 * 1024 * 1024
    max_total_uncompressed_bytes: int = 512 * 1024 * 1024
    max_text_output_bytes: int = 16 * 1024 * 1024
    max_units: int = 20_000
    max_pages: int = 5_000
    max_media_bytes: int = 256 * 1024 * 1024
    deadline: float | None = None

    def __post_init__(self) -> None:
        for name in _POSITIVE_INT_FIELDS:
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError(
                    f"{name} must be a strictly positive int, got {value!r}"
                )
            if value <= 0:
                raise ValueError(
                    f"{name} must be a strictly positive int, got {value!r}"
                )
        if self.deadline is not None:
            if isinstance(self.deadline, bool) or not isinstance(
                self.deadline, (int, float)
            ):
                raise TypeError(
                    "deadline must be a finite time.monotonic() reading or None"
                )
            deadline = float(self.deadline)
            if not math.isfinite(deadline):
                raise ValueError("deadline must be finite or None")
            object.__setattr__(self, "deadline", deadline)

    def check_deadline(self, where: str) -> None:
        if self.deadline is not None and time.monotonic() >= self.deadline:
            raise NormalizationLimitError(
                "deadline", self.deadline, f"reached during {where}"
            )

    def require_within(self, name: str, value: int) -> None:
        """Raise when ``value`` exceeds the configured integer limit."""
        if name not in _POSITIVE_INT_FIELDS:
            raise KeyError(name)
        limit = getattr(self, name)
        if value > limit:
            raise NormalizationLimitError(name, limit, f"requested {value}")


DEFAULT_LIMITS = NormalizationLimits()

__all__ = [
    "DEFAULT_LIMITS",
    "MAX_ZIP_MEMBERS",
    "NormalizationLimits",
]
