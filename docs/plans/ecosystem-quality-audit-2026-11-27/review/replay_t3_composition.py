"""Replay the public FF and CWP T3 contracts with three local acquisition doubles."""

import argparse
import json
import os
import shutil
import subprocess
import tempfile
import venv
from collections import Counter
from pathlib import Path
CASES = {
    "CN": ("300750", "宁德时代", "SZSE", "cninfo", "FY", 2024, "2025-03-14", ["CATL"]),
    "HK": ("00700", "騰訊控股", "HKEX", "hkexnews", "FY", 2025, "2026-03-18", ["腾讯", "Tencent"]),
    "US": ("AMD", "Advanced Micro Devices", "NASDAQ", "sec", "10-K", 2025, "2026-02-05", ["AMD"]),
}
FAKE = '''
import argparse, hashlib, json, sys
from pathlib import Path
p = argparse.ArgumentParser()
p.add_argument("action")
p.add_argument("--staging-dir")
p.add_argument("--provider-state-root")
p.add_argument("--market-fixture", required=True)
args = p.parse_args()
owner = Path(__file__).parent
cases = json.loads((owner / "cases.json").read_text(encoding="utf-8"))
market = args.market_fixture
sec, name, exchange, provider, form, year, filing, aliases = cases[market]
req = json.load(sys.stdin)
with (owner / "calls.jsonl").open("a", encoding="utf-8") as file:
    file.write(json.dumps([market, args.action]) + chr(10))
identity = {"name": f"test-{market.lower()}", "version": "1.0.0"}
provider_id = "case-" + market
url = "https://example.invalid/" + market + ".pdf"
result = {"schema_version": "1.0", "status": "ok", "adapter": identity}
body = b"%PDF-1.4" + bytes([10]) + b"Offline acquisition" + bytes([10]) + b"%%EOF"
result["acquisition_usage"] = {"schema_version": "1.0", "response_bytes": 0, "cost_usd": "0"}
if args.action == "discover":
    result["candidates"] = [{
        "candidate_id": provider_id, "provider": provider, "provider_document_id": provider_id,
        "market": market, "security_id": sec, "entity": req["entity"],
        "title": f"{name} {year} annual report", "source_url": url, "document_kind": "annual_report",
        "form_type": form, "filing_date": filing, "fiscal_year": year, "fiscal_period": "FY",
        "amended": False, "language": "en" if market=="US" else "zh",
    }]
else:
    path = Path(args.staging_dir) / "annual.pdf"
    path.write_bytes(body)
    result["acquisition_usage"]["response_bytes"] = len(body)
    result["receipt"] = {
        "candidate_id": provider_id, "provider": provider, "provider_document_id": provider_id,
        "source_url": url, "staged_path": str(path), "content_sha256": hashlib.sha256(body).hexdigest(),
        "byte_size": len(body), "mime_type": "application/pdf", "retrieved_at": filing + "T01:00:00Z",
        "http_status": 200, "adapter_name": identity["name"], "adapter_version": "1.0.0",
        "etag": None, "last_modified": None,
    }
print(json.dumps(result, ensure_ascii=True))
'''

