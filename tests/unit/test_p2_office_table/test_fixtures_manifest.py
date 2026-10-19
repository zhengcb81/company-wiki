"""Committed synthetic fixtures stay byte-identical to their generated form.

The fixtures are produced by :mod:`tests.unit.test_p2_office_table.ooxml_support`
inside the test session and stored under ``fixtures/`` with a SHA-256 manifest,
so the card's "fixtures/** plus sha256 manifest" requirement is checkable and
the bytes are proven reproducible (card §6, §8: every package is a synthetic
OOXML archive no larger than 128 KiB; no production material is copied).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from . import fixture_files

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"
MAX_BYTES = 128 * 1024


def test_manifest_lists_every_fixture_with_its_sha256():
    manifest = json.loads((FIXTURE_DIR / "sha256.json").read_text(encoding="utf-8"))
    assert manifest["schema"] == "cwp-office-table-fixtures/1"
    entries = manifest["fixtures"]
    on_disk = sorted(
        path.name for path in FIXTURE_DIR.iterdir() if path.name != "sha256.json"
    )
    assert sorted(entry["file"] for entry in entries) == on_disk
    for entry in entries:
        payload = (FIXTURE_DIR / entry["file"]).read_bytes()
        assert hashlib.sha256(payload).hexdigest() == entry["sha256"], entry["file"]
        assert entry["kind"] in {"docx", "pptx"}
        assert len(payload) <= MAX_BYTES, entry["file"]


def test_committed_fixtures_equal_freshly_generated_bytes():
    for name, payload in fixture_files.build_all().items():
        stored = (FIXTURE_DIR / name).read_bytes()
        assert stored == payload, (
            f"fixture {name} drifted from its generator; regenerate it instead of "
            "editing the committed bytes"
        )
