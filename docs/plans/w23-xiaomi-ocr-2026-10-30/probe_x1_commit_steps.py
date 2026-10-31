"""Diagnostic (not a comparison arm): per-step commit cost of the X1 load path.

Each step prints one JSON line with its commit delta, so the card's memory
bound can be checked against measured costs.  Runs inside a job limit (set by
the launcher) so a probe cannot starve the desktop.
"""
import ctypes
import json
import sys
import time
from math import prod
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
from tools.ocr_comparison.job_limit import (  # noqa: E402
    _ProcessMemoryCounters, _k32, _psapi, self_peak_commit_bytes,
)

SNAP = REPO / ".w23_cache/hub/models--xiaomi-research--Xiaomi-OCR-0/snapshots/bbd8cf8d21f256b3644b44cb860f3a7cecb93c30"


def commit_now():
    counters = _ProcessMemoryCounters()
    counters.cb = ctypes.sizeof(_ProcessMemoryCounters)
    _psapi.GetProcessMemoryInfo(_k32.GetCurrentProcess(), ctypes.byref(counters), counters.cb)
    return int(counters.PagefileUsage)


def step(name, fn):
    before = commit_now()
    started = time.perf_counter()
    status, error, result = "ok", None, None
    try:
        result = fn()
    except BaseException as exc:  # noqa: BLE001 - diagnostic records the failure
        status, error = "error", f"{type(exc).__name__}: {exc}"[:240]
    after = commit_now()
    print(json.dumps({
        "step": name, "status": status, "error": error,
        "seconds": round(time.perf_counter() - started, 2),
        "commit_before": before, "commit_after": after, "delta": after - before,
        "peak_self": self_peak_commit_bytes(),
    }), flush=True)
    return result


def import_torch():
    import torch  # noqa: F401


def import_model_module():
    import transformers.models.qwen3_5.modeling_qwen3_5  # noqa: F401


def import_processor_module():
    import transformers.models.qwen3_vl.processing_qwen3_vl  # noqa: F401


def load_processor():
    from transformers.models.qwen3_vl.processing_qwen3_vl import Qwen3VLProcessor
    return Qwen3VLProcessor.from_pretrained(str(SNAP))


def largest_tensor():
    from safetensors import safe_open
    handle = safe_open(str(SNAP / "model.safetensors"), framework="pt", device="cpu")
    name = max(handle.keys(), key=lambda k: prod(handle.get_slice(k).get_shape()))
    tensor = handle.get_tensor(name)
    return {"name": name, "shape": list(tensor.shape), "dtype": str(tensor.dtype),
            "bytes": tensor.numel() * tensor.element_size()}


if __name__ == "__main__":
    step("import torch", import_torch)
    step("import qwen3_5 modeling module", import_model_module)
    step("import qwen3_vl processing module", import_processor_module)
    step("Qwen3VLProcessor.from_pretrained", load_processor)
    step("safetensors get_tensor (largest)", largest_tensor)