def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=True), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cwp", type=Path, required=True, help="CWP release checkout")
    parser.add_argument("--ff", type=Path, required=True, help="FF release checkout")
    parser.add_argument("--temp-root", type=Path, help="Existing short scratch path")
    args = parser.parse_args()
    cwp = args.cwp.resolve(strict=True)
    ff_scripts = (args.ff / "scripts").resolve(strict=True)
    if not (cwp / "src/company_wiki/source_catalog/t3_workspace_cli.py").is_file():
        parser.error("CWP checkout does not include the T3 workspace command")
    with tempfile.TemporaryDirectory(prefix="s6-t3-", dir=args.temp_root) as d:
        base = Path(d)
        ff_root = base / "ff"
        shutil.copytree(ff_scripts, ff_root / "scripts", ignore=shutil.ignore_patterns("__pycache__"))
        ff = ff_root / "scripts/ff_t3_receipt.py"
        python_home = base / "v"
        venv.EnvBuilder(with_pip=False, system_site_packages=True).create(python_home)
        if os.name == "nt":
            python = python_home / "Scripts/pythonw.exe"
            package_dir = python_home / "Lib/site-packages"
            flags = subprocess.CREATE_NO_WINDOW
        else:
            python = python_home / "bin/python"
            package_dir, = (python_home / "lib").glob("python*/site-packages")
            flags = 0
        (package_dir / "cwp-source.pth").write_text(str(cwp / "src"), encoding="utf-8")
        py = str(python)
        owner = base / "own"
        owner.mkdir()
        identity = owner / "ids"
        identity.mkdir()
        save(owner / "cases.json", CASES)
        (owner / "fake.py").write_text(FAKE, encoding="utf-8")
        adapters = {}
        for market, (sec, name, exchange, provider, form, year, filing, aliases) in CASES.items():
            url = "https://example.invalid/" + market + ".pdf"
            row = {"schema_version":"1.0","market":market,"security_id":sec,"canonical_name":name,
                   "aliases":aliases,"exchange":exchange,"source_name":provider,"source_record_id":"fixture-"+sec,
                   "ticker":sec,"source_url":url,"active":True,"identifiers":{"org_id":"fixture-"+sec}}
            save(identity / (market.lower()+".json"), {
                "schema_version":"1.0","market":market,"retrieved_at":"2026-01-01T00:00:00Z",
                "sources":[url],"record_count":1,"records":[row]})
            adapters[market.lower()] = {
                "name":"test-"+market.lower(),"version":"1.0.0","project_root":str(owner),
                "config_root":None,"supports_acquisition_budget":True,
                "interface":"json_command_v1" if market=="CN" else "dayu_sdk_bounded_v1",
                "command":[py,"-B",str(owner/"fake.py"),"--market-fixture",market]}
        acq = owner / "acq.yaml"
        save(acq,{"schema_version":"1.1","staging_root":str(owner/"must-not-exist"),
                  "timeout_seconds":15,"adapters":adapters})
        base_config = base / "ff.json"
        work = base / "cases"
        command = [py,"-B","-m","company_wiki.source_catalog.t3_workspace_cli",
                   "--workspace-root",str(work),"--owner-root",str(owner),
                   "--acquisition-config",str(acq),"--identity-cache",str(identity)]
        save(base_config,{"schema_version":"1.0","connection":{"cwd":str(owner),"commands":{"t3_workspace":command}}})
        allowed = {"SYSTEMROOT", "WINDIR", "SYSTEMDRIVE", "COMSPEC", "PATH", "PATHEXT", "TEMP", "TMP", "TMPDIR"}
        env = {key: value for key, value in os.environ.items() if key.upper() in allowed}
        env.update(HOME=str(base), USERPROFILE=str(base), LOCALAPPDATA=str(base),
                   XDG_STATE_HOME=str(base), RESEARCH_FEEDBACK_DIR=str(base / "obs"),
                   PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1")
        args = [py,"-B",str(ff),"--receipts-dir",str(base/"receipts")]
        control = ["run-live","--run-id","s6-composition","--config",str(base_config)]
        def invoke(tail):
            done = subprocess.run(args + tail, stdin=subprocess.DEVNULL, capture_output=True,
                creationflags=flags, cwd=base, env=env, timeout=220)
            try:
                doc = json.loads(done.stdout)
            except ValueError:
                raise RuntimeError((done.returncode,done.stderr[-1800:].decode("utf-8",errors="replace"))) from None
            return done.returncode,doc
        original = invoke(control)
        tally = Counter(tuple(json.loads(s)) for s in (owner/"calls.jsonl").read_text().splitlines()) if (owner/"calls.jsonl").exists() else {}
        print(json.dumps({"exit":original[0],"cases":original[1].get("cases"),"provider_calls": {"/".join(key):n for key,n in tally.items()}}), flush=True)
        assert original[0] == 0 and len(tally) == 6 and set(tally.values()) == {1}, original[1]
        cold = invoke(["get","--run-id","s6-composition"])
        repeat = invoke(control)
        assert cold == original == repeat
        repeated = Counter(tuple(json.loads(s)) for s in (owner/"calls.jsonl").read_text().splitlines())
        assert repeated == tally and not any(path.is_dir() for path in work.iterdir())
        assert not (owner/"must-not-exist").exists()
        assert not (ff_root / ".ff_jobs").exists()
        print("cold_and_repeat_identical; four workspaces reclaimed; no additional calls", flush=True)
    print("temporary_root_removed=" + str(not base.exists()), flush=True)

if __name__ == "__main__":
    main()
