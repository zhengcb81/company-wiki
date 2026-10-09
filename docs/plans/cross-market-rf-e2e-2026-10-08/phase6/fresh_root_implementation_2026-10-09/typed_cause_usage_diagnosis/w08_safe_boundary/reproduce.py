"""Read-only W08 diagnosis through actual CLIs in an owned synthetic TEMP root.

No repository source/config mutation, real credentials, provider HTTP or paid calls.
The provider script comes from the current CWP hermetic CLI fixture. The FF/RF
entry points themselves are production code. Injected FF wire controls are
explicitly labelled and never confused with an actual producer observation.
"""
from __future__ import annotations

import ast
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import time

PROJECTS = Path(__file__).resolve().parents[8]
CWP = PROJECTS / "company-wiki"
FF = PROJECTS / "filing-fetch"
RF = PROJECTS / "revenue-forecast"
SENTINEL = "synthetic-w08-secret-never-use-as-a-key"


def safe_environment() -> dict[str, str]:
    names = {"SYSTEMROOT", "WINDIR", "PATH", "PATHEXT", "COMSPEC", "TEMP", "TMP",
             "USERPROFILE", "APPDATA", "LOCALAPPDATA", "HOMEDRIVE", "HOMEPATH"}
    value = {key: item for key, item in os.environ.items() if key.upper() in names}
    value.update(PYTHONPATH=str(CWP / "src"), PYTHONDONTWRITEBYTECODE="1",
                 PYTHONUTF8="1", PYTHON_DOTENV_DISABLED="1")
    return value


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def provider_source() -> str:
    path = CWP / "tests/integration/test_acquisition_failure_cli_e2e.py"
    for node in ast.parse(path.read_text(encoding="utf-8")).body:
        if isinstance(node, ast.Assign) and any(isinstance(n, ast.Name) and n.id == "PROVIDER" for n in node.targets):
            return ast.literal_eval(node.value)
    raise RuntimeError("fixture provider literal unavailable")


def setup(root: Path, mode: str) -> tuple[Path, Path, Path]:
    (root / "config").mkdir(parents=True)
    (root / "companies").mkdir()
    catalog = root / "config/source_catalog.yaml"
    write_json(catalog, {"schema_version": "1.0", "catalog_dir": str(root / "catalog"),
               "roots": [{"root_id": "company_raw", "kind": "company_raw",
                          "path": str(root / "companies"), "priority": 10}]})
    master = {"schema_version": "1.0", "market": "US", "retrieved_at": "2000-01-01T00:00:00Z",
              "sources": ["https://www.sec.gov/synthetic"], "record_count": 1,
              "records": [{"schema_version": "1.0", "active": True, "aliases": ["AAPL", "Fixture"],
                           "canonical_name": "Fixture", "exchange": "NASDAQ", "identifiers": {"org_id": "synthetic"},
                           "market": "US", "security_id": "AAPL", "source_name": "sec",
                           "source_record_id": "synthetic", "source_url": "https://www.sec.gov/synthetic", "ticker": "AAPL"}]}
    write_json(root / "catalog/security_master/us.json", master)
    provider = root / "provider.py"
    body = provider_source()
    fixture_mode = "discover-fail"
    if mode == "unsupported_language":
        body = body.replace("'upstream_unavailable'", "'unsupported_language'")
    if mode == "malformed_usage":
        body = body.replace("if a.mode=='discover-fail':fail(17)", "if a.mode=='discover-fail':fail(True)")
    if mode == "no_candidate":
        body = body.replace("if a.mode=='discover-fail':fail(17)",
            "if a.mode=='discover-fail':\n sys.stdout.write(json.dumps({'schema_version':'1.0','status':'ok','adapter':identity,'candidates':[],'acquisition_usage':usage(17)}));raise SystemExit(0)")
    if mode == "deadline":
        fixture_mode = "timeout-checkpoint"
    if mode == "bad_receipt":
        fixture_mode = "bad-receipt"
    provider.write_text(body, encoding="utf-8", newline="\n")
    log = root / "provider_calls.txt"
    adapter = {"name": "proof-cli", "version": "1.0.0", "interface": "json_command_v1",
               "project_root": str(root), "config_root": None, "supports_acquisition_budget": True,
               "command": [sys.executable, "-B", str(provider), fixture_mode, str(log)]}
    acquisition = root / "config/source_acquisition.yaml"
    write_json(acquisition, {"schema_version": "1.1", "staging_root": str(root / "staging"),
                            "timeout_seconds": 5, "adapters": {key: dict(adapter, interface="json_command_v1" if key == "cn" else "dayu_sdk_bounded_v1") for key in ("cn", "hk", "us")}})
    ff_config = root / "company_wiki.json"
    write_json(ff_config, {"schema_version": "1.0", "company_wiki_root": str(root)})
    return catalog, ff_config, log


