"""Shared helpers: frozen real Sina fixtures byte-exact from the W19 research capture.

The 18 gzip snapshots under docs/plans/w19-sina-statements-2026-10-25/inputs/
research/capture are the frozen provider responses this package must normalize
without re-fetching. Tests read the DECOMPRESSED bytes; the SHA-256 of each
decompressed payload was verified against observations.json at node A.
"""

from __future__ import annotations

import gzip
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CAPTURE_DIR = (
    REPO_ROOT
    / "docs"
    / "plans"
    / "w19-sina-statements-2026-10-25"
    / "inputs"
    / "research"
    / "capture"
)


def fixture_path(name: str) -> Path:
    path = CAPTURE_DIR / name
    if not path.is_file():
        raise FileNotFoundError(f"frozen Sina fixture missing: {name}")
    return path


def fixture_bytes(name: str) -> bytes:
    """Decompressed provider response bytes (what production sees on the wire)."""
    return gzip.decompress(fixture_path(name).read_bytes())


def fixture_json(name: str) -> dict:
    return json.loads(fixture_bytes(name).decode("utf-8"))


def zhongwei_pages(statement_source: str) -> list[bytes]:
    """All frozen pages of one statement for sh688012 (page 5 is the empty page)."""
    return [
        fixture_bytes(f"sh688012-{statement_source}-type0-page{page}-num10.json.gz")
        for page in range(1, 6)
    ]
