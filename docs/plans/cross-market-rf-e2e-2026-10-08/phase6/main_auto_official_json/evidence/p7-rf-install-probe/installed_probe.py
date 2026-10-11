"""Fresh-process installed RF acceptance; writes only this evidence and owned TEMP."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import time

SELECTED = (
    "CHANGELOG.md", "SKILL.md", "references/economic-support-diagnostics.md",
    "references/evidence-role-calibration.md", "scripts/contracts/constants.py",
    "scripts/research/evidence_roles.py", "scripts/research/native_dependencies.py",
    "scripts/research_support_diagnostics.py", "scripts/schema_compatibility.py",
)
INSTALLS = (
    Path(r"C:/Users/郑曾波/.agents/skills/revenue-forecast"),
    Path(r"C:/Users/郑曾波/.codex/skills/revenue-forecast"),
)
EVIDENCE = Path(__file__).resolve().parent
BOOTSTRAP = """
import hashlib, importlib, json, os, runpy, socket, sys
from pathlib import Path
install=Path(sys.argv[1]).resolve()
entry=sys.argv[2]
args=sys.argv[3:]
sys.path.insert(0,str(install/'scripts'))
network_attempts=[]
def blocked(*args,**kwargs):
    network_attempts.append('network')
    raise RuntimeError('Offline installed probe attempted network access')
socket.socket.connect=blocked
socket.create_connection=blocked
names=('contracts.constants','revenue_core','revenue_report','revenue_backtest',
       'publication_registry','research.evidence_roles','research.native_dependencies',
       'schema_compatibility','research_support_diagnostics')
