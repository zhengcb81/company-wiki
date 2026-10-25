"""Reuse the existing read-only annual14 observer in a newly owned attempt."""
from __future__ import annotations
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p / "pyproject.toml").exists())
PRIOR = HERE.parent / "r1-w08-material-value-20261024/bullet-parent-fix-20261025/business-scope-line-replay-20261025"

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load observer: {path}")
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    if len(sys.argv) != 2 or not sys.argv[1].isalnum():
        raise SystemExit("usage: replay.py NEW_ATTEMPT_NAME (alphanumeric)")
    attempt = HERE / sys.argv[1]
    attempt.mkdir(exist_ok=False)  # All descendant outputs belong to this fresh attempt.
    args = json.loads((PRIOR / "replay-receipt.json").read_text(encoding="utf-8"))["argv"]
    for option, filename in (("--output", "selection.json"), ("--trace-output", "trace.json")):
        args[args.index(option)+1] = str(attempt / filename)
    sys.argv = [str(__file__), *args]
    observer = load("existing_all_target_observer", PRIOR / "replay_all_targets.py")
    observer.HERE = attempt
    observer.main()
    compiler_path = HERE.parent / "r1-w08-crosspage-20261024/annual14-v5/compile_model_view.py"
    compiler = load("existing_scoped_compiler_observer", compiler_path)
    compiler.HERE = attempt
    compiler.SELECTION = attempt / "selection.json"
    compiler.OUTPUT = attempt / "model-view.json"
    compiler.main()
    receipt_path = attempt / "replay-receipt.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["entrypoint_sha256"] = sha(Path(__file__))
    receipt["new_scope_module_sha256"] = sha(ROOT / "src/company_wiki/source_catalog/narrative_recognition_scope.py")
    receipt["model_view_sha256"] = sha(attempt / "model-view.json")
    receipt["model_request_sent"] = False
    receipt["model_response_reviewed"] = False
    receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")

if __name__ == "__main__":
    main()
