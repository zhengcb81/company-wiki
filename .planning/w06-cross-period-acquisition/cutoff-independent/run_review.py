"""Bounded non-author cutoff acceptance, with no real credentials in child env."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
import uuid

HERE = Path(__file__).resolve().parent
CWP = Path("C:/Users/郑曾波/Projects/company-wiki")
AUTHOR = HERE.parent / "cutoff-implementation"
EXPECTED = "e13ee23e64e0ec720edce6e4f5c6847f0dea2ead17a8d112d63874cd0e4cf28a"


def observe(path):
    return {"sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "bytes": path.stat().st_size}


def snapshot():
    frozen_path = AUTHOR / "product-freeze.json"
    frozen_record = observe(frozen_path)
    assert frozen_record["sha256"] == EXPECTED, "cutoff freeze changed"
    frozen = json.loads(frozen_path.read_text(encoding="utf-8"))
    roots = {name: Path(value) for name, value in frozen["roots"].items()}
    product = {}
    for expected in frozen["files"]:
        key = expected["repository"] + ":" + expected["path"]
        product[key] = observe(roots[expected["repository"]] / expected["path"])
        assert product[key] == {field: expected[field] for field in ("sha256", "bytes")}, key
    golden = {}
    for repository in ("et", "ff"):
        for expected in frozen["old_goldens"][repository]:
            key = repository + ":" + expected["path"]
            golden[key] = observe(roots[repository] / expected["path"])
            assert golden[key] == {field: expected[field] for field in ("sha256", "bytes")}, key
    authority_record = frozen["old_author_freezes"][0]
    authority_path = Path(authority_record["path"])
    assert observe(authority_path)["sha256"] == authority_record["sha256"]
    authority = json.loads(authority_path.read_text(encoding="utf-8"))
    tools = {}
    for expected in authority["files"]:
        candidate = roots["ff"] / expected["path"]
        if not candidate.is_file():
            candidate = authority_path.parent / expected["path"]
        tools[str(candidate)] = observe(candidate)
        assert tools[str(candidate)] == {field: expected[field] for field in ("sha256", "bytes")}
    source_fix = CWP / "docs/plans/cross-market-rf-e2e-2026-10-08/phase6/w06_parallel_verification_2026-10-11/evidence/root-ff-matrix-acceptance/producer-scope-fix/product-freeze.json"
    assert observe(source_fix)["sha256"] == "1a753dd95c8e897891c48ee5e00e47bde0723a21741aae823af9806619ecdc91"
    source = json.loads(source_fix.read_text(encoding="utf-8"))
    cwp_product = {}
    cwp_original_mismatches = {}
    for relative, expected in source["product_files"].items():
        cwp_product[relative] = observe(Path(source["worktree"]) / relative)
        if cwp_product[relative] != expected:
            cwp_original_mismatches[relative] = {"original_freeze": expected, "observed": cwp_product[relative]}
    return {"cutoff_freeze": frozen_record, "product": product, "old_goldens": golden,
            "old_case_authority_manifest": observe(authority_path), "old_case_authority_files": tools,
            "cwp_freeze": observe(source_fix), "cwp_product": cwp_product,
            "cwp_original_mismatches": cwp_original_mismatches}


def main():
    before = snapshot()
    parent = CWP / ".tmp"
    existing_parent = parent.exists()
    scratch = parent / ("cut-review-" + uuid.uuid4().hex[:8])
    assert not scratch.exists()
    scratch.mkdir(parents=True)
    (scratch / "temp").mkdir()
    (scratch / "home").mkdir()
    env = {key: os.environ[key] for key in ("SystemRoot", "WINDIR", "COMSPEC", "PATHEXT") if key in os.environ}
    env.update(PATH="C:/Miniconda;C:/Miniconda/Library/bin;C:/Windows/System32", TEMP=str(scratch / "temp"),
               TMP=str(scratch / "temp"), HOME=str(scratch / "home"), USERPROFILE=str(scratch / "home"),
               APPDATA=str(scratch / "home/AppData"), PYTHONUTF8="1", PYTHONDONTWRITEBYTECODE="1",
               PYTEST_DISABLE_PLUGIN_AUTOLOAD="1")
    command = ["C:/Miniconda/python.exe", "-m", "pytest", "-q", "-p", "no:cacheprovider", "-c", str(HERE / "pytest.ini"),
               "--rootdir", str(HERE), "--confcutdir", str(HERE), "--basetemp", str(scratch / "tests"), str(HERE / "probes.py")]
    record = {"schema_version": "cutoff-independent-node/1", "command": command, "scratch": str(scratch),
              "scratch_initially_absent": True, "parent_initially_existed": existing_parent, "environment_keys": sorted(env),
              "before": before, "real_network_requests": 0, "real_credentials_read_or_inherited": False,
              "llm_calls": 0, "cost_usd": 0}
    started = time.monotonic()
    try:
        result = subprocess.run(command, env=env, cwd=scratch, capture_output=True, encoding="utf-8", errors="replace", timeout=90)
        record.update(exit_code=result.returncode, seconds=round(time.monotonic() - started, 3))
        (HERE / "probe.stdout.txt").write_text(result.stdout, encoding="utf-8")
        (HERE / "probe.stderr.txt").write_text(result.stderr, encoding="utf-8")
        print(result.stdout)
    except subprocess.TimeoutExpired:
        record.update(exit_code=None, error="independent_deadline", seconds=round(time.monotonic() - started, 3))
    finally:
        target = scratch.resolve()
        target.relative_to(parent.resolve())
        assert target.name.startswith("cut-review-") and len(target.name) == 19
        shutil.rmtree(target)
        if not existing_parent and not any(parent.iterdir()):
            parent.rmdir()
        record["scratch_restored"] = not scratch.exists() and parent.exists() == existing_parent
        record["after"] = snapshot()
        record["freeze_unchanged"] = record["before"] == record["after"]
        (HERE / "probe-result.json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return record.get("exit_code") or (0 if record.get("exit_code") == 0 else 1)


if __name__ == "__main__":
    raise SystemExit(main())
