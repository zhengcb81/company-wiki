"""Cross-process budget forwarding for the CN adapter protocol."""

from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest

from company_wiki.source_catalog.download_budget import (
    AcquisitionBudget,
    AcquisitionBudgetExceeded,
)


_BOUNDED_ADAPTER = r"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

parser = argparse.ArgumentParser()
parser.add_argument("log_path")
parser.add_argument("action", choices=("discover", "fetch"))
parser.add_argument("--staging-dir")
args = parser.parse_args()
payload = json.loads(sys.stdin.read())
budget = payload["acquisition_budget"]
with open(args.log_path, "a", encoding="utf-8") as log:
    log.write(json.dumps({"action": args.action, "budget": budget}) + "\n")
identity = {"name": "bounded-json", "version": "1.0.0"}
body = b"%PDF-1.7\nbounded bridge"
usage = {
    "schema_version": "1.0",
    "response_bytes": 17 if args.action == "discover" else len(body),
    "cost_usd": "0",
}
if args.action == "discover":
    response = {
        "schema_version": "1.0", "status": "ok", "adapter": identity,
        "acquisition_usage": usage,
        "candidates": [{
            "candidate_id": "fake:2025", "provider": "cninfo",
            "provider_document_id": "2025", "market": "CN",
            "entity": "示例公司", "title": "示例公司2025年年度报告",
            "source_url": "https://example.invalid/report.pdf",
            "document_kind": "annual_report", "form_type": "annual_report",
            "filing_date": "2026-03-20", "fiscal_year": 2025,
            "fiscal_period": "FY", "language": "zh-CN", "amended": False,
            "transport_token": "opaque-value"
        }]
    }
else:
    raw = json.loads(payload["adapter_payload_json"])
    assert raw["transport_token"] == "opaque-value"
    path = Path(args.staging_dir) / "report.pdf"
    path.write_bytes(body)
    response = {
        "schema_version": "1.0", "status": "ok", "adapter": identity,
        "acquisition_usage": usage,
        "receipt": {
            "candidate_id": payload["candidate_id"],
            "provider": payload["provider"],
            "provider_document_id": payload["provider_document_id"],
            "source_url": payload["source_url"], "staged_path": str(path),
            "content_sha256": hashlib.sha256(body).hexdigest(),
            "byte_size": len(body), "mime_type": "application/pdf",
            "retrieved_at": "2026-07-18T12:00:00Z", "http_status": 200,
            "adapter_name": identity["name"], "adapter_version": identity["version"]
        }
    }
