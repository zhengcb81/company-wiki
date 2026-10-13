"""Scale observation for DU2-LAYOUT (test-side tool, NOT a CI assertion).

Runs the pure ``derive_layout_hints`` over 1k / 10k / 40k synthetic units and
records units / groups / work_units / elapsed / peak RSS.  Wall-clock and RSS
are observations for the lane's handoff, never brittle millisecond CI checks.

Usage:
    python -B -X utf8 tests/fixtures/document_understanding_layout_hints/scale_run.py [--output <json>]
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import tracemalloc
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from cases import scale_case  # noqa: E402

from company_wiki.document_understanding.layout_hints import derive_layout_hints  # noqa: E402


def peak_rss_bytes() -> int | None:
    """Process peak working set on Windows; None when the host refuses it."""
    try:
        import ctypes
        from ctypes import wintypes

        class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
            _fields_ = [
                ("cb", wintypes.DWORD),
                ("PageFaultCount", wintypes.DWORD),
                ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t),
            ]

        counters = PROCESS_MEMORY_COUNTERS()
        counters.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS)
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        query = getattr(kernel32, "K32GetProcessMemoryInfo", None)
        if query is None:  # pragma: no cover - fallback for older hosts
            query = ctypes.WinDLL("psapi", use_last_error=True).GetProcessMemoryInfo
        query.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESS_MEMORY_COUNTERS), wintypes.DWORD]
        query.restype = wintypes.BOOL
        handle = kernel32.GetCurrentProcess()
        if not query(handle, ctypes.byref(counters), counters.cb):
            return None
        return int(counters.PeakWorkingSetSize)
    except Exception:
        return None


def run_one(size: int) -> dict:
    observation = scale_case(size)
    units = sum(len(page["units"]) for page in observation["pages"])
    tracemalloc.start()
    started = time.perf_counter()
    result = derive_layout_hints(observation)
    elapsed = time.perf_counter() - started
    _current, peak_python = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    work_units = next(
        (int(d["detail"]) for d in result["diagnostics"] if d["code"] == "WORK_UNITS"),
        None,
    )
    return {
        "requested_units": size,
        "units": units,
        "pages": len(observation["pages"]),
        "groups": len(result["groups"]),
        "table_regions": sum(1 for g in result["groups"] if g["kind"] == "table_region"),
        "rows": sum(1 for g in result["groups"] if g["kind"] == "table_row"),
        "work_units": work_units,
        "work_units_per_unit": round(work_units / units, 3) if work_units else None,
        "elapsed_seconds": round(elapsed, 4),
        "peak_python_bytes": peak_python,
        "peak_rss_bytes": peak_rss_bytes(),
        "complete": result["coverage"]["complete"],
        "deferred": len(result["coverage"]["deferred_unit_ids"]),
        "diagnostics": sorted({d["code"] for d in result["diagnostics"]}),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=None)
    parser.add_argument("--size", type=int, default=None, help="measure one size in this process")
    args = parser.parse_args()

    if args.size is not None:
        print(json.dumps(run_one(args.size), ensure_ascii=False))
        return 0

    # one fresh process per size: peak RSS is a process high-water mark
    rows = []
    for size in (1000, 10000, 40000):
        completed = subprocess.run(
            [sys.executable, "-B", "-X", "utf8", str(Path(__file__).resolve()), "--size", str(size)],
            capture_output=True,
            text=True,
            encoding="utf8",
        )
        if completed.returncode != 0:
            rows.append({"requested_units": size, "status": "FAILED", "stderr": completed.stderr[-400:]})
            continue
        rows.append(json.loads(completed.stdout.strip().splitlines()[-1]))

    payload = {"schema_version": "du2-layout-scale/1", "runs": rows}
    text = json.dumps(payload, ensure_ascii=False, indent=1)
    if args.output:
        Path(args.output).write_text(text + "\n", encoding="utf8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
