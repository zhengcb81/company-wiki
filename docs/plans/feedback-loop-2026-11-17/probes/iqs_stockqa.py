"""Replay the public IQS preview and StockQA inspection with original work and isolated failures."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
from tempfile import TemporaryDirectory


PY = [sys.executable, "-B", "-X", "utf8"]


def read(path):
    return json.loads(Path(path).read_bytes())


def save(path, value):
    path.write_text(json.dumps(value), encoding="utf8")
    return str(path)


def digest(value):
    data = json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(",", ":")).encode("ascii")
    return hashlib.sha256(data).hexdigest()


def owner(root, command, env, data=None):
    result = subprocess.run([*PY, *map(str, command)], cwd=root, env=env, capture_output=True,
                            input=json.dumps(data).encode("utf8") if data is not None else None, timeout=45)
    if result.returncode:
        raise RuntimeError(f"public process exited {result.returncode}: {result.stderr[-700:]!r}")
    return json.loads(result.stdout)


def stockqa_action(qa, work, env, event, kind):
    key = digest([kind, event["details_ref"]])
    payload = {"observation": event, "occurrence_id": digest([event["owner"], event["details_ref"]])}
    action = dict(schema_version="feedback-action/1", method="lookup" if kind == "reconcile" else "submit",
                  owner="stockqa", kind=kind, action_id=key, payload=payload,
                  request_digest=digest(["stockqa", kind, key, payload]))
    cli = ["-m", "src.utils.quick_scan_feedback_owner", "--state", work / "feedback.sqlite"]
    result = owner(qa, [*cli, kind], env, action)["result"]
    if kind == "triage":
        assert owner(qa, [*cli, "get-action", key], env)["receipt"]["result"] == result
    return result


def snapshot(config, work):
    for bundle in read(config)["execution_bundles"].values():
        if bundle.get("inspection_schema_version") != "1.1.0":
            continue
        request = Path(bundle["inspection_request"])
        admission = Path(bundle["admission_config"])
        if not (request.is_file() and admission.is_file()):
            continue
        binding = read(admission)
        ledger, policy = Path(binding["work_store"]), Path(binding["budget_policy_file"])
        if ledger.is_file() and policy.is_file():
            break
    else:
        raise ValueError("no registered historical inspection with its ledger and policy")
    # SQLite's online backup pins a consistent read transaction if the ordinary project is working.
    frozen = work / "original.sqlite"
    source = sqlite3.connect(ledger.resolve().as_uri() + "?mode=ro", uri=True)
    target = sqlite3.connect(frozen)
    try:
        source.backup(target)
    finally:
        target.close()
        source.close()
    return read(request), read(policy), frozen


def hash_file(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def run(iqs, qa, config, work, *, implicit=False):
    incoming, policy, ledger = snapshot(config, work)
    before = hash_file(ledger)
    clean = {k: v for k, v in os.environ.items() if k in {
        "PATH", "PATHEXT", "WINDIR", "SYSTEMROOT", "SYSTEMDRIVE", "COMSPEC",
        "TEMP", "TMP", "HOME", "USERPROFILE", "LOCALAPPDATA", "APPDATA"}}
    runtime = work / "runtime"
    runtime.mkdir()
    save(runtime / "llm_apis.json", {})
    entity = incoming["entity_id"]
    conditions = []
    for case in ("control", "request", "policy"):
        area = work / case
        area.mkdir()
        env = dict(clean, PYTHONPATH=os.pathsep.join(map(str, (iqs, iqs / "scripts"))),
                   RESEARCH_FEEDBACK_DIR=str(area / "events"), STOCKQA_FEEDBACK_STATE=str(area / "feedback.sqlite"),
                   PYTHONDONTWRITEBYTECODE="1")
        if not implicit:
            env.update(RESEARCH_FEEDBACK_RUN_ID="joint-preview", RESEARCH_FEEDBACK_ATTEMPT_ID=case)
        request = save(area / "request.json", incoming if case != "request" else {"entity_id": entity})
        policy_path = area / "policy.json"
        save(policy_path, policy)
        if case == "policy":
            policy_path.write_bytes(b"{")
        binding = save(area / "admission.json", {"work_store": str(ledger), "budget_policy_file": str(policy_path)})
        placeholder = save(area / "given.json", {"entity_id": entity})
        bundle = {name: placeholder for name in ("identity_snapshot", "questions", "manifest", "c06_authority",
                                                   "owner_config", "spend_authorization")}
        bundle.update(entity_id=entity, company="Fixture", provider="fixture", confirmation_id="offline",
                      inspection_request=request, inspection_schema_version="1.1.0", admission_config=binding)
        config_file = save(area / "config.json", dict(stockqa_root=str(qa), stockqa_python=sys.executable,
            runtime_dir=str(runtime), state_root=str(area / "state"), execution_bundles={"fixture": bundle}))
        # The control calls the public preview without looking up send permission. No case calls start/resume.
        if case == "control":
            control = """import json,sys; from scripts.dashboard_execution import ExecutionGateway
