"""Independent W22 review counterexamples (reviewer-authored, not the author's).

Each test targets a risk the author's own suite does not cover. Where a test
documents a gap, it asserts the observed behavior of the code under review and
says so in the docstring; the accompanying review report lists the minimal fix.
"""
from __future__ import annotations

import copy
import json
import os
from pathlib import Path

import pytest

from tools.pdf_runtime_deployment import deployment
from unit.test_w22_pdf_deployment_plan import mini_source


@pytest.fixture(autouse=True)
def relax_ascii_policy_for_non_ascii_host_temp(monkeypatch):
    """Same host limitation as the author's suites: %TEMP% is non-ASCII."""
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


def deploy(plan, *, fail_link_at=None):
    calls = {"n": 0}

    def link(source: Path, destination: Path) -> None:
        calls["n"] += 1
        if fail_link_at is not None and calls["n"] == fail_link_at:
            raise OSError("injected link failure")
        destination.parent.mkdir(parents=True, exist_ok=True)
        os.link(source, destination)

    return deployment.deploy(plan, host_python="unused",
                             venv_runner=FakeVenv(), link=link), calls["n"]


def test_plain_copy_planted_at_owned_path_fails_closed_and_recovery_relinks(tmp_path):
    """Rebound after the author's fix of this round-1 counterexample: a plain
    copy (not a hardlink) at a planned path during owned-incomplete recovery
    is foreign content, not a reused link. deploy must fail closed with
    TargetConflict, preserve the planted bytes, and only complete once the
    path really is a hardlink of the planned source."""
    target, plan = make_plan(tmp_path)
    with pytest.raises(deployment.DeploymentError):
        deploy(plan, fail_link_at=1)  # owned incomplete tree with a live receipt
    row = plan["env_rows"][0]
    destination = target.joinpath(*row["target"].split("/"))
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(Path(row["source"]).read_bytes())  # plain copy, no link
    assert not os.path.samefile(row["source"], destination)
    with pytest.raises(deployment.TargetConflict):
        deploy(plan)
    assert destination.read_bytes() == Path(row["source"]).read_bytes()  # copy preserved
    destination.unlink()  # remove the foreign copy from the owned path
    receipt, _ = deploy(plan)
    assert receipt["status"] == "COMPLETE"
    assert receipt["created_links"] >= 1  # the incomplete tree held no valid links
    assert os.path.samefile(row["source"], destination)  # recovery linked it


def test_duplicate_target_rows_after_load_plan_fail_closed(tmp_path):
    """load_plan validates only per-row shape plus the digest, so a re-digested
    plan carrying two rows for one target is accepted. deploy must still fail
    closed: a duplicate row whose sha does not match the source aborts with
    SourceChanged before touching the tree; a byte-identical duplicate is
    benign reuse and never overwrites."""
    target, plan = make_plan(tmp_path)
    first = copy.deepcopy(plan["env_rows"][0])
    second = copy.deepcopy(first)
    second["sha256"] = "f" * 64
    plan["env_rows"].append(second)
    plan["plan_sha256"] = deployment.plan_digest(plan)
    deployment.load_plan(plan)  # accepted: integrity, not authenticity
    with pytest.raises(deployment.SourceChanged):
        deploy(plan)
    assert not victim_bytes_differ(target, first, Path(first["source"]).read_bytes())
    # byte-identical duplicate: reconcile keeps one row, reuses the other
    target, plan = make_plan(tmp_path / "benign")
    benign = copy.deepcopy(plan["env_rows"][0])
    plan["env_rows"].append(benign)
    plan["plan_sha256"] = deployment.plan_digest(plan)
    receipt, _ = deploy(plan)
    assert receipt["status"] == "COMPLETE"
    victim = target.joinpath(*benign["target"].split("/"))
    assert victim.read_bytes() == Path(benign["source"]).read_bytes()


def victim_bytes_differ(target: Path, row: dict, expected: bytes) -> bool:
    victim = target.joinpath(*row["target"].split("/"))
    return victim.exists() and victim.read_bytes() != expected


def test_load_plan_bytes_field_tampering_caught_at_reconcile_not_load(tmp_path):
    """A bytes-field tamper with a valid int and a recomputed digest passes
    load_plan (size is advisory; sha256 is the authority) and must then abort
    via SourceChanged before linking that row. A non-int bytes value must be
    rejected outright."""
    target, plan = make_plan(tmp_path)
    tampered = copy.deepcopy(plan)
    tampered["env_rows"][0]["bytes"] = int(tampered["env_rows"][0]["bytes"]) + 1
    tampered["plan_sha256"] = deployment.plan_digest(tampered)
    deployment.load_plan(tampered)
    with pytest.raises(deployment.SourceChanged):
        deploy(tampered)
    broken = copy.deepcopy(plan)
    broken["env_rows"][0]["bytes"] = 1.5
    broken["plan_sha256"] = deployment.plan_digest(broken)
    with pytest.raises(deployment.DeploymentError, match="digest"):
        deployment.load_plan(broken)


