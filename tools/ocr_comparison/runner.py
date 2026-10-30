"""Arm runner: per-page execution with bounded retry, honest accounting.

Retry only on injected/transient backend crashes (never re-run to pick the
best output); every retry is recorded and counted as inference work.  A batch
with any non-ok page reports ``partial``, never a blanket PASS.
"""

from __future__ import annotations

import time


def run_pages(page_ids, backend_fn, *, max_retries: int = 0, retry_on: tuple = ()):  # noqa: ANN001
    records = []
    for page_id in page_ids:
        attempts = 0
        record = None
        while True:
            attempts += 1
            start = time.perf_counter()
            try:
                result = backend_fn(page_id)
                result = dict(result)
                result.setdefault("status", "ok")
            except retry_on:
                if attempts <= max_retries:
                    continue
                result = {"status": "error", "engine_seconds": time.perf_counter() - start}
            except Exception as exc:  # noqa: BLE001 - runner reports, does not raise
                result = {"status": "error", "error": f"{type(exc).__name__}"}
            break
        wall = time.perf_counter() - start
        record = {
            "page_id": page_id,
            "status": result.get("status", "error"),
            "engine_seconds": result.get("engine_seconds", wall),
            "wall_seconds": wall,
            "retries": attempts - 1,
            "inference_runs": attempts,
        }
        for key in ("text", "text_sha256", "raw_output_sha256", "error", "lines"):
            if key in result:
                record[key] = result[key]
        records.append(record)
    return records


def batch_summary(records: list[dict]) -> dict:
    pages_ok = sum(1 for r in records if r["status"] == "ok")
    if pages_ok == len(records) and records:
        batch_status = "ok"
    elif pages_ok == 0:
        batch_status = "failed"
    else:
        batch_status = "partial"
    return {
        "pages_total": len(records),
        "pages_ok": pages_ok,
        "batch_status": batch_status,
    }
