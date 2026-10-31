"""Probe: find the minimal torch op that crashes under a Job Object memory cap.

argv: cap_gib mode
modes: mm4096 (big fp32 matmul), conv (vision-like conv), mm4096_t1, conv_t1
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from tools.ocr_comparison.job_limit import GIB, JobMemoryLimit, self_peak_commit_bytes  # noqa: E402

cap = JobMemoryLimit(int(float(sys.argv[1]) * GIB))
try:
    import time

    import torch

    mode = sys.argv[2]
    threads = 1 if mode.endswith("_t1") else 10
    torch.set_num_threads(threads)
    print(f"mode={mode} threads={threads}", flush=True)
    if mode.startswith("mm4096"):
        a = torch.randn(4096, 4096)
        b = torch.randn(4096, 4096)
        t0 = time.perf_counter()
        c = a @ b
        print(f"mm ok {time.perf_counter()-t0:.2f}s", flush=True)
    elif mode.startswith("conv"):
        x = torch.randn(12032, 3, 2, 16, 16)  # Qwen3VL patch layout
        w = torch.randn(1152, 24, 1, 1)  # pseudo conv1 weights
        t0 = time.perf_counter()
        y = torch.nn.functional.conv2d(
            x.view(-1, 3, 2 * 16, 16 * 1)[:, :, :, :], w.view(1152, 24, 1, 1)[:, :3], stride=1,
        )
        print(f"conv ok {time.perf_counter()-t0:.2f}s out {tuple(y.shape)}", flush=True)
    print("peak_self", self_peak_commit_bytes(), "job_peak", cap.peak_process_bytes(), flush=True)
finally:
    cap.close()
