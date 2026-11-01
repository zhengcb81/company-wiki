"""R1 campaign: one cumulative inference budget closed across invocations.

The W23 original delivery charged each invocation separately and lost the
cumulative accounting (ROOT reception, finding P1).  This module closes that
loop with a minimal persistent ledger:

- ``create_ledger`` writes the budget once; ``load_ledger`` refuses corrupt
  files (bad JSON, schema drift, spent != sum of entries) instead of renewing.
- ``request_budget`` returns min(180, remaining) per the R1 card; a campaign
  must refuse to start when nothing remains.
- ``record`` appends one entry and atomically persists; recovery/restart never
  renews the budget and never re-charges cache hits.

No production task library, approval chain or hash-permission list is
introduced: the ledger is a single JSON file owned by this experiment.
"""

from __future__ import annotations

import json
import os
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path

LEDGER_SCHEMA = "cwp-ocr-campaign-ledger/1"
REQUEST_DEADLINE_CAP_SECONDS = 180.0


class LedgerCorrupt(RuntimeError):
    """The ledger exists but cannot be trusted; conservatively refuse to run."""


def create_ledger(path: str | Path, *, plan_id: str, budget_seconds: float) -> dict:
    path = Path(path)
    if path.exists():
        raise FileExistsError(f"ledger already exists: {path}")
    ledger = {
        "schema_version": LEDGER_SCHEMA,
        "plan_id": plan_id,
        "created_at_utc": datetime.now(UTC).isoformat(),
        "budget_seconds": float(budget_seconds),
        "spent_seconds": 0.0,
        "entries": [],
    }
    _atomic_write_json(path, ledger)
    return ledger


def _atomic_write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle_fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(handle_fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=1)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
    except BaseException:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def load_ledger(path: str | Path) -> dict:
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"ledger missing: {path}")
    try:
        ledger = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise LedgerCorrupt(f"ledger is not valid JSON: {exc}") from None
    if not isinstance(ledger, dict) or ledger.get("schema_version") != LEDGER_SCHEMA:
        raise LedgerCorrupt("ledger schema mismatch")
    budget = ledger.get("budget_seconds")
    entries = ledger.get("entries")
    spent = ledger.get("spent_seconds")
    if not isinstance(budget, (int, float)) or isinstance(budget, bool) or budget <= 0:
        raise LedgerCorrupt("ledger budget invalid")
    if not isinstance(entries, list) or not all(isinstance(e, dict) for e in entries):
        raise LedgerCorrupt("ledger entries invalid")
    expected = 0.0
    for entry in entries:
        seconds = entry.get("seconds")
        if not isinstance(seconds, (int, float)) or isinstance(seconds, bool) or seconds < 0:
            raise LedgerCorrupt("ledger entry seconds invalid")
        expected += float(seconds)
    if not isinstance(spent, (int, float)) or isinstance(spent, bool):
        raise LedgerCorrupt("ledger spent invalid")
    if abs(float(spent) - expected) > 1e-6:
        raise LedgerCorrupt(
            f"ledger spent {spent} does not equal entry sum {expected}")
    return ledger


def remaining_seconds(ledger: dict) -> float:
    return float(ledger["budget_seconds"]) - float(ledger["spent_seconds"])


def request_budget(ledger: dict) -> float:
    """Per-request deadline for the next request: min(180, remaining)."""
    return min(REQUEST_DEADLINE_CAP_SECONDS, remaining_seconds(ledger))


def record(ledger: dict, path: str | Path, *, arm: str, page_id: str,
           seconds: float, status: str) -> dict:
    if seconds < 0:
        raise ValueError("seconds must be >= 0")
    if remaining_seconds(ledger) + 1e-9 < seconds:
        # Never silently exceed the budget: refuse the write so the caller
        # records an honest refusal instead of washing the cost.
        raise ValueError(
            f"entry would exceed budget: remaining {remaining_seconds(ledger):.3f} < {seconds:.3f}")
    entry = {
        "ts_utc": datetime.now(UTC).isoformat(),
        "arm": arm,
        "page_id": page_id,
        "seconds": round(float(seconds), 6),
        "status": status,
    }
    ledger["entries"].append(entry)
    ledger["spent_seconds"] = round(
        float(ledger["spent_seconds"]) + float(entry["seconds"]), 6)
    _atomic_write_json(Path(path), ledger)
    return ledger


# ---------------------------------------------------------------------------
# Batch orchestration: per-page accounting into the persistent ledger.
# ---------------------------------------------------------------------------


