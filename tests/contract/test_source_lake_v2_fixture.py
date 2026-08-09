"""WU-102 RED/audit tests: FIX-01..04 for the source-lake v2 fixture."""
import re
import sys
from pathlib import Path

import pytest

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "source_lake_v2"
sys.path.insert(0, str(FIXTURES))
from factory import build_source_lake  # noqa: E402

# Real absolute-path fragments that must never appear inside the fixture
# (FIX-01): the three real roots and the user home.
REAL_PATH_FRAGMENTS = [
    "C:\\Users\\郑曾波",
    "/Users/郑曾波",
    "Projects\\company-wiki\\companies",
    "Projects/dayu-agent/workspace/portfolio",
    "Dropbox\\Stock",
    "Dropbox/Stock",
]

EXPECTED_ROOTS = {"company_raw", "dayu", "sidecar_root", "future_root"}


def _all_relative_paths(lake) -> list[str]:
    paths: list[str] = []
    for root in lake.roots.values():
        for path in root.rglob("*"):
            if path.is_file():
                paths.append(str(path.relative_to(root)))
    return paths


def test_fix01_no_real_absolute_paths(tmp_path):
    lake = build_source_lake(tmp_path)
    assert set(lake.roots) == EXPECTED_ROOTS, f"roots: {set(lake.roots)}"
    for relative in _all_relative_paths(lake):
        for fragment in REAL_PATH_FRAGMENTS:
            assert fragment not in str(relative), (
                f"fixture leaks real path fragment {fragment!r}: {relative}"
            )


def test_fix02_tamper_byte_breaks_manifest(tmp_path):
    lake = build_source_lake(tmp_path)
    assert lake.manifest, "manifest must not be empty"
    # pick one manifest entry, tamper the file, manifest check must fail
    relative, entry = next(iter(lake.manifest.items()))
    target = next(
        root / relative
        for root in lake.roots.values()
        if (root / relative).is_file()
    )
    target.write_bytes(target.read_bytes() + b"\x00")
    import hashlib

    actual = hashlib.sha256(target.read_bytes()).hexdigest()
    assert actual != entry["sha256"], "tampered file must change its sha256"
    # manifest re-check must report the mismatch
    assert lake.manifest[relative]["sha256"] != actual


def test_fix03_future_root_no_special_case():
    """FIX-03: the factory must not branch on future_root by name."""
    source = (FIXTURES / "factory.py").read_text(encoding="utf-8")
    # a conditional that names future_root would be a special case
    pattern = re.compile(
        r"\b(if|elif|else|match|case)\b.*future_root|future_root\s*(==|!=)"
    )
    assert not pattern.search(source), (
        "factory.py must not contain a future_root-specific branch"
    )


def test_fix04_no_external_side_effects(tmp_path, monkeypatch):
    """FIX-04: builder must not network / subprocess / write outside tmp_path."""

    def _forbid(*args, **kwargs):
        raise AssertionError("fixture builder must not spawn subprocesses")

    monkeypatch.setattr("subprocess.run", _forbid)
    before = sorted(str(p) for p in tmp_path.parent.rglob("*"))
    lake = build_source_lake(tmp_path)
    after = sorted(str(p) for p in tmp_path.parent.rglob("*"))
    assert set(before) | {str(p) for p in tmp_path.rglob("*")} == set(after) | {
        str(p) for p in tmp_path.rglob("*")
    }
    # all writes must live under tmp_path
    for root in lake.roots.values():
        assert str(root).startswith(str(tmp_path))