sys.stdout.write(json.dumps(response, ensure_ascii=False))
"""


def _request():
    from company_wiki.source_catalog import SourceRequest

    return SourceRequest(
        entity="示例公司",
        security_id="600000",
        market="CN",
        document_kind="annual_report",
        fiscal_year=2025,
        as_of_date="2026-07-18",
        allow_download=True,
    )


def test_bounded_json_adapter_passes_and_accumulates_one_shared_budget(tmp_path: Path):
    from company_wiki.source_catalog import JsonCommandAdapter

    project = tmp_path / "adapter"
    project.mkdir()
    script = project / "bounded_adapter.py"
    script.write_text(_BOUNDED_ADAPTER, encoding="utf-8")
    log_path = tmp_path / "calls.jsonl"
    adapter = JsonCommandAdapter(
        name="bounded-json",
        version="1.0.0",
        command=(sys.executable, str(script), str(log_path)),
        project_root=project,
        timeout_seconds=30,
        supports_acquisition_budget=True,
    )
    body_size = len(b"%PDF-1.7\nbounded bridge")
    budget = AcquisitionBudget.from_limits(
        max_response_bytes=17 + body_size,
        max_seconds=10,
        max_cost_usd="0",
    )

    candidates = adapter.discover_bounded(_request(), budget)
    receipt = adapter.fetch_bounded(candidates[0], tmp_path / "staging", budget)

    sent = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]
    assert [item["action"] for item in sent] == ["discover", "fetch"]
    assert sent[0]["budget"]["max_response_bytes"] == 17 + body_size
    assert sent[1]["budget"]["max_response_bytes"] == body_size
    assert sent[0]["budget"]["schema_version"] == "1.0"
    assert 0 < sent[0]["budget"]["timeout_seconds"] <= 10
    assert sent[0]["budget"]["max_cost_usd"] == "0"
    assert budget.response_bytes_used == 17 + body_size
    assert budget.remaining_cost_usd == 0
    assert Path(receipt.staged_path).read_bytes() == b"%PDF-1.7\nbounded bridge"


def test_bounded_json_adapter_fails_closed_when_usage_receipt_is_missing(tmp_path: Path):
    from company_wiki.source_catalog import JsonCommandAdapter
    from company_wiki.source_catalog.adapter_process import AdapterProcessError

    script = tmp_path / "missing_usage.py"
    script.write_text(
        _BOUNDED_ADAPTER.replace('        "acquisition_usage": usage,\n', ""),
        encoding="utf-8",
    )
    adapter = JsonCommandAdapter(
        name="bounded-json",
        version="1.0.0",
        command=(sys.executable, str(script), str(tmp_path / "calls.jsonl")),
        project_root=tmp_path,
        timeout_seconds=30,
        supports_acquisition_budget=True,
    )
    budget = AcquisitionBudget.from_limits(
        max_response_bytes=100,
        max_seconds=10,
        max_cost_usd="0",
    )

    with pytest.raises(AdapterProcessError, match="acquisition_usage"):
        adapter.discover_bounded(_request(), budget)

    assert budget.response_bytes_used == 0


def test_bounded_json_adapter_charges_partial_usage_reported_with_failure(
    tmp_path: Path,
):
    from company_wiki.source_catalog import JsonCommandAdapter
    from company_wiki.source_catalog.adapter_process import AdapterProcessError

    script = tmp_path / "partial_failure.py"
    script.write_text(
        """import json, sys
