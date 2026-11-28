"""Combine production intake with the released owner ports and their native evidence."""

from collections import Counter
from contextlib import closing
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[2]
PYTHON = [sys.executable, "-B", "-X", "utf8"]


def checkout_for(name):
    variable = f"FEEDBACK_{name}_RUNTIME_ROOT"
    deployed = os.environ.get(variable)
    if not deployed:
        pytest.skip(f"set {variable} to the {name} owner-runtime checkout")
    return Path(deployed).resolve()


def register_sidecar(source):
    sidecar = source.with_name(f"feedback-{1:032x}.jsonl")
    source.rename(sidecar)
    sidecar.with_suffix(".ready").touch()
    return sidecar


def real_feedback(tmp_path, checkout, owner, observations, command, *, repair=True):
    kinds = ["triage", "replay", "report"]
    if repair:
        kinds.append("repair")
    actions = {kind: {"argv": [*command, kind], "lookup_argv": [*command, "get-action"]}
               for kind in kinds}
    actions["reconcile"] = [*command, "reconcile"]
    settings = tmp_path / "settings.json"
    settings.write_text(json.dumps({"state": "actions.sqlite", "owners": {owner: {
        "cwd": str(checkout), "observation_dir": str(observations),
        "timeout_seconds": 15, "actions": actions,
    }}}), encoding="utf-8")
    hosts = tmp_path / "hosts.json"
    hosts.write_text(json.dumps({owner: [*PYTHON, "-m", "tools.feedback_loop.local_host",
                                         "--config", str(settings), "rpc"]}), encoding="utf-8")
    drain = [*PYTHON, "-m", "tools.feedback_loop.intake", "--settings", str(settings),
             "--hosts", str(hosts), "--wait-seconds", "30", "drain"]

    def snapshot():
        with closing(sqlite3.connect(tmp_path / "actions.sqlite")) as connection:
            return connection.execute("SELECT action_id, state, request, receipt FROM actions ORDER BY action_id").fetchall()

    first = json.loads(subprocess.check_output(drain, cwd=ROOT, timeout=90))
    assert not first["diagnostics"]
    rows = snapshot()
    counts = Counter(json.loads(request)["kind"] for _, _, request, _ in rows)
    assert counts.pop("observe") >= 1
    assert counts == dict.fromkeys(kinds, 1)
    assert all(state == "done" for _, state, _, _ in rows)
    reports = [json.loads(request)["payload"] for _, _, request, _ in rows
               if json.loads(request)["kind"] == "report"]
    assert len(reports) == 1 and reports[0]["verdict"] == "verified"
    subprocess.check_output(drain, cwd=ROOT, timeout=90)
    assert snapshot() == rows
    return {json.loads(request)["kind"]: (key, json.loads(receipt)["result"])
            for key, _, request, receipt in rows}


@pytest.mark.public_owner
def test_et_original_usage_enters_feedback_loop(tmp_path):
    checkout = checkout_for("ET")
    samples = checkout / "docs/plans/feedback-loop-2026-11-17/samples"
    observations = tmp_path / "observations"
    observations.mkdir()
    saved = {}
    for index, source in enumerate(("deviation-usage-receipt.jsonl", "unknown-usage.jsonl"), 1):
        destination = observations / f"feedback-{index:032x}.jsonl"
        for suffix in ("", ".details.jsonl"):
            path = destination.with_name(destination.name + suffix)
            shutil.copyfile(samples / (source + suffix), path)
            saved[path] = path.read_bytes()
        destination.with_suffix(".ready").touch()

    command = [*PYTHON, str(checkout / "tools/feedback_owner.py"), "--db", str(tmp_path / "et.sqlite"),
               "--sidecar-dir", str(observations)]
    actions = real_feedback(tmp_path, checkout, "earnings-transcripts", observations, command)
    publication = json.loads(subprocess.check_output([*command, "get-usage", actions["repair"][0]],
                                                     cwd=checkout, timeout=25))["publication"]
    assert publication["usage_receipt"]["schema_version"] == "earnings-retrieval-usage/1"
    assert {path: path.read_bytes() for path in saved} == saved


