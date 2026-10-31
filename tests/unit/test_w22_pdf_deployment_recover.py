"""Deploy is idempotent, recovers owned incomplete trees and protects others."""
import hashlib
import json
import os
from pathlib import Path

import pytest

from tools.pdf_runtime_deployment import deployment
from unit.test_w22_pdf_deployment_plan import mini_source


@pytest.fixture(autouse=True)
def relax_ascii_policy_for_non_ascii_host_temp(monkeypatch):
    """See test_w22_pdf_deployment_plan.relax_ascii_policy_for_non_ascii_host_temp."""
    monkeypatch.setattr(deployment, "require_ascii", lambda path: None)


class FakeVenv:
    """Stands in for `python -m venv --without-pip --copies`."""

    def __init__(self):
        self.calls: list[Path] = []

    def __call__(self, host_python: str, env_path: Path) -> None:
        self.calls.append(env_path)
        (env_path / "Scripts").mkdir(parents=True, exist_ok=True)
        (env_path / "Scripts" / "python.exe").write_bytes(b"interpreter")
        (env_path / "pyvenv.cfg").write_text(
            "home = somewhere\ninclude-system-site-packages = false\n", encoding="utf-8")
        (env_path / "Lib" / "site-packages").mkdir(parents=True, exist_ok=True)


def make_plan(tmp_path: Path, **kwargs):
    profile, probe = mini_source(tmp_path, **kwargs)
    target = tmp_path / "deploy-target"
    plan = deployment.build_plan(target, profile, probe)
    return target, plan


def deploy(plan, *, fail_link_at=None, venv=None):
    calls = {"n": 0}

    def link(source: Path, destination: Path) -> None:
        calls["n"] += 1
        if fail_link_at is not None and calls["n"] == fail_link_at:
            raise OSError("injected link failure")
        destination.parent.mkdir(parents=True, exist_ok=True)
        os.link(source, destination)

    receipt = deployment.deploy(plan, host_python="unused",
                                venv_runner=venv or FakeVenv(), link=link)
    return receipt, calls["n"]


def test_fresh_deploy_writes_env_links_config_and_receipt(tmp_path):
    target, plan = make_plan(tmp_path)
    venv = FakeVenv()
    receipt, link_calls = deploy(plan, venv=venv)
    assert receipt["status"] == "COMPLETE"
    assert receipt["created_links"] == 4 and link_calls == 4
    assert receipt["sdk_bytes_copied"] == 0 and receipt["model_bytes_copied"] == 0
    assert len(venv.calls) == 1
    config_path = Path(plan["output_config"]["path"])
    raw = json.loads(config_path.read_text(encoding="utf-8"))
    assert raw["python"] == str(target / "env" / "Scripts" / "python.exe")
    assert raw["artifacts"] == str(target / "artifacts")
    assert raw["model_sha256"] == plan["source_profile"]["model_sha256"]
    assert receipt["output_config_sha256"] == hashlib.sha256(
        config_path.read_bytes()).hexdigest()
    assert (target / deployment.RECEIPT_NAME).is_file()


def test_source_change_after_plan_aborts_before_linking_that_row(tmp_path):
    target, plan = make_plan(tmp_path)
    victim = Path(plan["env_rows"][0]["source"])
    victim.write_text("VALUE = 'mutated'\n", encoding="utf-8")
    with pytest.raises(deployment.SourceChanged):
        deploy(plan)
    assert deployment.classify_target(target, plan["plan_sha256"]) == "OWNED_INCOMPLETE"


def test_link_failure_midway_recovers_without_relitigating_existing_links(tmp_path):
    target, plan = make_plan(tmp_path)
    with pytest.raises(deployment.DeploymentError):
        deploy(plan, fail_link_at=3)
    assert deployment.classify_target(target, plan["plan_sha256"]) == "OWNED_INCOMPLETE"
    venv = FakeVenv()
    receipt, link_calls = deploy(plan, venv=venv)
    assert receipt["status"] == "COMPLETE"
    assert receipt["created_links"] == 2 and receipt["reused_links"] == 2
    assert len(venv.calls) == 0  # recovery must not recreate the venv
    assert deployment.classify_target(target, plan["plan_sha256"]) == "OWNED_COMPLETE"


def test_complete_target_reused_with_zero_writes(tmp_path):
    target, plan = make_plan(tmp_path)
    deploy(plan)
    before = deployment.snapshot_tree(target)
    receipt, link_calls = deploy(plan)
    assert receipt["status"] == "REUSED"
    assert link_calls == 0 and receipt["created_links"] == 0
    assert deployment.snapshot_tree(target) == before


def test_foreign_file_at_planned_path_conflicts_and_is_never_touched(tmp_path):
    target, plan = make_plan(tmp_path)
    victim_rel = plan["env_rows"][0]["target"]
    victim = target / Path(*victim_rel.split("/"))
    victim.parent.mkdir(parents=True)
    victim.write_bytes(b"foreign payload")
    with pytest.raises(deployment.TargetConflict):
        deploy(plan)
    assert victim.read_bytes() == b"foreign payload"


def test_venv_failure_is_explicit_and_leaves_target_incomplete(tmp_path):
    target, plan = make_plan(tmp_path)

    def broken_venv(host_python, env_path):
        raise RuntimeError("venv backend unavailable")

    with pytest.raises(deployment.DeploymentError, match="venv"):
        deployment.deploy(plan, host_python="unused",
                          venv_runner=broken_venv, link=lambda s, d: None)
    assert deployment.classify_target(target, plan["plan_sha256"]) in {"EMPTY", "OWNED_INCOMPLETE"}


def test_base_python_requirement_is_explicit(tmp_path):
    profile, probe = mini_source(tmp_path)
    with pytest.raises(deployment.DeploymentError, match="base"):
        deployment.require_base_python(str(tmp_path / "base-python"), prefix="other", base_prefix="other")
    deployment.require_base_python(str(tmp_path / "base-python"),
                                   prefix=str(tmp_path / "base-python"),
                                   base_prefix=str(tmp_path / "base-python"))
