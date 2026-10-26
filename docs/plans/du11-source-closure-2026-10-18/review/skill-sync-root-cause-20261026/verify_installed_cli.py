"""Real installed FF CLI -> CWP readonly reuse, isolated frozen Sina data.

Uses the existing CWP fixture-provider seed, not mocked FF responses. No live
network or production catalog; removes only the scratch directory it creates.
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
import tempfile
import time


def check(value, message):
    if not value:
        raise RuntimeError(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cwp-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    check(not args.output.exists(), "preserve old receipts; use a new output path")
    root = args.cwp_root.resolve()
    sys.path[:0] = [str(root / "src"), str(root / "tests")]
    from financial_statements import test_offline_e2e_full as fixture
    from company_wiki.source_catalog.config import load_catalog_config
    from company_wiki.source_catalog.service import SourceCatalog
    from company_wiki.source_catalog.source_reader import SourceVersionReader, SourceRef

    control = root / ".planning/w19-root-reception-20261026"
    scratch = Path(tempfile.mkdtemp(prefix="skill-smoke-", dir=control)).resolve()
    receipt = {"schema_version": "installed-ff-cli-reuse/1", "passed": False,
               "network_requests": 0, "paid_calls": 0, "runs": []}
    started = time.monotonic()
    catalog = None
    try:
        wiki = fixture._wiki_root(scratch)
        replay = fixture._fixture_root(scratch)
        env = os.environ.copy()
        env.update(PYTHONPATH=str(root / "src"), PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1")
        seeded = subprocess.run([sys.executable, "-m", "company_wiki.source_catalog.financial_statements.cli", "--wiki-root", str(wiki), "--fixture-root", str(replay)], input=json.dumps(fixture.REQUEST).encode(), capture_output=True, env=env, cwd=root, timeout=45)
        check(seeded.returncode == 0, "CWP fixture seed failed: " + seeded.stderr.decode("utf-8", errors="replace")[-1500:])
        seed = json.loads(seeded.stdout)
        check(seed["status"] == "complete", "seed incomplete")
        receipt["seed_provider"] = "frozen Sina bytes via existing fixture port; not live HTTP"
        receipt["seed_fixture_exchanges"] = seed["usage"]["http_requests"]
        connection = scratch / "connection.json"
        connection.write_text(json.dumps({"schema_version": "1.0", "company_wiki_root": str(wiki)}), encoding="utf-8")
        request = {**fixture.REQUEST, "intent": "reuse_only"}
        request.pop("acquisition_limits")
        raw = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in fixture._lake(wiki)}
        check(len(raw) == 12, "wrong immutable source count")
        catalog = SourceCatalog(load_catalog_config(wiki / "config/source_catalog.yaml", project_root=wiki))
        reader = SourceVersionReader(catalog)
        for alias in (".agents", ".claude", ".codex"):
            script = Path.home() / alias / "skills/filing-fetch/scripts/fetch_statements.py"
            command = [sys.executable, str(script), "--config", str(connection), "--timeout-seconds", "30"]
            proc = subprocess.run(command, input=json.dumps(request).encode(), capture_output=True, env=env, cwd=scratch, timeout=40)
            check(proc.returncode == 0, alias + " CLI failed: " + proc.stderr.decode("utf-8", errors="replace")[-1500:])
            data = json.loads(proc.stdout)
            check(data["status"] == "complete" and data["usage"]["http_requests"] == 0, alias + " readonly result invalid")
            periods = {s["statement_type"]: len(s["reports"]) for s in data["statements"]}
            check(periods == fixture.PAGE_COUNTS, "installed CLI lost periods")
            rows = sum(len(r["rows"]) for s in data["statements"] for r in s["reports"])
            check(rows == 9729, "installed CLI lost source rows")
            refs = {r["source_ref"]["source_id"]: r["source_ref"] for s in data["statements"] for r in s["reports"]}
            for ref in refs.values():
                opened = reader.open_version(SourceRef(**ref), purpose="source_export")
                check(len(opened.data) == ref["byte_size"], "installed source reference not directly readable")
            receipt["runs"].append({"alias": alias, "actual_script": str(script), "physical_script": str(script.resolve()), "returncode": proc.returncode, "status": data["status"], "http_requests": 0, "periods": periods, "rows": rows, "direct_sources_opened": len(refs)})
        check(raw == {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in fixture._lake(wiki)}, "readonly installed entry changed originals")
        receipt.update(passed=True, immutable_originals_unchanged=True, temporary_bytes=sum(p.stat().st_size for p in scratch.rglob("*") if p.is_file()))
    finally:
        if catalog is not None:
            catalog.close()
        check(scratch.parent == control.resolve() and scratch.name.startswith("skill-smoke-"), "unexpected cleanup path")
        shutil.rmtree(scratch)
        receipt["temporary_root_restored_absent"] = not scratch.exists()
        receipt["elapsed_seconds"] = round(time.monotonic() - started, 3)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x", encoding="utf-8") as stream:
            json.dump(receipt, stream, indent=2, ensure_ascii=False)
            stream.write("\n")
    print(json.dumps(receipt, ensure_ascii=True))


if __name__ == "__main__":
    main()
