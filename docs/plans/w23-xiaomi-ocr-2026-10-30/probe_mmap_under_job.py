"""Probe: do read-only file-backed mapped pages count against a Job Object
process-memory limit?  Touches every page of model.safetensors via mmap under
a job limit smaller than the file, and reports survival plus the job peak.
Pure measurement, no model involved."""
import ctypes
import json
import mmap
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from tools.ocr_comparison.job_limit import (  # noqa: E402
    GIB, JobMemoryLimit, self_peak_commit_bytes,
)

FILE = (Path(__file__).resolve().parents[3]
        / ".w23_cache/hub/models--xiaomi-research--Xiaomi-OCR-0/snapshots"
        / "bbd8cf8d21f256b3644b44cb860f3a7cecb93c30" / "model.safetensors")
LIMIT = int(2.0 * GIB)

job = JobMemoryLimit(LIMIT)
try:
    size = FILE.stat().st_size
    with open(FILE, "rb") as fh:
        with mmap.mmap(fh.fileno(), length=0, access=mmap.ACCESS_READ) as view:
            touched = 0
            chunk = 1 << 20
            for offset in range(0, size, chunk):
                touched += view[offset]
            peak_self = self_peak_commit_bytes()
    peak_job = job.peak_process_bytes()
    result = {
        "file_bytes": size, "job_limit_bytes": LIMIT,
        "survived": True, "touched_sum": touched,
        "peak_self_commit_bytes": peak_self,
        "peak_self_commit_gib": round(peak_self / GIB, 3),
        "job_peak_process_bytes": peak_job,
        "job_peak_process_gib": round(peak_job / GIB, 3),
        "verdict": "mapped pages do NOT count against the job process-memory limit"
        if peak_job < size else "mapped pages DO count against the job limit",
    }
except MemoryError as exc:
    peak_job = job.peak_process_bytes()
    result = {"file_bytes": FILE.stat().st_size, "job_limit_bytes": LIMIT,
              "survived": False, "error": f"MemoryError: {exc}",
              "job_peak_process_bytes": peak_job,
              "job_peak_process_gib": round(peak_job / GIB, 3),
              "verdict": "allocation refused while touching mapped pages"}
finally:
    job.close()
print(json.dumps(result))
