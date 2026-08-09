"""WU-501: SourceAdapter SPI — the only contract between roots and the
scanner pipeline.

An adapter enumerates file groups and turns a source layout into
NormalizedCandidates.  It NEVER writes the database, never decides
downloads, never bypasses admission, and never imports store/resolver/
download/parser/LLM (ARC-FIT-02/05).  Adapters are deterministic: the same
tree twice yields the same candidates in the same order (SPI-03).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class NormalizedCandidate:
    """Source-independent filing facts produced by an adapter."""

    relative_path: str
    content_sha256: str
    group_key: str
    role: str  # primary | sidecar | markdown | summary | sections
    normalized: dict = field(default_factory=dict)
    evidence: dict = field(default_factory=dict)


class SourceAdapter(Protocol):
    """An adapter is a pure function from a root directory to candidates."""

    adapter_id: str
    version: str

    def enumerate(self, root_path, *, limit: int | None = None) -> list[NormalizedCandidate]:
        """Stable-sorted file groups with roles; never touches the DB."""
        ...


def check_candidate_determinism(
    first: list[NormalizedCandidate], second: list[NormalizedCandidate]
) -> list[str]:
    """SPI-03: same tree twice => identical candidates in identical order."""
    problems: list[str] = []
    if len(first) != len(second):
        problems.append(
            f"candidate count changed: {len(first)} -> {len(second)}"
        )
    for index, (left, right) in enumerate(zip(first, second)):
        if left.relative_path != right.relative_path:
            problems.append(
                f"candidate[{index}] order/path changed: "
                f"{left.relative_path!r} -> {right.relative_path!r}"
            )
        if left.content_sha256 != right.content_sha256:
            problems.append(
                f"candidate[{index}] hash changed: "
                f"{left.content_sha256[:8]} -> {right.content_sha256[:8]}"
            )
    return problems


def check_no_duplicate_candidates(candidates: list[NormalizedCandidate]) -> list[str]:
    """SPI-03b: duplicate candidates must be rejected deterministically."""
    problems: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        key = (candidate.group_key, candidate.relative_path)
        if key in seen:
            problems.append(f"duplicate candidate: {candidate.relative_path}")
        seen.add(key)
    return problems
