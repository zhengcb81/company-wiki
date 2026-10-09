"""Offline public FF -> real ET worker -> CWP import/open/reuse contract.

Only the supplier HTTP session is replaced by ET's test launcher. This is
engineering evidence, not a real supplier or company research acceptance.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8", newline="\n")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("ff-root", "et-root", "cwp-root", "output"):
        parser.add_argument("--" + name, required=True, type=Path)
    args = parser.parse_args(argv)
    ff, et, cwp = (p.resolve(strict=True) for p in
                   (args.ff_root, args.et_root, args.cwp_root))
    report = {"schema_version": "transcript-budget-contract/1",
              "started_at": datetime.now(timezone.utc).isoformat(),
              "roots": {"ff": str(ff), "et": str(et), "cwp": str(cwp)},
              "supplier_requests": 0, "supplier_cost_usd": "0",
              "checks": [], "commands": []}
    started = time.monotonic()
    old_env = dict(os.environ)
    temp_path = None

    def check(name, condition, detail=None):
        report["checks"].append({"name": name, "status": "PASS" if condition else "FAIL",
                                 "detail": detail})

    def run(command, env, request=None):
        start = time.monotonic()
        result = subprocess.run(command,
            input=None if request is None else json.dumps(request).encode("utf-8"),
            cwd=str(ff), env=env, capture_output=True, timeout=140)
        report["commands"].append({"command": command, "exit_code": result.returncode,
            "seconds": round(time.monotonic() - start, 3),
            "stderr": result.stderr.decode("utf-8", errors="replace")[:4096]})
        return result

    try:
        env = dict(old_env)
        env.pop("FMP_API_KEY", None)
        env["PYTHONUTF8"] = "1"
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PYTHONPATH"] = str(cwp / "src") + os.pathsep + env.get("PYTHONPATH", "")
        # IsolatedWiki.scan inherits environment; restore it in finally.
        os.environ.update(env)
        os.environ.pop("FMP_API_KEY", None)
        sys.path.insert(0, str(ff / "tests" / "e2e_support"))
        fixture = load_module("transcript_budget_isolated_wiki", ff / "tests" /
                              "e2e_support" / "isolated_wiki.py")
        proxy = et / "tests" / "request_budget_cli_proxy.py"
        if not proxy.is_file():
            raise ValueError("ET test-only transparent CLI proxy is required")
        with tempfile.TemporaryDirectory(prefix="cwpet-") as temporary:
            temp_path = Path(temporary).resolve()
            report["temporary_root"] = str(temp_path)
            for case, size, cap in (("success", 1024, 128 * 1024 * 1024),
                                    ("padded-json", 20386, 1024)):
                base = temp_path / case
                wiki_root = base / "wiki"
                wiki = fixture.IsolatedWiki(wiki_root, with_security_master=False)
                master = wiki.catalog_dir / "security_master"
                master.mkdir(parents=True)
                for market in ("cn", "hk", "us"):
                    write_json(master / (market + ".json"),
                               fixture._synthetic_security_master(market))
                primary = wiki.seed_market("US")
                old_sha = hashlib.sha256(primary.read_bytes()).hexdigest()
                wiki.scan()
                worker_root = base / "worker"
                worker_root.mkdir()
                calls = base / "http.jsonl"
                spec_path = base / "spec.json"
                write_json(spec_path, {"case": case, "response_bytes": size,
                    "calls_file": str(calls), "worker_temp_root": str(worker_root),
                    "call_date": "2026-09-01", "content_utf8": "A" * 286})
                wrapper = base / "et_proxy.py"
                wrapper.write_text("import runpy,sys\n"
                    f"sys.argv=[{str(proxy)!r},{str(spec_path)!r},*sys.argv[1:]]\n"
                    f"runpy.run_path({str(proxy)!r},run_name='__main__')\n",
                    encoding="utf-8", newline="\n")
                case_env = dict(env, EARNINGS_TRANSCRIPTS_TOOL=str(wrapper))
                # Transparent failure capture: preserve the real transport's
                # exception and only retain this fixture's rejected import.
                debug_input = base / "rejected_import.json"
                ff_wrapper = base / "ff_observe.py"
                ff_wrapper.write_text("import runpy,sys\nfrom pathlib import Path\n"
                    f"sys.path.insert(0,{str(ff / 'scripts')!r})\n"
                    "import ff_process_transport as t\noriginal=t.run_bounded_json\n"
                    "def observe(command,**kwargs):\n"
                    " try: return original(command,**kwargs)\n"
                    " except t.ChildFailed:\n"
                    "  if 'company_wiki.source_catalog.transcript_import_cli' in command:\n"
                    f"   Path({str(debug_input)!r}).write_bytes(kwargs['input_bytes'])\n"
                    "  raise\n"
                    "t.run_bounded_json=observe\n"
                    f"sys.argv=[{str(ff / 'scripts' / 'fetch_filing.py')!r},*sys.argv[1:]]\n"
                    f"runpy.run_path({str(ff / 'scripts' / 'fetch_filing.py')!r},run_name='__main__')\n",
                    encoding="utf-8", newline="\n")
                request = {"schema_version": "2.0", "company_query": "Apple Inc",
                    "market": "US", "document_kind": "annual_report", "mode": "exact",
                    "filing_intent": "reuse_only", "fiscal_year": 2025, "as_of_date": "2026-10-09",
                    "companion_transcript": {"intent": "fetch_if_missing",
                        "fiscal_year": 2026, "fiscal_quarter": 2, "provider": "fmp",
                        "acquisition_limits": {"max_bytes": cap,
                            "timeout_seconds": 30, "max_cost_usd": "0.00"}}}
                command = [sys.executable, "-X", "utf8", "-B",
                    str(ff_wrapper), "--config",
                    str(wiki_root / "company_wiki.json"), "--source-ref-v2",
                    "--timeout-seconds", "120"]
                first = run(command, case_env, request)
                payload = json.loads(first.stdout)
                report[case] = {"first": payload}
                transcript = payload.get("transcript", {})
                if debug_input.is_file():
                    sys.path.insert(0, str(cwp / "src"))
                    from company_wiki.source_catalog.transcript_import_cli import run_import
                    try:
                        diagnostic = run_import(wiki_root, io.BytesIO(debug_input.read_bytes()))
                        report[case]["import_diagnostic"] = diagnostic
                    except Exception as exc:
                        report[case]["import_diagnostic"] = {"type": type(exc).__name__,
                                                               "message": str(exc)[:2048]}
                check(case + ":primary_reused", first.returncode == 0 and
                      payload.get("status") == "source_candidate" and
                      payload.get("filing", {}).get("download_events") == 0, payload.get("status"))
                check(case + ":actual_usage", transcript.get("provider_requests") == 1 and
                      transcript.get("provider_response_bytes") == size and
                      transcript.get("provider_usage_complete") is True, transcript)
                logs = ([json.loads(line) for line in calls.read_text(encoding="utf-8").splitlines()]
                        if calls.is_file() else [])
                get_count = sum(line.get("op") == "get" for line in logs)
                report[case]["observed_http_gets"] = get_count
                check(case + ":one_mock_http", get_count == 1, get_count)
                if case == "success":
                    ref = transcript.get("source_ref")
                    check("success:canonical_import", transcript.get("status") in
                          {"downloaded", "unknown_publication"} and isinstance(ref, dict),
                          transcript.get("status"))
                    if isinstance(ref, dict):
                        opened = run([sys.executable, "-X", "utf8", "-B", "-m",
                            "company_wiki.source_catalog.source_reader_cli", "--config",
                            str(wiki.config_path), "--document-id", ref["document_id"],
                            "--source-id", ref["source_id"], "--content-sha256",
                            ref["content_sha256"], "--purpose", "preview"], case_env)
                        read_sha = hashlib.sha256(opened.stdout).hexdigest()
                        receipt = json.loads(opened.stderr)
                        body = json.loads(opened.stdout)
                        check("success:verified_raw_open", opened.returncode == 0 and
                              read_sha == ref["content_sha256"] and len(opened.stdout) == size and
                              receipt.get("status") == "ok" and body[0]["content"] == "A" * 286)
                        second = run(command, case_env, request)
                        repeated = json.loads(second.stdout)
                        report[case]["repeat"] = repeated
                        after_logs = [json.loads(line) for line in calls.read_text(encoding="utf-8").splitlines()]
                        check("success:repeat_zero_http", sum(line.get("op") == "get"
                              for line in after_logs) == get_count)
                        check("success:repeat_same_ref", second.returncode == 0 and
                              repeated.get("transcript", {}).get("source_ref") == ref and
                              repeated.get("transcript", {}).get("provider_calls") == 0,
                              repeated.get("transcript"))
                        originals = [p for p in (wiki_root / "companies").rglob("*")
                            if p.is_file() and not p.name.endswith(".source.json") and
                            hashlib.sha256(p.read_bytes()).hexdigest() == read_sha]
                        check("success:one_canonical_raw", len(originals) == 1, len(originals))
                else:
                    check("padded-json:terminal_byte_limit", transcript.get("status") ==
                          "provider_unavailable" and transcript.get("reason") == "byte_limit" and
                          transcript.get("retryable") is False, transcript)
                    check("padded-json:no_transcript_import", "source_ref" not in transcript and
                          len([p for p in (wiki_root / "companies").rglob("*") if p.is_file()
                               and not p.name.endswith(".source.json")]) == 1)
                check(case + ":primary_unchanged", hashlib.sha256(primary.read_bytes()).hexdigest() == old_sha)
                check(case + ":worker_restored", not list(worker_root.iterdir()))
    except Exception as exc:
        report["error"] = {"type": type(exc).__name__, "message": str(exc)[:2048]}
        check("driver_completed", False, report["error"])
    finally:
        os.environ.clear()
        os.environ.update(old_env)
        report["temporary_root_restored"] = temp_path is not None and not temp_path.exists()
        check("temporary_root_restored", report["temporary_root_restored"])
        report["seconds"] = round(time.monotonic() - started, 3)
        report["passed"] = sum(item["status"] == "PASS" for item in report["checks"])
        report["failed"] = sum(item["status"] == "FAIL" for item in report["checks"])
        args.output.parent.mkdir(parents=True, exist_ok=True)
        write_json(args.output, report)
    print(json.dumps({key: report[key] for key in ("passed", "failed", "seconds",
          "temporary_root_restored", "supplier_cost_usd")}, ensure_ascii=False))
    return int(report["failed"] > 0)


if __name__ == "__main__":
    raise SystemExit(main())
