"""Worker: runs inside the producer import environment (frozen deploy).

One process handles one sample. It performs, in order:

1. import-root proof (company_wiki must resolve under the producer repo);
2. a read-only native observation of the real parser/selector (DU-BENCH
   ``observer.observe_native``) against the SHA-verified original;
3. an optional zero-POST scoped model-view compile through the configured
   production chain (``holdout_acceptance_contracts.configured_preview``);
4. per-target mechanical visibility against the frozen gold and the compiled
   task material, plus the DU-BENCH evaluation of the observation.

No model POST, no network, no writes outside the attempt directory.
"""
from __future__ import annotations

import hashlib
import inspect
import time
import json
import re
import sys
from pathlib import Path
from typing import Any


def _flexible(quote: str) -> re.Pattern[str]:
    chars = [re.escape(c) for c in quote if not c.isspace()]
    return re.compile(r"\s*".join(chars))


def _collect_text(value: Any) -> str:
    parts: list[str] = []
    if isinstance(value, str):
        parts.append(value)
    elif isinstance(value, dict):
        for item in value.values():
            parts.append(_collect_text(item))
    elif isinstance(value, (list, tuple)):
        for item in value:
            parts.append(_collect_text(item))
    return "\n".join(parts)


def _task_texts(material: dict[str, Any]) -> dict[str, str]:
    tasks = material.get("tasks")
    if not isinstance(tasks, list):
        material_text = _collect_text(material)
        return {"<material>": material_text}
    rows = {}
    for task in tasks:
        if isinstance(task, dict) and task.get("key"):
            rows[str(task["key"])] = _collect_text(task)
    if not rows:
        return {"<material>": _collect_text(material)}
    return rows


def _model_view_report(body: bytes) -> dict[str, Any]:
    """Summarize the compiled wire body without sending it anywhere."""
    envelope = json.loads(body)
    data = envelope["messages"][1]["content"]
    data_obj = json.loads(data) if isinstance(data, str) else data
    material = data_obj.get("material", {}) if isinstance(data_obj, dict) else {}
    tasks = _task_texts(material)
    return {
        "wire_schema": envelope.get("model") and "ok",
        "request_schema": data_obj.get("schema_version") if isinstance(data_obj, dict) else None,
        "material_schema": material.get("schema_version"),
        "task_count": len(tasks) - (1 if "<material>" in tasks else 0),
        "material_bytes": len(data.encode("utf-8")) if isinstance(data, str) else len(json.dumps(data_obj)),
        "task_keys": sorted(tasks),
        "tasks": tasks,
        "request_sent": False,
        "response_reviewed": False,
        "summary_status": "not_reviewed",
    }


