"""Replay three genuine acceptance defects through real CLI; restore owned scratch to absent."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
LEAF = Path("C:/Users/郑曾波/Projects/_harness_worktrees/w06/audit-measures")
SCRATCH = (ROOT / "cwpa-independent-measures-cli").resolve()
assert SCRATCH.parent == ROOT.resolve() and not SCRATCH.exists()
cases = json.loads((ROOT / "counterexamples.json").read_text(encoding="utf-8"))["cases"]
selected = {"sum_output_silently_relabels_currency_entity_definition",
            "conversion_result_missing_source_ref", "difference_one_operand_should_diagnose_not_crash"}
observations = []
SCRATCH.mkdir()
try:
    sentinel = SCRATCH / "sentinel.txt"
    sentinel.write_bytes(b"independent-acceptance-initial")
    initial_sha = hashlib.sha256(sentinel.read_bytes()).hexdigest()
    for case in cases:
        if case["id"] not in selected:
            continue
        ledger_path = SCRATCH / f"{case['id']}.json"
        ledger_path.write_text(json.dumps(case["ledger"], ensure_ascii=False), encoding="utf-8")
        command = [sys.executable, "-B", "-X", "utf8", str(LEAF / "skills/revenue-forecast-audit/scripts/financial_measure_audit.py"),
                   "--ledger", str(ledger_path), "--out-root", str(SCRATCH / "attempts")]
        proc = subprocess.run(command, capture_output=True, encoding="utf-8", timeout=15)
        row = {"id": case["id"], "argv": command, "exit_code": proc.returncode,
               "stdout": proc.stdout, "stderr": proc.stderr}
        try:
            printed = json.loads(proc.stdout)
            row["report"] = json.loads(Path(printed["output_file"]).read_text(encoding="utf-8"))
        except (ValueError, KeyError):
            row["report"] = None
        observations.append(row)
    assert hashlib.sha256(sentinel.read_bytes()).hexdigest() == initial_sha
finally:
    assert SCRATCH.parent == ROOT.resolve() and SCRATCH.name == "cwpa-independent-measures-cli"
    for path in [SCRATCH, *SCRATCH.rglob("*")]:
        assert path.resolve().is_relative_to(SCRATCH) and not path.is_symlink()
        if os.name == "nt":
            assert not path.stat(follow_symlinks=False).st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT
    shutil.rmtree(SCRATCH)
    assert not SCRATCH.exists()
receipt = {"schema_version": "w06-independent-real-cli-probes/1", "owned_root": str(SCRATCH),
           "initial": "absent", "final": "absent", "cleanup_verified": True,
           "provider_calls": 0, "model_calls": 0, "source_truth_verified": False,
           "economic_reasonableness": "not_evaluated", "cases": observations}
(ROOT / "real-cli-counterexamples.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"cases": [{"id": row["id"], "exit_code": row["exit_code"],
                             "overall": row["report"] and row["report"]["overall"]} for row in observations],
                  "cleanup_verified": True}, ensure_ascii=False))
