"""Offline StockInfoDLSimple failure census. Pass its v2-clean-rewrite checkout."""

import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory


CWP = Path(__file__).resolve().parents[4]
PYTHON = [sys.executable, "-B", "-X", "utf8"]
TRANSPORT = """
import json, sys
from pathlib import Path
from unittest.mock import patch
from src.cninfo_api import CninfoAnnouncementClient
from src.company_wiki_adapter_cli import main
from src.company_wiki_adapter import DisclosureCandidate
case, sample = sys.argv[1:3]
original = DisclosureCandidate.to_dict
def post(*args, **kwargs):
    if case == 'provider-timeout':
        raise TimeoutError('synthetic offline timeout')
    records = json.loads(Path(sample).read_text(encoding='utf8'))['announcements']
    return {'announcements': records, 'totalRecordNum': len(records), 'totalpages': 1}
def serialized(candidate):
    value = original(candidate)
    if case == 'missing-candidate-id':
        del value['security_id']
    return value
with patch.object(CninfoAnnouncementClient, '_post_json', post), patch.object(DisclosureCandidate, 'to_dict', serialized):
    raise SystemExit(main(['discover','--config','valid.json']))
"""
SINGLE_DOWNLOAD = """
import runpy, sys
from unittest.mock import patch
from src.downloader import StockDownloader
from src.mapping import MappingManager
sys.argv = [sys.argv[1], '002594', '--config', 'single.json']
with patch.object(MappingManager, 'get_stock_name', return_value='fixture'), patch.object(
        StockDownloader, 'download', side_effect=PermissionError('offline storage fault')):
    runpy.run_path(sys.argv[0], run_name='__main__')
"""
LOG_WRITE = """
import builtins, json
from pathlib import Path
from unittest.mock import patch
from src.downloader import FailedDownloadLogger
sink = FailedDownloadLogger('failed.json')
sink.record('002594', 'fixture', 'document', 'fixture-url', 'offline failure')
original = builtins.open
def write_fault(path, mode='r', *args, **kwargs):
    if mode == 'w' and Path(path) == sink.log_file:
        raise PermissionError('offline log write fault')
    return original(path, mode, *args, **kwargs)
with patch('builtins.open', write_fault):
    sink.flush()
sink.flush()
print(json.dumps({'remaining':len(sink.get_failed()), 'on_disk':sink.log_file.is_file()}))
"""


def readback(sidecar):
    plan = subprocess.run(
        [*PYTHON, "-m", "tools.feedback_loop", "plan", str(sidecar)], cwd=CWP,
        capture_output=True, timeout=10, check=True,
    )
    batch = json.loads(plan.stdout)
    details = Path(str(sidecar) + ".details.jsonl")
    records = [json.loads(line) for line in details.read_bytes().splitlines()] if details.is_file() else []
    return {
        "observations": [[r["actual"], r["disposition"], r.get("refusal_code")] for r in batch["observations"]],
        "f4_diagnostics": [d["code"] for d in batch["diagnostics"]],
        "cause_chains": [r["cause_chain"] for r in records if "cause_chain" in r],
        "details_rows": len(records),
    }


def census(sid, work):
    (work / "sitecustomize.py").write_text(
        "import sys\ndef no_network(event,args):\n"
        "    if event in ('socket.connect','socket.getaddrinfo'): raise RuntimeError('offline fixture')\n"
        "sys.addaudithook(no_network)\n", encoding="ascii")
    (work / "valid.json").write_text("{}", encoding="ascii")
    (work / "single.json").write_text('{"pages":[{"suffix":"research"}]}', encoding="ascii")
    (work / "bad.json").write_text("{", encoding="ascii")
    stage = work / "already-a-file"
    stage.touch()
    sample = sid / "tests/fixtures/feedback_observation/listing_identity_rows.json"
    fixture = json.loads(sample.read_text(encoding="utf8"))
    discover = {**fixture["request"], "org_id": fixture["announcements"][0]["orgId"]}
    budget = {"schema_version": "1.0", "max_response_bytes": 65536, "timeout_seconds": 5, "max_cost_usd": "0"}
    fetch = {"adapter_payload_json": json.dumps(fixture["legacy_claim_verified"]), "acquisition_budget": budget}
    adapter = ["-m", "src.company_wiki_adapter_cli"]
    cases = [
        ("bad-switch", [*adapter, "--bad-action"], ""),
        ("main-config", [str(sid / "main.py"), "--config", "bad.json"], ""),
        ("single-download", ["-c", SINGLE_DOWNLOAD, str(sid / "main.py")], ""),
        ("failure-log-write", ["-c", LOG_WRITE], ""),
        ("bad-json", [*adapter, "discover", "--config", "valid.json"], "{"),
        ("fetch-stage-file", [*adapter, "fetch", "--config", "valid.json", "--staging-dir", str(stage)], json.dumps(fetch)),
    ]
    for case in ("provider-timeout", "valid-candidate", "missing-candidate-id"):
        cases.append((case, ["-c", TRANSPORT, case, str(sample)], json.dumps({**discover, "acquisition_budget": budget})))
    env = {k: v for k, v in os.environ.items() if k.upper() in
           {"PATH", "PATHEXT", "COMSPEC", "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "SYSTEMDRIVE", "USERPROFILE"}}
    env.update(PYTHONPATH=os.pathsep.join((str(work), str(sid))), PYTHONUTF8="1", PYTHONDONTWRITEBYTECODE="1")
    results = []
    for name, cli, payload in cases:
        sidecar = work / f"{name}.jsonl"
        env.update(RESEARCH_FEEDBACK_OUT=str(sidecar), RESEARCH_FEEDBACK_RUN_ID=name, RESEARCH_FEEDBACK_ATTEMPT_ID="first")
        outcome = subprocess.run([*PYTHON, *cli], input=payload.encode("utf8"), cwd=work, env=env,
                                 capture_output=True, timeout=15)
        last = (outcome.stderr.splitlines() or [b""])[-1]
        receipt = json.loads(last) if last.startswith(b"{") else {}
        err = receipt.get("error", {})
        result = json.loads(outcome.stdout) if outcome.stdout.lstrip().startswith(b"{") else {}
        details = subprocess.check_output([*PYTHON, str(Path(__file__).resolve()), "--read", str(sidecar)],
                                          cwd=CWP, timeout=15)
        results.append({"case": name, "exit": outcome.returncode, "status": receipt.get("status", result.get("status")),
                        "stderr_code": err.get("code"), "stderr_type": err.get("type"),
                        "stderr_retryable": err.get("retryable"), "usage": err.get("acquisition_usage"),
                        "reported_download_failure": b"Task failed" in outcome.stderr,
                        "reported_done": b"All tasks completed" in outcome.stderr,
                        "log_after_second_flush": result if name == "failure-log-write" else None,
                        "candidates": len(result["candidates"]) if "candidates" in result else None,
                        **json.loads(details)})
    return results


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--read":
        print(json.dumps(readback(Path(sys.argv[2]))))
    else:
        with TemporaryDirectory(prefix="f4-sid-") as folder:
            print(json.dumps(census(Path(sys.argv[1]).resolve(), Path(folder)), indent=2))
