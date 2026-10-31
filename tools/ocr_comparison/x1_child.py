"""X1 child process: loads the checkpoint once and runs the frozen pages in order.

Launched by run_x1 under a Windows Job Object memory limit.  Every stage and
every finished page is appended to the JSON-lines output immediately, so a
failure can be attributed to the stage where it happened.  This module never
imports pdfium: pages arrive as PNG paths.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path


def main(argv: list[str]) -> int:
    import_start = time.perf_counter()
    from tools.ocr_comparison.backends.xiaomi_x1 import XiaomiX1
    from tools.ocr_comparison.job_limit import self_peak_commit_bytes

    import torch

    import_seconds = time.perf_counter() - import_start
    cfg = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
    out_path = Path(cfg["out_jsonl"])
    child_start = time.perf_counter()
    current = {"page_id": None}

    with out_path.open("a", encoding="utf-8") as out:

        def emit(obj: dict) -> None:
            out.write(json.dumps(obj, ensure_ascii=False) + "\n")
            out.flush()

        def on_stage(stage: str) -> None:
            try:
                emit({
                    "event": "stage",
                    "stage": stage,
                    "page_id": current["page_id"],
                    "t_seconds": round(time.perf_counter() - child_start, 3),
                    "peak_commit_self": self_peak_commit_bytes(),
                })
            except Exception:  # noqa: BLE001 - observation must never change results
                pass

        emit({
            "event": "child_ready",
            "import_seconds": import_seconds,
            "torch_threads": torch.get_num_threads(),
            "process_peak_commit_bytes_self": self_peak_commit_bytes(),
        })
        backend = XiaomiX1(
            model_dir=cfg["model_dir"],
            deadline_seconds=cfg["deadline_seconds"],
            max_new_tokens=cfg["max_new_tokens"],
            output_char_cap=cfg["output_char_cap"],
            dtype=cfg["dtype"],
            on_stage=on_stage,
            weights_mode=cfg.get("weights_mode", "copy"),
        )
        spent = 0.0
        load_failed = None
        for page in cfg["pages"]:
            current["page_id"] = page["page_id"]
            if load_failed is not None:
                record = {"status": "error",
                          "error": f"model_load_failed_on_earlier_page: {load_failed}"}
            elif spent >= cfg["total_inference_budget_seconds"]:
                record = {"status": "not_run", "error": "total_inference_budget_exhausted"}
            else:
                try:
                    record = backend.run_page(page["png"])
                except MemoryError as exc:
                    record = {"status": "error", "error": f"MemoryError: {exc}",
                              "process_peak_commit_bytes_self": self_peak_commit_bytes()}
                    if backend._model is None:
                        load_failed = "MemoryError"
                except Exception as exc:  # noqa: BLE001 - recorded per page
                    record = {"status": "error", "error": f"{type(exc).__name__}: {exc}",
                              "process_peak_commit_bytes_self": self_peak_commit_bytes()}
                    if backend._model is None:
                        load_failed = type(exc).__name__
                spent += float(record.get("request_seconds") or 0.0)
            record["page_id"] = page["page_id"]
            emit(record)
        emit({"event": "child_done", "total_request_seconds": spent})
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
