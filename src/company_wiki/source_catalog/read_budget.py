"""Shared per-request byte and candidate budget for source reads."""

from dataclasses import dataclass

from company_wiki.source_contract.source_version import SourceReadError

DEFAULT_REQUEST_MAX_CANDIDATES = 64
DEFAULT_REQUEST_MAX_BYTES = 2 * 1024 * 1024 * 1024


@dataclass
class ReadBudget:
    """Finite byte/candidate account with sticky caller cancellation.

    Catalog resolution and local inventory share this contract. Owners extend
    the checkpoint with their own resource dimensions rather than duplicating
    or silently resetting the byte/candidate accounting.
    """

    max_candidates: int = DEFAULT_REQUEST_MAX_CANDIDATES
    max_bytes: int = DEFAULT_REQUEST_MAX_BYTES
    candidates: int = 0
    bytes_read: int = 0
    cancelled: bool = False

    def cancel(self) -> None:
        """Caller-side cancellation: no further candidate byte is read."""
        self.cancelled = True

    def check(self) -> None:
        """Honor the shared stop state without importing a read implementation."""
        if self.cancelled:
            raise SourceReadError("unavailable", "cancelled")

    def begin_request(self) -> None:
        """Reset per-request observations while preserving explicit cancellation."""
        self.candidates = 0
        self.bytes_read = 0

    def take_candidate(self) -> str:
        if self.cancelled:
            return "cancelled"
        if self.candidates >= self.max_candidates:
            return "budget_exceeded"
        self.candidates += 1
        return ""

    def charge(self, size: int) -> str:
        if self.cancelled:
            return "cancelled"
        if self.bytes_read + size > self.max_bytes:
            return "budget_exceeded"
        self.bytes_read += size
        return ""


__all__ = [
    "DEFAULT_REQUEST_MAX_BYTES",
    "DEFAULT_REQUEST_MAX_CANDIDATES",
    "ReadBudget",
]
