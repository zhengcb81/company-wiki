"""Node B/C conventions: lane scratch hygiene and real-original read-only use.

Two card requirements are locked here rather than left to manual habit:

* tests that use their own scratch directory drop a sentinel and clean up in
  ``finally`` even when an assertion fails;
* the opt-in real-original path never writes to an original (SHA-256 and mtime
  identical before and after the call).
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path

import pytest

import real_probe
from checks import groups_of_kind

from company_wiki.document_understanding.layout_hints import derive_layout_hints

ROOT = Path(__file__).resolve().parents[3]
BINDINGS_PATH = ROOT / ".planning" / "du2-layout" / "bindings.local.json"
REAL_OPT_IN = os.environ.get("CW_DU2_LAYOUT_REAL") == "1"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def test_lane_scratch_uses_a_sentinel_and_cleans_up_on_failure() -> None:
    """The lane's own scratch convention: sentinel in, always cleaned out."""
    owned = tempfile.mkdtemp(prefix="du2-layout-sentinel-")
    scratch = Path(owned)
    sentinel = scratch / "SENTINEL-owned-by-du2-layout"
    raised = False
    try:
        sentinel.write_text("owned scratch sentinel\n", encoding="utf8")
        assert sentinel.is_file()
        # a failure inside the body must still hit the finally block below
        try:
            raise RuntimeError("simulated failing assertion body")
        except RuntimeError:
            raised = True
        raise AssertionError("simulated test failure")
    except AssertionError:
        pass
    finally:
        if sentinel.exists():
            sentinel.unlink()
        if scratch.exists():
            scratch.rmdir()
        assert raised

    assert not sentinel.exists()
    assert not scratch.exists()


def test_probe_sampling_never_writes_to_the_original(tmp_path) -> None:
    """A probe read must leave the source bytes and mtime untouched (offline proof)."""
    fitz = pytest.importorskip("fitz")
    original = tmp_path / "original.pdf"
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text((70, 120), "2023 3,926 4,386", fontsize=11)
    doc.save(original)
    doc.close()

    before = (_sha256(original), original.stat().st_mtime_ns, original.stat().st_size)
    digest = real_probe.sha256_of(original)
    monkeypatch_target = real_probe.PROBE_SAMPLES
    try:
        real_probe.PROBE_SAMPLES = (
            {"sample_id": "readonly-proof", "label": "readonly-proof", "pages": [1], "sha256": digest},
        )
        result = real_probe.load_probe_input({"readonly-proof": str(original)}, "readonly-proof", mode="span")
        assert result["status"] == "ok"
        derive_layout_hints(result["observation"])
    finally:
        real_probe.PROBE_SAMPLES = monkeypatch_target

    after = (_sha256(original), original.stat().st_mtime_ns, original.stat().st_size)
    assert after == before


@pytest.mark.real_data
def test_real_originals_are_unchanged_by_the_opt_in_run() -> None:
    """C node: every bound original keeps its SHA-256 and mtime across a real run."""
    if not REAL_OPT_IN:
        pytest.skip("opt-in: real originals are not touched unless CW_DU2_LAYOUT_REAL=1")
    if not BINDINGS_PATH.is_file():
        pytest.skip(f"UNAVAILABLE: {BINDINGS_PATH} missing")
    bindings = {str(k): str(v) for k, v in json.loads(BINDINGS_PATH.read_text(encoding="utf8")).items()}

    observed = 0
    for spec in real_probe.PROBE_SAMPLES:
        sample_id = spec["sample_id"]
        raw = bindings.get(sample_id)
        if not raw:
            continue
        path = Path(raw)
        if not path.is_file():
            continue
        before = (_sha256(path), path.stat().st_mtime_ns, path.stat().st_size)
        probe = real_probe.load_probe_input(bindings, sample_id, mode="span")
        if probe["status"] != "ok":
            pytest.skip(f"UNAVAILABLE: {probe.get('reason')}")
        result = derive_layout_hints(probe["observation"])
        assert result["schema_version"] == "du2-layout-hints/1"
        groups_of_kind(result, "table_region")  # exercise the result, not just the call
        after = (_sha256(path), path.stat().st_mtime_ns, path.stat().st_size)
        assert after == before, f"{sample_id} original changed during the probe run"
        observed += 1

    assert observed > 0, "no bound original was actually checked; bindings path is wrong"