@pytest.mark.owner_local_checkout
def test_sid_recovers_the_original_candidate_without_a_second_discovery(tmp_path):
    checkout = checkout_for("SID")
    observations = tmp_path / "observations"
    observations.mkdir()
    case = checkout / "tests/unit/test_feedback_owner.py"
    probe = ("import runpy,sys; from pathlib import Path; "
             "outcome=runpy.run_path(sys.argv[1])['producer'](Path(sys.argv[2]), 'legacy'); "
             "raise SystemExit(outcome.returncode)")
    subprocess.check_call([*PYTHON, "-c", probe, str(case), str(observations)], cwd=checkout, timeout=30)
    sidecar = register_sidecar(observations / "legacy.jsonl")
    original = sidecar.read_bytes()

    command = [*PYTHON, "-m", "src.feedback_owner", "--db", str(tmp_path / "sid.sqlite"),
               "--sidecar-dir", str(observations)]
    actions = real_feedback(tmp_path, checkout, "stockinfo-dl-simple", observations, command)
    result = json.loads(subprocess.check_output([*command, "get-publication", actions["repair"][0]],
                                               cwd=checkout, timeout=25))
    assert result["publication"]["candidate"]["security_id"]
    assert sidecar.read_bytes() == original
    assert (observations / "calls").read_text().splitlines() == ["native-discovery"]


@pytest.mark.owner_local_checkout
def test_ir_replays_coverage_with_original_report_preserved(tmp_path):
    checkout = checkout_for("IR")
    case = checkout / "tests/test_feedback_owner.py"
    fixture = json.loads(subprocess.check_output([*PYTHON, str(case), "--fixture-root", str(tmp_path)],
                                                cwd=checkout, timeout=30))
    sidecar = register_sidecar(Path(fixture["sidecar"]))
    report = tmp_path / "original.md"
    original = report.read_bytes()

    command = [*PYTHON, str(checkout / "tools/feedback_owner.py"), "--root", str(tmp_path),
               "--sidecar-dir", str(sidecar.parent)]
    actions = real_feedback(tmp_path, checkout, "industry-research", sidecar.parent, command)
    corrected = subprocess.check_output([*command, "get-correction", actions["repair"][1]["fixed_version"]],
                                        cwd=checkout, timeout=25)
    assert b"unavailable" in corrected
    assert report.read_bytes() == original


@pytest.mark.owner_local_checkout
def test_stockwiki_restores_native_assessment_run_references(tmp_path):
    checkout = checkout_for("SW")
    case = checkout / "tests/test_feedback_owner.py"
    fixture_root = tmp_path / "case"
    fixture = json.loads(subprocess.check_output([*PYTHON, str(case), "--fixture-root", str(fixture_root)],
                                                cwd=checkout, timeout=30))
    sidecar = register_sidecar(Path(fixture["sidecar"]))
    original = sidecar.read_bytes()
    command = [*PYTHON, str(checkout / "feedback_owner.py"), "--workspace", fixture["workspace"],
               "--state", str(tmp_path / "stockwiki.sqlite")]
    actions = real_feedback(tmp_path, checkout, "stockwiki", sidecar.parent, command)
    publication = actions["repair"][1]["publication"]
    assert publication["result_id"] == fixture["result_id"]
    assert len(publication["observation_refs"]) == 3 and publication["provider_calls"] == 0
    assert all(ref["run_id"].startswith("origin-run-") for ref in publication["observation_refs"])
    assert sidecar.read_bytes() == original