def seconds_to_charge(record: dict, deadline_seconds: float) -> float:
    """Conservative charge for one page record.

    Completed/failed records carry the child-measured elapsed time.  A page the
    watchdog killed has no measured time, so the full request deadline is
    charged (unknown in-flight cost counts conservatively and is never washed
    out).  A page that never started charges nothing.
    """
    status = record.get("status")
    elapsed = record.get("request_seconds")
    if isinstance(elapsed, (int, float)) and not isinstance(elapsed, bool) and elapsed >= 0:
        return float(elapsed)
    if status in ("timeout", "no_record"):
        return float(deadline_seconds)
    return 0.0


class FakePageBackend:
    """Test-only page backend: no model, deterministic small sleeps.

    Declared for the cross-process campaign TDD the R1 card requires; never
    used by real runs (the CLI refuses --fake unless explicitly passed).
    """

    def __init__(self, sleep_seconds: float = 0.3):
        self.sleep_seconds = float(sleep_seconds)

    def run_page(self, page_id: str, png_path, *, deadline_seconds: float) -> dict:
        start = time.perf_counter()
        slept = min(self.sleep_seconds, max(0.0, deadline_seconds))
        time.sleep(slept)
        timed_out = self.sleep_seconds > deadline_seconds + 1e-9
        return {
            "status": "timeout" if timed_out else "ok",
            "text": f"fake text for {page_id}",
            "request_seconds": time.perf_counter() - start,
            "finish_reason": "deadline" if timed_out else "stop",
        }


