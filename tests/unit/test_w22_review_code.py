"""Independent W22 review counterexamples, round 2 (reviewer-authored).

Written by the independent reviewer against commit 0434d88f; none of these
tests existed in the author's suite or in the round-1 reviewer file
(test_w22_review_counterexamples.py). They attack: receipt-misclassification
with matching files, externally modified emitted config, permission-denied
linking, plan-digest key-order stability, and the CLI constructor deadline
binding. The REPO_SRC off-by-one tests (round-1 R2 / finding D1) were
rebound to pass after the author fixed the parents[3] index.
"""
from __future__ import annotations

import copy
import json
import os
import subprocess
from pathlib import Path

import pytest

from tools.pdf_runtime_deployment import deployment
from unit.test_w22_pdf_deployment_plan import mini_source


@pytest.fixture(autouse=True)
def _relax_ascii(monkeypatch):
    """%TEMP% on this host carries non-ASCII characters (same rationale as the
    author's suites); production targets remain ASCII-enforced by contract."""
    monkeypatch.setattr(deployment, "require_ascii", lambda path: None)


class FakeVenv:
    def __init__(self):
        self.calls = 0

    def __call__(self, host_python: str, env_path: Path) -> None:
        self.calls += 1
        (env_path / "Scripts").mkdir(parents=True, exist_ok=True)
        (env_path / "Scripts" / "python.exe").write_bytes(b"interpreter")
        (env_path / "pyvenv.cfg").write_text(
            "home = somewhere\ninclude-system-site-packages = false\n", encoding="utf-8")
        (env_path / "Lib" / "site-packages").mkdir(parents=True, exist_ok=True)


def make_plan(root: Path):
    profile, probe = mini_source(root)
    target = root / "deploy-target"
    plan = deployment.build_plan(target, profile, probe)
    return target, plan


def deploy(plan, *, fail_link_at=None, venv=None, permission_denied_at=None):
    calls = {"n": 0}

    def link(source: Path, destination: Path) -> None:
        calls["n"] += 1
        if fail_link_at is not None and calls["n"] == fail_link_at:
            raise OSError("injected link failure")
        if permission_denied_at is not None and calls["n"] == permission_denied_at:
            raise PermissionError(13, "injected permission denial")
        destination.parent.mkdir(parents=True, exist_ok=True)
        os.link(source, destination)

    return deployment.deploy(plan, host_python="unused",
                             venv_runner=venv or FakeVenv(), link=link), calls["n"]


def test_corrupt_receipt_with_matching_files_fails_closed_and_preserves_bytes(tmp_path):
    """Misclassification angle: the tree is byte-perfect but the receipt on
    disk is corrupt/foreign. deploy() must refuse (FOREIGN -> TargetConflict)
    and must not "repair" or rewrite anything, including the corrupt receipt;
    restoring the original receipt must resume zero-write reuse. The tool is
    required never to guess ownership from matching bytes alone."""
    target, plan = make_plan(tmp_path)
    deploy(plan)
    receipt_path = target / deployment.RECEIPT_NAME
    genuine = receipt_path.read_bytes()
    victim = target.joinpath(*plan["env_rows"][0]["target"].split("/"))
    victim_bytes = victim.read_bytes()
    receipt_path.write_bytes(b"{not json at all")
    with pytest.raises(deployment.TargetConflict):
        deploy(plan)
    assert receipt_path.read_bytes() == b"{not json at all"  # nothing rewritten
    assert victim.read_bytes() == victim_bytes
    receipt_path.write_bytes(genuine)
    before = deployment.snapshot_tree(target)
    receipt, links = deploy(plan)
    assert receipt["status"] == "REUSED" and links == 0
    assert deployment.snapshot_tree(target) == before


def test_foreign_schema_receipt_with_matching_files_is_refused_not_reused(tmp_path):
    """Same angle, foreign receipt that parses: a valid-JSON receipt of another
    schema/tool claiming COMPLETE over an identical tree must not be treated as
    this tool's deployment, and must not be overwritten on the refusal path."""
    target, plan = make_plan(tmp_path)
    deploy(plan)
    receipt_path = target / deployment.RECEIPT_NAME
    foreign = {"schema_version": "someone-else/9", "tool": {"name": "pdf_runtime_deployment"},
               "status": "COMPLETE", "plan_sha256": plan["plan_sha256"]}
    receipt_path.write_text(json.dumps(foreign), encoding="utf-8")
    with pytest.raises(deployment.TargetConflict):
        deploy(plan)
    assert json.loads(receipt_path.read_text(encoding="utf-8")) == foreign
    assert deployment.classify_target(target, plan["plan_sha256"]) == "FOREIGN"


def test_externally_modified_config_conflicts_then_restored_config_recovers(tmp_path):
    """Config-error fault injection: a modified emitted config must abort with
    TargetConflict before it is overwritten, and a later deploy with the
    original bytes must recover to COMPLETE without relinking."""
    target, plan = make_plan(tmp_path)
    deploy(plan)
    config_path = Path(plan["output_config"]["path"])
    tampered = config_path.read_bytes() + b" "
    config_path.write_bytes(tampered)
    with pytest.raises(deployment.TargetConflict, match="config"):
        deploy(plan)
    assert config_path.read_bytes() == tampered  # conflict never overwrites
    config_path.write_bytes(config_path.read_bytes().rstrip(b" "))
    receipt, links = deploy(plan)
    assert receipt["status"] == "COMPLETE"
    assert receipt["reused_links"] == 4 and receipt["created_links"] == 0


