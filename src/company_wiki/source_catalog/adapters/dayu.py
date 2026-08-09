"""WU-602: dayu portfolio adapter — mechanically extracted from scanner v1.

Enumerates ``portfolio/{ticker}/filings/...`` trees and merges the rich
``meta.json`` sibling into candidate metadata (provider metadata, document
kind via form_type, fiscal_year, source_url, language, filing_date).
Behavior matches scanner v1 (parity tests); download paths stay fully
separate from adapter scanning.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .common import _walk_files
from .interface import NormalizedCandidate


class DayuAdapter:
    """dayu layout: portfolio/{ticker}/filings/... + meta.json enrichment."""

    adapter_id = "dayu_filing_v1"
    version = "1.0.0"

    def enumerate(self, root_path: Path, *, limit: int | None = None) -> list[NormalizedCandidate]:
        candidates: list[NormalizedCandidate] = []
        for path in sorted(_walk_files(root_path)):
            if path.name.endswith(".source.json") or path.name == "meta.json":
                continue
            metadata = dict(_load_sibling_meta(path))
            candidates.append(NormalizedCandidate(
                relative_path=path.relative_to(root_path).as_posix(),
                content_sha256=_sha256_file(path),
                group_key=path.relative_to(root_path).as_posix(),
                role="original_primary",
                normalized=metadata,
            ))
            if limit is not None and len(candidates) >= limit:
                break
        return candidates


def _load_sibling_meta(path: Path) -> dict:
    meta_path = path.parent / "meta.json"
    try:
        payload = json.loads(meta_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
