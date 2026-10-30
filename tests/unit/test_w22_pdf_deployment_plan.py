"""Deployment plan is explicit, ASCII-bound and diagnostic-honest (no SDK)."""
import hashlib
import json
from pathlib import Path

import pytest

from tools.pdf_runtime_deployment import deployment


@pytest.fixture(autouse=True)
def relax_ascii_policy_for_non_ascii_host_temp(monkeypatch):
    """This host's %TEMP% carries non-ASCII profile characters, so mechanics
    tests cannot materialise an ASCII target there. Production targets stay
    ASCII by contract: the dedicated policy tests live in
    test_w22_pdf_deployment_config.py and the verify probe re-asserts the
    interpreter prefix ASCII-ness inside the deployed process."""
    monkeypatch.setattr(deployment, "require_ascii", lambda path: None)


def write_record_file(path: Path, rows: list[tuple[str, str, str]]) -> str:
    body = "\n".join(",".join(row) for row in rows) + "\n"
    path.write_text(body, encoding="utf-8")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def mini_source(tmp_path: Path, *, declare_wrong_hash: bool = False):
    """A tiny fake source env: one dist with two real files plus artifacts."""
    site = tmp_path / "source-env" / "Lib" / "site-packages"
    package = site / "acme_pkg"
    package.mkdir(parents=True)
    init = package / "__init__.py"
    init.write_text("VALUE = 'acme-1.0'\n", encoding="utf-8")
    info = site / "acme_pkg-1.0.0.dist-info"
    info.mkdir()
    metadata = info / "METADATA"
    metadata.write_text("Metadata-Version: 2.1\nName: acme-pkg\nVersion: 1.0.0\n", encoding="utf-8")
    installer = info / "INSTALLER"
    installer.write_text("conda\n", encoding="utf-8")
    init_declared = "sha256=" + hashlib.sha256(init.read_bytes()).hexdigest()
    if declare_wrong_hash:
        init_declared = "sha256=" + hashlib.sha256(b"stale").hexdigest()
    rows = [
        ("acme_pkg/__init__.py", init_declared, str(init.stat().st_size)),
        ("acme_pkg-1.0.0.dist-info/METADATA", "", ""),
        ("acme_pkg/_unhashed.pyc", "", ""),
    ]
    record_sha = write_record_file(info / "RECORD", rows)
    artifacts = tmp_path / "source-model"
    artifacts.mkdir()
    config = artifacts / "config.json"
    config.write_text('{"model_type": "acme"}\n', encoding="utf-8")
    weights = artifacts / "model.safetensors"
    weights.write_bytes(b"weights-bytes-0123456789")
    profile = {
        "schema_version": "pdf-paragraph-runtime/2",
        "python": str(tmp_path / "source-env" / "Scripts" / "python.exe"),
        "artifacts": str(artifacts),
        "model_sha256": hashlib.sha256(weights.read_bytes()).hexdigest(),
        "model_config_sha256": hashlib.sha256(config.read_bytes()).hexdigest(),
        "docling_version": "2.96.0",
        "runtime_versions": {"acme-pkg": "1.0.0"},
        "environment_sha256": "e" * 64,
        "environment_algorithm": "pdf-runtime-closure/2",
    }
    probe = {
        "python": profile["python"],
        "prefix": str(tmp_path / "source-env"),
        "base_prefix": str(tmp_path / "base-python"),
        "site_packages": str(site),
        "closure": {
            "schema_version": "pdf-paragraph-environment/2",
            "environment_algorithm": "pdf-runtime-closure/2",
            "environment_sha256": "e" * 64,
            "roots": ["acme-pkg==1.0.0"],
            "marker_environment": {},
            "distributions": [{"name": "acme-pkg", "version": "1.0.0", "extras": [], "requires": []}],
        },
        "distributions": {
            "acme-pkg": {
                "version": "1.0.0",
                "path": str(info),
                "record_sha256": record_sha,
                "record": rows,
            },
        },
    }
    return profile, probe


def record_rows(plan: dict) -> dict[str, dict]:
    return {row["target"]: row for row in plan["env_rows"]}


def test_build_plan_freezes_rows_diagnostics_and_is_deterministic(tmp_path):
    profile, probe = mini_source(tmp_path)
    target = Path(temporary_ascii(tmp_path))
    plan_one = deployment.build_plan(target, profile, probe)
    plan_two = deployment.build_plan(target, profile, probe)
    assert plan_one["plan_sha256"] == plan_two["plan_sha256"]
    rows = record_rows(plan_one)
    assert set(rows) == {
        "env/Lib/site-packages/acme_pkg/__init__.py",
        "env/Lib/site-packages/acme_pkg-1.0.0.dist-info/METADATA",
    }
    init_row = rows["env/Lib/site-packages/acme_pkg/__init__.py"]
    assert init_row["sha256"] == hashlib.sha256(
        (tmp_path / "source-env/Lib/site-packages/acme_pkg/__init__.py").read_bytes()).hexdigest()
    assert init_row["owner"] == "acme-pkg"
    artifact_rows = {row["target"]: row for row in plan_one["artifact_rows"]}
    assert set(artifact_rows) == {"artifacts/config.json", "artifacts/model.safetensors"}
    assert artifact_rows["artifacts/model.safetensors"]["sha256"] == profile["model_sha256"]
    assert plan_one["closure"]["environment_sha256"] == profile["environment_sha256"]
    assert plan_one["same_volume"] is True
    assert plan_one["diagnostics"]["missing_unhashed_bytecode"] == 1


