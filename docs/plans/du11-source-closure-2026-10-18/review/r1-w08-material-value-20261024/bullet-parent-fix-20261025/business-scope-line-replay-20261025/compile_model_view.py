"""Compile this frozen selection into the existing production task view offline.

The output stores IDs and payload hashes only. It does not save model prose,
send a request, or review a response.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent


def main() -> None:
    source = HERE.parents[2] / "r1-w08-crosspage-20261024/annual14-v5/compile_model_view.py"
    spec = importlib.util.spec_from_file_location("annual14_scoped_model_view", source)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load the existing scoped model-view compiler")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.HERE = HERE
    module.SELECTION = HERE / "selection.json"
    module.OUTPUT = HERE / "model-view.json"
    if module.OUTPUT.exists():
        raise FileExistsError("refusing to overwrite a frozen model view")
    module.main()
    output = json.loads(module.OUTPUT.read_text(encoding="utf-8"))
    output.update(
        request_sent=False,
        response_reviewed=False,
        compiler_observer_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
    )
    module.OUTPUT.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
