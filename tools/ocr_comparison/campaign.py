"""One experiment ledger: atomic reservations, conservative unknowns and recovery.

Legacy entries remain historical facts. Short OS transactions serialize budget
allocation; inference runs outside the mutex. The existing ResultCache captures
outputs and a small completion marker before a reservation can be settled.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import tempfile
import time
from uuid import uuid4

UTC = timezone.utc
LEDGER_SCHEMA = "cwp-ocr-campaign-ledger/1"
REQUEST_DEADLINE_CAP_SECONDS = 180.0


class LedgerCorrupt(RuntimeError):
    """Unknown/corrupt accounting never renews an experiment budget."""


def _finite(value, *, minimum=0.0):
    try:
        return (not isinstance(value, bool) and isinstance(value, (int, float))
                and math.isfinite(value) and value >= minimum)
    except OverflowError:
        return False


def _atomic_write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=1, allow_nan=False)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


@contextmanager
def _lock(path: Path):
    from company_wiki._file_mutex import os_file_mutex
    path.parent.mkdir(parents=True, exist_ok=True)
    with os_file_mutex(path.with_name(path.name + ".lock"), timeout_seconds=10):
        yield


def create_ledger(path: str | Path, *, plan_id: str, budget_seconds: float) -> dict:
    path = Path(path)
    if not _finite(budget_seconds) or budget_seconds > 1800:
        raise ValueError("campaign budget must be finite and in [0, 1800]")
    if not isinstance(plan_id, str) or not plan_id.strip():
        raise ValueError("campaign plan_id must be nonempty")
    with _lock(path):
        if path.exists():
            raise FileExistsError(f"ledger already exists: {path}")
        ledger = {"schema_version": LEDGER_SCHEMA, "plan_id": plan_id,
                  "created_at_utc": datetime.now(UTC).isoformat(),
                  "budget_seconds": float(budget_seconds), "spent_seconds": 0.0,
                  "entries": [], "inflight": []}
        _atomic_write_json(path, ledger)
        return ledger


def load_ledger(path: str | Path) -> dict:
    try:
        ledger = json.loads(Path(path).read_text(encoding="utf-8"))
    except (ValueError, UnicodeError) as exc:
        raise LedgerCorrupt("ledger is not valid JSON") from exc
    if not isinstance(ledger, dict) or ledger.get("schema_version") != LEDGER_SCHEMA:
        raise LedgerCorrupt("ledger schema mismatch")
    budget, spent, entries = (ledger.get(key) for key in ("budget_seconds", "spent_seconds", "entries"))
    if not _finite(budget) or budget > 1800 or not _finite(spent):
        raise LedgerCorrupt("ledger resource values invalid")
    if not isinstance(entries, list) or not all(isinstance(row, dict) for row in entries):
        raise LedgerCorrupt("ledger entries invalid")
    if any(not _finite(row.get("seconds")) for row in entries):
        raise LedgerCorrupt("ledger entry seconds invalid")
    total = sum(float(row["seconds"]) for row in entries)
    if not math.isfinite(total) or abs(spent - total) > 1e-6:
        raise LedgerCorrupt("ledger spent does not equal entry sum")
    inflight = ledger.get("inflight", [])  # Existing historical ledgers are readable unchanged.
    if not isinstance(inflight, list):
        raise LedgerCorrupt("ledger inflight invalid")
    seen = set()
    for row in inflight:
        if (not isinstance(row, dict) or not isinstance(row.get("reservation_id"), str)
                or row["reservation_id"] in seen or not _finite(row.get("seconds")) or row["seconds"] <= 0
                or not isinstance(row.get("pages"), list) or not row["pages"]):
            raise LedgerCorrupt("ledger reservation invalid")
        seen.add(row["reservation_id"])
        for page in row["pages"]:
            if (not isinstance(page, dict) or not isinstance(page.get("key"), str)
                    or len(page["key"]) != 64 or any(c not in "0123456789abcdef" for c in page["key"])
                    or not isinstance(page.get("page_id"), str) or not page["page_id"]):
                raise LedgerCorrupt("ledger reservation page invalid")
    if sum(row["seconds"] for row in inflight) > max(0, budget - spent) + 1e-6:
        raise LedgerCorrupt("ledger reservations exceed available budget")
    return ledger


def remaining_seconds(ledger: dict) -> float:
    return max(0.0, float(ledger["budget_seconds"]) - float(ledger["spent_seconds"])
               - sum(float(row["seconds"]) for row in ledger.get("inflight", ())))


def request_budget(ledger: dict) -> float:
    return min(REQUEST_DEADLINE_CAP_SECONDS, remaining_seconds(ledger))


def _resource_cost_unknown(ledger):
    # Absence of a new field is not a permission gate. Only observed real
    # inference rows with zero cost and no transactional charge provenance are
    # unknown; N0/not-started/cache observations and complete old costs are safe.
    return any(row.get("arm") in {"R0", "X1F", "X1"}
               and row.get("status") not in {"not_run", "cache_hit"}
               and row["seconds"] == 0 and not row.get("reservation_id")
               and not row.get("cache_hit") for row in ledger["entries"])


def _entry(ledger, *, arm, page_id, seconds, status, **extra):
    ledger["entries"].append({"ts_utc": datetime.now(UTC).isoformat(), "arm": arm,
                              "page_id": page_id, "seconds": float(seconds), "status": status, **extra})
    ledger["spent_seconds"] = sum(row["seconds"] for row in ledger["entries"])


def record(ledger: dict, path: str | Path, *, arm: str, page_id: str, seconds: float, status: str) -> dict:
    if not _finite(seconds):
        raise ValueError("seconds must be finite and nonnegative")
    path = Path(path)
    with _lock(path):
        current = load_ledger(path)  # Never allocate against a caller's stale snapshot.
        if seconds > remaining_seconds(current) + 1e-9:
            raise ValueError("entry would exceed budget")
        _entry(current, arm=arm, page_id=page_id, seconds=seconds, status=status)
        _atomic_write_json(path, current)
    ledger.clear()
    ledger.update(current)
    return ledger


def seconds_to_charge(record: dict, deadline_seconds: float) -> float:
    elapsed = record.get("request_seconds")
    if elapsed is not None:
        if not _finite(elapsed):
            raise ValueError("runner elapsed must be finite and nonnegative")
        return float(elapsed)
    return float(deadline_seconds) if record.get("status") in {"timeout", "no_record", "error"} else 0.0


def _reservation(ledger, arm, pages, seconds):
    row = {"reservation_id": uuid4().hex, "arm": arm, "seconds": seconds,
           "created_at_utc": datetime.now(UTC).isoformat(), "pages": pages}
    ledger.setdefault("inflight", []).append(row)
    return row


def _finalize_reservation(ledger, reservation, completion):
    """Only durable cache completion proof can release an in-flight hold."""
    rows = completion["settlements"]
    expected = {(p["key"], p["page_id"]) for p in reservation["pages"]}
    if (completion.get("reservation_id") != reservation["reservation_id"]
            or len(rows) != len(expected)
            or {(r.get("key"), r.get("page_id")) for r in rows} != expected
            or any(not _finite(r.get("seconds")) for r in rows)):
        raise LedgerCorrupt("captured completion does not bind its reservation")
    ledger["inflight"].remove(reservation)
    for row in rows:
        _entry(ledger, arm=reservation["arm"], page_id=row["page_id"], seconds=row["seconds"],
               status=row["status"], cache_key=row["key"], reservation_id=reservation["reservation_id"],
               charge_basis=row["basis"])


def _recover(ledger, cache):
    changed = False
    for reservation in list(ledger.get("inflight", ())):
        completion = cache.get("reservation_" + reservation["reservation_id"])
        if completion is None:
            continue
        rows = completion.get("settlements", ())
        # A marker without its captured output is not evidence of a completed run.
        if any(row.get("status") != "not_run" and (
                (cached := cache.get(row.get("key", ""))) is None
                or cached.get("campaign_reservation_id") != reservation["reservation_id"])
               for row in rows):
            continue
        _finalize_reservation(ledger, reservation, completion)
        changed = True
    return changed


def _prepare(path, cache, arm, keyed, *, batch):
    with _lock(path):
        ledger = load_ledger(path)
        if _recover(ledger, cache):
            _atomic_write_json(path, ledger)
        available, missing = {}, []
        completed = {row.get("cache_key") for row in ledger["entries"] if row["status"] != "not_run"}
        pending = {page["key"] for row in ledger.get("inflight", ()) for page in row["pages"]}
        for page, key in keyed:
            hit = cache.get(key)
            if hit is not None:
                available[key] = {**hit, "page_id": page["page_id"]}
                continue
            reason = ("inference_outcome_unknown" if key in pending else
                      "captured_result_unavailable" if key in completed else
                      "prior_inference_cost_unknown" if _resource_cost_unknown(ledger) else
                      "budget_exhausted" if remaining_seconds(ledger) <= 0 else
                      "campaign_inflight" if ledger.get("inflight") else None)
            if reason is None:
                if key not in {row[1] for row in missing}:
                    missing.append((page, key))
                continue
            available[key] = {"page_id": page["page_id"], "status": "not_run", "error": reason,
                              "request_seconds": 0.0, "inference_runs": 0}
            if reason == "budget_exhausted" and not any(row.get("cache_key") == key for row in ledger["entries"]):
                _entry(ledger, arm=arm, page_id=page["page_id"], seconds=0, status="not_run", cache_key=key)
                _atomic_write_json(path, ledger)
        reservation = None
        if missing:
            seconds = remaining_seconds(ledger) if batch else request_budget(ledger)
            reservation = _reservation(ledger, arm, [{"page_id": p["page_id"], "key": k} for p, k in missing], seconds)
            _atomic_write_json(path, ledger)  # Durable before any model/runner invocation.
        return available, missing, reservation


def _capture(path, cache, reservation, records, *, wall_seconds=0.0):
    indexed = {row["page_id"]: row for row in records}
    if len(indexed) != len(records):
        raise ValueError("runner returned duplicate page records")
    settlements = []
    unknown = None
    for page in reservation["pages"]:
        row = indexed.get(page["page_id"], {"page_id": page["page_id"], "status": "no_record"})
        if row.get("status") == "not_run":
            seconds = 0.0
        elif row.get("request_seconds") is None:
            seconds = 0.0
            unknown = page["key"]
        else:
            seconds = seconds_to_charge(row, 0.0)
        settlements.append({"key": page["key"], "page_id": page["page_id"], "seconds": seconds,
                            "status": row.get("status", "no_record"), "basis": "observed_request"})
        indexed[page["page_id"]] = row
    total = sum(row["seconds"] for row in settlements)
    required = max(total, wall_seconds, reservation["seconds"] if unknown else 0.0)
    if not _finite(required):
        raise ValueError("runner wall duration must be finite")
    recipient = next((row for row in settlements if row["key"] == unknown), settlements[0])
    recipient["seconds"] += required - total
    if required > total:
        recipient["basis"] = "unknown_reservation" if unknown else "observed_batch_wall"
    completion = {"reservation_id": reservation["reservation_id"], "settlements": settlements}
    with _lock(path):
        ledger = load_ledger(path)
        current = next(row for row in ledger["inflight"] if row["reservation_id"] == reservation["reservation_id"])
        for page in reservation["pages"]:
            row = indexed[page["page_id"]]
            if row["status"] != "not_run":
                cache.put(page["key"], {**row, "campaign_reservation_id": reservation["reservation_id"]})
        cache.put("reservation_" + reservation["reservation_id"], completion)
        _finalize_reservation(ledger, current, completion)
        _atomic_write_json(path, ledger)
    return indexed


def _batch_result(path, records, deadline):
    from .runner import batch_summary
    current = load_ledger(path)
    accounting_complete = not current.get("inflight") and not _resource_cost_unknown(current)
    resource_exceeded = current["spent_seconds"] > current["budget_seconds"]
    return {"records": records, "remaining_seconds": remaining_seconds(current),
            "request_deadline": deadline,
            "unresolved_reservations": len(current.get("inflight", ())),
            "known_spent_seconds": current["spent_seconds"],
            "accounting_complete": accounting_complete,
            "resource_limit_exceeded": resource_exceeded,
            "execution_status": batch_summary(records)["batch_status"] if accounting_complete and not resource_exceeded else "partial"}


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


def run_campaign_batch(*, ledger_path: Path, ledger: dict, arm: str, pages: list[dict],
                       cache_dir: str | Path | None = None, max_new_tokens: int = 4096,
                       weights_mode: str = "mapped-f32", model_dir: str | None = None,
                       manifest_path: str | Path | None = None,
                       fake_sleep_seconds: float | None = None) -> dict:
    """The ledger argument is a compatibility snapshot, never an allocation.

    Every allocation rereads the single durable owner under its short mutex;
    inference executes outside that mutex. Cache uses the nominal request cap,
    while captured records/receipts retain the smaller effective deadline.
    """
    from .cache import ResultCache, cache_key
    path = Path(ledger_path)
    if (not isinstance(max_new_tokens, int) or isinstance(max_new_tokens, bool) or max_new_tokens < 1
            or (fake_sleep_seconds is not None and not _finite(fake_sleep_seconds))):
        raise ValueError("runner limits must be finite and nonnegative")
    ids = [p["page_id"] for p in pages]
    if len(ids) != len(set(ids)) or not all(isinstance(pid, str) and pid for pid in ids):
        raise ValueError("campaign pages require unique nonempty IDs")
    cache = ResultCache(cache_dir)
    starting = load_ledger(path)
    request_deadline = request_budget(starting)
    if arm == "N0":
        from .backends.native_n0 import NativeN0
        candidate = Path(manifest_path).parent / "r1_gold.json" if manifest_path else None
        backend = NativeN0(manifest_path, gold_path=candidate if candidate and candidate.is_file() else None)
        records = []
        for page in pages:
            rec = {**backend.run_page(page["page_id"]), "page_id": page["page_id"]}
            rec.setdefault("request_seconds", 0.0)
            records.append(rec)
            record(starting, path, arm=arm, page_id=page["page_id"], seconds=0, status=rec.get("status", "unknown"))
        return _batch_result(path, records, request_deadline)
    if arm == "X1F-fake":
        backend = FakePageBackend(0.3 if fake_sleep_seconds is None else fake_sleep_seconds)
        identity = {"arm": arm, "sleep": fake_sleep_seconds}
    elif arm == "R0":
        from .backends.rapidocr_r0 import RapidOCRR0, load_production_config
        config = load_production_config(REPO_ROOT / "config" / "local_ocr.json")
        backend = RapidOCRR0(config, deadline_seconds=REQUEST_DEADLINE_CAP_SECONDS)
        identity = backend.identity_manifest
    elif arm == "X1F":
        from .run_x1 import run_x1_batch, _model_dir
        from .backends.xiaomi_x1 import XiaomiX1
        model = _model_dir(model_dir)
        identity = XiaomiX1(model_dir=str(model), deadline_seconds=REQUEST_DEADLINE_CAP_SECONDS,
                            max_new_tokens=max_new_tokens, weights_mode=weights_mode).identity_manifest
    else:
        raise ValueError(f"unknown campaign arm: {arm}")

    def keyed(page):
        image = page.get("png_sha256") or page.get("sha256")
        if image is None:
            if arm == "X1F-fake":
                image = page["page_id"]
            else:
                from .manifest import sha256_file
                image = sha256_file(Path(page["png"]))
        return page, cache_key(identity, image, identity.get("prompt_sha256", "n/a"),
                               {"request_deadline_cap": REQUEST_DEADLINE_CAP_SECONDS,
                                "max_new_tokens": max_new_tokens, "campaign_contract": "reservation/1"})

    pairs = [keyed(page) for page in pages]
    outputs = {}
    batches = [pairs] if arm == "X1F" else [[pair] for pair in pairs]
    for group in batches:
        available, missing, reservation = _prepare(path, cache, arm, group, batch=arm == "X1F")
        outputs.update(available)
        if reservation is None:
            continue
        elapsed_start = time.perf_counter()
        if arm == "X1F":
            deadline = min(REQUEST_DEADLINE_CAP_SECONDS, reservation["seconds"])
            result = run_x1_batch([p for p, _ in missing], deadline=deadline,
                                  total_budget=reservation["seconds"], max_new_tokens=max_new_tokens,
                                  weights_mode=weights_mode, model_dir=str(model), backend_identity=identity)
            if result.get("identity") != identity:
                raise ValueError("runner identity differs from its cache recipe")
            child_wall = result.get("receipt", {}).get("child", {}).get("wall_seconds", 0.0)
            if not _finite(child_wall):
                raise ValueError("runner wall duration must be finite and nonnegative")
            wall = max(time.perf_counter() - elapsed_start, child_wall)
            for row in result["records"]:
                row["effective_deadline_seconds"] = deadline
                row["requested_deadline_cap_seconds"] = REQUEST_DEADLINE_CAP_SECONDS
            receipt_dir = path.parent / "receipts"
            receipt_dir.mkdir(exist_ok=True)
            _atomic_write_json(receipt_dir / (reservation["reservation_id"] + ".json"), result.get("receipt", {}))
            captured = _capture(path, cache, reservation, result["records"], wall_seconds=wall)
        else:
            page = missing[0][0]
            deadline = reservation["seconds"]
            if arm == "X1F-fake":
                rec = backend.run_page(page["page_id"], page.get("png"), deadline_seconds=deadline)
                # The explicit fake models requested sleep as simulated cost;
                # retain the actual wall separately, not as real model timing.
                rec["wall_seconds"] = rec["request_seconds"]
                rec["request_seconds"] = min(backend.sleep_seconds, deadline)
                rec["measurement_scope"] = "simulated-inference-time"
            else:
                backend.deadline_seconds = deadline
                rec = backend.run_page(page["png"])
                rec.setdefault("request_seconds", time.perf_counter() - elapsed_start)
            rec["page_id"] = page["page_id"]
            captured = _capture(path, cache, reservation, [rec],
                                wall_seconds=0.0 if arm == "X1F-fake" else time.perf_counter() - elapsed_start)
        for page, key in missing:
            outputs[key] = captured[page["page_id"]]
    return _batch_result(path, [{**outputs[key], "page_id": page["page_id"]} for page, key in pairs], request_deadline)


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
        "unresolved_reservations": result["unresolved_reservations"],
        "known_spent_seconds": result["known_spent_seconds"],
        "accounting_complete": result["accounting_complete"],
        "resource_limit_exceeded": result["resource_limit_exceeded"],
        "execution_status": result["execution_status"],
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
