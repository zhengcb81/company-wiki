"""Real CWP CLI -> isolated fake provider; originals and temp baseline preserved."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory

import pytest


from support.acquisition_cli_fixture import RAW_BODY, fixture_root

def cli(root: Path, mode: str, *, latest=False, v2=False, close_gap=False):
    catalog, acquisition, log = fixture_root(root, mode)
    args = [sys.executable, "-X", "utf8", "-B", "-m", "company_wiki.source_catalog.cli", "--config", str(catalog),
        "close-gap" if close_gap else "ensure", "--entity", "Fixture", "--market", "US", "--security-id", "FIXTURE",
        "--document-kind", "annual_report", "--fiscal-year", "2025", "--as-of-date", "2026-10-09",
        # The fixture adapter times out after 5 seconds on its hanging routes.
        # Leave the operation enough time to reach fetch after discovery.
        "--max-download-bytes", "10000", "--max-download-seconds", "15", "--max-download-cost-usd", "1",
        "--acquisition-config", str(acquisition)]
    if not close_gap:
        args += ["--allow-download"]
    else:
        binding = root / "binding.json"
        binding.write_text(json.dumps({"provider": "sec", "allowed_accessions": ["accession-one"]}), encoding="utf-8")
        args += ["--binding-file", str(binding)]
    if latest:
        args += ["--mode", "latest_as_of"]
    if v2:
        args += ["--source-ref-v2"]
    env = dict(os.environ)
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[2]/"src")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return args, env, log


@pytest.mark.parametrize("mode,code,started,complete,byte_count", [
    ("discover-fail", "upstream_unavailable", True, True, 17),
    ("missing-security", "acquisition_validation_failed", True, True, 17),
    ("retry-fail", "upstream_unavailable", True, True, 17+9+18+27),
    ("timeout-checkpoint", "adapter_timeout", True, False, 17+19),
    # Discovery already proved target execution, so whole-operation started remains true.
    ("timeout-unknown", "adapter_timeout", True, False, 17),
    ("output", "adapter_output_limit", True, False, 17+19),
    ("bad-receipt", "acquisition_validation_failed", True, True, 17+len(RAW_BODY)),
])
def test_real_cli_failure_proofs_and_cleanup(tmp_path, mode, code, started, complete, byte_count):
    assert not list(tmp_path.iterdir())
    with TemporaryDirectory(prefix="failure-", dir=tmp_path) as temporary:
        root = Path(temporary)
        args, env, log = cli(root, mode)
        result = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", env=env, timeout=25, check=False)
        assert result.returncode == 1, (result.stdout, result.stderr)
        value = json.loads(result.stderr)
        dto = value["acquisition_failure"]
        assert dto["code"] == code
        assert dto["provider_started"] is started and dto["usage_complete"] is complete
        assert dto["acquisition_usage"]["response_bytes"] == byte_count
        assert dto["usage_scope"] == "operation"
        assert "secret" not in json.dumps(dto) and "staged_path" not in json.dumps(dto)
        calls = log.read_text().splitlines()
        assert calls.count("fetch") == (3 if mode == "retry-fail" else 0 if mode in {"discover-fail", "missing-security"} else 1)
        assert not list((root/"companies").rglob("*.txt"))
        assert not list((root/"staging").rglob("*.txt"))
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("latest,v2,close_gap", [(True, False, False), (True, True, False), (False, False, True)])
def test_returned_failure_has_same_top_level_dto_and_legacy_status(tmp_path, latest, v2, close_gap):
    with TemporaryDirectory(prefix="returned-", dir=tmp_path) as temporary:
        args, env, _ = cli(Path(temporary), "discover-fail", latest=latest, v2=v2, close_gap=close_gap)
        result = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", env=env, timeout=25, check=False)
        assert result.returncode == 0, result.stderr
        value = json.loads(result.stdout)
        assert value["status"] == ("failed" if close_gap else "gap")
        assert value["acquisition_failure"]["code"] == "upstream_unavailable"
        assert value["acquisition_failure"]["acquisition_usage"]["response_bytes"] == 17
        assert value["acquisition_failure"]["usage_complete"] is True
    assert not list(tmp_path.iterdir())


def test_success_import_then_reuse_preserves_original_and_has_no_failure(tmp_path):
    with TemporaryDirectory(prefix="success-", dir=tmp_path) as temporary:
        root = Path(temporary)
        args, env, log = cli(root, "ok", v2=True)
        first = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", env=env, timeout=25, check=False)
        assert first.returncode == 0, first.stderr
        before = {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in (root/"companies").rglob("*") if p.is_file()}
        assert before
        second = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", env=env, timeout=25, check=False)
        assert second.returncode == 0, second.stderr
        a, b = json.loads(first.stdout), json.loads(second.stdout)
        assert a["source_ref"] == b["source_ref"]
        assert "acquisition_failure" not in a and "acquisition_failure" not in b
        assert log.read_text().splitlines() == ["discover", "fetch"]
        after = {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
                 for p in (root/"companies").rglob("*") if p.is_file()}
        assert after == before
    assert not list(tmp_path.iterdir())