def test_permission_denied_linking_is_explicit_incomplete_then_recovers(tmp_path):
    """Unwritable-scratch class fault injection: PermissionError from the link
    backend surfaces as an explicit DeploymentError, leaves an OWNED_INCOMPLETE
    receipt, and a later permitted run recovers without recreating the venv."""
    target, plan = make_plan(tmp_path)
    venv = FakeVenv()
    with pytest.raises(deployment.DeploymentError, match="linking failed"):
        deploy(plan, venv=venv, permission_denied_at=2)
    assert deployment.classify_target(target, plan["plan_sha256"]) == "OWNED_INCOMPLETE"
    receipt, _links = deploy(plan, venv=venv)
    assert receipt["status"] == "COMPLETE"
    assert venv.calls == 1  # recovery must not recreate the venv


def test_plan_digest_is_stable_under_dict_key_order(tmp_path):
    """plan_digest must be content-addressed: recursively re-inserting the
    same plan mapping with a different key order (and re-serialising through
    JSON) must reproduce the identical digest, so idempotent reuse cannot be
    broken by harmless re-serialisation of the plan file."""
    _target, plan = make_plan(tmp_path)

    def reorder(value):
        if isinstance(value, dict):
            return {key: reorder(value[key]) for key in sorted(value, reverse=True)}
        if isinstance(value, list):
            return [reorder(item) for item in value]
        return value

    shuffled = reorder(copy.deepcopy(plan))
    assert list(shuffled) != list(plan)
    assert deployment.plan_digest(shuffled) == deployment.plan_digest(plan)
    assert shuffled["plan_sha256"] == plan["plan_sha256"]
    deployment.load_plan(json.loads(json.dumps(shuffled)))  # still validates


def test_cli_constructor_probe_enforces_deadline_budget(tmp_path, monkeypatch, capsys):
    """The CLI must fail (1) any observation that exceeds the 30s constructor
    cap even when the probe reports CONSTRUCTOR_OK, pass (0) an in-budget one,
    propagate the deadline into the probe, and map an external subprocess
    timeout kill to exit 3."""
    from tools.pdf_runtime_deployment import __main__ as cli

    config = tmp_path / "cfg.json"
    config.write_text(json.dumps({"python": "C:/x/python.exe",
                                  "artifacts": "C:/x/artifacts"}), encoding="utf-8")
    seen = {}

    def fake_probe(python, artifacts, *, timeout, production_launch=False, repo_src=None):
        seen["timeout"] = timeout
        seen["production_launch"] = production_launch
        return dict(seen["result"])

    monkeypatch.setattr(deployment, "constructor_probe", fake_probe)
    argv = ["constructor-probe", "--config", str(config)]

    seen["result"] = {"status": "CONSTRUCTOR_OK", "seconds": 45.001}
    assert cli.main(argv) == 1
    assert seen["timeout"] == deployment.CONSTRUCTOR_DEADLINE_SECONDS == 30
    assert seen["production_launch"] is False  # bare diagnostic by default

    seen["result"] = {"status": "CONSTRUCTOR_OK", "seconds": 22.748}
    assert cli.main(argv) == 0

    seen["result"] = {"status": "SDK_CONSTRUCTOR_FAILED", "seconds": 3.2}
    assert cli.main(argv) == 1

    seen["result"] = {"status": "CONSTRUCTOR_OK", "seconds": 13.7}
    assert cli.main([*argv, "--production-launch"]) == 0
    assert seen["production_launch"] is True  # production launch shape selectable

    def exploding_probe(python, artifacts, *, timeout, production_launch=False, repo_src=None):
        raise subprocess.TimeoutExpired(cmd=[python], timeout=timeout)

    monkeypatch.setattr(deployment, "constructor_probe", exploding_probe)
    assert cli.main(argv) == 3
    capsys.readouterr()


def test_cli_default_repo_src_resolves_into_this_repo():
    """Rebound from a non-strict xfail: the author fixed the parents[3]
    off-by-one (finding D1); the CLI default now resolves into this repo."""
    from tools.pdf_runtime_deployment import __main__ as cli

    repo_root = Path(__file__).resolve().parents[2]
    assert cli.REPO_SRC == repo_root / "src"
    assert cli.REPO_SRC.is_dir()


def test_alignment_diagnostic_parent_path_resolves_into_this_repo():
    """Rebound from the round-2 documentation test: the author fixed the
    parents[3] off-by-one, so the diagnostic now inserts this repo's src/."""
    module = __import__("tools.pdf_runtime_deployment._alignment_diagnostic",
                        fromlist=["__file__"])
    diagnostic = Path(module.__file__ or "").resolve()
    assert diagnostic.parents[2] / "src" == Path(__file__).resolve().parents[2] / "src"
    assert (diagnostic.parents[2] / "src").is_dir()
