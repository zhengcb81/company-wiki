"""FC-504: sidecar-root-exclusive canary sample registry (hashed, path-safe).

A canary sample descriptor carries NO absolute paths — only root_id +
relative_path; ``sample_id`` is the sha256 of ``root_id|relative_path``;
``content_sha256`` pins the bytes; expected identity/period/provider
record the intended filing.  Registration validates the descriptor,
proves the bytes are exclusive of other roots (read-only catalog check),
and — when the real root has fewer than 2 eligible filings (FC-503's
replay proved eligible=0) — returns ``needs_user_samples`` instead of
fabricating a sample.
"""

from __future__ import annotations

import hashlib
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

MIN_ELIGIBLE_FOR_SELECTION = 2


@dataclass(frozen=True)
class CanarySample:
    sample_id: str
    root_id: str
    relative_path: str
    content_sha256: str
    expected_identity: str
    expected_period_end: str
    expected_provider: str

    def as_dict(self) -> dict[str, str]:
        return {
            "sample_id": self.sample_id,
            "root_id": self.root_id,
            "relative_path": self.relative_path,
            "content_sha256": self.content_sha256,
            "expected_identity": self.expected_identity,
            "expected_period_end": self.expected_period_end,
            "expected_provider": self.expected_provider,
        }


def sample_id_for(root_id: str, relative_path: str) -> str:
    """Deterministic hashed sample id — never leaks the absolute path."""
    return hashlib.sha256(
        f"{root_id}|{relative_path}".encode("utf-8")
    ).hexdigest()


def _is_relative_safe(relative_path: str) -> bool:
    parts = relative_path.replace("\\", "/").split("/")
    if any(p in ("..", "") for p in parts):
        return False
    head = parts[0]
    # no drive letters, no rooted/absolute prefixes
    if ":" in head or head.startswith("/") or head == ".":
        return False
    return True


def validate_sample_descriptor(desc: dict[str, Any]) -> CanarySample:
    """Validate a descriptor; raise ValueError on any path leak or a
    forged sample_id."""
    root_id = str(desc.get("root_id") or "")
    relative_path = str(desc.get("relative_path") or "")
    if not _is_relative_safe(relative_path):
        raise ValueError(f"FC-504: unsafe relative path {relative_path!r}")
    expected = sample_id_for(root_id, relative_path)
    if str(desc.get("sample_id") or "") != expected:
        raise ValueError("FC-504: sample_id does not match root|path hash")
    return CanarySample(
        sample_id=expected,
        root_id=root_id,
        relative_path=relative_path,
        content_sha256=str(desc.get("content_sha256") or ""),
        expected_identity=str(desc.get("expected_identity") or ""),
        expected_period_end=str(desc.get("expected_period_end") or ""),
        expected_provider=str(desc.get("expected_provider") or ""),
    )


def exclusive_of_other_roots(
    catalog: Path,
    content_sha256: str,
    other_root_ids: tuple[str, ...],
) -> bool:
    """True when the bytes have NO active location in another root
    (read-only).  Registering a non-exclusive sample would fabricate
    exclusive-source proof."""
    if not other_root_ids:
        return True
    con = sqlite3.connect(f"file:{catalog}?mode=ro", uri=True)
    try:
        root_ids = ",".join("?" for _ in other_root_ids)
        row = con.execute(
            f"""SELECT COUNT(*) c FROM locations l
                JOIN sources s ON s.source_id = l.source_id
                WHERE l.root_id IN ({root_ids})
                  AND l.location_status = 'active'
                  AND s.content_sha256 = ?""",
            (*other_root_ids, content_sha256),
        ).fetchone()
        return row[0] == 0
    finally:
        con.close()


def canary_decision(report: dict[str, Any]) -> str:
    """'selectable' when >= 2 eligible filings exist in the inventory,
    else 'needs_user_samples' (never fabricate a sample)."""
    eligible = int(report.get("buckets", {}).get("eligible", 0))
    if eligible >= MIN_ELIGIBLE_FOR_SELECTION:
        return "selectable"
    return "needs_user_samples"


def register_canary(
    desc: dict[str, Any],
    *,
    catalog: Path | None,
    other_root_ids: tuple[str, ...] = (),
) -> CanarySample:
    """Validate + exclusivity-check a canary descriptor and register it.

    When ``canary_decision`` is ``needs_user_samples`` the caller must
    not select anything: the real samples do not exist yet.
    """
    sample = validate_sample_descriptor(desc)
    if catalog is not None and not exclusive_of_other_roots(
        catalog, sample.content_sha256, other_root_ids
    ):
        raise ValueError(
            f"FC-504: sample {sample.sample_id[:12]} already exists in "
            f"another root — registering it would fabricate exclusive-"
            f"source proof"
        )
    return sample


__all__ = [
    "CanarySample",
    "canary_decision",
    "exclusive_of_other_roots",
    "register_canary",
    "sample_id_for",
    "validate_sample_descriptor",
]
