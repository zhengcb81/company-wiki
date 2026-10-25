"""Read-only source/selection replay with existing frozen observers."""
from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent


def load(name, path):
    spec = spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError("observer unavailable")
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


if __name__ == "__main__":
    if sys.argv[1:] == ["structure"]:
        observer = load("existing_real_structure", HERE / "probe_real_structure.py")
        observer.OUTPUT = HERE / "real-structure-after-rootfix.json"
        observer.main()
    elif len(sys.argv) == 2 and sys.argv[1].startswith("attempt") and sys.argv[1].isalnum():
        observer = load("existing_read_only_replay", HERE.parent / "st-a13-recognition-scope-20261025/replay.py")
        observer.HERE = HERE
        observer.main()
    else:
        raise SystemExit("usage: replay_current.py structure|attemptNN (fresh output only)")