def test_classify_target_rejects_corrupt_or_mistyped_receipts(tmp_path):
    """Corrupt JSON, wrong schema, wrong tool name, missing plan digest or a
    directory named deployment.json must never classify as owned."""
    target, plan = make_plan(tmp_path)
    target.mkdir()
    marker = target / deployment.RECEIPT_NAME
    marker.write_text("{not json", encoding="utf-8")
    assert deployment.classify_target(target, plan["plan_sha256"]) == "FOREIGN"
    wrong_schema = deployment.receipt_stub(plan, "COMPLETE")
    wrong_schema["schema_version"] = "pdf-runtime-deployment/0"
    marker.write_text(json.dumps(wrong_schema), encoding="utf-8")
    assert deployment.classify_target(target, plan["plan_sha256"]) == "FOREIGN"
    wrong_tool = deployment.receipt_stub(plan, "COMPLETE")
    wrong_tool["tool"] = {"name": "someone_else", "implementation_sha256": "0" * 64}
    marker.write_text(json.dumps(wrong_tool), encoding="utf-8")
    assert deployment.classify_target(target, plan["plan_sha256"]) == "FOREIGN"
    no_digest = deployment.receipt_stub(plan, "COMPLETE")
    no_digest.pop("plan_sha256")
    marker.write_text(json.dumps(no_digest), encoding="utf-8")
    assert deployment.classify_target(target, plan["plan_sha256"]) == "FOREIGN"
    marker.unlink()
    marker.mkdir()  # receipt path occupied by a directory
    assert deployment.classify_target(target, plan["plan_sha256"]) == "FOREIGN"
    marker.rmdir()
    odd_status = deployment.receipt_stub(plan, "SOMETHING_ELSE")
    deployment.write_receipt(target, odd_status)
    assert deployment.classify_target(target, plan["plan_sha256"]) == "OWNED_INCOMPLETE"


def test_record_unknown_hash_algorithm_is_silently_ignored(tmp_path):
    """Counterexample: a RECORD hash declaration with an unknown algorithm
    (hashlib.new raises) makes _declared_hash_matches return None, and build_plan
    neither records a deviation nor blocks. The card requires diagnostics to be
    honest; a silent ignore is a (nonblocking) honesty gap."""
    profile, probe = mini_source(tmp_path)
    extra = (tmp_path / "source-env/Lib/site-packages/acme_pkg/extra.py")
    extra.write_text("x = 1\n", encoding="utf-8")
    entry = probe["distributions"]["acme-pkg"]
    entry["record"].append(["acme_pkg/extra.py", "rot13=cKks", str(extra.stat().st_size)])
    plan = deployment.build_plan(Path(tmp_path / "deploy-target"), profile, probe)
    assert plan["blocking_errors"] == []
    # (mini_source declares hex digests, so __init__.py shows a fixture-level
    # hash deviation; the point is that the rot13 row adds no signal at all)
    assert not any(d["path"].endswith("extra.py")
                   for d in plan["diagnostics"]["record_deviations"])  # silently ignored
    assert "env/Lib/site-packages/acme_pkg/extra.py" in {r["target"] for r in plan["env_rows"]}


def test_row_source_deletion_between_plan_and_deploy_aborts(tmp_path):
    """A selected source (env row or artifact row) deleted after planning must
    abort with SourceChanged before any link touches the tree."""
    target, plan = make_plan(tmp_path / "artifact-case")
    Path(plan["artifact_rows"][0]["source"]).unlink()
    with pytest.raises(deployment.SourceChanged):
        deploy(plan)
    target, plan = make_plan(tmp_path / "env-case")
    Path(plan["env_rows"][-1]["source"]).unlink()
    with pytest.raises(deployment.SourceChanged):
        deploy(plan)
    assert not (target / "artifacts").exists() or not any((target / "artifacts").iterdir())


def test_cli_default_repo_src_points_at_this_repo():
    """Rebound from a strict xfail: the author fixed the parents[3] off-by-one
    (finding D1), so the CLI default now resolves into this repo's src/."""
    from tools.pdf_runtime_deployment import __main__ as cli

    expected = Path(cli.__file__).resolve().parents[2] / "src"
    assert cli.REPO_SRC == expected, (
        f"CLI default --repo-src resolves to {cli.REPO_SRC}, expected {expected}")
    assert cli.REPO_SRC.is_dir()
