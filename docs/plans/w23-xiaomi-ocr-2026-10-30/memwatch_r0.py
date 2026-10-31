"""One-page instrumented R0 memory measurement (self-audit gap: peak RAM).

Runs the same engine/runtime as the isolated child (LocalOCRAdapter via the
R0 backend wrapper's config path) in-process and reads this process's peak
working set / peak commit around it.  Labelled honestly: it excludes the
child-process boundary overhead of IsolatedOCRAdapter; the production child
does the same ONNX work with the same model bytes.
"""
import ctypes
import json
import shutil
import sys
import tempfile
from ctypes import wintypes
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))


class PMC(ctypes.Structure):
    _fields_ = [
        ("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
        ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
        ("Q1", ctypes.c_size_t), ("Q2", ctypes.c_size_t),
        ("Q3", ctypes.c_size_t), ("Q4", ctypes.c_size_t),
        ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t),
    ]


k32 = ctypes.windll.kernel32
k32.GetCurrentProcess.restype = ctypes.c_void_p
k32.K32GetProcessMemoryInfo.argtypes = [ctypes.c_void_p, ctypes.POINTER(PMC), wintypes.DWORD]
k32.K32GetProcessMemoryInfo.restype = wintypes.BOOL


def peaks():
    pmc = PMC()
    pmc.cb = ctypes.sizeof(PMC)
    assert k32.K32GetProcessMemoryInfo(k32.GetCurrentProcess(), ctypes.byref(pmc), ctypes.sizeof(PMC))
    return {"peak_workingset_bytes": pmc.PeakWorkingSetSize,
            "peak_commit_bytes": pmc.PeakPagefileUsage}


def main():
    from tools.ocr_comparison.backends.rapidocr_r0 import RapidOCRR0, load_production_config
    from tools.ocr_comparison.render_pages import render_pages

    baseline = peaks()
    cfg = load_production_config(REPO / "config" / "local_ocr.json")
    backend = RapidOCRR0(cfg, deadline_seconds=180.0)
    tmp = Path(tempfile.mkdtemp(prefix="w23-mem-"))
    try:
        rendered = render_pages(REPO / "docs/plans/w23-xiaomi-ocr-2026-10-30/sample_manifest.json", tmp)
        png = next(r for r in rendered if r["page_id"] == "byd_ar_2024_p021")["png"]
        out = backend.run_page(png)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    after = peaks()
    receipt = {
        "schema_version": "cwp-ocr-memwatch-receipt/1",
        "purpose": "self-audit gap: R0 peak memory on a representative page (instrumented re-run, not for accuracy)",
        "page": "byd_ar_2024_p021",
        "engine": "LocalOCRAdapter engine in-process (same ONNX models/runtime/threads as the IsolatedOCRAdapter child); excludes child-process boundary overhead",
        "status": out["status"],
        "before": baseline,
        "after": after,
        "peak_workingset_gb": round(after["peak_workingset_bytes"] / 1024 ** 3, 3),
        "peak_commit_gb": round(after["peak_commit_bytes"] / 1024 ** 3, 3),
        "note": "the isolated child holds the same three ONNX sessions; parent-side accounting in the delivered runs records engine_seconds only",
    }
    out_path = REPO / "delivery/w23-xiaomi-ocr/memwatch_r0_receipt.json"
    out_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: receipt[k] for k in ("status", "peak_workingset_gb", "peak_commit_gb")}, indent=1))
    print("WROTE", out_path)


if __name__ == "__main__":
    main()
