"""Owned isolated, bounded author test node; no real supplier credentials."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import uuid

ROOT = Path("C:/Users/郑曾波/Projects/_harness_worktrees/w06/ff-contract-matrix-root").resolve()
OUT = Path(__file__).resolve().parent
label = sys.argv[1]
assert label in {"business-red", "focused-green", "binding-red", "binding-green", "schema-type-red", "schema-types-red", "final-focused-green"}
paths = ["tests/test_transcript_launch_contract.py", "tests/test_transcript_companion_transport.py",
         "tests/test_et_s0b_contract.py"]
scratch = OUT / ("s-" + uuid.uuid4().hex[:8])
assert not scratch.exists()
scratch.mkdir()
(scratch / "profile").mkdir()
env = {k: os.environ[k] for k in ("SYSTEMROOT", "WINDIR", "PATH", "TEMP", "TMP") if k in os.environ}
env.update({"PYTHONDONTWRITEBYTECODE": "1", "PYTHONUTF8": "1", "HOME": str(scratch / "profile"),
            "USERPROFILE": str(scratch / "profile")})
selection = "not_found_envelope" if label == "binding-red" else "not_found_"
if label in {"schema-type-red", "schema-types-red"}:
    selection = "not_found_envelope and schema_version"
args = [sys.executable, "-B", "-m", "pytest", "-p", "no:cacheprovider", "--basetemp", str(scratch / "p"),
        "-q", *paths, "-k", selection]
assert not (OUT / (label + ".json")).exists(), "never replace earlier evidence"
start = time.monotonic()
try:
    result = subprocess.run(args, cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            timeout=60, check=False)
    (OUT / (label + ".log")).write_bytes(result.stdout)
    restored_target = scratch.resolve()
    assert restored_target.parent == OUT.resolve() and restored_target.name.startswith("s-")
    shutil.rmtree(restored_target)
    record = {"label": label, "command": args, "exit_code": result.returncode,
              "seconds": round(time.monotonic() - start, 4), "scratch": str(scratch),
              "scratch_restored": not scratch.exists(), "real_provider_calls": 0, "real_key_reads": 0,
              "llm_calls": 0, "log_sha256": hashlib.sha256(result.stdout).hexdigest(),
              "files": [{"path": p, "sha256": hashlib.sha256((ROOT/p).read_bytes()).hexdigest()} for p in paths]}
    (OUT / (label + ".json")).write_text(json.dumps(record, indent=2), encoding="utf-8")
    print(json.dumps(record, ensure_ascii=False))
    print(result.stdout.decode("utf-8", errors="replace")[-2000:])
finally:
    if scratch.exists():
        target = scratch.resolve()
        assert target.parent == OUT.resolve() and target.name.startswith("s-")
        shutil.rmtree(target)