cfg=json.load(open(sys.argv[1],encoding='utf8'));cfg['bundles']=cfg['execution_bundles']
r=ExecutionGateway(cfg).preview({'bundle_id':'fixture'},check_permissions=False); v=r['inspection']
print(json.dumps([len(v['work_items']),v['reservation_created'],r['API_requests']]))"""
            count, reserved, calls = owner(iqs, ["-c", control, config_file], env)
            assert count > 0 and reserved is False and calls == 0
            conditions.append(dict(case=case, work_items=count, api_requests=calls, reservation_created=reserved))
            continue
        dispatch = """import json,sys; from scripts.dashboard_service import DashboardService
service=DashboardService(config_path=sys.argv[1])
status,body=service.dispatch('POST','/api/product/tasks/preview',{'bundle_id':'fixture'})
print(json.dumps([status,body.get('error',{}).get('code')]))"""
        status, public = owner(iqs, ["-c", dispatch, config_file], env)
        events = [read(p) for p in (area / "events").glob("feedback-*.jsonl")]
        failures = {row["owner"]: row for row in events if row["disposition"] == "deviation"}
        assert status == 409 and public == "refresh_executor_inspection_rejected", (status, public)
        assert set(failures) == {"invest-quick-scan", "stockqa"}, list(failures)
        ids = {(r["run_id"], r["attempt_id"]) for r in failures.values()}
        assert len(ids) == 1 and (implicit or ids == {("joint-preview", case)}), (case, ids)
        row = failures["stockqa"]
        qa_env = dict(env, PYTHONPATH=str(qa))
        triage = stockqa_action(qa, area, qa_env, row, "triage")
        receipt = stockqa_action(qa, area, qa_env, row, "reconcile")
        assert receipt["job_status"] == "failed" and receipt["cost_state"] == "not_applicable"
        iqs_ref = failures["invest-quick-scan"]["details_ref"]
        iqs_args = [iqs / "scripts/iqs_feedback_owner.py", "get-diagnostic", iqs_ref, "--state-root", area / "state"]
        cold = [owner(iqs, iqs_args, env)["diagnostic"] for _ in range(2)]
        assert cold[0] == cold[1] and cold[0]["observation"]["details_ref"] == iqs_ref
        kinds = [node["type"] for node in triage["diagnostic"]["chain"]]
        conditions.append(dict(case=case, http=status, reason=public, cost=receipt["cost_state"],
                               owners=sorted(failures), cause_types=kinds))
    assert conditions[1]["cause_types"] != conditions[2]["cause_types"], conditions
    assert hash_file(ledger) == before
    assert not list(runtime.rglob("*.sqlite"))
    return conditions


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("iqs", "stockqa", "config", "temp_parent"):
        parser.add_argument(name, type=Path)
    parser.add_argument("--implicit", action="store_true", help="have the calling IQS process create the correlation")
    args = parser.parse_args()
    with TemporaryDirectory(prefix="iqs-qa-", dir=args.temp_parent.resolve()) as temp:
        print(json.dumps(run(args.iqs.resolve(), args.stockqa.resolve(), args.config.resolve(), Path(temp),
                             implicit=args.implicit), ensure_ascii=True))
