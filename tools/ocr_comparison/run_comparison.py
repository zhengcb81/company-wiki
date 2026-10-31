"""W23 comparison runner CLI.

Runs the frozen 14-page sample through the selected arms in a dedicated
per-process flow, caches raw outputs, evaluates against the frozen gold and
writes ``comparison.json`` under the delivery directory.  Page PNGs are
rendered into an owned temp directory and deleted on exit; raw texts are
kept (small) for audit.

Usage (from the worktree root):
  python -m tools.ocr_comparison.run_comparison --arms R0,X1,N0 \
      --out delivery/w23-xiaomi-ocr/comparison.json --pages pilot:byd_ar_2024_p021
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import tempfile
import time
from datetime import datetime, timezone

from pathlib import Path

from .cache import ResultCache, cache_key
from .compare import evaluate_split
from .manifest import build_run_manifest, resource_snapshot, sha256_file
from .runner import batch_summary, run_pages
from .render_pages import render_pages


class owned_tmp_dir:
    """Card-required temp hygiene as a testable primitive: the directory is
    created owned by this run and always removed on exit."""

    def __init__(self, prefix: str = "w23-ocr-run-"):
        self.prefix = prefix
        self.path: Path | None = None

    def __enter__(self) -> Path:
        self.path = Path(tempfile.mkdtemp(prefix=self.prefix))
        return self.path

    def __exit__(self, *exc) -> None:
        if self.path is not None:
            shutil.rmtree(self.path, ignore_errors=True)


_RAW_SEQ = __import__("itertools").count()


def raw_output_path(out_dir: Path, arm: str) -> Path:
    """Per-invocation raw filename: two runs sharing an out dir must never
    clobber each other's per-page records (delta-review finding D2).  Unique
    via UTC stamp + pid + a strictly monotonic per-process counter."""
    stamp = time.strftime("%Y%m%dT%H%M%S", time.gmtime())
    return out_dir / f"raw_{arm.lower()}_{stamp}_{os.getpid()}_{next(_RAW_SEQ)}.json"


UTC = timezone.utc


def _plan_dir(repo: Path) -> Path:
    return repo / "docs" / "plans" / "w23-xiaomi-ocr-2026-10-30"


def _git_commit(repo: Path) -> str:
    import subprocess

    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True, check=True,
    ).stdout.strip()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="W23 OCR comparison runner")
    parser.add_argument("--arms", default="R0,X1,N0")
    parser.add_argument("--out", required=True)
    parser.add_argument("--pages", default="all",
                        help="'all', or page_id(s) comma-separated, or 'pilot:<page_id>'")
    parser.add_argument("--deadline", type=float, default=180.0)
    parser.add_argument("--memory-cap-gb", type=float, default=None,
                        help="defaults to min(8, avail_phys/2) computed at start")
    parser.add_argument("--max-new-tokens", type=int, default=2048)
    parser.add_argument("--no-cache", action="store_true")
    parser.add_argument("--cache-dir", type=Path, default=None, help="explicit persistent experiment result cache")
    parser.add_argument("--x1-weights-mode", choices=("copy", "mapped", "mapped-f32"), default="copy")
    parser.add_argument("--x1-dtype", default="bfloat16")
    args = parser.parse_args(argv)
    from .run_x1 import validate_card_limits
    validate_card_limits(args.deadline, 1800.0)

    repo = Path(__file__).resolve().parents[2]
    plan = _plan_dir(repo)
    manifest_path = plan / "sample_manifest.json"
    gold_path = plan / "gold.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    gold = json.loads(gold_path.read_text(encoding="utf-8"))

    os.environ.setdefault("CWP_PROJECT_ROOT", str(repo))
    if os.environ["CWP_PROJECT_ROOT"] != str(repo):
        raise SystemExit("CWP_PROJECT_ROOT must point at the W23 worktree")

    if args.memory_cap_gb is None:
        snapshot = resource_snapshot()
        available = snapshot["avail_phys_gb"]
        args.memory_cap_gb = min(8.0, available / 2) if available is not None else None

    pages = manifest["pages"]
    if args.pages == "all":
        selected = [p["page_id"] for p in pages]
    elif args.pages.startswith("pilot:"):
        pilot_id = args.pages.split(":", 1)[1]
        selected = [pilot_id]
    else:
        wanted = set(args.pages.split(","))
        selected = [p["page_id"] for p in pages if p["page_id"] in wanted]

    initial_resources = resource_snapshot()
    arms = [a.strip().upper() for a in args.arms.split(",") if a.strip()]
    with owned_tmp_dir() as run_dir:
        run_dir = Path(run_dir)
        started = time.perf_counter()
        results: dict = {"schema_version": "cwp-ocr-comparison/1", "arms": {}}
        rendered = render_pages(manifest_path, run_dir / "pages")
        by_id = {r["page_id"]: r for r in rendered}
        cache = ResultCache(args.cache_dir if not args.no_cache else None)
        arm_identity = {}
        for arm in arms:
            records = []
            execution_receipt = None
            if arm == "R0":
                from .backends.rapidocr_r0 import RapidOCRR0, load_production_config

                config = load_production_config(repo / "config" / "local_ocr.json")
                backend = RapidOCRR0(config, deadline_seconds=args.deadline)
                arm_identity["R0"] = backend.identity_manifest

                def r0_page(page_id, _backend=backend):
                    import hashlib

                    png = by_id[page_id]["png"]
                    key = cache_key(
                        _backend.identity_manifest, by_id[page_id]["sha256"], "n/a",
                        {"deadline": args.deadline},
                    )
                    hit = cache.get(key)
                    if hit is not None and not args.no_cache:
                        return hit
                    out = _backend.run_page(png)
                    out["text_sha256"] = hashlib.sha256(out["text"].encode()).hexdigest()
                    cache.put(key, out)
                    return out

                records = run_pages(selected, r0_page)
            elif arm == "X1":
                from .run_x1 import run_x1_batch, _model_dir, require_memory_limit
                from .backends.xiaomi_x1 import XiaomiX1

                require_memory_limit()
                model_dir = str(_model_dir(os.environ.get("W23_XIAOMI_MODEL_DIR")))
                identity = XiaomiX1(model_dir=model_dir, deadline_seconds=args.deadline,
                                    max_new_tokens=args.max_new_tokens, dtype=args.x1_dtype,
                                    weights_mode=args.x1_weights_mode).identity_manifest
                arm_identity["X1"] = identity
                keys = {pid: cache_key(identity, by_id[pid]["sha256"], identity["prompt_sha256"],
                                       {"deadline": args.deadline, "max_new_tokens": args.max_new_tokens})
                        for pid in selected}
                available = {pid: (None if args.no_cache else cache.get(keys[pid])) for pid in selected}
                missing = [pid for pid in selected if available[pid] is None]
                if missing:
                    result = run_x1_batch(
                        [{"page_id": pid, "png": by_id[pid]["png"]} for pid in missing],
                        deadline=args.deadline, total_budget=1800.0,
                        max_new_tokens=args.max_new_tokens,
                        dtype=args.x1_dtype, weights_mode=args.x1_weights_mode,
                        cap_bytes=int(args.memory_cap_gb * (1024 ** 3)) if args.memory_cap_gb is not None else None,
                        model_dir=model_dir, workdir=run_dir / "x1-child",
                        backend_identity=identity,
                    )
                    execution_receipt = result.get("receipt")
                    for record in result["records"]:
                        pid = record["page_id"]
                        available[pid] = record
                        if record["status"] not in ("not_run", "no_record"):
                            cache.put(keys[pid], record)
                records = [{**available[pid], "page_id": pid} for pid in selected]
            elif arm == "N0":
                from .backends.native_n0 import NativeN0

                backend = NativeN0(manifest_path)
                arm_identity["N0"] = backend.identity_manifest
                records = run_pages(selected, backend.run_page)
            elif arm == "X2":
                arm_identity["X2"] = {
                    "arm": "X2",
                    "backend": "xiaomi-ocr-0-two-stage-paddlex",
                    "status": "not_run",
                    "reason": (
                        "PP-DocLayoutV3 requires the upstream paddlex dependency stack "
                        "(new heavy runtime).  Under the frozen resource bounds "
                        "(avail RAM envelope, no GPU, download budget) this run does not "
                        "install it; X2 is NOT_RUN and is never merged into X1 scores."
                    ),
                }
                records = [
                    {"page_id": page_id, "status": "not_run", "retries": 0}
                    for page_id in selected
                ]
            else:
                raise SystemExit(f"unknown arm {arm}")
            summary = batch_summary(records)
            split = evaluate_split(gold, records, manifest, arm=arm)
            out_dir = Path(args.out).parent
            out_dir.mkdir(parents=True, exist_ok=True)
            raw_path = raw_output_path(out_dir, arm)
            raw_path.write_text(
                json.dumps({"records": records, "summary": summary}, ensure_ascii=False, indent=1),
                encoding="utf-8",
            )
            results["arms"][arm] = {
                "identity": arm_identity.get(arm),
                "summary": summary,
                "evaluation": split,
                "raw_output_file": raw_path.name,
                "execution_receipt": execution_receipt,
            }
        results["run"] = {
            "created_at_utc": datetime.now(UTC).isoformat(),
            "pages_selected": selected,
            "wall_seconds": round(time.perf_counter() - started, 3),
            "cache_entries": len(cache),
        }
        results["run_manifest"] = build_run_manifest(
            repo,
            arms=arm_identity,
            deadline_seconds=args.deadline,
            memory_cap_gb=args.memory_cap_gb,
            cache_enabled=not args.no_cache,
            sample_manifest_sha256=sha256_file(manifest_path),
            gold_sha256=sha256_file(gold_path),
        )
        results["run_manifest"]["limits"]["max_new_tokens"] = args.max_new_tokens
        results["run_manifest"]["resources_at_start"] = initial_resources
        results["run_manifest"]["cache"]["directory"] = str(args.cache_dir) if args.cache_dir else None
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
        print("WROTE", out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
