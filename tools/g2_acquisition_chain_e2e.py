"""Offline real-CLI acquisition E2E; supplier I/O is explicitly a fixture.

Exercises FF v1/v2, the actual ET supervisor/worker with an injected HTTP
session, and CWP canonical import/read/reuse. Reads real originals, never
writes production, and restores the previously absent short test directory.
This is a milestone tool, not an additional daily CI matrix.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import yaml


ROOT = Path(__file__).resolve().parents[1]
PDF = ROOT / "companies/比亚迪/raw/financial_reports/annual/2025-03-24_cninfo_1222881496_2024年年度报告.pdf"
HTML = ROOT / "companies/MICROSOFT CORP/raw/financial_reports/annual/2026-07-29_sec_0001193125-26-323660_MICROSOFT CORP 10-K 2026-06-30.htm"

PROVIDER = '''import hashlib, json, os, sys
from pathlib import Path
action = sys.argv[1]
payload = json.loads(sys.stdin.read())
fixture = json.loads(Path(os.environ['G2_PROVIDER_FIXTURE']).read_text(encoding='utf-8'))
with Path(os.environ['G2_PROVIDER_LOG']).open('a', encoding='utf-8') as log:
    log.write(json.dumps({'action': action, 'budget': payload.get('acquisition_budget')}) + '\\n')
adapter = {'name': 'g2-fixture', 'version': '1.0.0'}
if action == 'discover':
    values = [fixture['candidate']]
    size = len(json.dumps(values, ensure_ascii=False).encode())
    result = {'candidates': values}
else:
    body = Path(fixture['original']).read_bytes()
    size = len(body)
    staging = Path(sys.argv[sys.argv.index('--staging-dir') + 1])
    path = staging / ('original' + Path(fixture['original']).suffix)
    path.write_bytes(body)
    result = {'receipt': {'schema_version': '1.0', 'candidate_id': payload['candidate_id'],
        'provider': payload['provider'], 'provider_document_id': payload['provider_document_id'],
        'source_url': payload['source_url'], 'staged_path': str(path), 'content_sha256': hashlib.sha256(body).hexdigest(),
        'byte_size': size, 'mime_type': fixture['mime_type'], 'retrieved_at': '2026-10-07T00:00:00Z',
        'http_status': 200, 'adapter_name': 'g2-fixture', 'adapter_version': '1.0.0'}}
assert size <= payload['acquisition_budget']['max_response_bytes']
print(json.dumps({'schema_version': '1.0', 'status': 'ok', 'adapter': adapter,
    'acquisition_usage': {'schema_version': '1.0', 'response_bytes': size, 'cost_usd': '0'}, **result}))
'''

HTTP = '''import json
from pathlib import Path
from urllib.parse import urlencode
class Response:
    status_code = 200
    headers = {'Content-Type': 'application/json'}
    def __init__(self, url, body): self.url, self.content = url, body
    def iter_content(self, chunk_size=65536):
        for start in range(0, len(self.content), chunk_size): yield self.content[start:start + chunk_size]
    def close(self): pass
    def raise_for_status(self): pass
    def __enter__(self): return self
    def __exit__(self, *args): self.close()
class Session:
    def __init__(self, spec): self.spec, self.headers = spec, {}
    def get(self, url, *args, **kwargs):
        assert url.startswith('https://financialmodelingprep.com/'), url
        with Path(self.spec['http_log']).open('a', encoding='utf-8') as log: log.write('GET\\n')
        effective_url = url + '?' + urlencode(kwargs.get('params', {}))
        return Response(effective_url, Path(self.spec['body_file']).read_bytes())
    def close(self): pass
def factory(spec, context): return Session(spec)
'''


def digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def fingerprints(paths):
    return {str(path): {"sha256": digest(path), "bytes": path.stat().st_size}
            for path in paths if path.is_file()}


def run(command, *, env, cwd, request=None):
    result = subprocess.run(command, input=None if request is None else json.dumps(request).encode(),
        cwd=cwd, env=env, capture_output=True, timeout=75)
    if result.returncode:
        raise RuntimeError(f"CLI failed ({result.returncode}): "
                           + result.stdout.decode("utf-8", errors="replace")
                           + result.stderr.decode("utf-8", errors="replace"))
    return json.loads(result.stdout)


def verified_read(catalog, ref, *, env, cwd, purpose="filing_reuse"):
    """Exercise the actual binary CLI and verify its returned buffer."""
    command = [sys.executable, "-m", "company_wiki.source_catalog.source_reader_cli",
        "--config", str(catalog), "--document-id", ref["document_id"],
        "--source-id", ref["source_id"], "--content-sha256", ref["content_sha256"],
        "--purpose", purpose]
    result = subprocess.run(command, env=env, cwd=cwd, capture_output=True, timeout=30)
    receipt = json.loads(result.stderr)
    assert result.returncode == 0 and receipt["status"] == "ok", receipt
    actual_sha = hashlib.sha256(result.stdout).hexdigest()
    assert actual_sha == ref["content_sha256"] == receipt["content_sha256"]
    assert len(result.stdout) == ref["byte_size"] == receipt["byte_size"]
    assert receipt["source_id"] == ref["source_id"]
    return {"status": "verified", "purpose": purpose, "source_id": ref["source_id"],
        "sha256": actual_sha, "byte_size": len(result.stdout),
        "source_read_policy_sha256": receipt["source_read_policy_sha256"]}


def make_wiki(root, spec, provider_script):
    (root / "config").mkdir(parents=True)
    (root / "companies").mkdir()
    catalog_dir = root / ".source_catalog"
    master_dir = catalog_dir / "security_master"
    master_dir.mkdir(parents=True)
    record = {"schema_version": "1.0", "active": True,
        "canonical_name": spec["entity"], "market": spec["market"], "exchange": spec["exchange"],
        "ticker": spec["security"], "security_id": spec["security"], "aliases": [spec["security"]],
        "identifiers": {}, "source_name": "offline-identity-fixture", "source_url": spec["url"],
        "source_record_id": "g2-identity-fixture"}
    (master_dir / (spec["market"].lower() + ".json")).write_text(json.dumps({
        "schema_version": "1.0", "market": spec["market"], "retrieved_at": "2026-10-07T00:00:00Z",
        "record_count": 1, "records": [record], "sources": [spec["url"]]}, ensure_ascii=False), encoding="utf-8")
    catalog_config = root / "config/source_catalog.yaml"
    catalog_config.write_text(yaml.safe_dump({"schema_version": "1.0", "catalog_dir": ".source_catalog",
        "roots": [{"root_id": "company_raw", "kind": "company_raw", "path": "companies",
                   "priority": 10, "adapter_id": "company_raw_v1", "read_only": False}]}), encoding="utf-8")
    adapters = {"cn": {"name": "g2-fixture", "version": "1.0.0", "interface": "json_command_v1",
        "supports_acquisition_budget": True, "project_root": str(root), "config_root": None,
        "command": [sys.executable, str(provider_script)]}}
    # The real HK/US route is Dayu and cannot enforce a response-byte budget.
    # Keep that capability boundary; never fake a bounded Dayu implementation.
    for market in ("hk", "us"):
        adapters[market] = {"name": "offline-dayu-unused", "version": "1.0.0",
            "interface": "dayu_cli_v1", "supports_acquisition_budget": False,
            "project_root": str(root), "config_root": str(root / "config"),
            "command": [sys.executable, "-c", "raise SystemExit('unexpected Dayu invocation')"]}
    (root / "config/source_acquisition.yaml").write_text(yaml.safe_dump({
        "schema_version": "1.1", "staging_root": str(root / ".source_catalog/staging"),
        "timeout_seconds": 60, "adapters": adapters}), encoding="utf-8")
    return catalog_config


def case(parent, spec, ff_root, et_root, env):
    root = parent / (spec["market"].lower() + spec["schema"].replace(".", ""))
    provider = parent / "provider.py"
    catalog = make_wiki(root, spec, provider)
    fixture = root / "provider.json"
    log = root / "provider.log"
    candidate = {"candidate_id": spec["accession"], "provider": spec["provider"],
        "provider_document_id": spec["accession"], "market": spec["market"], "entity": spec["entity"],
        "title": spec["title"], "source_url": spec["url"], "document_kind": "annual_report",
        "form_type": "annual_report", "filing_date": spec["date"], "fiscal_year": spec["year"],
        "fiscal_period": "FY", "language": spec["language"]}
    fixture.write_text(json.dumps({"candidate": candidate, "original": str(spec["original"]),
                                  "mime_type": spec["mime"]}, ensure_ascii=False), encoding="utf-8")
    local_env = dict(env, G2_PROVIDER_FIXTURE=str(fixture), G2_PROVIDER_LOG=str(log))
    if spec.get("local_reuse"):
        target = root / "companies" / spec["entity"] / "raw/financial_reports/annual" / spec["original"].name
        target.parent.mkdir(parents=True)
        shutil.copyfile(spec["original"], target)
        target.with_name(target.name + ".source.json").write_text(json.dumps({
            "market": spec["market"], "security_id": spec["security"],
            "source_title": spec["title"], "provider": spec["provider"],
            "provider_document_id": spec["accession"], "source_url": spec["url"],
            "published_date": spec["date"], "fiscal_year": spec["year"], "form_type": "FY"}),
            encoding="utf-8")
    run([sys.executable, "-m", "company_wiki.source_catalog.cli", "--config", str(catalog),
         "scan", "--root-id", "company_raw"], env=local_env, cwd=root)
    run([sys.executable, "-m", "company_wiki.source_catalog.cli", "--config", str(catalog),
         "identify", "--query", spec["security"], "--market", spec["market"]], env=local_env, cwd=root)
    ff_config = parent / (spec["market"] + ".json")
    ff_config.write_text(json.dumps({"schema_version": "1.0", "company_wiki_root": str(root)}), encoding="utf-8")
    request = {"schema_version": spec["schema"], "company_query": spec["security"], "market": spec["market"],
        "document_kind": "annual_report", "mode": "exact" if spec.get("local_reuse") else "latest_as_of",
        "as_of_date": "2026-10-07",
        "acquisition_limits": {"max_bytes": spec["original"].stat().st_size + 1048576,
                               "timeout_seconds": 60, "max_cost_usd": "0"}}
    command = [sys.executable, str(ff_root / "scripts/fetch_filing.py"), "--config", str(ff_config),
               "--timeout-seconds", "70"]
    if spec["schema"] == "1.2":
        command.append("--allow-download")
    else:
        request["filing_intent"] = "fetch_if_missing"
    if spec.get("local_reuse"):
        request["fiscal_year"] = spec["year"]
    if spec.get("companion"):
        command[1] = str(parent / "ff_cli.py")
        request["companion_transcript"] = {"intent": "fetch_if_missing", "fiscal_year": 2026,
            "fiscal_quarter": 4, "provider": "fmp", "acquisition_limits": {
                "max_bytes": 1048576, "timeout_seconds": 30, "max_cost_usd": "0.01"}}
        local_env["EARNINGS_TRANSCRIPTS_TOOL"] = str(parent / "et_cli.py")
    try:
        first = run(command, env=local_env, cwd=ff_root, request=request)
    except RuntimeError as exc:
        # Failed fixture runs may replay ensure for diagnostics; successful
        # runs never add a second acquisition call or alter the count oracle.
        debug_command = [sys.executable, "-m", "company_wiki.source_catalog.cli",
            "--config", str(catalog), "ensure", "--company-query", spec["security"],
            "--market", spec["market"], "--document-kind", "annual_report",
            "--mode", request["mode"], "--as-of-date", "2026-10-07", "--allow-download",
            "--max-download-bytes", str(request["acquisition_limits"]["max_bytes"]),
            "--max-download-seconds", "60", "--max-download-cost-usd", "0"]
        if spec["schema"] == "2.0":
            debug_command.append("--source-ref-v2")
        if request.get("fiscal_year"):
            debug_command.extend(["--fiscal-year", str(request["fiscal_year"])])
        debug = subprocess.run(debug_command,
            cwd=root, env=local_env, capture_output=True, timeout=65)
        raise RuntimeError(str(exc) + "; diagnostic ensure replay: "
            + debug.stdout.decode("utf-8", errors="replace")
            + debug.stderr.decode("utf-8", errors="replace")) from exc
    before = fingerprints(path for path in (root / "companies").rglob("*") if path.is_file())
    second = run(command, env=local_env, cwd=ff_root, request=request)
    assert fingerprints(path for path in (root / "companies").rglob("*") if path.is_file()) == before
    actions = [json.loads(line)["action"] for line in log.read_text(encoding="utf-8").splitlines()] if log.is_file() else []
    assert actions == ([] if spec.get("local_reuse") else ["discover", "fetch", "discover"]), actions
    assert first["downloads"] == (0 if spec.get("local_reuse") else 1) and second["downloads"] == 0, (first, second)
    if spec["schema"] == "1.2":
        a, b = first["handle"], second["handle"]
        assert a["source_id"] == b["source_id"]
        assert a["content_sha256"] == digest(spec["original"])
        assert digest(Path(a["canonical_path"])) == digest(spec["original"])
    else:
        a, b = first["filing"], second["filing"]
        assert a["source_ref"] == b["source_ref"]
        assert a["source_ref"]["content_sha256"] == digest(spec["original"])
        assert str(parent) not in json.dumps(first)
    ref = a if spec["schema"] == "1.2" else a["source_ref"]
    filing_read = verified_read(catalog, ref, env=local_env, cwd=root)
    transcript_read = None
    unsupported_status = None
    if spec.get("companion"):
        # FMP supplies a call date, not a verified publication date. Capture
        # the raw response and preserve that distinction on the second query.
        trace = (parent / "child-errors.jsonl").read_text(encoding="utf-8") if (parent / "child-errors.jsonl").exists() else ""
        assert first["transcript"]["status"] == "downloaded", (first, trace)
        assert first["transcript"]["publication_date"] is None
        assert first["transcript"]["as_of_cutoff_verified"] is False
        assert second["transcript"]["status"] == "unknown_publication", second
        assert second["transcript"]["provider_calls"] == 0, second
        assert second["transcript"]["source_ref"] == first["transcript"]["source_ref"]
        assert (parent / "et-http.log").read_text().splitlines() == ["GET"]
        transcript_read = verified_read(catalog, first["transcript"]["source_ref"],
                                       env=local_env, cwd=root, purpose="preview")
        latest = dict(request, mode="latest_as_of")
        latest.pop("fiscal_year")
        latest.pop("companion_transcript")
        unsupported = run(command, env=local_env, cwd=ff_root, request=latest)
        assert unsupported["status"] == "gap", unsupported
        assert unsupported["downloads"] == 0, unsupported
        assert not log.exists() and fingerprints(path for path in (root / "companies").rglob("*") if path.is_file()) == before
        unsupported_status = unsupported["status"]
    return {"schema": spec["schema"], "market": spec["market"], "original_sha256": digest(spec["original"]),
            "provider_actions": actions, "first_downloads": first["downloads"],
            "second_downloads": second["downloads"], "first_status": first["status"],
            "second_status": second["status"], "filing_verified_read": filing_read,
            "transcript_verified_read": transcript_read, "unsupported_latest_status": unsupported_status,
            "transcript_first_status": first.get("transcript", {}).get("status"),
            "transcript_second_provider_calls": second.get("transcript", {}).get("provider_calls"),
            "offline_et_http_calls": 1 if spec.get("companion") else 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ff-root", type=Path, required=True)
    parser.add_argument("--et-root", type=Path, required=True)
    parser.add_argument("--test-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    parent = args.test_root.resolve()
    if parent.parent != (ROOT / ".planning").resolve() or parent.exists():
        raise ValueError("test root must be an absent direct child of this repo's .planning")
    if args.output.exists():
        raise ValueError("output must be new")
    txt = args.et_root / "transcripts/MSFT/MSFT_Q4_2026_earnings_call.txt"
    originals = [PDF, HTML, txt]
    protected = originals + [ROOT / "config/source_catalog.yaml", ROOT / "config/source_acquisition.yaml",
                             ROOT / ".source_catalog/catalog.sqlite3", ROOT / ".source_catalog/runtime_policy.json"]
    before = fingerprints(protected)
    for original in originals:
        if not original.is_file():
            raise FileNotFoundError(original)
    report = {"schema_version": "g2-acquisition-chain-e2e/1", "status": "running",
        "boundary": "real FF/CWP CLIs and ET supervisor/worker; offline identity, acquisition provider and ET HTTP session",
        "live_provider_calls": 0, "model_calls": 0, "translation_calls": 0, "production_writes": 0}
    parent.mkdir()
    try:
        (parent / "provider.py").write_text(PROVIDER, encoding="utf-8")
        (parent / "g2_http_fixture.py").write_text(HTTP, encoding="utf-8")
        (parent / "ff_cli.py").write_text(
            "import io, json, runpy, sys\nfrom pathlib import Path\n"
            f"sys.path.insert(0, {str(args.ff_root.resolve() / 'scripts')!r})\n"
            "import ff_process_transport as transport\noriginal = transport.run_bounded_json\n"
            "def traced(*args, **kwargs):\n"
            "    try: return original(*args, **kwargs)\n"
            "    except transport.ChildFailed as exc:\n"
            "        diagnostic = None\n"
            "        if 'company_wiki.source_catalog.transcript_import_cli' in args[0]:\n"
            "            from company_wiki.source_catalog.transcript_import_cli import run_import\n"
            "            command = args[0]\n"
            "            try: run_import(Path(command[command.index('--wiki-root') + 1]), io.BytesIO(kwargs['input_bytes']))\n"
            "            except Exception as cause: diagnostic = type(cause).__name__ + ':' + str(cause)\n"
            f"        with Path({str(parent / 'child-errors.jsonl')!r}).open('a', encoding='utf-8') as log:\n"
            "            log.write(json.dumps({'code': exc.returncode, 'stderr': exc.stderr[:8192].decode('utf-8', errors='replace'), 'diagnostic_replay': diagnostic}) + '\\n')\n"
            "        raise\n"
            "transport.run_bounded_json = traced\n"
            f"runpy.run_path({str(args.ff_root.resolve() / 'scripts/fetch_filing.py')!r}, run_name='__main__')\n",
            encoding="utf-8")
        (parent / "et-body.json").write_text(json.dumps([{"symbol": "MSFT", "year": 2026,
            "period": "Q4", "date": "2026-07-29", "content": txt.read_text(encoding="utf-8")}]), encoding="utf-8")
        (parent / "et_cli.py").write_text(
            "import sys\nfrom pathlib import Path\n"
            f"sys.path.insert(0, {str(args.et_root.resolve())!r})\n"
            "from transcript_tool import main\nfrom transcript_api import ProviderSettings\n"
            "raise SystemExit(main(_provider_settings=ProviderSettings(motley_fool_enabled=False, fmp_enabled=True),\n"
            "    _retrieval_launcher='g2_http_fixture:factory',\n"
            f"    _retrieval_spec={{'body_file': {str(parent / 'et-body.json')!r}, 'http_log': {str(parent / 'et-http.log')!r}}},\n"
            f"    _retrieval_temp_root=Path({str(parent)!r})))\n", encoding="utf-8")
        env = dict(os.environ)
        for key in ("OPENAI_API_KEY", "DEEPSEEK_API_KEY", "MINIMAX_API_KEY", "MIMO_API_KEY", "ANTHROPIC_API_KEY"):
            env.pop(key, None)
        env.update(PYTHONPATH=os.pathsep.join((str(ROOT / "src"), str(parent))), FMP_API_KEY="offline-fixture",
            PYTHON_DOTENV_DISABLED="1", COMPANY_WIKI_NETWORK="blocked", COMPANY_WIKI_REAL_LLM="0",
            TEMP=str(parent), TMP=str(parent), PYTHONIOENCODING="utf-8")
        cn = dict(schema="1.2", market="CN", entity="比亚迪", security="002594", exchange="SZSE",
            provider="cninfo", accession="1222881496", title="2024年年度报告", date="2025-03-24", year=2024,
            original=PDF, mime="application/pdf", language="zh",
            url="https://static.cninfo.com.cn/finalpage/2025-03-24/1222881496.PDF")
        specs = [cn, dict(cn, schema="2.0"),
            dict(schema="2.0", market="US", entity="MICROSOFT CORP", security="MSFT", exchange="NASDAQ", local_reuse=True, companion=True,
            provider="sec", accession="0001193125-26-323660", title="MICROSOFT CORP 10-K 2026-06-30",
            date="2026-07-29", year=2026, original=HTML, mime="text/html", language="en",
            url="https://www.sec.gov/Archives/edgar/data/789019/000119312526323660/")]
        report["cases"] = []
        for spec in specs:
            report["cases"].append(case(parent, spec, args.ff_root.resolve(), args.et_root.resolve(), env))
        report["status"] = "passed"
    except Exception as exc:
        report.update(status="failed", error_type=type(exc).__name__, error=str(exc))
        raise
    finally:
        # Only this absent-at-start direct child can contain our fixture data.
        if parent.parent != (ROOT / ".planning").resolve() or parent.is_symlink():
            raise RuntimeError("test root ownership changed; refusing cleanup")
        if any(path.is_symlink() or getattr(path.lstat(), "st_file_attributes", 0) & 0x400
               for path in parent.rglob("*")):
            raise RuntimeError("test tree contains a reparse path; refusing cleanup")
        shutil.rmtree(parent)
        report["test_root_restored_absent"] = not parent.exists()
        report["protected_originals_and_production_unchanged"] = fingerprints(protected) == before
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        if not report["protected_originals_and_production_unchanged"]:
            raise RuntimeError("protected originals/production changed")
    print(json.dumps({"status": report["status"], "cases": len(report["cases"]),
                      "restored_absent": report["test_root_restored_absent"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
