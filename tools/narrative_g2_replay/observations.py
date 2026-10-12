"""Actual evidence observations for the manual G2 replay, never a product engine."""
from __future__ import annotations

import copy
import hashlib
import json
import math
from pathlib import Path
import time


def remaining_seconds(deadline: float, *, now: float | None = None) -> float:
    remaining = deadline - (time.monotonic() if now is None else now)
    if not math.isfinite(remaining) or remaining <= 0:
        raise TimeoutError("whole G2 replay deadline exhausted")
    return remaining


def source_posts(requests: list[dict], source_id: str) -> int:
    return sum(row.get("data", {}).get("source", {}).get("source_id") == source_id
               for row in requests)


def read_observations(spec, bundle: dict, receipt: dict, fixture: dict,
                      manifest: dict) -> dict:
    spans = bundle.get("evidence_spans") or []
    claims = ((bundle.get("summary") or {}).get("draft") or {}).get("claims") or []
    selected_text = "".join("".join((span.get("raw_text") or "").split()) for span in spans)
    required = "".join((spec.required_span_text or "").split())
    selected_ids = {span.get("span_id") for span in spans}
    cited = bool(claims) and all(
        bool(claim.get("evidence_ids")) and set(claim["evidence_ids"]) <= selected_ids
        for claim in claims)
    forbidden = any(text in (claim.get("text") or "")
                    for text in spec.forbidden_summary_text for claim in claims)
    is_skip = spec.expectation == "skip"
    return {
        "locator_verified": bool(spans) and receipt.get("replay_status") == "verified"
            and receipt.get("locator_count") == len(spans)
            and bundle.get("source_ref", {}).get("content_sha256") == fixture["content_sha256"],
        "required_fact_present": not required or required in selected_text,
        "summary_supported": not forbidden and (not claims if is_skip else cited),
        "period_preserved": all(manifest.get(key) == fixture.get(key)
                                for key in ("fiscal_year", "fiscal_period", "period_end")),
    }


def save_bytes(attempt: Path, relative: str, payload: bytes) -> str:
    path = attempt / relative
    assert path.resolve().is_relative_to(attempt.resolve())
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return hashlib.sha256(payload).hexdigest()


def invalidation_checks(*, lake, model, env, attempt, bounded, original_request,
                        original_pins) -> list[dict]:
    """Real public batch on a new TXT version, then changed model generation spec.

    The original is immutable. A separate synthetic successor is registered by
    the same public scanner; no DB rows or valid pins are hand manufactured.
    """
    from tools.narrative_g2_replay import run
    info = lake.indexed["call-txt-en"]
    original = lake.root / info["fixture"]["path_ref"]
    original_bytes = original.read_bytes()
    successor = original.with_name("w08-call-en-v2.txt")
    assert not successor.exists()
    successor.write_bytes(original_bytes + b"CEO: We launched another product for overseas customers.\n")
    digest = hashlib.sha256(successor.read_bytes()).hexdigest()
    sidecar = json.loads(original.with_name(original.name + ".source.json").read_text(encoding="utf-8"))
    sidecar.update(content_sha256=digest)
    successor.with_name(successor.name + ".source.json").write_text(
        json.dumps(sidecar, ensure_ascii=False), encoding="utf-8")
    lake.catalog.scan()
    row = lake.catalog.reader.fetchone(
        "SELECT d.document_id,d.primary_source_id AS source_id FROM documents d "
        "JOIN sources s ON s.source_id=d.primary_source_id WHERE s.content_sha256=?", (digest,))
    if row is None:
        raise RuntimeError("successor not registered by canonical scan")
    ref = lake.reader.query_ref(row["document_id"], row["source_id"], digest)
    wire = {key: getattr(ref, key) for key in ("schema_version", "document_id", "source_id",
                                             "content_sha256", "byte_size", "mime_type")}
    old_pin = original_pins[info["ref"].document_id]
    previous_pin = old_pin
    results = []
    for index, kind in enumerate(("source-version", "model-spec"), start=3):
        request = copy.deepcopy(original_request)
        request.update(run_id=f"w08-g2-invalidation-{index}", sources=[wire], max_seconds=bounded())
        if kind == "model-spec":
            request["model"]["max_output_tokens"] += 1
        path = lake.root.parent / "requests" / f"run{index}.json"
        path.write_text(json.dumps(request, ensure_ascii=False), encoding="utf-8")
        save_bytes(attempt, f"requests/run{index}.json", path.read_bytes())
        before = model.post_count
        process = run.invoke_batch(lake, request_path=path, run_id=request["run_id"],
                                   work_dir=lake.root.parent / f"work-run{index}", env=env,
                                   timeout_seconds=bounded())
        save_bytes(attempt, f"receipts/run{index}.json", process.stdout)
        receipt, error = run.parse_receipt(process)
        document = run.document_by_id(receipt or {}).get(ref.document_id, {})
        pin = document.get("artifact_ref")
        public = run.read_public_artifact(lake, pin, env, timeout_seconds=bounded()) if pin else {}
        public_receipt = public.get("receipt") or {}
        ok = (process.returncode == 0 and error is None and model.post_count-before == 1
              and pin is not None and pin != previous_pin and pin["source_sha256"] == digest
              and public.get("body_matches_pin") is True and public_receipt.get("replay_status") == "verified"
              and original.read_bytes() == original_bytes)
        results.append({"kind": kind, "status": "PASS" if ok else "FAIL",
                        "run_index": index, "model_posts": model.post_count-before,
                        "exit_code": process.returncode, "source_sha256": digest,
                        "pin_changed": pin != previous_pin, "original_unchanged": original.read_bytes() == original_bytes,
                        "public_receipt": public_receipt, "receipt_ref": f"receipts/run{index}.json"})
        previous_pin = pin
    return results
