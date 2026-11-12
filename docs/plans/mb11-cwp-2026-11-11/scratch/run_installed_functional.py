"""Scratch probe: functional installed-wheel run against the materialized lake."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

VENV_PY = Path(r"C:/Users/Public/mb11-cwp-scratch/venv/Scripts/python.exe")
EXE = VENV_PY.parent / "company-wiki-narrative-read.exe"
CWD = Path(r"C:/Users/Public/mb11-cwp-scratch/empty-cwd")
MANIFEST = json.loads(Path(r"C:/Users/Public/mb11-cwp-scratch/lake/manifest.json").read_text(encoding="utf-8"))


def run(operation, payload):
    return subprocess.run(
        [str(EXE), "--config", MANIFEST["config"], "--operation", operation],
        input=json.dumps(payload).encode("utf-8"), capture_output=True,
        cwd=str(CWD), timeout=120, check=False,
    )


reference_run = run("reference", {
    "schema_version": "narrative-reference-request/1",
    "source_ref": MANIFEST["source_ref"],
})
sys.stdout.write("reference rc=%s\n" % reference_run.returncode)
assert reference_run.returncode == 0, reference_run.stderr.decode("utf-8", "replace")
reference = json.loads(reference_run.stdout)
sys.stdout.write("reference keys: %s\n" % sorted(reference))
assert reference["artifact_sha256"] == MANIFEST["artifact_sha256"]
assert json.loads(reference_run.stderr)["status"] == "metadata_only"

read_run = run("read", {
    "schema_version": "narrative-read-request/1",
    "narrative_ref": reference,
    "as_of_date": "2026-09-01",
    "expected_source": MANIFEST["expected_source"],
})
sys.stdout.write("read rc=%s\n" % read_run.returncode)
assert read_run.returncode == 0, read_run.stderr.decode("utf-8", "replace")
digest = hashlib.sha256(read_run.stdout).hexdigest()
sys.stdout.write("read bytes=%s sha=%s\n" % (len(read_run.stdout), digest))
assert digest == MANIFEST["payload_sha256"], "installed wheel returned different bytes"
receipt = json.loads(read_run.stderr)
sys.stdout.write("receipt status=%s replay=%s locators=%s\n" % (
    receipt["status"], receipt["replay_status"], receipt["locator_count"]))
assert receipt["status"] == "ok"
assert receipt["replay_status"] == "verified"
bundle = json.loads(read_run.stdout)
assert str(MANIFEST["root"]) not in read_run.stdout.decode("utf-8"), "physical path leaked"
sys.stdout.write("FUNCTIONAL OK: installed wheel serves exact persisted bytes\n")
