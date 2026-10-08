"""Verify Git's staged audit blobs equal the recorded working-tree bytes."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parent
CWP = ROOT.parents[2]
PREFIX = ROOT.relative_to(CWP).as_posix()
entries = subprocess.check_output(
    ["git", "ls-files", "--stage", "-z", "--", PREFIX], cwd=CWP
).split(b"\0")
batch = subprocess.Popen(["git", "cat-file", "--batch"], cwd=CWP,
                         stdin=subprocess.PIPE, stdout=subprocess.PIPE)
verified = {}
issues = []
count = 0
try:
    for entry in entries:
        if not entry:
            continue
        header, raw_path = entry.split(b"\t", 1)
        _, oid, stage = header.split()
        assert stage == b"0"
        path = CWP / raw_path.decode("utf-8")
        if path == ROOT / "staged_artifact_integrity.json":
            continue  # This derived report cannot fingerprint its own next bytes.
        if oid not in verified:
            batch.stdin.write(oid + b"\n")
            batch.stdin.flush()
            result = batch.stdout.readline().split()
            assert result[1] == b"blob"
            size = int(result[2])
            content = batch.stdout.read(size)
            assert len(content) == size and batch.stdout.read(1) == b"\n"
            verified[oid] = (size, hashlib.sha256(content).hexdigest())
        content = path.read_bytes()
        actual = (len(content), hashlib.sha256(content).hexdigest())
        if actual != verified[oid]:
            issues.append({"path": str(path), "issue": "staged bytes differ"})
        count += 1
finally:
    batch.stdin.close()
    batch.stdout.close()
    assert batch.wait(timeout=10) == 0
record = {"schema_version": "1.0", "staged_files_checked": count,
          "unique_git_blobs_checked": len(verified), "mismatches": issues,
          "scope": "All then-staged task files except this derived report, generated after the check."}
(ROOT / "staged_artifact_integrity.json").write_text(
    json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"files": count, "mismatches": len(issues)}))
raise SystemExit(bool(issues))