def run_campaign_batch(
    *,
    ledger_path: Path,
    ledger: dict,
    arm: str,
    pages: list[dict],
    cache_dir: str | Path | None = None,
    max_new_tokens: int = 4096,
    weights_mode: str = "mapped-f32",
    model_dir: str | None = None,
    manifest_path: str | Path | None = None,
    fake_sleep_seconds: float | None = None,
) -> dict:
    """Run one arm over ``pages`` charging every request to the ledger.

    Per-request deadline is min(180, remaining); the batch budget handed to the
    X1 child is the whole remaining balance, so the parent watchdog stops the
    batch exactly where the card budget ends.  Cache hits keep their original
    measured time and are not re-charged.
    """
    from .cache import ResultCache, cache_key

    ledger_path = Path(ledger_path)
    # A zero balance does not refuse the batch: cache hits still serve (no
    # inference, no charge) and missed pages are recorded honestly as
    # not_run budget_exhausted with the full denominator preserved.
    initial_remaining = remaining_seconds(ledger)
    request_deadline = min(REQUEST_DEADLINE_CAP_SECONDS, initial_remaining)
    cache = ResultCache(cache_dir)
    charged: list[dict] = []

    if arm == "X1F-fake":
        backend = FakePageBackend(fake_sleep_seconds if fake_sleep_seconds else 0.3)
        for page in pages:
            pid = page["page_id"]
            page_deadline = request_budget(ledger)
            key = cache_key({"arm": "X1F-fake", "sleep": fake_sleep_seconds},
                            page.get("png_sha256") or pid, "fake",
                            {"request_deadline_cap": REQUEST_DEADLINE_CAP_SECONDS})
            hit = cache.get(key)
            if hit is not None:
                hit = dict(hit)
                hit["page_id"] = pid
                hit.setdefault("request_seconds", 0.0)
                charged.append({**hit, "cache_hit": True})
                continue
            if page_deadline <= 0:
                charged.append({"page_id": pid, "status": "not_run",
                                "error": "budget_exhausted", "request_seconds": 0.0})
                ledger = record(ledger, ledger_path, arm=arm, page_id=pid,
                                seconds=0.0, status="not_run")
                continue
            record_dict = backend.run_page(pid, page.get("png"), deadline_seconds=page_deadline)
            record_dict["page_id"] = pid
            cache.put(key, record_dict)
            charged.append(record_dict)
            # Interleaved accounting: the next page's request budget must see
            # the balance after this page, so the ledger is persisted here.
            ledger = record(ledger, ledger_path, arm=arm, page_id=pid,
                            seconds=min(seconds_to_charge(record_dict, page_deadline),
                                        remaining_seconds(ledger)),
                            status=record_dict.get("status", "unknown"))
    elif arm == "X1F":
        from .run_x1 import run_x1_batch, _model_dir
        from .backends.xiaomi_x1 import XiaomiX1

        model = _model_dir(model_dir)
        remaining = remaining_seconds(ledger)
        identity = XiaomiX1(
            model_dir=str(model),
            deadline_seconds=min(REQUEST_DEADLINE_CAP_SECONDS, remaining),
            max_new_tokens=max_new_tokens,
            weights_mode=weights_mode,
        ).identity_manifest
        result = run_x1_batch(
            pages,
            deadline=min(REQUEST_DEADLINE_CAP_SECONDS, remaining),
            total_budget=remaining,
            max_new_tokens=max_new_tokens,
            weights_mode=weights_mode,
            model_dir=str(model),
            backend_identity=identity,
        )
        by_id = {r["page_id"]: r for r in result["records"]}
        cache_keys = {
            pid: cache_key(result["identity"], page.get("png_sha256") or pid,
                           result["identity"].get("prompt_sha256", ""),
                           {"request_deadline_cap": REQUEST_DEADLINE_CAP_SECONDS,
                            "max_new_tokens": max_new_tokens})
            for pid, page in ((p["page_id"], p) for p in pages)
        }
        for page in pages:
            pid = page["page_id"]
            rec = by_id[pid]
            if rec.get("status") in ("not_run", "no_record"):
                charged.append(rec)
                continue
            cache.put(cache_keys[pid], rec)
            charged.append(rec)
    elif arm == "R0":
        from .backends.rapidocr_r0 import RapidOCRR0, load_production_config

        config = load_production_config(REPO_ROOT / "config" / "local_ocr.json")
        for page in pages:
            pid = page["page_id"]
            page_deadline = request_budget(ledger)
            backend = RapidOCRR0(config, deadline_seconds=page_deadline)
            key = cache_key(backend.identity_manifest, page.get("png_sha256") or pid,
                            "n/a", {"request_deadline_cap": REQUEST_DEADLINE_CAP_SECONDS})
            hit = cache.get(key)
            if hit is not None:
                hit = dict(hit)
                hit["page_id"] = pid
                hit.setdefault("request_seconds", hit.get("engine_seconds", 0.0))
                charged.append({**hit, "cache_hit": True})
                continue
            if page_deadline <= 0:
                charged.append({"page_id": pid, "status": "not_run",
                                "error": "budget_exhausted", "request_seconds": 0.0})
                ledger = record(ledger, ledger_path, arm=arm, page_id=pid,
                                seconds=0.0, status="not_run")
                continue
            started = time.perf_counter()
            rec = backend.run_page(page["png"])
            elapsed = time.perf_counter() - started
            rec["page_id"] = pid
            rec["request_seconds"] = float(rec.get("request_seconds") or elapsed)
            rec["engine_seconds"] = float(rec.get("engine_seconds") or elapsed)
            cache.put(key, rec)
            charged.append(rec)
            ledger = record(ledger, ledger_path, arm=arm, page_id=pid,
                            seconds=min(seconds_to_charge(rec, page_deadline),
                                        remaining_seconds(ledger)),
                            status=rec.get("status", "unknown"))
    elif arm == "N0":
        from .backends.native_n0 import NativeN0

        gold_path_for_roles = None
        if manifest_path is not None:
            candidate = Path(manifest_path).parent / "r1_gold.json"
            if candidate.is_file():
                gold_path_for_roles = candidate
        backend = NativeN0(manifest_path, gold_path=gold_path_for_roles)
        for page in pages:
            rec = backend.run_page(page["page_id"])
            rec["page_id"] = page["page_id"]
            rec.setdefault("request_seconds", 0.0)
            charged.append(rec)
            ledger = record(ledger, ledger_path, arm=arm, page_id=page["page_id"],
                            seconds=0.0, status=rec.get("status", "unknown"))
    else:
        raise ValueError(f"unknown campaign arm: {arm}")

    # Charge the ledger per page, persisting after each entry so a crash leaves
    # an honest partial ledger.  Requests never exceed the per-request budget,
    # so the charge cannot overrun the remaining balance.
    # X1F real: the child enforces the per-page/batch budget internally and
    # returns elapsed per record; charge after the batch, capping at the
    # balance so watchdog-killed pages cannot push the ledger past the budget.
    if arm == "X1F":
        if initial_remaining <= 0:
            for page in pages:
                ledger = record(ledger, ledger_path, arm=arm,
                                page_id=page["page_id"], seconds=0.0,
                                status="not_run")
            return {"records": [{"page_id": p["page_id"], "status": "not_run",
                                 "error": "budget_exhausted"} for p in pages],
                    "remaining_seconds": 0.0, "request_deadline": 0.0}
        ledger = load_ledger(ledger_path)
        for rec in charged:
            seconds = min(seconds_to_charge(rec, request_deadline),
                          remaining_seconds(ledger))
            ledger = record(ledger, ledger_path, arm=arm,
                            page_id=rec.get("page_id", "?"), seconds=seconds,
                            status=rec.get("status", "unknown"))
    return {"records": charged, "remaining_seconds": remaining_seconds(ledger),
            "request_deadline": request_deadline}


