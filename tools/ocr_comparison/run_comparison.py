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
from datetime import UTC, datetime
from pathlib import Path

from .cache import ResultCache, cache_key
from .compare import evaluate_split
from .manifest import build_run_manifest, resource_snapshot, sha256_file
from .runner import batch_summary, run_pages
from .render_pages import render_pages


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
    args = parser.parse_args(argv)

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
        args.memory_cap_gb = min(8.0, max(0.5, snapshot["avail_phys_gb"] / 2))

    pages = manifest["pages"]
    if args.pages == "all":
        selected = [p["page_id"] for p in pages]
    elif args.pages.startswith("pilot:"):
        pilot_id = args.pages.split(":", 1)[1]
        selected = [pilot_id]
    else:
        wanted = set(args.pages.split(","))
        selected = [p["page_id"] for p in pages if p["page_id"] in wanted]

    arms = [a.strip().upper() for a in args.arms.split(",") if a.strip()]
    run_dir = Path(tempfile.mkdtemp(prefix="w23-ocr-run-"))
    started = time.perf_counter()
    results: dict = {"schema_version": "cwp-ocr-comparison/1", "arms": {}}
    try:
        rendered = render_pages(manifest_path, run_dir / "pages")
        by_id = {r["page_id"]: r for r in rendered}
        cache = ResultCache()
        arm_identity = {}
        for arm in arms:
            records = []
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
                from .backends.xiaomi_x1 import XiaomiX1

                model_dir = os.environ["W23_XIAOMI_MODEL_DIR"]
                backend = XiaomiX1(
                    model_dir=model_dir,
                    deadline_seconds=args.deadline,
                    max_new_tokens=args.max_new_tokens,
                )
                arm_identity["X1"] = backend.identity_manifest

                def x1_page(page_id, _backend=backend):
                    import hashlib

                    png = by_id[page_id]["png"]
                    key = cache_key(
                        _backend.identity_manifest, by_id[page_id]["sha256"],
                        _backend.identity_manifest["prompt_sha256"],
                        {"max_new_tokens": _backend.max_new_tokens},
                    )
                    hit = cache.get(key)
                    if hit is not None and not args.no_cache:
                        return hit
                    out = _backend.run_page(png)
                    out["text_sha256"] = hashlib.sha256(out["text"].encode()).hexdigest()
                    out["engine_seconds_original"] = out.get("engine_seconds")
                    cache.put(key, out)
                    return out

                records = run_pages(selected, x1_page)
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
            raw_path = out_dir / f"raw_{arm.lower()}.json"
            raw_path.write_text(
                json.dumps({"records": records, "summary": summary}, ensure_ascii=False, indent=1),
                encoding="utf-8",
            )
            results["arms"][arm] = {
                "identity": arm_identity.get(arm),
                "summary": summary,
                "evaluation": split,
                "raw_output_file": raw_path.name,
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
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
        print("WROTE", out_path)
    finally:
        shutil.rmtree(run_dir, ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
