"""Named errors for deterministic document normalization.

The normalization layer never returns a silently empty success: a real parse
problem is raised, and a replay refusal is raised with the reason attached.
"""

from __future__ import annotations


class NormalizationError(ValueError):
    """Base class for normalization and replay refusals."""


class UnsupportedFormatError(NormalizationError):
    """Declared MIME type is unsupported or contradicts the actual bytes."""


class NormalizationLimitError(NormalizationError):
    """A configured finite resource limit was exceeded.

    The parser refuses instead of silently truncating; the message names the
    limit field and its configured value.
    """

    def __init__(self, limit_name: str, limit_value: int | float, detail: str = ""):
        self.limit_name = limit_name
        self.limit_value = limit_value
        message = f"normalization limit exceeded: {limit_name}={limit_value}"
        if detail:
            message = f"{message} ({detail})"
        super().__init__(message)


class ReplayError(NormalizationError):
    """A replay request was refused (identity, version, locator, or text)."""


__all__ = [
    "NormalizationError",
    "NormalizationLimitError",
    "ReplayError",
    "UnsupportedFormatError",
]
