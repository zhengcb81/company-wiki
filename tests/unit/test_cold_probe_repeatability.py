"""An explicit diagnostic rerun needs fresh output, not a revision permit."""
import json
import sys

import pytest

from tools.pdf_runtime_probe import run_cold_probe as probe


@pytest.mark.parametrize("archived", [False, True])
def test_explicit_probe_rerun_preserves_prior_receipts_without_revision_bump(tmp_path, monkeypatch, archived):
    receipts = tmp_path / "receipts"
    receipts.mkdir()
    marker = receipts / "cold-rev5.marker.json"
    if archived:
        marker.write_bytes(b"old observation")
    profile = tmp_path / "profile.json"
    profile.write_text(json.dumps({"python": sys.executable, "artifacts": [],
        "max_memory_bytes": 128000000, "environment_sha256": "a" * 64,
        "docling_version": "synthetic"}), encoding="utf-8")
    monkeypatch.setattr(sys, "argv", [str(probe.__file__), "--profile", str(profile),
        "--receipts-dir", str(receipts), "--deadline", "0.7"])
    monkeypatch.setattr(probe, "child_launch_command", lambda binary, child: [binary, str(child)])
    monkeypatch.setattr(probe, "child_environment", lambda **_kwargs: {})
    calls = []
    def child(_command, **kwargs):
        calls.append(kwargs)
        return {"stdout": b'{"stage":"DONE","active":"DONE_NO_DOCUMENT"}\n', "stderr": b""}
    monkeypatch.setattr(probe, "run_bounded", child)
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    original = probe.tempfile.mkdtemp
    def own_scratch(*args, **kwargs):
        if kwargs.get("dir") is None:
            kwargs["dir"] = str(scratch)
        return original(*args, **kwargs)
    monkeypatch.setattr(probe.tempfile, "mkdtemp", own_scratch)
    probe.main()
    probe.main()
    outputs = list(receipts.glob("cold-rev5-*/cold-rev5.json"))
    assert len(outputs) == 2 and outputs[0].parent != outputs[1].parent
    assert len(calls) == 2 and all(call["timeout_seconds"] == .7 for call in calls)
    assert all(call["stdout_cap_bytes"] == 2*1024*1024 for call in calls)
    assert not list(scratch.iterdir())
    for path in outputs:
        result = json.loads(path.read_text(encoding="utf-8"))
        assert result["done_no_document"] and result["scratch_restored_absent"]
    if archived:
        assert marker.read_bytes() == b"old observation"