def test_build_plan_records_declared_hash_mismatch_as_diagnostic_not_blocker(tmp_path):
    profile, probe = mini_source(tmp_path, declare_wrong_hash=True)
    plan = deployment.build_plan(Path(temporary_ascii(tmp_path)), profile, probe)
    kinds = {row["kind"] for row in plan["diagnostics"]["record_deviations"]}
    assert kinds == {"record_hash_mismatch"}
    assert plan["blocking_errors"] == []


def test_build_plan_rejects_cross_volume_target(tmp_path):
    profile, probe = mini_source(tmp_path)
    with pytest.raises(deployment.DeploymentError, match="volume"):
        deployment.build_plan(Path("D:/elsewhere/deploy"), profile, probe)


def test_build_plan_reports_missing_record_source_as_blocker(tmp_path):
    profile, probe = mini_source(tmp_path)
    (tmp_path / "source-env/Lib/site-packages/acme_pkg/__init__.py").unlink()
    plan = deployment.build_plan(Path(temporary_ascii(tmp_path)), profile, probe)
    assert [row["kind"] for row in plan["blocking_errors"]] == ["missing_record_source"]


def test_build_plan_projects_env_local_script_entries_and_blocks_escaping(tmp_path):
    profile, probe = mini_source(tmp_path)
    scripts = tmp_path / "source-env" / "Scripts"
    scripts.mkdir()
    script = scripts / "acme-cli.exe"
    script.write_bytes(b"launcher")
    escaped = tmp_path / "outside-root.exe"
    escaped.write_bytes(b"escapes")
    entry = probe["distributions"]["acme-pkg"]
    entry["record"].append(["../../Scripts/acme-cli.exe", "", ""])
    entry["record"].append(["../../../outside-root.exe", "", ""])
    plan = deployment.build_plan(Path(temporary_ascii(tmp_path)), profile, probe)
    rows = record_rows(plan)
    assert "env/Scripts/acme-cli.exe" in rows
    assert plan["diagnostics"]["script_entries"] == 1
    assert [row["kind"] for row in plan["blocking_errors"]] == ["escaping_record_path"]


def test_classify_target_distinguishes_absent_empty_owned_and_foreign(tmp_path):
    profile, probe = mini_source(tmp_path)
    target = tmp_path / "deploy"
    assert deployment.classify_target(target, "x" * 64) == "ABSENT"
    target.mkdir()
    assert deployment.classify_target(target, "x" * 64) == "EMPTY"
    plan = deployment.build_plan(target, profile, probe)
    receipt = deployment.receipt_stub(plan, "COMPLETE")
    deployment.write_receipt(target, receipt)
    assert deployment.classify_target(target, plan["plan_sha256"]) == "OWNED_COMPLETE"
    assert deployment.classify_target(target, "a" * 64) == "FOREIGN"
    receipt["status"] = "INCOMPLETE"
    deployment.write_receipt(target, receipt)
    assert deployment.classify_target(target, plan["plan_sha256"]) == "OWNED_INCOMPLETE"
    foreign_dir = tmp_path / "unknown"
    foreign_dir.mkdir()
    (foreign_dir / "unrelated.txt").write_text("keep me", encoding="utf-8")
    assert deployment.classify_target(foreign_dir, plan["plan_sha256"]) == "FOREIGN"


def temporary_ascii(tmp_path: Path) -> str:
    return str(tmp_path / "deploy-target")


def test_load_plan_rejects_escaping_or_absolute_row_targets(tmp_path):
    profile, probe = mini_source(tmp_path)
    plan = deployment.build_plan(Path(temporary_ascii(tmp_path)), profile, probe)
    deployment.load_plan(json.loads(json.dumps(plan)))
    broken = json.loads(json.dumps(plan))
    broken["env_rows"][0]["target"] = "../escape.py"
    broken["plan_sha256"] = deployment.plan_digest(broken)
    with pytest.raises(deployment.DeploymentError, match="target"):
        deployment.load_plan(broken)
    broken = json.loads(json.dumps(plan))
    broken["env_rows"][0]["target"] = "C:/absolute.py"
    broken["plan_sha256"] = deployment.plan_digest(broken)
    with pytest.raises(deployment.DeploymentError, match="target"):
        deployment.load_plan(broken)
    tampered = json.loads(json.dumps(plan))
    tampered["env_rows"][0]["sha256"] = "f" * 64
    with pytest.raises(deployment.DeploymentError, match="integrity"):
        deployment.load_plan(tampered)
