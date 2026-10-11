"""Run one bounded offline non-author acceptance node in an owned short lake."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import uuid

HERE = Path(__file__).resolve().parent
TREE = Path("C:/Users/郑曾波/Projects/_harness_worktrees/w06/cwp-acquisition-scope-root")
CWP = Path("C:/Users/郑曾波/Projects/company-wiki")
AUTHOR = HERE.parent / "producer-scope-fix"
EXPECTED_FREEZE = "1a753dd95c8e897891c48ee5e00e47bde0723a21741aae823af9806619ecdc91"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def snapshot():
    freeze_path = AUTHOR / "product-freeze.json"
    assert sha(freeze_path) == EXPECTED_FREEZE, "author product freeze changed"
    frozen = json.loads(freeze_path.read_text(encoding="utf-8"))
    records = frozen.get("files") or frozen.get("product_files")
    assert isinstance(records, dict), frozen.keys()
    current = {}
    for relative, expected in records.items():
        path = TREE / relative
        current[relative] = {"sha256": sha(path), "bytes": path.stat().st_size}
        assert current[relative]["sha256"] == expected["sha256"], relative
        assert current[relative]["bytes"] == expected["bytes"], relative
    manifest = json.loads((AUTHOR / "manifest.json").read_text(encoding="utf-8"))
    author_files = {}
    for relative, expected in manifest["files"].items():
        path = AUTHOR / relative
        author_files[relative] = {"sha256": sha(path), "bytes": path.stat().st_size}
        assert author_files[relative]["sha256"] == expected["sha256"], relative
        assert author_files[relative]["bytes"] == expected["bytes"], relative
    return {"product_files": current, "author_evidence_files": author_files,
            "author_manifest_sha256": sha(AUTHOR / "manifest.json"), "freeze_sha256": sha(freeze_path)}


def main():
    prefix = sys.argv[1] if len(sys.argv) > 1 else "probes"
    assert prefix.replace("-", "").isalnum()
    before = snapshot()
    parent = CWP / ".tmp"
    parent_existed = parent.exists()
    scratch = parent / ("w06scope-" + uuid.uuid4().hex[:8])
    assert not scratch.exists()
    scratch.mkdir(parents=True)
    scratch.resolve().relative_to(parent.resolve())
    child_temp = scratch / "temp"
    child_temp.mkdir()
    home = scratch / "home"
    home.mkdir()
    # Inherit only Windows runtime prerequisites. Never read or propagate API credentials.
    env = {key: os.environ[key] for key in ("SystemRoot", "WINDIR", "COMSPEC", "PATHEXT") if key in os.environ}
    env.update(PATH="C:/Miniconda;C:/Miniconda/Library/bin;C:/Windows/System32", TEMP=str(child_temp),
               TMP=str(child_temp), HOME=str(home), USERPROFILE=str(home), APPDATA=str(home / "AppData"),
               PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1", PYTEST_DISABLE_PLUGIN_AUTOLOAD="1")
    command = ["C:/Miniconda/python.exe", "-m", "pytest", "-q", "-p", "no:cacheprovider", "-c", str(HERE / "pytest.ini"),
               "--rootdir", str(HERE), "--confcutdir", str(HERE), "--basetemp", str(scratch / "tests"),
               str(HERE / "probes.py")]
    if len(sys.argv) == 3:
        command += ["-k", sys.argv[2]]
    started = time.monotonic()
    result = {"schema_version": "1.0", "command": command, "scratch": str(scratch),
              "scratch_initially_absent": True, "parent_initially_existed": parent_existed,
              "environment_keys": sorted(env), "freeze_before": before, "network_calls": 0,
              "llm_calls": 0, "fee_usd": 0, "real_credentials_read_or_inherited": False}
    try:
        completed = subprocess.run(command, env=env, cwd=scratch, capture_output=True,
                                   encoding="utf-8", errors="replace", timeout=90)
        result.update(exit_code=completed.returncode, elapsed_seconds=round(time.monotonic() - started, 3))
        (HERE / f"{prefix}.stdout.txt").write_text(completed.stdout, encoding="utf-8")
        (HERE / f"{prefix}.stderr.txt").write_text(completed.stderr, encoding="utf-8")
        print(completed.stdout)
    except subprocess.TimeoutExpired as exc:
        result.update(exit_code=None, elapsed_seconds=round(time.monotonic() - started, 3),
                      error="review_node_timeout", details=str(exc))
    finally:
        # Delete exactly this new owned lake after checking the final absolute target.
        target = scratch.resolve()
        target.relative_to(parent.resolve())
        assert target.name.startswith("w06scope-") and len(target.name) == 17
        shutil.rmtree(target)
        if not parent_existed and not any(parent.iterdir()):
            parent.rmdir()
        result["scratch_restored"] = not scratch.exists() and parent.exists() == parent_existed
        result["freeze_after"] = snapshot()
        result["freeze_unchanged"] = result["freeze_before"] == result["freeze_after"]
        (HERE / f"{prefix}-result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result.get("exit_code") or (0 if result.get("exit_code") == 0 else 1)


if __name__ == "__main__":
    raise SystemExit(main())
