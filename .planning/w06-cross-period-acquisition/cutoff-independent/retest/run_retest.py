"""Only three original failures plus four necessary usage projection controls."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
import uuid

HERE = Path(__file__).resolve().parent
OLD = HERE.parent
CWP = Path("C:/Users/郑曾波/Projects/company-wiki")
AUTHOR = OLD.parent / "cutoff-implementation"
EXPECTED = "87495b11e3c41986c3a10374bae0c603af6db4d61d7b8ed8c6a01771b7ed3381"
SOURCE_FREEZE = CWP / "docs/plans/cross-market-rf-e2e-2026-10-08/phase6/w06_parallel_verification_2026-10-11/evidence/root-ff-matrix-acceptance/source-publication/root-product-freeze.json"


def record(path):
    return {"sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "bytes": path.stat().st_size}


def snapshot():
    frozen_path = AUTHOR / "product-freeze-v2.json"
    frozen = record(frozen_path)
    assert frozen["sha256"] == EXPECTED
    freeze = json.loads(frozen_path.read_text(encoding="utf-8"))
    roots = {key: Path(value) for key, value in freeze["roots"].items()}
    product = {}
    for expected in freeze["files"]:
        key = expected["repository"] + ":" + expected["path"]
        product[key] = record(roots[expected["repository"]] / expected["path"])
        assert product[key] == {name: expected[name] for name in ("sha256", "bytes")}, key
    goldens = {}
    for root in ("et", "ff"):
        for expected in freeze["old_goldens"][root]:
            key = root + ":" + expected["path"]
            goldens[key] = record(roots[root] / expected["path"])
            assert goldens[key] == {name: expected[name] for name in ("sha256", "bytes")}
    old_manifest = record(OLD / "manifest.json")
    assert old_manifest["sha256"] == "3140797e6c6839063446565ea88d89138ec4a9afae84ad1c8da03138443c9050"
    old = json.loads((OLD / "manifest.json").read_text(encoding="utf-8"))
    original_failure = {}
    for name, expected in old["files"].items():
        original_failure[name] = record(OLD / name)
        assert original_failure[name] == expected, name
    root_source = record(SOURCE_FREEZE)
    assert root_source["sha256"] == "397a02e903e1543c6ca4d3116eff10c03d46cb9d6fe657a1c93fb2860f1fcb2c"
    source = json.loads(SOURCE_FREEZE.read_text(encoding="utf-8"))
    cwp = {}
    for path, expected in source["product_files"].items():
        cwp[path] = record(Path(source["worktree"]) / path)
        assert cwp[path] == expected, path
    repair = AUTHOR / "ff/malformed-usage-repair/manifest.json"
    repair_record = record(repair)
    assert repair_record["sha256"] == "2176c0c39e97d20ce510f73b7d72c47175ff1834e702b6e1a9d252621b6905c0"
    repaired = {}
    for expected in json.loads(repair.read_text(encoding="utf-8"))["files"]:
        repaired[expected["path"]] = record(repair.parent / expected["path"])
        assert repaired[expected["path"]] == {name: expected[name] for name in ("sha256", "bytes")}
    authority_path = Path(freeze["old_author_freezes"][0]["path"])
    assert record(authority_path)["sha256"] == "e2bf72bde855935db1beeca45ad10d4a9b205f4ca1137dab07db4d827e3f7fe3"
    tools = {}
    for expected in json.loads(authority_path.read_text(encoding="utf-8"))["files"]:
        candidate = roots["ff"] / expected["path"]
        if not candidate.is_file():
            candidate = authority_path.parent / expected["path"]
        tools[str(candidate)] = record(candidate)
        assert tools[str(candidate)] == {name: expected[name] for name in ("sha256", "bytes")}
    return {"v2_freeze": frozen, "product": product, "old_goldens": goldens,
            "original_failure_manifest": old_manifest, "original_failure": original_failure,
            "root_cwp_freeze": root_source, "cwp_product": cwp, "repair_manifest": repair_record,
            "repair_evidence": repaired, "old_case_authority": tools}


def main():
    before = snapshot()
    parent = CWP / ".tmp"
    parent_existed = parent.exists()
    scratch = parent / ("cut-review-" + uuid.uuid4().hex[:8])
    assert not scratch.exists()
    scratch.mkdir(parents=True)
    (scratch / "temp").mkdir()
    (scratch / "home").mkdir()
    env = {key: os.environ[key] for key in ("SystemRoot", "WINDIR", "COMSPEC", "PATHEXT") if key in os.environ}
    env.update(PATH="C:/Miniconda;C:/Miniconda/Library/bin;C:/Windows/System32", TEMP=str(scratch / "temp"),
               TMP=str(scratch / "temp"), HOME=str(scratch / "home"), USERPROFILE=str(scratch / "home"),
               APPDATA=str(scratch / "home/AppData"), PYTHONUTF8="1", PYTHONDONTWRITEBYTECODE="1",
               PYTEST_DISABLE_PLUGIN_AUTOLOAD="1", PYTHONPATH=str(HERE))
    probe = str(OLD / "probes.py")
    selected = [
        probe + "::test_ff_malformed_stdout_does_not_erase_valid_usage",
        probe + "::test_ff_closed_reason_and_observed_usage[earnings-transcript-result/2-call_after_as_of-call_after_as_of-True]",
        probe + "::test_ff_closed_reason_and_observed_usage[earnings-transcript-result/1-None-exact_transcript_missing-True]",
        probe + "::test_ff_closed_reason_and_observed_usage[earnings-transcript-result/2-call_after_as_of-call_after_as_of-False]",
        str(HERE / "test_unknown_control.py"),
    ]
    command = ["C:/Miniconda/python.exe", "-m", "pytest", "-q", "-p", "no:cacheprovider", "-p", "scoped_receipts",
               "-c", str(OLD / "pytest.ini"), "--rootdir", str(HERE), "--confcutdir", str(OLD),
               "--basetemp", str(scratch / "tests"), *selected]
    evidence = {"schema_version": "cutoff-independent-scoped-retest/1", "command": command,
                "selected": selected, "before": before, "scratch": str(scratch), "initial_scratch_absent": True,
                "environment_keys": sorted(env), "real_credentials_read_or_inherited": False,
                "real_network_requests": 0, "llm_calls": 0, "cost_usd": 0}
    started = time.monotonic()
    try:
        done = subprocess.run(command, env=env, cwd=scratch, capture_output=True, encoding="utf-8", errors="replace", timeout=60)
        evidence.update(exit_code=done.returncode, elapsed_seconds=round(time.monotonic() - started, 3))
        (HERE / "retest.stdout.txt").write_text(done.stdout, encoding="utf-8")
        (HERE / "retest.stderr.txt").write_text(done.stderr, encoding="utf-8")
        print(done.stdout)
    except subprocess.TimeoutExpired:
        evidence.update(exit_code=None, error="independent_retest_deadline")
    finally:
        target = scratch.resolve()
        target.relative_to(parent.resolve())
        assert target.name.startswith("cut-review-") and len(target.name) == 19
        shutil.rmtree(target)
        if not parent_existed and not any(parent.iterdir()):
            parent.rmdir()
        evidence["scratch_restored"] = not scratch.exists() and parent.exists() == parent_existed
        evidence["after"] = snapshot()
        evidence["freeze_unchanged"] = evidence["before"] == evidence["after"]
        (HERE / "retest-result.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return evidence.get("exit_code") or (0 if evidence.get("exit_code") == 0 else 1)


if __name__ == "__main__":
    raise SystemExit(main())
