"""Independent W22 re-review counterexample (reviewer-authored, round 2).

Targets NEW code introduced by the D1-D3 fix commits (e962198c/ee8138cf) that
neither the author's suite nor either earlier reviewer round attacks: the
zero-write reuse path. The samefile contract was tightened in ``_reconcile``
(recovery), but ``_reconcile_fully_consistent`` (OWNED_COMPLETE zero-write
reuse) still verifies content hashes only — and the shared ``receipt_stub``
still asserts ``source_protection.samefile_verified_per_link: true`` on the
REUSED receipt it emits. Documents the observed behavior; the accompanying
re-review report lists the one-line minimal fix.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from tools.pdf_runtime_deployment import deployment
from unit.test_w22_pdf_deployment_plan import mini_source


@pytest.fixture(autouse=True)
def _relax_ascii(monkeypatch):
    monkeypatch.setattr(deployment, "require_ascii", lambda path: None)


class FakeVenv:
    def __call__(self, host_python: str, env_path: Path) -> None:
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


def deploy(plan):
    def link(source: Path, destination: Path) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        os.link(source, destination)

    return deployment.deploy(plan, host_python="unused", venv_runner=FakeVenv(), link=link)


def test_zero_write_reuse_enforces_samefile_and_conflicts_on_plain_copy(tmp_path):
    """Rebound after the author's fix of review finding R3: the zero-write
    reuse path now proves the samefile attestation it emits. A byte-identical
    plain copy planted at an owned path fails the reuse consistency check
    (not samefile), falls through to reconciliation, and is rejected there as
    foreign content — the same fail-closed contract as recovery. Removing the
    copy restores zero-write reuse."""
    target, plan = make_plan(tmp_path)
    deploy(plan)
    row = plan["env_rows"][0]
    destination = target.joinpath(*row["target"].split("/"))
    destination.unlink()
    destination.write_bytes(Path(row["source"]).read_bytes())  # byte-identical copy
    assert not os.path.samefile(row["source"], destination)
    with pytest.raises(deployment.TargetConflict, match="different content"):
        deploy(plan)  # reuse check proves samefile; the copy is foreign content
    assert destination.read_bytes() == Path(row["source"]).read_bytes()  # preserved
    destination.unlink()
    receipt = deploy(plan)
    # The missing row is relinked (not silently skipped), then a fully
    # consistent tree takes the zero-write reuse path with the samefile
    # attestation proven.
    assert receipt["status"] == "COMPLETE" and receipt["created_links"] >= 1
    assert os.path.samefile(row["source"], destination)  # restored as a hardlink
    again = deploy(plan)
    assert again["status"] == "REUSED" and again["created_links"] == 0
    assert again["source_protection"]["samefile_verified_per_link"] is True
    assert os.path.samefile(row["source"], destination)
    # Recovery-path symmetry: the same tamper during owned-incomplete recovery
    # is rejected the same way (round-1 rebound test covers that path).
    target2, plan2 = make_plan(tmp_path / "recovery-case")

    def link_fail_at_one(source: Path, destination: Path) -> None:
        raise OSError("injected link failure")

    with pytest.raises(deployment.DeploymentError, match="linking failed"):
        deployment.deploy(plan2, host_python="unused", venv_runner=FakeVenv(),
                          link=link_fail_at_one)
    row2 = plan2["env_rows"][0]
    dest2 = target2.joinpath(*row2["target"].split("/"))
    dest2.parent.mkdir(parents=True, exist_ok=True)
    dest2.write_bytes(Path(row2["source"]).read_bytes())
    with pytest.raises(deployment.TargetConflict, match="different content"):
        deploy(plan2)  # both paths now enforce samefile consistently


def test_production_launch_requires_explicit_repo_src():
    """New constructor_probe production-launch mode must refuse to guess the
    first-party source root instead of importing from an ambient path."""
    with pytest.raises(deployment.DeploymentError, match="source root"):
        deployment.constructor_probe("C:/x/python.exe", "C:/x/artifacts",
                                     production_launch=True, repo_src=None)
