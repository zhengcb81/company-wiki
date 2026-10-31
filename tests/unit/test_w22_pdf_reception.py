"""ROOT reception regressions; no SDK, real model, or production environment."""
import os
from pathlib import Path

import pytest

from tools.pdf_runtime_deployment import deployment
from unit.test_w22_pdf_deployment_plan import mini_source
from unit.test_w22_pdf_deployment_recover import FakeVenv


@pytest.fixture(autouse=True)
def _mechanics_in_host_temp(monkeypatch):
    monkeypatch.setattr(deployment, "require_ascii", lambda path: None)


def make_plan(tmp_path):
    profile, probe = mini_source(tmp_path)
    target = tmp_path / "target"
    return target, deployment.build_plan(target, profile, probe)


def deploy(plan):
    return deployment.deploy(plan, host_python="unused", venv_runner=FakeVenv())


def junction(source, destination):
    if os.name != "nt":
        destination.symlink_to(source, target_is_directory=True)
    else:
        import _winapi
        _winapi.CreateJunction(str(source), str(destination))


def test_blocked_plan_cannot_be_deployed(tmp_path):
    profile, probe = mini_source(tmp_path)
    Path(probe["site_packages"]).joinpath("acme_pkg/__init__.py").unlink()
    target = tmp_path / "target"
    plan = deployment.build_plan(target, profile, probe)
    assert plan["blocking_errors"]
    with pytest.raises(deployment.DeploymentError, match="block"):
        deploy(plan)
    assert not target.exists()


def test_output_config_escape_is_rejected_before_any_write(tmp_path):
    target, plan = make_plan(tmp_path)
    outside = tmp_path / "outside-config.json"
    plan["output_config"]["path"] = str(outside)
    plan["plan_sha256"] = deployment.plan_digest(plan)
    with pytest.raises(deployment.DeploymentError, match="config"):
        deploy(plan)
    assert not target.exists() and not outside.exists()


def test_empty_target_junction_is_rejected_without_writing_referent(tmp_path):
    target, plan = make_plan(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    junction(outside, target)
    try:
        with pytest.raises(deployment.DeploymentError, match="link|reparse|alias"):
            deploy(plan)
        assert list(outside.iterdir()) == []
    finally:
        target.rmdir() if os.name == "nt" else target.unlink()


def test_recovery_rejects_junction_parent_before_writing_outside(tmp_path):
    target, plan = make_plan(tmp_path)
    target.mkdir()
    deployment.write_receipt(target, deployment.receipt_stub(plan, "INCOMPLETE"))
    FakeVenv()("unused", target / "env")
    outside = tmp_path / "outside-package"
    outside.mkdir()
    link = target / "env/Lib/site-packages/acme_pkg"
    junction(outside, link)
    before = (target / deployment.RECEIPT_NAME).read_bytes()
    try:
        with pytest.raises(deployment.DeploymentError, match="link|reparse|alias"):
            deploy(plan)
        assert list(outside.iterdir()) == []
        assert (target / deployment.RECEIPT_NAME).read_bytes() == before
    finally:
        link.rmdir() if os.name == "nt" else link.unlink()


def test_reuse_restores_missing_interpreter_instead_of_claiming_ready(tmp_path):
    target, plan = make_plan(tmp_path)
    deploy(plan)
    python = target / "env/Scripts/python.exe"
    python.unlink()
    receipt = deploy(plan)
    assert receipt["status"] == "COMPLETE"
    assert python.is_file()


def test_reuse_rejects_modified_venv_isolation(tmp_path):
    target, plan = make_plan(tmp_path)
    deploy(plan)
    cfg = target / "env/pyvenv.cfg"
    cfg.write_text("include-system-site-packages = true\n", encoding="utf-8")
    with pytest.raises(deployment.DeploymentError, match="system site"):
        deploy(plan)
    assert cfg.read_text(encoding="utf-8") == "include-system-site-packages = true\n"


def test_plan_for_a_different_tool_revision_is_not_rebound_silently(tmp_path):
    target, plan = make_plan(tmp_path)
    plan["tool"]["implementation_sha256"] = "0" * 64
    plan["plan_sha256"] = deployment.plan_digest(plan)
    with pytest.raises(deployment.DeploymentError, match="tool"):
        deploy(plan)
    assert not target.exists()


def test_receipt_writer_rejects_target_alias_before_creating_temp(tmp_path):
    outside = tmp_path / "outside-marker"
    outside.mkdir()
    alias = tmp_path / "marker-alias"
    junction(outside, alias)
    try:
        with pytest.raises(deployment.DeploymentError, match="link|reparse|alias"):
            deployment.write_receipt(alias, {"status": "COMPLETE"})
        assert list(outside.iterdir()) == []
    finally:
        alias.rmdir() if os.name == "nt" else alias.unlink()


@pytest.mark.parametrize("relative,payload", [
    ("env/Scripts/python.exe", b"NOT AN INTERPRETER"),
    ("env/pyvenv.cfg", b"home = C:/different-python\ninclude-system-site-packages = false\n"),
])
def test_reuse_rejects_changed_scaffold_bytes(tmp_path, relative, payload):
    target, plan = make_plan(tmp_path)
    deploy(plan)
    victim = target / relative
    victim.write_bytes(payload)
    before = (target / deployment.RECEIPT_NAME).read_bytes()
    with pytest.raises(deployment.DeploymentError, match="scaffold"):
        deploy(plan)
    assert victim.read_bytes() == payload
    assert (target / deployment.RECEIPT_NAME).read_bytes() == before


def test_legacy_complete_receipt_cannot_attest_unbound_scaffold(tmp_path):
    import json
    target, plan = make_plan(tmp_path)
    deploy(plan)
    marker = target / deployment.RECEIPT_NAME
    receipt = json.loads(marker.read_text(encoding="utf-8"))
    receipt.pop("scaffold_sha256", None)
    marker.write_text(json.dumps(receipt), encoding="utf-8")
    before = marker.read_bytes()
    with pytest.raises(deployment.DeploymentError, match="scaffold.*binding"):
        deploy(plan)
    assert marker.read_bytes() == before