sys.stderr.write(json.dumps({
    'schema_version': '1.0', 'status': 'failed',
    'adapter': {'name': 'bounded-json', 'version': '1.0.0'},
    'error': {
        'code': 'budget_exceeded', 'retryable': False,
        'acquisition_usage': {
            'schema_version': '1.0', 'response_bytes': 23, 'cost_usd': '0'
        }
    }
}) + '\\n')
raise SystemExit(1)
""",
        encoding="utf-8",
    )
    adapter = JsonCommandAdapter(
        name="bounded-json",
        version="1.0.0",
        command=(sys.executable, str(script)),
        project_root=tmp_path,
        timeout_seconds=30,
        supports_acquisition_budget=True,
    )
    budget = AcquisitionBudget.from_limits(
        max_response_bytes=100,
        max_seconds=10,
        max_cost_usd="0",
    )

    with pytest.raises(AdapterProcessError) as exc:
        adapter.discover_bounded(_request(), budget)

    assert exc.value.error_code == "budget_exceeded"
    assert exc.value.retryable is False
    assert budget.response_bytes_used == 23


def test_bounded_json_adapter_accounts_failure_usage_after_deadline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    import time

    from company_wiki.source_catalog import JsonCommandAdapter
    from company_wiki.source_catalog.adapter_process import AdapterProcessError

    adapter = JsonCommandAdapter(
        name="bounded-json",
        version="1.0.0",
        command=(sys.executable, "unused.py"),
        project_root=tmp_path,
        timeout_seconds=30,
        supports_acquisition_budget=True,
    )
    budget = AcquisitionBudget.from_limits(
        max_response_bytes=100,
        max_seconds=10,
        max_cost_usd="0.50",
    )

    def _fail_after_deadline(action, payload, **kwargs):
        budget.deadline_monotonic = time.monotonic() - 1
        error = AdapterProcessError("provider exhausted its deadline")
        error.acquisition_usage = {
            "schema_version": "1.0",
            "response_bytes": 23,
            "cost_usd": "0.25",
        }
        raise error

    monkeypatch.setattr(adapter, "_run", _fail_after_deadline)

    with pytest.raises(AdapterProcessError, match="provider exhausted"):
        adapter.discover_bounded(_request(), budget)

    assert budget.response_bytes_used == 23
    assert budget.cost_usd_used == 0.25
    with pytest.raises(AcquisitionBudgetExceeded, match="deadline"):
        adapter.discover_bounded(_request(), budget)


def test_bounded_json_adapter_rejects_reported_usage_over_remaining_cap(tmp_path: Path):
    from company_wiki.source_catalog import JsonCommandAdapter

    script = tmp_path / "over_cap.py"
    source = _BOUNDED_ADAPTER.replace(
        '"response_bytes": 17 if args.action == "discover" else len(body),',
        '"response_bytes": budget["max_response_bytes"] + 1,',
    )
    script.write_text(source, encoding="utf-8")
    adapter = JsonCommandAdapter(
        name="bounded-json",
        version="1.0.0",
        command=(sys.executable, str(script), str(tmp_path / "calls.jsonl")),
        project_root=tmp_path,
        timeout_seconds=30,
        supports_acquisition_budget=True,
    )
    budget = AcquisitionBudget.from_limits(
        max_response_bytes=100,
        max_seconds=10,
        max_cost_usd="0",
    )

    with pytest.raises(AcquisitionBudgetExceeded):
        adapter.discover_bounded(_request(), budget)

    assert budget.response_bytes_used == 101


def test_bounded_json_adapter_uses_remaining_time_as_process_deadline(
    tmp_path: Path,
):
    import time

    from company_wiki.source_catalog import JsonCommandAdapter
    from company_wiki.source_catalog.adapter_process import AdapterProcessError

    script = tmp_path / "slow_adapter.py"
    script.write_text(
        "import time\ntime.sleep(2)\n",
        encoding="utf-8",
    )
    adapter = JsonCommandAdapter(
        name="bounded-json",
        version="1.0.0",
        command=(sys.executable, str(script)),
        project_root=tmp_path,
        timeout_seconds=30,
        supports_acquisition_budget=True,
    )
    budget = AcquisitionBudget.from_limits(
        max_response_bytes=100,
        max_seconds=0.15,
        max_cost_usd="0",
    )
    started = time.monotonic()

    with pytest.raises(AdapterProcessError, match="process failed"):
        adapter.discover_bounded(_request(), budget)

    assert time.monotonic() - started < 1.25


def test_optional_wire_observation_preserves_entity_receipt_and_shared_remaining_cap(tmp_path):
    from company_wiki.source_catalog import JsonCommandAdapter
    project = tmp_path / "compressed"
    project.mkdir()
    script = project / "adapter.py"
    source = _BOUNDED_ADAPTER.replace('        "acquisition_usage": usage,',
        '        "acquisition_usage": usage, "http_wire_bytes": 32 if args.action == "discover" else 9,')
    script.write_text(source, encoding="utf-8")
    log = tmp_path / "calls.jsonl"
    adapter = JsonCommandAdapter(name="bounded-json", version="1.0.0",
        command=(sys.executable, str(script), str(log)), project_root=project,
        timeout_seconds=30, supports_acquisition_budget=True)
    budget = AcquisitionBudget.from_limits(max_response_bytes=100, max_seconds=10, max_cost_usd="0")
    candidate = adapter.discover_bounded(_request(), budget)[0]
    receipt = adapter.fetch_bounded(candidate, tmp_path / "staging", budget)
    sent = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()]
    assert sent[1]["budget"]["max_response_bytes"] == 68
    assert budget.response_bytes_used == 17 + receipt.byte_size
    assert budget.wire_response_bytes_used == 41 and budget.wire_usage_complete
    assert receipt.byte_size > 9 and Path(receipt.staged_path).read_bytes().startswith(b"%PDF")


@pytest.mark.parametrize("wire", [None, True, -1, "12"])
def test_missing_or_bad_optional_wire_observation_keeps_real_entity_and_cost(wire):
    from decimal import Decimal
    from company_wiki.source_catalog.adapter_process import JsonCommandAdapter
    b = AcquisitionBudget.from_limits(max_response_bytes=100, max_seconds=10, max_cost_usd="1")
    response = {"acquisition_usage": {"schema_version": "1.0", "response_bytes": 23, "cost_usd": "0.25"}}
    if wire is not None:
        response["http_wire_bytes"] = wire
    JsonCommandAdapter._charge_bounded_usage(response, b)
    assert b.response_bytes_used == 23 and b.cost_usd_used == Decimal("0.25")
    assert not b.wire_usage_complete and b.wire_response_bytes_used == 0
    b.ensure_new_request()  # Missing observation is not a new permission gate.


def test_wire_overage_keeps_already_reported_entity_and_fee():
    from decimal import Decimal
    from company_wiki.source_catalog.adapter_process import JsonCommandAdapter
    b = AcquisitionBudget.from_limits(max_response_bytes=100, max_seconds=10, max_cost_usd="1")
    response = {"acquisition_usage": {"schema_version": "1.0", "response_bytes": 23, "cost_usd": "0.25"},
                "http_wire_bytes": 101}
    with pytest.raises(AcquisitionBudgetExceeded, match="byte budget"):
        JsonCommandAdapter._charge_bounded_usage(response, b)
    assert b.response_bytes_used == 23 and b.cost_usd_used == Decimal("0.25")
    assert b.wire_response_bytes_used == 101


def test_failure_final_wire_receipt_is_not_replaced_by_earlier_checkpoint(tmp_path):
    import subprocess
    from decimal import Decimal
    from company_wiki.source_catalog.adapter_process import JsonCommandAdapter, AdapterProcessError
    adapter = JsonCommandAdapter(name="bounded-json", version="1.0.0",
        command=(sys.executable, "unused.py"), project_root=tmp_path,
        supports_acquisition_budget=True)
    identity = {"name": "bounded-json", "version": "1.0.0"}
    progress = {"schema_version": "1.0", "status": "progress", "adapter": identity,
        "acquisition_usage": {"schema_version": "1.0", "response_bytes": 8, "cost_usd": "0"},
        "http_wire_bytes": 15}
    final = {"schema_version": "1.0", "status": "failed", "adapter": identity,
        "http_wire_bytes": 31,
        "error": {"code": "incomplete_response", "retryable": False,
                  "acquisition_usage": {"schema_version": "1.0", "response_bytes": 23, "cost_usd": "0.25"}}}
    completed = subprocess.CompletedProcess([], 1, "", json.dumps(progress)+"\n"+json.dumps(final))
    with pytest.raises(AdapterProcessError) as caught:
        adapter._decode_response(completed, "fetch")
    b = AcquisitionBudget.from_limits(max_response_bytes=100, max_seconds=10, max_cost_usd="1")
    adapter._charge_failure_usage(caught.value, b)
    assert b.response_bytes_used == 23 and b.cost_usd_used == Decimal("0.25")
    assert b.wire_response_bytes_used == 31 and b.wire_usage_complete


def test_hard_kill_checkpoint_charges_last_cumulative_wire_once(tmp_path):
    from company_wiki.source_catalog.adapter_process import JsonCommandAdapter, AdapterProcessError
    adapter = JsonCommandAdapter(name="bounded-json", version="1.0.0",
        command=(sys.executable, "unused.py"), project_root=tmp_path,
        supports_acquisition_budget=True)
    identity = {"name": "bounded-json", "version": "1.0.0"}
    lines = [json.dumps({"schema_version": "1.0", "status": "progress", "adapter": identity,
        "acquisition_usage": {"schema_version": "1.0", "response_bytes": entity, "cost_usd": "0"},
        "http_wire_bytes": wire}) for entity, wire in [(0,0),(5,10),(8,15)]]
    exc = AdapterProcessError("hard stopped")
    adapter._attach_usage_checkpoint(exc, "\n".join(lines)+'\n{"truncated":')
    b = AcquisitionBudget.from_limits(max_response_bytes=100, max_seconds=10, max_cost_usd="0")
    adapter._charge_failure_usage(exc, b)
    assert b.response_bytes_used == 8 and b.wire_response_bytes_used == 15
    assert not b.usage_complete and not b.wire_usage_complete
    assert exc.acquisition_usage_complete is False and exc.retryable is False