def run(args: list[str], root: Path, request: dict | None = None) -> dict:
    started = time.monotonic()
    result = subprocess.run(args, input=json.dumps(request) if request is not None else None,
                            cwd=root, capture_output=True, text=True, encoding="utf-8", errors="strict",
                            env=safe_environment(), timeout=30, check=False)
    stdout, stderr = result.stdout, result.stderr
    # Persist no sentinel even when a tested production boundary leaks it.
    safe_stdout, safe_stderr = stdout.replace(SENTINEL, "[SYNTHETIC_REDACTED]"), stderr.replace(SENTINEL, "[SYNTHETIC_REDACTED]")
    try:
        payload = json.loads(safe_stdout or safe_stderr)
    except ValueError:
        payload = None
    return {"argv": [str(item) for item in args], "exit_code": result.returncode,
            "duration_seconds": round(time.monotonic() - started, 3), "payload": payload,
            "stdout": safe_stdout, "stderr": safe_stderr, "synthetic_sentinel_leaked": SENTINEL in stdout + stderr}


def request(intent: str = "fetch_if_missing") -> dict:
    value = {"schema_version": "2.0", "company_query": "AAPL", "market": "US", "exchange": "NASDAQ",
             "document_kind": "annual_report", "fiscal_year": 2025, "fiscal_period": "FY",
             "as_of_date": "2026-10-09", "form_type": "10-K", "language": "en", "mode": "exact",
             "filing_intent": intent}
    if intent == "fetch_if_missing":
        value["acquisition_limits"] = {"max_bytes": 10000, "timeout_seconds": 8, "max_cost_usd": "1"}
    return value


def chain(root: Path, mode: str, *, reuse: bool = False) -> dict:
    catalog, config, log = setup(root, mode)
    req = request("reuse_only" if reuse else "fetch_if_missing")
    if mode == "local_metadata_gap":
        original = root / "companies/Fixture/raw/financial_reports/annual/2025_annual.pdf"
        original.parent.mkdir(parents=True)
        original.write_bytes(b"%PDF-1.4 synthetic 2025 annual original. Devices and services.\n")
        write_json(original.with_name(original.name + ".source.json"), {
            "market": "US", "security_id": "AAPL", "company_name": "Fixture", "source_title": "Fixture 2025 Annual Report",
            "provider": "sec", "provider_document_id": "synthetic-annual", "source_url": "https://www.sec.gov/synthetic.txt",
            "document_kind": "annual_report", "fiscal_year": 2025, "fiscal_period": "FY", "form_type": "10-K", "language": "en"})
    scan = run([sys.executable, "-X", "utf8", "-B", "-m", "company_wiki.source_catalog.cli", "--config", str(catalog), "scan"], root)
    if scan["exit_code"] != 0:
        return {"mode": mode, "fixture_failure": scan}
    if reuse:
        query = {"entity": "Fixture", "market": "US", "security_id": "AAPL", "document_kind": "annual_report",
                 "fiscal_year": 2025, "fiscal_period": "FY", "form_type": "10-K", "language": "en", "as_of_date": "2026-10-09", "allow_download": False}
        direct = run([sys.executable, "-X", "utf8", "-B", "-m", "company_wiki.source_catalog.source_query_cli", "--config", str(catalog)], root, query)
    else:
        direct = run([sys.executable, "-X", "utf8", "-B", "-m", "company_wiki.source_catalog.cli", "--config", str(catalog), "ensure",
                      "--entity", "Fixture", "--market", "US", "--security-id", "AAPL", "--document-kind", "annual_report",
                      "--fiscal-year", "2025", "--fiscal-period", "FY", "--form-type", "10-K", "--language", "en",
                      "--as-of-date", "2026-10-09", "--allow-download", "--source-ref-v2", "--max-download-bytes", "10000",
                      "--max-download-seconds", "2" if mode == "deadline" else "8", "--max-download-cost-usd", "1",
                      "--acquisition-config", str(root / "config/source_acquisition.yaml")], root)
    ff = run([sys.executable, "-X", "utf8", "-B", str(FF / "scripts/fetch_filing.py"), "--source-ref-v2",
              "--config", str(config), "--timeout-seconds", "15"], root, req)
    rf_client = run([sys.executable, "-X", "utf8", "-B", str(RF / "scripts/filing_fetch_client.py"), "--source-ref-v2", "--result-envelope",
                     "--filing-fetch-root", str(FF), "--company-wiki-config", str(config), "--timeout-seconds", "15"], root, req)
    rf_prepare = run([sys.executable, "-X", "utf8", "-B", str(RF / "scripts/source_preparation.py"), "--result-envelope",
                      "--filing-fetch-root", str(FF), "--company-wiki-config", str(config), "--company-wiki-catalog-config", str(catalog), "--timeout-seconds", "15"], root, req)
    calls = log.read_text(encoding="utf-8").splitlines() if log.exists() else []
    return {"mode": mode, "fixture": "real_CWP_FF_RF_public_CLIs_synthetic_no_HTTP_provider",
            "cwp": direct, "ff": ff, "rf_client": rf_client, "rf_prepare": rf_prepare,
            "provider_invocations_all_four_probes": calls, "provider_http_requests": 0,
            "paid_cost_usd": "0", "raw_files_remaining": len(list((root / "companies").rglob("*.txt")))}


