"""Same hard worker command, import only, finite 15s total (not a budget increase)."""

import json
import os
from pathlib import Path
import sys
import tempfile
import time

HERE = Path(__file__).resolve().parent
ROOT = Path("C:/Users/郑曾波/Projects/_harness_worktrees/w05/cwp-ocr-root")
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(HERE))
OUT = HERE / "probe-import-stack.json"
TRACE = HERE / "probe-import-stack-trace.jsonl"
STACK = HERE / "probe-import-stack.txt"
assert not any(p.exists() for p in (OUT, TRACE, STACK))
os.environ["CWP_OCR_PERF_TRACE"] = str(TRACE)
os.environ["CWP_OCR_PERF_STACK"] = str(STACK)

from company_wiki.document_normalization.isolated_ocr import IsolatedOCRAdapter
from company_wiki.document_normalization.local_ocr import LocalOCRConfig
from stack_backend import StackImportAdapter

config = LocalOCRConfig.from_dict(json.loads((ROOT / "config/local_ocr.json").read_bytes()))
scratch = Path(tempfile.mkdtemp(prefix="cwp-ocr-perf-import-"))
started = time.monotonic()
adapter = IsolatedOCRAdapter(config, deadline=started + 15, scratch_dir=scratch,
                             _backend_factory=StackImportAdapter)
status = {"status": "RUNNING", "budget_seconds": 15, "native_inference_calls": 0}
try:
    adapter.validate_environment()
    status["status"] = "PASS"
except Exception as error:
    status["status"] = "FAIL"
    status["error_type"] = type(error).__name__
    status["error"] = str(error)
finally:
    adapter.close()
    status["elapsed_seconds"] = time.monotonic() - started
    assert not any(scratch.iterdir())
    scratch.rmdir()
    status["scratch_restored"] = not scratch.exists()
    OUT.write_text(json.dumps(status, indent=2), encoding="utf-8")
    print(json.dumps(status))