def identity_sha(identity: dict) -> str:
    import hashlib

    return hashlib.sha256(json.dumps(identity, sort_keys=True).encode("utf-8")).hexdigest()


REPO_ROOT = Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------------------
# CLI: init / run.  The run sub-command is what cross-process tests drive.
# ---------------------------------------------------------------------------


def _cli_init(args) -> int:
    create_ledger(Path(args.ledger), plan_id=args.plan_id, budget_seconds=args.budget)
    print(json.dumps({"ledger": args.ledger, "budget": args.budget}))
    return 0


def _cli_run(args) -> int:
    ledger = load_ledger(Path(args.ledger))
    manifest_path = Path(args.manifest) if args.manifest else None
    if args.arm in ("R0", "X1F") and manifest_path is None:
        raise SystemExit(f"arm {args.arm} requires --manifest")
    if args.pages == "all":
        if manifest_path is None:
            raise SystemExit("--pages all requires --manifest")
        page_ids = [p["page_id"] for p in json.loads(
            Path(manifest_path).read_text(encoding="utf-8"))["pages"]]
    else:
        page_ids = [s.strip() for s in args.pages.split(",") if s.strip()]
    import tempfile

    with tempfile.TemporaryDirectory(prefix="w23-r1-campaign-") as tmp:
        rendered = {}
        if args.arm not in ("N0", "X1F-fake") or manifest_path is not None:
            # Real arms render the frozen pages; the fake backend needs no PNG
            # unless a manifest was provided for sha-keyed cache identity.
            if manifest_path is None and args.arm != "N0":
                raise SystemExit(f"arm {args.arm} requires --manifest")
            from .render_pages import render_pages

            for record in render_pages(manifest_path, Path(tmp) / "pages"):
                rendered[record["page_id"]] = record
        pages = []
        for pid in page_ids:
            rendered_page = rendered.get(pid) or {}
            page = {"page_id": pid}
            if rendered_page.get("png"):
                page["png"] = rendered_page["png"]
            if rendered_page.get("sha256"):
                page["png_sha256"] = rendered_page["sha256"]
            pages.append(page)
        result = run_campaign_batch(
            ledger_path=Path(args.ledger), ledger=ledger, arm=args.arm, pages=pages,
            cache_dir=args.cache_dir, max_new_tokens=args.max_new_tokens,
            weights_mode=args.weights_mode, model_dir=args.model_dir,
            manifest_path=manifest_path, fake_sleep_seconds=args.page_sleep,
        )
    out = Path(args.out) if args.out else None
    payload = {
        "schema_version": "cwp-ocr-campaign-batch/1",
        "arm": args.arm,
        "pages_selected": page_ids,
        "records": result["records"],
        "remaining_seconds": result["remaining_seconds"],
        "request_deadline": result["request_deadline"],
    }
    text = json.dumps(payload, ensure_ascii=False, indent=1)
    if out is not None:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
    else:
        print(text)
    return 0


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="W23-R1 campaign ledger and batches")
    sub = parser.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init", help="create the campaign ledger (once)")
    init.add_argument("--ledger", required=True)
    init.add_argument("--plan-id", default="w23-ocr-r1-2026-10-31")
    init.add_argument("--budget", type=float, default=1800.0)
    init.set_defaults(func=_cli_init)
    run = sub.add_parser("run", help="run one arm batch under the persistent ledger")
    run.add_argument("--ledger", required=True)
    run.add_argument("--arm", required=True,
                     choices=["X1F", "X1F-fake", "R0", "N0"])
    run.add_argument("--pages", default="all")
    run.add_argument("--manifest", default=None)
    run.add_argument("--cache-dir", default=None)
    run.add_argument("--max-new-tokens", type=int, default=4096)
    run.add_argument("--weights-mode", default="mapped-f32")
    run.add_argument("--model-dir", default=None)
    run.add_argument("--page-sleep", type=float, default=None,
                     help="fake backend page sleep seconds (X1F-fake only)")
    run.add_argument("--out", default=None)
    run.set_defaults(func=_cli_run)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