@pytest.mark.public_owner
def test_iqs_publishes_partial_coverage_from_the_original_answers(tmp_path):
    checkout = checkout_for("IQS")
    runs = tmp_path / "runs"
    run = runs / "original"
    run.mkdir(parents=True)
    answers = run / "answers.json"
    shutil.copyfile(checkout / "tests/fixtures/company_coverage/answers-partial-24of38.json", answers)
    (run / "run-log.json").write_text("[]", encoding="utf-8")
    (run / "index.html").write_text("<html></html>", encoding="utf-8")
    original = answers.read_bytes()
    archived = tmp_path / "archived.json"
    archived.write_text(json.dumps({"question_count": 24, "scored": 15, "ok": True, "usable": True}),
                        encoding="utf-8")
    observations = tmp_path / "observations"
    observations.mkdir()
    out = observations / f"feedback-{1:032x}.jsonl"
    env = {**os.environ, "RESEARCH_FEEDBACK_OUT": str(out), "RESEARCH_FEEDBACK_ATTEMPT_ID": "scan-result-check",
           "IQS_FEEDBACK_RUNS_ROOT": str(runs)}
    env.pop("RESEARCH_FEEDBACK_RUN_ID", None)
    scanned = subprocess.run([*PYTHON, str(checkout / "scripts/scan_result_check.py"), "--run", str(run),
                              "--previous-check", str(archived)], cwd=checkout, env=env,
                             capture_output=True, timeout=20, check=False)
    assert scanned.returncode == 1 and json.loads(scanned.stdout)["coverage"] == "partial"
    out.with_suffix(".ready").touch()

    command = [*PYTHON, str(checkout / "scripts/iqs_feedback_owner.py"), "--db", str(tmp_path / "iqs.sqlite"),
               "--runs-root", str(runs)]
    actions = real_feedback(tmp_path, checkout, "invest-quick-scan", observations, command)
    saved = json.loads(subprocess.check_output([*command, "get-coverage", actions["repair"][0]],
                                              cwd=checkout, timeout=25))["coverage"]
    assert (saved["question_count"], saved["manifest_question_count"], saved["missing_question_count"]) == (24, 38, 14)
    assert saved["usable"] is False and answers.read_bytes() == original


@pytest.mark.public_owner
def test_stockqa_recovers_the_settled_attempt_from_native_binding(tmp_path):
    checkout = checkout_for("QA")
    case = checkout / "tests/unit/test_quick_scan_feedback_owner.py"
    fixture = json.loads(subprocess.check_output([*PYTHON, str(case), "--fixture-root", str(tmp_path / "case")],
                                                cwd=checkout, timeout=45))
    sidecar = register_sidecar(Path(fixture["sidecar"]))
    ledger = Path(fixture["ledger"])
    before = ledger.read_bytes()
    command = [*PYTHON, "-m", "src.utils.quick_scan_feedback_owner", "--state", fixture["state"]]
    actions = real_feedback(tmp_path, checkout, "stockqa", sidecar.parent, command)
    publication = actions["repair"][1]["publication"]
    assert publication["attempt_id"] == fixture["attempt_id"]
    assert publication["API_requests"] == publication["new_attempts"] == publication["new_generations"] == 0
    assert ledger.read_bytes() == before


@pytest.mark.owner_local_checkout
def test_dashboard_confirms_disclosure_through_the_public_http_read(tmp_path):
    checkout = checkout_for("DASH")
    case = checkout / "tests/unit/m6-feedback-runtime/test_feedback_owner.py"
    with subprocess.Popen([*PYTHON, str(case), "--fixture-root", str(tmp_path / "case")],
                          cwd=checkout, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                          text=True, encoding="utf-8") as native:
        try:
            fixture = json.loads(native.stdout.readline())
            sidecar = register_sidecar(Path(fixture["sidecar"]))
            before = sidecar.read_bytes()
            command = [*PYTHON, str(checkout / "scripts/feedback_owner.py"), "--db", str(tmp_path / "dashboard.sqlite"),
                       "--sidecar-dir", str(sidecar.parent), "--origin", fixture["origin"]]
            actions = real_feedback(tmp_path, checkout, "investment-dashboard", sidecar.parent, command, repair=False)
            publication = actions["replay"][1]
            evidence = json.loads(subprocess.check_output(
                [*command, "get-evidence", publication["evidence_ref"]], cwd=checkout, timeout=20,
            ))["evidence"]
            assert evidence["observation_id"] and evidence["company"]["analysis_subject_id"]
            assert evidence["data_as_of"] == "2026-09-30" and sidecar.read_bytes() == before
        finally:
            try:
                native.communicate("\n", timeout=15)
            except subprocess.TimeoutExpired:
                native.kill()
                native.communicate()
