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


RAW_BODY = b"Fixture original annual report. The company provides devices and services.\n"


PROVIDER = r'''
import argparse, hashlib, json, sys, time
from pathlib import Path
p=argparse.ArgumentParser()
p.add_argument('mode');p.add_argument('log');p.add_argument('action');p.add_argument('--staging-dir')
a=p.parse_args()
request=json.loads(sys.stdin.read())
log=Path(a.log)
entries=log.read_text().splitlines() if log.exists() else []
with log.open('a',encoding='utf-8') as f:f.write(a.action+'\n')
identity={'name':'proof-cli','version':'1.0.0'}
def usage(n,c='0.01'):return {'schema_version':'1.0','response_bytes':n,'cost_usd':c}
def fail(n,c='0.01'):
 sys.stderr.write(json.dumps({'schema_version':'1.0','status':'failed','adapter':identity,
  'error':{'code':'upstream_unavailable','retryable':True,'message':'never-copy-secret?api_key=bad','acquisition_usage':usage(n,c)}})+'\n')
 raise SystemExit(1)
def progress(n):
 sys.stderr.write(json.dumps({'schema_version':'1.0','status':'progress','adapter':identity,'acquisition_usage':usage(n,'0.02')})+'\n');sys.stderr.flush()
if a.mode=='discover-fail':fail(17)
if a.action=='discover':
 result={'schema_version':'1.0','status':'ok','adapter':identity,'acquisition_usage':usage(17),
  'candidates':[{'candidate_id':'one','provider':'sec','provider_document_id':'accession-one','market':'US',
   'entity':request['entity'],'title':'Fixture 2025 Annual Report','source_url':'https://www.sec.gov/fixture.txt',
   'document_kind':'annual_report','form_type':'10-K','filing_date':'2026-03-20','fiscal_year':2025,'fiscal_period':'FY','language':'en'}]}
else:
 if a.mode=='retry-fail':fail(9*(entries.count('fetch')+1))
 if a.mode=='timeout-checkpoint':progress(19);time.sleep(30)
 if a.mode=='timeout-unknown':time.sleep(30)
 if a.mode=='output':progress(19);sys.stderr.write('x'*1200000);sys.stderr.flush();time.sleep(30)
 body=b'Fixture original annual report. The company provides devices and services.\n'
 path=Path(a.staging_dir)/'report.txt';path.write_bytes(body)
 result={'schema_version':'1.0','status':'ok','adapter':identity,'acquisition_usage':usage(len(body)),
  'receipt':{'candidate_id':request['candidate_id'],'provider':request['provider'],'provider_document_id':request['provider_document_id'],
   'source_url':request['source_url'],'staged_path':str(path),'content_sha256':hashlib.sha256(body).hexdigest(),
   'byte_size':len(body),'mime_type':'text/plain','retrieved_at':'2026-10-09T12:00:00Z','http_status':200,
   'adapter_name':identity['name'],'adapter_version':identity['version']}}
 if a.mode=='bad-receipt':result['receipt']['content_sha256']='0'*64
sys.stdout.write(json.dumps(result))
'''


def fixture_root(root: Path, mode: str):
    (root / "config").mkdir()
    (root / "companies").mkdir()
    script = root / "provider.py"
    script.write_text(PROVIDER, encoding="utf-8", newline="\n")
    log = root / "provider_calls.txt"
    catalog = root / "config" / "source_catalog.yaml"
    catalog.write_text(json.dumps({"schema_version": "1.0", "catalog_dir": str(root/"catalog"),
        "roots": [{"root_id": "company_raw", "kind": "company_raw", "path": str(root/"companies"), "priority": 10}]}), encoding="utf-8")
    spec = {"name": "proof-cli", "version": "1.0.0", "interface": "json_command_v1", "project_root": str(root),
            "config_root": None, "command": [sys.executable, "-B", str(script), mode, str(log)], "supports_acquisition_budget": True}
    acquisition = root / "config" / "source_acquisition.yaml"
    acquisition.write_text(json.dumps({"schema_version": "1.1", "staging_root": str(root/"staging"),
        "timeout_seconds": 5, "adapters": {m: dict(spec, interface="json_command_v1" if m == "cn" else "dayu_sdk_bounded_v1") for m in ("cn", "hk", "us")}}), encoding="utf-8")
    return catalog, acquisition, log


def cli(root: Path, mode: str, *, latest=False, v2=False, close_gap=False):
    catalog, acquisition, log = fixture_root(root, mode)
    args = [sys.executable, "-X", "utf8", "-B", "-m", "company_wiki.source_catalog.cli", "--config", str(catalog),
        "close-gap" if close_gap else "ensure", "--entity", "Fixture", "--market", "US", "--security-id", "FIXTURE",
        "--document-kind", "annual_report", "--fiscal-year", "2025", "--as-of-date", "2026-10-09",
        "--max-download-bytes", "10000", "--max-download-seconds", "2", "--max-download-cost-usd", "1",
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
        result = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", env=env, timeout=15, check=False)
        assert result.returncode == 1, (result.stdout, result.stderr)
        value = json.loads(result.stderr)
        dto = value["acquisition_failure"]
        assert dto["code"] == code
        assert dto["provider_started"] is started and dto["usage_complete"] is complete
        assert dto["acquisition_usage"]["response_bytes"] == byte_count
        assert dto["usage_scope"] == "operation"
        assert "secret" not in json.dumps(dto) and "staged_path" not in json.dumps(dto)
        calls = log.read_text().splitlines()
        assert calls.count("fetch") == (3 if mode == "retry-fail" else 0 if mode == "discover-fail" else 1)
        assert not list((root/"companies").rglob("*.txt"))
        assert not list((root/"staging").rglob("*.txt"))
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("latest,v2,close_gap", [(True, False, False), (True, True, False), (False, False, True)])
def test_returned_failure_has_same_top_level_dto_and_legacy_status(tmp_path, latest, v2, close_gap):
    with TemporaryDirectory(prefix="returned-", dir=tmp_path) as temporary:
        args, env, _ = cli(Path(temporary), "discover-fail", latest=latest, v2=v2, close_gap=close_gap)
        result = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", env=env, timeout=15, check=False)
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
        first = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", env=env, timeout=15, check=False)
        assert first.returncode == 0, first.stderr
        before = {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in (root/"companies").rglob("*") if p.is_file()}
        assert before
        second = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", env=env, timeout=15, check=False)
        assert second.returncode == 0, second.stderr
        a, b = json.loads(first.stdout), json.loads(second.stdout)
        assert a["source_ref"] == b["source_ref"]
        assert "acquisition_failure" not in a and "acquisition_failure" not in b
        assert log.read_text().splitlines() == ["discover", "fetch"]
        after = {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
                 for p in (root/"companies").rglob("*") if p.is_file()}
        assert after == before
    assert not list(tmp_path.iterdir())
