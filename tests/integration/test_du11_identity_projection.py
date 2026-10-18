"""Real unchanged FF CLI -> CWP identity/query/open, isolated synthetic bytes."""

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from company_wiki.source_catalog import SecurityMasterStore, SecurityRecord
from unit.du11_identity_projection.test_identity_projection import indexed  # noqa: F401


FF = Path(os.environ.get("DU11_FILING_FETCH_ROOT", Path.home() / "Projects" / "filing-fetch"))
SRC = Path(__file__).resolve().parents[2] / "src"


@pytest.mark.parametrize("indexed,query", [("9896", "09896"), ("09896", "9896")], indirect=["indexed"])
def test_actual_ff_reuses_both_hk_representations_and_open_keeps_sha(indexed, query):  # noqa: F811
    catalog, reader, ref, raw, facts = indexed
    root = catalog.config.project_root
    before = raw.read_bytes()
    observed_sidecar = raw.with_name(raw.name + ".source.json").read_bytes()
    config = root / "config" / "source_catalog.yaml"
    config.parent.mkdir()
    config.write_text(json.dumps({"schema_version": "1.0", "catalog_dir": "catalog",
        "reusable_root_kinds": ["directory"], "roots": [{"root_id": "raw", "path": "lake",
            "kind": "directory", "adapter_id": "sidecar_filing_v1", "reusable_for_filing": True}]}), encoding="utf8")
    master = SecurityMasterStore(catalog.config.catalog_dir / "security_master")
    master.write_market("HK", [SecurityRecord(canonical_name="Acme", market="HK", exchange="HKEX",
        ticker="09896", security_id="09896", aliases=(), active=True, source_name="hkex",
        source_url="https://official.example.invalid/hk", source_record_id="09896", identifiers={})],
        retrieved_at="2026-10-18T00:00:00Z", sources=("https://official.example.invalid/hk",))
    connection = root / "connection.json"
    connection.write_text(json.dumps({"schema_version": "1.0", "company_wiki_root": str(root)}), encoding="utf8")
    request_file = root / "request.json"
    request_file.write_text(json.dumps({"schema_version": "2.0", "company_query": query,
        "market": "HK", "document_kind": "annual_report", "fiscal_year": 2024,
        "as_of_date": "2026-10-18", "filing_intent": "reuse_only"}), encoding="utf8")
    bootstrap = root / "bootstrap"
    bootstrap.mkdir()
    # Instrument failures only. No source service, CLI response or identity is mocked.
    (bootstrap / "sitecustomize.py").write_text(
        "import socket\nfrom pathlib import Path\n"
        "def blocked(*args, **kwargs):\n"
        "    Path(__file__).with_name('network-attempt').write_text('unexpected')\n"
        "    raise RuntimeError('DU11_OFFLINE_NETWORK_ATTEMPT')\n"
        "socket.socket.connect = blocked\nsocket.create_connection = blocked\n", encoding="utf8")
    env = {**os.environ, "PYTHONPATH": os.pathsep.join((str(SRC), str(bootstrap))),
           "PYTHONDONTWRITEBYTECODE": "1", "PYTHONUTF8": "1", "PYTHON_DOTENV_DISABLED": "1"}
    ff_source = FF / "scripts" / "fetch_filing.py"
    assert ff_source.is_file(), "integration requires readonly filing-fetch checkout or DU11_FILING_FETCH_ROOT"
    ff_before = hashlib.sha256(ff_source.read_bytes()).hexdigest()
    process = subprocess.run([sys.executable, "-B", "-X", "utf8", str(ff_source),
        "--config", str(connection), "--request-file", str(request_file), "--source-ref-v2"],
        cwd=root, env=env, capture_output=True, timeout=40, check=False)
    result = json.loads(process.stdout)
    assert process.returncode == 0, (result, process.stderr.decode("utf8"))
    assert result["status"] == "source_candidate"
    assert result["calls"] == 2  # actual identify then DB-only query; never ensure/download
    assert result["downloads"] == 0
    assert result["filing"]["source_ref"]["content_sha256"] == ref.content_sha256
    assert result["filing"]["source_ref"]["document_id"] == ref.document_id
    assert reader.describe_candidate(ref)["security_id"] == "09896"
    assert reader.describe_version(ref)["security_id"] == facts["security_id"]
    command = [sys.executable, "-B", "-X", "utf8", "-m", "company_wiki.source_catalog.source_reader_cli",
        "--config", str(config), "--document-id", ref.document_id, "--source-id", ref.source_id,
        "--content-sha256", ref.content_sha256, "--purpose", "filing_reuse"]
    opened = subprocess.run(command, cwd=root, env=env, capture_output=True, timeout=20, check=False)
    assert opened.returncode == 0, opened.stderr
    receipt = json.loads(opened.stderr)
    assert receipt["status"] == "ok"
    assert receipt["manifest"]["security_id"] == facts["security_id"]
    assert opened.stdout == before
    assert hashlib.sha256(opened.stdout).hexdigest() == ref.content_sha256
    raw.write_bytes(b"X" * len(before))
    try:
        tampered = subprocess.run(command, cwd=root, env=env, capture_output=True, timeout=20, check=False)
        assert tampered.returncode == 2
        assert tampered.stdout == b""
        assert json.loads(tampered.stderr)["status"] == "unavailable"
    finally:
        raw.write_bytes(before)
    assert raw.with_name(raw.name + ".source.json").read_bytes() == observed_sidecar
    assert not (bootstrap / "network-attempt").exists()
    assert hashlib.sha256(ff_source.read_bytes()).hexdigest() == ff_before