def _anchor_visibility(gold: dict[str, Any], observed: dict[str, Any],
                       tasks: dict[str, str] | None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    selected = observed.get("selected_evidence") or []
    read_pages = (observed.get("coverage") or {}).get("read_pages")
    opaque = set((observed.get("coverage") or {}).get("opaque_pages") or [])
    for fact in gold.get("facts", []):
        anchors_out = []
        for group in fact.get("any_support_sets", []):
            for anchor in group:
                quote = anchor.get("exact_quote", "")
                pattern = _flexible(quote)
                page = anchor.get("page")
                matching_rows = []
                for row in selected:
                    if page is not None and row.get("page") != page:
                        continue
                    if pattern.search(row.get("text") or ""):
                        matching_rows.append(row.get("locator"))
                task_hits = []
                if tasks is not None:
                    task_hits = sorted(key for key, text in tasks.items() if pattern.search(text))
                anchors_out.append({
                    "quote_head": quote[:40],
                    "page": page,
                    "on_read_page": (
                        True if page is None
                        else (None if read_pages is None else page in read_pages)
                    ),
                    "page_opaque": page in opaque if page is not None else None,
                    "selected_locators": matching_rows,
                    "model_input_task_keys": task_hits,
                })
        rows.append({
            "fact_id": fact.get("id"),
            "target_kind": fact.get("target_kind", "required_business"),
            "importance": fact.get("importance"),
            "anchors": anchors_out,
            "summary_status": "not_reviewed",
        })
    return rows


def _native_observation(path: Path, sample: dict[str, Any], *,
                        selector_version: str = "0.9.0") -> dict[str, Any]:
    from tools.document_understanding_benchmark.observer import observe_native
    ports = inspect.signature(observe_native).parameters
    supports_selector = "selector_version" in ports
    result = observe_native(
        Path(path), sha256=sample["source_ref"]["content_sha256"],
        sample_id=sample["sample_id"], existing_kind=sample.get("document_kind", "unknown"),
        **({"selector_version": selector_version} if supports_selector else {}),
        **({"language": sample.get("language", "zh")} if "language" in ports else {}),
    )
    execution = result.setdefault("execution", {})
    execution["requested_selector_version"] = selector_version
    if not supports_selector:
        execution["compatibility_reason"] = "producer_observer_has_no_selector_port"
    return result


def _compile_model_view(spec: dict[str, Any], sample: dict[str, Any],
                        run_id: str, selector_version: str = "0.9.0") -> tuple[bytes, dict[str, Any]]:
    from tools.document_understanding_benchmark.holdout_acceptance_contracts import (
        configured_preview,
    )
    raw_request = {
        "schema_version": "narrative-batch-request/1",
        "run_id": run_id,
        "sources": [dict(sample["source_ref"])],
        "profile": "P1",
        "max_seconds": 900,
        "max_tokens": 8192,
        "max_cost_usd": "0",
        "model": {"model_id": "w18-preview", "endpoint": "http://127.0.0.1:9/never-sent",
                  "api_key_env": "W18_UNUSED_KEY"},
        "pricing": {"version": "w18-zero-post-preview/1",
                    "input_micro_usd_per_million_tokens": 0,
                    "output_micro_usd_per_million_tokens": 0},
        "selector_version": selector_version,
        "reading_model_projection": "reading-model-input/4",
    }
    return configured_preview(spec, raw_request)


def _selector_versions(compile_selector_version: str) -> dict[str, Any]:
    """Record which selector generation each replay path actually uses.

    The producer default is historical configuration, not execution proof.
    run_job stamps observe_path_actual from the observed execution receipt;
    compatible old producers explicitly retain their historical entry point.
    The compile path pins the requested scoped projection selector.
    """
    from company_wiki.source_catalog import narrative_evidence
    return {
        "observe_path_default": getattr(narrative_evidence, "NARRATIVE_SELECTOR_VERSION", None),
        "compile_path_pinned": compile_selector_version,
    }


def run_job(job: dict[str, Any]) -> dict[str, Any]:
    producer_root = Path(job["producer_root"])
    from tools.holdout_replay import producer as producer_mod
    roots = producer_mod.record_import_roots(producer_root)
    producer_mod.assert_imports_from_producer(roots, producer_root)

    sample = job["sample"]
    gold = job["gold"]
    path = Path(job["original_path"])
    result: dict[str, Any] = {
        "schema_version": "w18-holdout-sample-result/1",
        "sample_id": sample["sample_id"],
        "producer_commit": job["producer_commit"],
        "import_roots": roots,
        "original_before_sha256": job["original_sha256"],
    }
    phase_start = time.monotonic()
    observed = _native_observation(path, sample,
        selector_version=job.get("compile_selector_version", "0.9.0"))
    result["phase_seconds"] = {"source_observation": round(time.monotonic() - phase_start, 3)}
    result["native_observed"] = observed
    result["selector_versions"] = _selector_versions(
        job.get("compile_selector_version", "0.9.0"))

    result["selector_versions"]["observe_path_actual"] = observed.get("execution", {}).get("selector_version")

    compile_spec = job.get("compile_spec")
    tasks: dict[str, str] | None = None
    model_view: dict[str, Any] = {"status": "not_attempted"}
    if compile_spec:
        phase_start = time.monotonic()
        try:
            body, facts = _compile_model_view(
                compile_spec, sample, job.get("run_id", sample["sample_id"]),
                selector_version=job.get("compile_selector_version", "0.9.0"))
            report = _model_view_report(body)
            tasks = report.pop("tasks")
            report.update(facts)
            model_view = {"status": "compiled", "wire_body_sha256": hashlib.sha256(body).hexdigest(),
                          **report}
        except Exception as exc:  # noqa: BLE001 - record the raw failure reason
            model_view = {"status": "failed", "reason": f"{type(exc).__name__}: {exc}"[:500]}
        result["phase_seconds"]["model_view_compile"] = round(time.monotonic() - phase_start, 3)
    result["model_view"] = model_view

    result["targets"] = _anchor_visibility(gold, observed, tasks)
    try:
        from tools.document_understanding_benchmark import evaluate
        result["evaluation"] = evaluate(observed, gold)
    except Exception as exc:  # noqa: BLE001 - evaluation failure is a finding, not a crash
        result["evaluation"] = {"status": "failed", "reason": f"{type(exc).__name__}: {exc}"[:500]}

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    result["original_after_sha256"] = digest.hexdigest()
    result["original_unchanged"] = (
        result["original_after_sha256"] == result["original_before_sha256"]
    )
    return result


def main(argv: list[str] | None = None) -> int:
    args = list(argv if argv is not None else sys.argv[1:])
    if len(args) != 2:
        print("usage: python -m tools.holdout_replay.worker <job.json> <result.json>", file=sys.stderr)
        return 2
    job = json.loads(Path(args[0]).read_text(encoding="utf-8"))
    result = run_job(job)
    with Path(args[1]).open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(result, ensure_ascii=False, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
