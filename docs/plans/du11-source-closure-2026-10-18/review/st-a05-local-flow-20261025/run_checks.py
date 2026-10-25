"""Reuse ROOT's isolated check runner without copying fixtures or originals."""
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

path = Path(__file__).resolve().parent.parent / "docs-only-push-20261025/run_checks.py"
spec = spec_from_file_location("root_isolated_checks", path)
if spec is None or spec.loader is None:
    raise RuntimeError("isolated test runner unavailable")
runner = module_from_spec(spec)
spec.loader.exec_module(runner)
runner.EVIDENCE = Path(__file__).resolve().parent
if len(sys.argv) > 1 and sys.argv[1].startswith("review"):
    label = sys.argv[1]
    if not label.replace("-", "").isalnum():
        raise ValueError("invalid review evidence label")
    runner.EVIDENCE = runner.EVIDENCE / label
    runner.EVIDENCE.mkdir(exist_ok=False)
    sys.argv[1] = "red" if label.endswith("-red") else "final"

if __name__ == "__main__":
    raise SystemExit(runner.main())
