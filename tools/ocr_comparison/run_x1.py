"""Run the X1 arm (Xiaomi-OCR-0) in a child process under the card's memory bound.

Pages are rendered in this process with the same bytes every arm uses.  One
child process then loads the checkpoint and runs the pages in order, under a
Windows Job Object whose ProcessMemoryLimit is the card bound
min(8 GiB, available RAM / 2), taken at run start.  The operating system
enforces the limit on committed memory; the peak is read back from the job
object after the run.  Nothing here predicts memory use.

Timing: each page request is bounded by --deadline seconds from run_page entry
(cold load included for the first page); the whole batch is bounded by
--total-budget seconds of request time (card: total inference <= 30 min).
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path

from .job_limit import GIB, JobMemoryLimit, card_memory_cap_bytes, host_memory_snapshot

REPO = Path(__file__).resolve().parents[2]
PLAN = REPO / "docs" / "plans" / "w23-xiaomi-ocr-2026-10-30"
DELIVERY = REPO / "delivery" / "w23-xiaomi-ocr"
DEFAULT_MODEL_DIR = (
    REPO / ".w23_cache" / "hub" / "models--xiaomi-research--Xiaomi-OCR-0"
    / "snapshots" / "bbd8cf8d21f256b3644b44cb860f3a7cecb93c30"
)


def _model_dir(explicit: str | None) -> Path:
    path = Path(explicit or os.environ.get("W23_XIAOMI_MODEL_DIR") or DEFAULT_MODEL_DIR)
    if not (path / "model.safetensors").is_file():
        raise FileNotFoundError(f"model.safetensors missing under {path}")
    return path


def run_x1_batch(
    pages: list[dict],
    *,
    deadline: float,
    total_budget: float,
    max_new_tokens: int = 4096,
    dtype: str = "bfloat16",
    weights_mode: str = "copy",
    cap_bytes: int | None = None,
    model_dir: str | None = None,
    workdir: str | Path | None = None,
) -> dict:
    from .backends.xiaomi_x1 import XiaomiX1

    model = _model_dir(model_dir)
    identity = XiaomiX1(
        model_dir=str(model), deadline_seconds=deadline,
        max_new_tokens=max_new_tokens, dtype=dtype, weights_mode=weights_mode,
    ).identity_manifest

    host_before = host_memory_snapshot()
    cap = int(cap_bytes) if cap_bytes else card_memory_cap_bytes(host_before["avail_phys_bytes"])

    owned = None
    if workdir is None:
        owned = tempfile.TemporaryDirectory(prefix="w23-x1-child-")
        workdir = owned.name
    work = Path(workdir)
    work.mkdir(parents=True, exist_ok=True)
    out_jsonl = work / "x1_records.jsonl"
    cfg = {
        "model_dir": str(model),
        "deadline_seconds": deadline,
        "total_inference_budget_seconds": total_budget,
        "max_new_tokens": max_new_tokens,
        "output_char_cap": 60000,
        "dtype": dtype,
        "weights_mode": weights_mode,
        "pages": pages,
        "out_jsonl": str(out_jsonl),
    }
    cfg_path = work / "x1_config.json"
    cfg_path.write_text(json.dumps(cfg, ensure_ascii=False), encoding="utf-8")
    env = {
        **os.environ,
        "PYTHONUTF8": "1",
        "HF_HUB_OFFLINE": "1",
        "TRANSFORMERS_OFFLINE": "1",
    }

    job = JobMemoryLimit(cap)
    try:
        with (work / "child_stdout.log").open("w", encoding="utf-8") as so, \
                (work / "child_stderr.log").open("w", encoding="utf-8") as se:
            started = time.perf_counter()
            proc = subprocess.Popen(
                [sys.executable, "-m", "tools.ocr_comparison.x1_child", str(cfg_path)],
                cwd=str(REPO), stdout=so, stderr=se, env=env,
            )
            try:
                job.assign(proc.pid)
            except OSError:
                proc.kill()
                proc.wait()
                raise
            backstop = total_budget + deadline + 300
            backstop_hit = False
            try:
                return_code = proc.wait(timeout=backstop)
            except subprocess.TimeoutExpired:
                job.terminate()
                return_code = proc.wait()
                backstop_hit = True
        wall_seconds = time.perf_counter() - started
        peak_bytes = job.peak_process_bytes()
    finally:
        job.close()

    host_after = host_memory_snapshot()
    records: list[dict] = []
    events: list[dict] = []
    if out_jsonl.exists():
        for line in out_jsonl.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            obj = json.loads(line)
            (events if "event" in obj else records).append(obj)
    done = {r["page_id"] for r in records}
    for page in pages:
        if page["page_id"] not in done:
            records.append({
                "page_id": page["page_id"],
                "status": "no_record",
                "error": f"child_exit_code={return_code}; backstop_hit={backstop_hit}",
            })
    order = {p["page_id"]: i for i, p in enumerate(pages)}
    records.sort(key=lambda r: order[r["page_id"]])

    stderr_tail = (work / "child_stderr.log").read_text(encoding="utf-8", errors="replace")[-3000:]
    receipt = {
        "schema_version": "cwp-ocr-x1-run-receipt/1",
        "created_at_utc": datetime.now(UTC).isoformat(),
        "method": (
            "pages rendered in the parent with the shared pypdfium2 renderer; one child process "
            "loads Xiaomi-OCR-0 on CPU and runs the pages in order under a Windows Job Object "
            "ProcessMemoryLimit (committed bytes); the peak is read from the job object"
        ),
        "config": {
            "deadline_seconds_per_request": deadline,
            "total_inference_budget_seconds": total_budget,
            "max_new_tokens": max_new_tokens,
            "dtype": dtype,
            "weights_mode": weights_mode,
            "threads": "torch default (reported by the child)",
        },
        "memory": {
            "cap_bytes": cap,
            "cap_gib": round(cap / GIB, 3),
            "rule": "min(8 GiB, available physical RAM / 2) at run start" if not cap_bytes else "explicit --cap-gb",
            "job_peak_process_bytes": peak_bytes,
            "job_peak_process_gib": round(peak_bytes / GIB, 3),
        },
        "host_before": host_before,
        "host_after": host_after,
        "child": {
            "return_code": return_code,
            "backstop_hit": backstop_hit,
            "wall_seconds": round(wall_seconds, 2),
            "events": events,
            "stderr_tail": stderr_tail,
        },
        "identity": identity,
    }
    if owned is not None:
        owned.cleanup()
    return {"records": records, "receipt": receipt, "identity": identity}


def main(argv: list[str] | None = None) -> int:
    from .render_pages import render_pages

    parser = argparse.ArgumentParser(description="W23 X1 arm runner (memory-bounded child process)")
    parser.add_argument("--pages", default="pilot:byd_ar_2024_p021",
                        help="'all' or 'pilot:<page_id>' or comma-separated page ids")
    parser.add_argument("--deadline", type=float, default=180.0)
    parser.add_argument("--total-budget", type=float, default=1800.0)
    parser.add_argument("--max-new-tokens", type=int, default=4096)
    parser.add_argument("--dtype", default="bfloat16")
    parser.add_argument("--weights-mode", choices=["copy", "mapped", "mapped-f32"], default="copy")
    parser.add_argument("--cap-gb", type=float, default=None)
    parser.add_argument("--model-dir", default=None)
    parser.add_argument("--tag", required=True)
    args = parser.parse_args(argv)

    manifest_path = PLAN / "sample_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    all_ids = [p["page_id"] for p in manifest["pages"]]
    if args.pages == "all":
        selected = all_ids
    elif args.pages.startswith("pilot:"):
        selected = [args.pages.split(":", 1)[1]]
    else:
        wanted = set(args.pages.split(","))
        selected = [pid for pid in all_ids if pid in wanted]
    if not selected or any(pid not in all_ids for pid in selected):
        raise SystemExit("unknown page selection")

    cap_bytes = int(args.cap_gb * GIB) if args.cap_gb else None
    with tempfile.TemporaryDirectory(prefix="w23-x1-run-") as tmp:
        rendered = render_pages(manifest_path, Path(tmp) / "pages")
        by_id = {r["page_id"]: r for r in rendered}
        pages = [{"page_id": pid, "png": by_id[pid]["png"]} for pid in selected]
        result = run_x1_batch(
            pages, deadline=args.deadline, total_budget=args.total_budget,
            max_new_tokens=args.max_new_tokens, dtype=args.dtype,
            weights_mode=args.weights_mode, cap_bytes=cap_bytes,
            model_dir=args.model_dir, workdir=Path(tmp) / "child",
        )

    out_path = DELIVERY / f"x1_{args.tag}_receipt.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "cwp-ocr-x1-run/1",
        "tag": args.tag,
        "pages_selected": selected,
        "receipt": result["receipt"],
        "records": result["records"],
    }
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    summary = {r["page_id"]: r["status"] for r in result["records"]}
    mem = result["receipt"]["memory"]
    print(json.dumps({"summary": summary, "cap_gib": mem["cap_gib"],
                      "job_peak_gib": mem["job_peak_process_gib"],
                      "child_return_code": result["receipt"]["child"]["return_code"]},
                     ensure_ascii=False, indent=1))
    print("WROTE", out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