def injected_controls(root: Path) -> list[dict]:
    controls = []
    (root / "scripts").mkdir(parents=True)
    catalog = root / "catalog.json"
    write_json(catalog, {})  # RF fails before any reader access in these controls.
    for name in ("known_cause", "untrusted_reason", "untrusted_top_level_error", "untrusted_stderr", "untrusted_success_exit_reason", "post_selection_reader_failure"):
        message = "safe fixed message" if name == "known_cause" else "provider URL https://example.invalid/?api_key=" + SENTINEL
        cause = {"schema_version": "filing-upstream-cause/1", "operation": "ensure", "code": "canonical_import_failed",
                 "provider_started": True, "usage_complete": True, "retry_scope": "none"}
        body = {"schema_version": "2.0", "status": "upstream_error",
                "filing": {"status": "upstream_error", "reason": message, "retryable": False, "upstream_cause": cause,
                           "acquisition_usage": {"schema_version": "1.0", "response_bytes": 4096, "cost_usd": "0.02"}},
                "transcript": {"status": "not_requested"}, "calls": 2, "downloads": 0}
        if name == "untrusted_top_level_error":
            body["error"] = message
        if name == "post_selection_reader_failure":
            sha = "a" * 64
            body.update(status="source_candidate")
            body["filing"] = {"status": "source_candidate", "document_kind": "annual_report", "fiscal_year": 2025,
                "fiscal_period": "FY", "resolution_outcome": "downloaded_new", "download_events": 1,
                "source_ref": {"schema_version": "2.0", "document_id": "synthetic", "source_id": "synthetic",
                               "content_sha256": sha, "byte_size": 4096, "mime_type": "text/plain"},
                "acquisition_usage": {"schema_version": "1.0", "response_bytes": 4096, "cost_usd": "0.02"}}
            body["downloads"] = 1
        script = "import json,sys\nsys.stdin.read()\nprint(" + repr(json.dumps(body)) + ")\nraise SystemExit(" + ("0" if name in {"untrusted_success_exit_reason", "post_selection_reader_failure"} else "2") + ")\n"
        if name == "untrusted_stderr":
            script = "import sys\nsys.stdin.read()\nsys.stderr.write(" + repr(message) + ")\nraise SystemExit(2)\n"
        (root / "scripts/fetch_filing.py").write_text(script, encoding="utf-8")
        actual = run([sys.executable, "-X", "utf8", "-B", str(RF / "scripts/source_preparation.py"), "--filing-fetch-root", str(root),
                      "--company-wiki-catalog-config", str(catalog), "--timeout-seconds", "5"], root, request("reuse_only"))
        controls.append({"name": name, "fixture": "injected_FF_wire_actual_RF_client_and_preparation_CLIs",
                         "input": body if name == "known_cause" else {"fields": sorted(body), "sentinel_present": True}, "rf_prepare": actual})
    return controls


def main() -> int:
    global FF, RF
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", nargs="*", default=["discover-fail", "unsupported_language", "malformed_usage", "bad_receipt", "no_candidate", "local_metadata_gap", "true_no_local_match"])
    parser.add_argument("--output", default="observations.json")
    parser.add_argument("--filing-fetch-root", type=Path, default=FF)
    parser.add_argument("--revenue-forecast-root", type=Path, default=RF)
    args = parser.parse_args()
    FF, RF = args.filing_fetch_root.resolve(strict=True), args.revenue_forecast_root.resolve(strict=True)
    if Path(args.output).name != args.output:
        raise ValueError("output must be a local file name")
    output = Path(__file__).with_name(args.output)
    files = {"CWP": CWP / "src/company_wiki/source_catalog/acquisition_failure.py",
             "FF": FF / "scripts/fetch_filing.py", "RF": RF / "scripts/source_preparation.py"}
    result = {"schema_version": "w08-readonly-diagnosis/1", "source_file_sha256": {k: hashlib.sha256(p.read_bytes()).hexdigest() for k, p in files.items()},
              "external_http_requests": 0, "paid_calls": 0, "production_originals_modified": False, "production_config_modified": False,
              "cases": [], "wire_controls": []}
    with TemporaryDirectory(prefix="cwp-w08-readonly-20261009-") as temporary:
        root = Path(temporary)
        result["owned_temp_root"] = str(root)
        for mode in args.cases:
            result["cases"].append(chain(root / mode, mode, reuse=mode in {"local_metadata_gap", "true_no_local_match"}))
        result["wire_controls"] = injected_controls(root / "wire_controls")
    result["temp_root_exists_after_cleanup"] = root.exists()
    write_json(output, result)
    print(json.dumps({"output": str(output), "cases": len(result["cases"]), "wire_controls": len(result["wire_controls"]), "temp_cleaned": not root.exists()}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
