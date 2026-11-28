"""Accept FF short CLI observations through the public CWP and ROOT boundaries."""

from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys

import pytest

from . import test_m3_acquisition_usage_cwp as metered_provider
from tools.document_understanding_benchmark.phase_c_runner import seed_identity
from tools.feedback_loop.coordinator import advance
from tools.feedback_loop.local_host import LocalHost
from tools.feedback_loop.observations import read_batch


pytestmark = [pytest.mark.requires_owner]


ROOT = Path(__file__).resolve().parents[2]
PY = [sys.executable, "-B", "-X", "utf8"]
loopback = metered_provider.loopback


def test_ff_short_intake_preserves_owner_usage_and_never_opens_a_native_job(tmp_path, loopback, monkeypatch):
    setting = os.environ.get("FEEDBACK_FF_CODE_ROOT")
    if not setting:
        pytest.skip("set FEEDBACK_FF_CODE_ROOT to the F2-FF-SHORT checkout")
    ff = Path(setting)
    cli = ff / "scripts/fetch_filing.py"
    assert cli.is_file()

    catalog, acquisition, provider_log, _ = metered_provider._fixture_root(tmp_path, "ok")
    seed_identity(tmp_path, "loopback", {"market": "US"})
    http_calls = []
    serve = loopback.RequestHandlerClass.do_GET

    def counted(handler):
        http_calls.append(handler.path)
        serve(handler)

    monkeypatch.setattr(loopback.RequestHandlerClass, "server_mode", "ok")
    monkeypatch.setattr(loopback.RequestHandlerClass, "do_GET", counted)
    environment = {**os.environ, "PYTHONPATH": str(ROOT / "src"),
                   "M3_LOOPBACK_BASE_URL": f"http://127.0.0.1:{loopback.server_address[1]}"}
    commands = {name: [*PY, "-m", "company_wiki.source_catalog." + module, "--config", str(catalog)]
                for name, module in {"catalog": "cli", "query": "source_query_cli", "open": "source_reader_cli"}.items()}
    limits = {"max_bytes": 20000, "timeout_seconds": 90, "max_cost_usd": "1.00"}
    config = tmp_path / "ff.json"
    config.write_text(json.dumps({"schema_version": "1.0", "connection": {
        "cwd": str(ROOT), "acquisition_config": str(acquisition), "commands": commands,
    }}), encoding="utf-8")

    def fetch(request, destination):
        output = subprocess.run([*PY, str(cli), "--config", str(config)], cwd=tmp_path,
                                input=json.dumps(request).encode("utf-8"), capture_output=True, timeout=45,
                                env={**environment, "RESEARCH_FEEDBACK_OUT": str(destination)}, check=False)
        assert output.returncode == 0, (output.stdout, output.stderr)
        return json.loads(output.stdout)

    request = {"schema_version": "2.0", "company_query": "ACME", "market": "US",
               "document_kind": "annual_report", "as_of_date": "2026-10-10", "mode": "exact", "fiscal_year": 2025}
    first_sidecar, reuse_sidecar = tmp_path / "first.jsonl", tmp_path / "reuse.jsonl"
    first = fetch({**request, "filing_intent": "fetch_if_missing", "acquisition_limits": limits}, first_sidecar)
    assert first["filing"]["resolution_outcome"] == "downloaded_new"
    assert first["acquisition_observation"]["http_exchanges"] == 3
    assert first["acquisition_observation"]["cost_usd"] == "0.0009"
    reused = fetch({**request, "filing_intent": "reuse_only"}, reuse_sidecar)
    assert reused["filing"]["resolution_outcome"] == "reused_existing"
    assert reused["filing"]["source_ref"]["content_sha256"] == first["filing"]["source_ref"]["content_sha256"]
    assert {(row["check_id"], row["actual"]) for row in read_batch([first_sidecar]).observations.values()} >= {
        ("request-outcome", "source_candidate/downloaded_new"), ("provider-usage", "known"), ("download-receipt", "1"),
    }
    assert {(row["check_id"], row["actual"]) for row in read_batch([reuse_sidecar]).observations.values()} >= {
        ("request-outcome", "source_candidate/reused_existing"), ("provider-start", "not_started"), ("download-receipt", "0"),
    }

    samples = sorted((ff / "docs/plans/f2-ff-short/samples").glob("sample-*.jsonl"))
    sample_rows = read_batch(samples)
    assert len(samples) == 6 and len(sample_rows.observations) == 27
    assert sum(row["disposition"] == "unknown" for row in sample_rows.observations.values()) == 2
    paths = [*samples, first_sidecar, reuse_sidecar]
    batch = read_batch(paths)
    assert batch.plan() == read_batch(paths + paths).plan()
    assert not batch.diagnostics and not batch.unfinished_starts()

    native_call = tmp_path / "native-call"
    settings = tmp_path / "host.json"
    trap = f"from pathlib import Path; Path({str(native_call)!r}).touch()"
    settings.write_text(json.dumps({"state": "actions.sqlite", "owners": {"filing-fetch": {
        "cwd": str(tmp_path), "ff_status_argv": [*PY, "-c", trap],
    }}}), encoding="utf-8")
    host = LocalHost(settings)

    def observe(_owner, action):
        assert action["kind"] == "observe" or (action["kind"], action["method"]) == ("reconcile", "lookup")
        return host.handle(action)

    accepted = advance(batch, observe)
    assert accepted == advance(read_batch(paths + paths), observe)
    assert sum(row["status"] == "unknown" for row in accepted["observations"]) == 2
    assert {row["status"] for row in accepted["observations"]} == {"expected", "unknown"}
    with closing(sqlite3.connect(tmp_path / "actions.sqlite")) as conn:
        assert conn.execute("SELECT COUNT(*) FROM actions").fetchone() == (len(batch.observations),)
    assert not native_call.exists()
    assert provider_log.read_text(encoding="utf-8").splitlines() == ["discover", "fetch"]
    assert http_calls == ["/meta1", "/meta2", "/body"]
