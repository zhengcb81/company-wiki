"""One new control: malformed stdout cannot fabricate complete absent usage."""
import importlib.util
import json
from pathlib import Path


spec = importlib.util.spec_from_file_location("frozen_cutoff_probes", Path(__file__).resolve().parent.parent / "probes.py")
old = importlib.util.module_from_spec(spec)
spec.loader.exec_module(old)


def test_unknown_usage_stays_unknown_for_malformed_stdout(tmp_path, monkeypatch):
    obj, calls = old.transport(tmp_path, monkeypatch, b"[]", b"")
    result = obj._et_result(request=old.ff_request(), limits=old.limits())
    assert result["status"] == "provider_unavailable" and result["reason"] == "provider_result_invalid"
    assert result["provider_usage_complete"] is False
    assert result["provider_requests"] is None and result["provider_response_bytes"] is None
    assert result["provider_started"] is None
    assert len(calls) == 1 and "source_ref" not in result
    with Path(__file__).with_name("trace.jsonl").open("a", encoding="utf-8") as stream:
        stream.write(json.dumps({"kind": "malformed_stdout_unknown_usage_control", "output": result}) + "\n")
