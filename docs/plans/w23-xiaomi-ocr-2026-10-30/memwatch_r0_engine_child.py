"""Engine-memory child process (delta review OPEN D3).

Runs in a FRESH interpreter so process-lifetime peaks measure exactly:
baseline imports + LocalOCRAdapter engine load + one transcribe.  The parent
driver renders the page PNG first, so pdfium is never imported here.
"""
import ctypes
import json
import sys
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
    png = Path(sys.argv[1])
    baseline = peaks()  # interpreter + stdlib only so far
    from tools.ocr_comparison.backends.rapidocr_r0 import load_production_config
    from company_wiki.document_normalization.local_ocr import LocalOCRAdapter, OCRLimits
    import time

    config = load_production_config(REPO / "config" / "local_ocr.json")
    adapter = LocalOCRAdapter(config)
    after_import = peaks()
    adapter.validate_environment()
    after_load = peaks()
    start = time.perf_counter()
    result = adapter.transcribe(png.read_bytes(), limits=OCRLimits(deadline=time.monotonic() + 180))
    engine_seconds = time.perf_counter() - start
    final = peaks()
    print(json.dumps({
        "status": "ok" if result.lines is not None else "empty",
        "line_count": len(result.lines),
        "engine_seconds": round(engine_seconds, 2),
        "baseline": baseline,
        "after_import": after_import,
        "after_engine_load": after_load,
        "final": final,
        "engine_peak_workingset_gb": round(final["peak_workingset_bytes"] / 1024 ** 3, 3),
        "engine_peak_commit_gb": round(final["peak_commit_bytes"] / 1024 ** 3, 3),
        "engine_delta_over_import_commit_gb": round(
            (final["peak_commit_bytes"] - after_import["peak_commit_bytes"]) / 1024 ** 3, 3),
    }))


if __name__ == "__main__":
    main()