origins={}
for name in names:
    module=importlib.import_module(name)
    path=Path(module.__file__).resolve()
    assert path.is_relative_to(install/'scripts'), (name,str(path))
    origins[name]={'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
assert importlib.import_module('revenue_core').ENGINE_VERSION=='4.2.1'
registry=importlib.import_module('publication_registry').registry_file().resolve()
assert registry==Path(os.environ['REVENUE_PUBLICATION_REGISTRY']).resolve()
assert os.environ['RF_PUBLICATION_REGISTRY']==os.environ['REVENUE_PUBLICATION_REGISTRY']
sys.argv=[str(install/'scripts'/entry),*args]
try:
    runpy.run_path(str(install/'scripts'/entry),run_name='__main__')
finally:
    assert not network_attempts, network_attempts
    print('INSTALLED_ORIGINS='+json.dumps({'install':str(install),'origins':origins,'registry':str(registry),'network_attempts':0},ensure_ascii=False),file=sys.stderr)
"""
FACTORY = """
import json, socket, sys
from copy import deepcopy
from pathlib import Path
repo=Path(sys.argv[1]).resolve()
out=Path(sys.argv[2]).resolve()
shared=Path(sys.argv[3]).resolve()
def blocked(*args,**kwargs): raise RuntimeError('Fixture factory attempted network access')
socket.socket.connect=blocked;socket.create_connection=blocked
sys.path[:0]=[str(repo/'scripts'),str(repo/'tests')]
from test_scoped_calibration_support import target_period_bridge_document
fixture=repo/'tests/fixtures/scoped_calibration_support'
read=lambda p:json.loads(p.read_text(encoding='utf-8'))
raw=read(fixture/'valid_calibrated.json')
scoped=read(shared)
company=deepcopy(scoped)
company['operating_research']['calibrations'][0]['scope']=company['company_name']
for observation in company['operating_research']['observations']:
    observation['scope']=company['company_name']
sync=deepcopy(raw)
for parameter in sync['parameters']:
    if parameter['parameter_id'].startswith('conversion_'): parameter['period']='FY2031'
for claim in sync['evidence_claims']:
    if claim['target_id'].startswith('conversion_'): claim['period']='FY2031'
for observation in sync['operating_research']['observations']:
    if observation['observation_kind']=='conversion': observation['period']='FY2031'
bridge=target_period_bridge_document()
assert all(p['period']=='FY2025' for p in bridge['parameters'] if p['parameter_id'] in {'conversion_low','conversion_base','conversion_high'})
assert all(p['period']=='FY2026' for p in bridge['parameters'] if p['parameter_id'].endswith('_for_2026'))
assert all(c['period']=='FY2025' for c in bridge['evidence_claims'] if c['target_id'].startswith('conversion_'))
objects={'no_optional':read(fixture/'no_research.json'),'scope_a_only':scoped,
         'company_scope':company,'synchronized_future':sync,'historical_native_bridge':bridge}
for name,doc in objects.items():
    (out/(name+'.json')).write_text(json.dumps(doc,ensure_ascii=False,indent=1)+'\\n',encoding='utf-8')
print(json.dumps({'cases':list(objects),'test_helpers_are_engineering_input_factory_only':True,'bridge_factory':str(repo/'tests/test_scoped_calibration_support.py')},ensure_ascii=False))
"""


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tree_snapshot(root: Path) -> dict[str, str]:
    return {p.relative_to(root).as_posix(): sha(p) for p in sorted(root.rglob("*")) if p.is_file()}


def tree_digest(value: dict) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def cell(diag: dict, segment: str, scenario: str, year: int) -> dict:
    return next(entry for row in diag["segments"] if row["segment"] == segment
                for entry in row["entries"] if entry["scenario"] == scenario and entry["year"] == str(year))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rf-repo", type=Path, default=Path(r"C:/Users/郑曾波/Projects/revenue-forecast"))
    parser.add_argument("--sync-verification", type=Path, help="Existing ROOT evidence only; this script never writes it.")
    args = parser.parse_args()
    repo = args.rf_repo.resolve()
    shared = EVIDENCE.parent / "p7-rf-final-review/shared_root_minimal_input.json"
    source_inputs = [shared, repo / "tests/fixtures/scoped_calibration_support/no_research.json",
                     repo / "tests/fixtures/scoped_calibration_support/valid_calibrated.json",
                     repo / "tests/test_scoped_calibration_support.py", repo / "tests/test_research_evidence_roles.py",
                     repo / "tests/test_recognition_bridge.py", repo / "tests/test_data_contract.py"]
    before_inputs = {str(p): sha(p) for p in source_inputs}
    source_selected = {name: sha(repo / name) for name in SELECTED}
    before = {str(root): tree_snapshot(root) for root in INSTALLS}
    for root in INSTALLS:
        assert {name: sha(root / name) for name in SELECTED} == source_selected, f"Installed source not synced: {root}"
    clean = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, env=clean, text=True, encoding="utf-8").strip()
    environment_before = dict(os.environ)
    owned = Path(tempfile.mkdtemp(prefix="p7-rf-installed-"))
    receipt = {"schema_version": "p7-rf-installed-probe/1", "status": "running", "source_head": head,
               "source_root": str(repo), "source_selected_sha256": source_selected, "input_source_sha256": before_inputs,
               "sync_verification": {"path": str(args.sync_verification), "sha256": sha(args.sync_verification)} if args.sync_verification else None,
               "owned_temp": str(owned), "provider_calls": 0, "model_calls": 0, "new_cost_usd": 0,
               "commands": [], "installations": []}
    started = time.monotonic()

    def run(name: str, code: str, argv: list[str], registry: Path):
        assert registry.resolve().is_relative_to(owned.resolve())
        env = dict(clean)
        env.update(PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1", PYTHONIOENCODING="utf-8",
                   REVENUE_PUBLICATION_REGISTRY=str(registry), RF_PUBLICATION_REGISTRY=str(registry))
        command = [sys.executable, "-I", "-X", "utf8", "-B", "-c", code, *argv]
        tick = time.monotonic()
        done = subprocess.run(command, cwd=owned, env=env, capture_output=True, timeout=60)
        (EVIDENCE / (name + ".log")).write_bytes(done.stdout + done.stderr)
        record = {"name": name, "argv": command, "exit_code": done.returncode,
                  "seconds": time.monotonic() - tick, "registry": str(registry),
                  "stdout": done.stdout.decode("utf-8"), "stderr": done.stderr.decode("utf-8")}
        receipt["commands"].append(record)
        print(json.dumps({"name": name, "exit_code": done.returncode, "seconds": record["seconds"]}), flush=True)
        assert done.returncode == 0, record
        return record

    try:
        inputs = owned / "inputs"
        inputs.mkdir()
        run("factory", FACTORY, [str(repo), str(inputs), str(shared)], owned / "factory-registry/publications.jsonl")
        input_hashes = {p.name: sha(p) for p in inputs.iterdir()}
        for install_index, install in enumerate(INSTALLS):
            prefix = f"install-{install_index}"
            version = run(prefix + "-version", BOOTSTRAP, [str(install), "revenue_forecast.py", "--version"], owned / prefix / "version/publications.jsonl")
            assert version["stdout"].startswith("revenue-forecast 4.2.1 "), version
            outcomes = {}
            for name in ("no_optional", "scope_a_only", "company_scope", "synchronized_future", "historical_native_bridge"):
                input_path = inputs / (name + ".json")
                output = owned / prefix / name
                output.mkdir(parents=True)
                registry = output / "publications.jsonl"
                cli = [str(install), "revenue_forecast.py", str(input_path)]
                run(prefix + "-" + name + "-validate", BOOTSTRAP, [*cli, "--validate-only", "--verbose"], registry)
                run(prefix + "-" + name + "-compute", BOOTSTRAP, [*cli, "--output", str(output / "forecast.json"), "--markdown", str(output / "forecast.md")], registry)
                forecast = json.loads((output / "forecast.json").read_text(encoding="utf-8"))
                run(prefix + "-" + name + "-snapshot", BOOTSTRAP, [str(install), "revenue_backtest.py", "create", str(input_path), "--version", forecast["forecast_version"], "--output", str(output / "snapshot.json")], registry)
                run(prefix + "-" + name + "-diagnostics", BOOTSTRAP, [str(install), "research_support_diagnostics.py", "--input", str(input_path), "--output", str(output / "diagnostics.json")], registry)
                snapshot = json.loads((output / "snapshot.json").read_text(encoding="utf-8"))
                diag = json.loads((output / "diagnostics.json").read_text(encoding="utf-8"))
                report = (output / "forecast.md").read_text(encoding="utf-8")
                assert forecast["engine_version"] == snapshot["engine_version"] == "4.2.1"
                assert snapshot["snapshot_schema_version"] == "2.0"
                assert snapshot["forecast_result"]["consolidated_forecast"] == forecast["consolidated_forecast"]
                assert diag["input_sha256"] == sha(input_path) and diag["economic_truth_inferred"] is False
                assert forecast["confidence"]["calculation_version"] == "stable-fsum/1"
                research = forecast["confidence"].get("research_adequacy")
                if name == "no_optional":
                    assert research is None
                    assert all(e["status"] == "unsupported" for row in diag["segments"] for e in row["entries"])
                else:
                    cal = research["calibrations"][0]
                    expected = "unverified" if name == "synchronized_future" else "referenced_range"
                    assert cal["adequacy_status"] == expected and expected in report
                    for scenario in ("low", "base", "high"):
                        expected_a = "unsupported" if name == "synchronized_future" else "supported"
                        assert cell(diag, "Segment A", scenario, 2026)["status"] == expected_a
                        if name in {"scope_a_only", "company_scope"}:
                            b = cell(diag, "Segment B", scenario, 2026)
                            assert b["status"] == ("supported" if name == "company_scope" else "unsupported")
                            if name == "scope_a_only":
                                assert b["calibration_ids"] == b["claim_ids"] == []
                                assert "calibration_scope_not_covering:reference_bridge:Segment B" in b["reasons"]
                        if name == "synchronized_future":
                            assert f"conversion_output_period_mismatch:conversion_{scenario}:FY2031:0_{scenario}_2026:FY2026:claim_parameter_conversion_{scenario}" in cal["reasons"]
                assert registry.is_file() and registry.resolve().is_relative_to(owned.resolve())
                outcomes[name] = {"engine_version": forecast["engine_version"], "research_adequacy": research,
                                  "consolidated_forecast": forecast["consolidated_forecast"],
                                  "confidence_score": forecast["confidence"]["score"], "confidence_components": forecast["confidence"]["components"],
                                  "cells": diag["segments"], "sha256": {p.name: sha(p) for p in output.iterdir() if p.is_file()},
                                  "real_snapshot": True, "real_markdown": True}
            assert outcomes["no_optional"]["consolidated_forecast"] == outcomes["synchronized_future"]["consolidated_forecast"] == outcomes["historical_native_bridge"]["consolidated_forecast"]
            for field in ("confidence_score", "confidence_components", "consolidated_forecast"):
                assert outcomes["scope_a_only"][field] == outcomes["company_scope"][field]
            for field in ("confidence_score", "confidence_components"):
                assert outcomes["no_optional"][field] == outcomes["synchronized_future"][field]
            receipt["installations"].append({"root": str(install), "selected_sha256": {n: sha(install / n) for n in SELECTED},
                                             "cases": outcomes, "before_file_count": len(before[str(install)]),
                                             "before_tree_sha256": tree_digest(before[str(install)])})
        assert {p.name: sha(p) for p in inputs.iterdir()} == input_hashes
        receipt["status"] = "accepted"
    except BaseException as exc:
        receipt.update(status="failed", error=repr(exc))
        raise
    finally:
        after = {str(root): tree_snapshot(root) for root in INSTALLS}
        receipt["all_installed_files_unchanged"] = before == after
        receipt["installed_file_count"] = sum(len(value) for value in before.values())
        receipt["source_inputs_unchanged"] = {str(p): sha(p) for p in source_inputs} == before_inputs
        receipt["source_selected_unchanged"] = {n: sha(repo / n) for n in SELECTED} == source_selected
        receipt["environment_unchanged"] = environment_before == dict(os.environ)
        receipt["seconds"] = time.monotonic() - started
        def retry(function, path, error):
            assert Path(path).resolve().is_relative_to(owned.resolve())
            os.chmod(path, stat.S_IWRITE | stat.S_IREAD)
            function(path)
        assert owned.resolve().is_relative_to(Path(tempfile.gettempdir()).resolve())
        shutil.rmtree(owned, onexc=retry)
        receipt["owned_temp_removed"] = not owned.exists()
        receipt["log_sha256"] = {p.name: sha(p) for p in EVIDENCE.glob("*.log")}
        (EVIDENCE / "receipt.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        assert receipt["all_installed_files_unchanged"] and receipt["source_inputs_unchanged"] and receipt["source_selected_unchanged"]
        assert receipt["owned_temp_removed"] and receipt["environment_unchanged"]
        print(json.dumps({k: receipt[k] for k in ("status", "seconds", "all_installed_files_unchanged", "installed_file_count", "owned_temp_removed", "provider_calls", "model_calls")}), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
