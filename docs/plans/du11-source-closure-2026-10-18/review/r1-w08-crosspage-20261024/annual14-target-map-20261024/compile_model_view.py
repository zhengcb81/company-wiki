"""Reproduce task visibility with the existing production scoped compiler.

Only an offline projection: no request is sent and no response is reviewed.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent


def main():
    source = HERE.parent / "annual14-v5/compile_model_view.py"
    spec = importlib.util.spec_from_file_location("existing_w08_model_projection", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.HERE = HERE
    module.SELECTION = HERE / "selection.json"
    module.OUTPUT = HERE / "model-view.json"
    if module.OUTPUT.exists():
        raise FileExistsError("Do not overwrite a frozen model view")
    module.main()
    result = json.loads(module.OUTPUT.read_text(encoding="utf-8"))
    result.update(schema_version="w08-annual14-source-purpose-model-view/1",
                  compiler_observer_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                  request_sent=False, response_reviewed=False)
    module.OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                             encoding="utf-8")


if __name__ == "__main__":
    main()
