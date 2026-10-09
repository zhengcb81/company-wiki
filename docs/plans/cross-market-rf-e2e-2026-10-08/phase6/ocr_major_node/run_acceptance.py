"""Prepare or execute the finite MAIN OCR composition acceptance node.

preflight is free: hashes, pure contracts and real CLI --help only. run/resume
may send a real provider request. No transport is mocked or replaced here.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
import uuid

DECK_SHA = "c02f4ea1a2719b74d5752559ad7b907d89dd4b47d292424ade8988396fb2dcd4"
DECK_SIZE = 4_016_522
PPTX = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
SCHEMA = "main-ocr-major-node/1"
TERMINAL = {"succeeded", "dead_letter", "cancelled", "blocked_human"}


class CheckFailed(Exception):
    pass


def require(condition, code):
    if not condition:
        raise CheckFailed(code)


def now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save(path, value):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def file_identity(path):
    path = Path(path)
    st = path.stat()
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return {"path": str(path.resolve()), "sha256": digest.hexdigest(),
            "byte_size": st.st_size, "mtime_ns": st.st_mtime_ns}


def protected(project):
    names = ("config.yaml", "config/source_catalog.yaml", "config/local_ocr.json", ".env",
             "docs/plans/cross-market-rf-e2e-2026-10-08/task_plan.md",
             "docs/plans/cross-market-rf-e2e-2026-10-08/findings.md",
             "docs/plans/cross-market-rf-e2e-2026-10-08/progress.md",
             "docs/plans/cross-market-rf-e2e-2026-10-08/phase6/main_budget_preparation.json")
    return {name: file_identity(project / name) if (project / name).is_file() else None
            for name in names}


def source_from_index(project):
    cases = load(project / "benchmarks/cross_market_rf/cases.json")
    case = next(c for c in cases["cases"] if c["case"] == "US-MSFT")
    selected = [s for s in case["sources"] if s["sha256"] == DECK_SHA]
    require(len(selected) == 1, "archive_case_not_unique")
    source = selected[0]
    index_path = project / cases["audit_index"]
    index = load(index_path)
    matches = [a for a in index["artifacts"]
               if a.get("sha256") == DECK_SHA and a.get("byte_size") == DECK_SIZE
               and a.get("storage") == "retained_object"
               and a.get("relative_path") == "US-MSFT/" + source["filename"]]
    require(len(matches) == 1, "archive_object_not_unique")
    archive = Path(matches[0]["archive_path"]).resolve()
    durable = Path(index["durable_output_root"]).resolve()
    require(archive.is_relative_to(durable / "objects"), "archive_outside_object_root")
    require(archive == (durable / source["object_relative"]).resolve(), "archive_index_binding")
    observed = file_identity(archive)
    require(observed["sha256"] == DECK_SHA and observed["byte_size"] == DECK_SIZE,
            "archive_bytes_changed")
    require(source["published_date"] == "2026-09-02", "publication_metadata_changed")
    return {"archive_index": file_identity(index_path), "original": observed,
            "filename": source["filename"], "title": source["title"],
            "url": source["url"], "published_date": source["published_date"],
            "entity": case["company_name"], "market": case["market"],
            "security_id": case["security_id"]}


def environment(project, root, config):
    # The actual loader supplies secrets in memory. Never serialize config._raw.
    env = os.environ.copy()
    env["PYTHONPATH"] = str(project / "src")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHON_DOTENV_DISABLED"] = "1"
    env["WIKI_ROOT"] = str(root)
    env[config.llm.api_key_env] = config.llm.api_key
    if config.search.api_key:
        env["TAVILY_API_KEY"] = config.search.api_key
    return env


def execute(root, name, command, env, *, stdin=None, timeout=45):
    log = root / "logs"
    log.mkdir(exist_ok=True)
    # Preserve each real invocation, including repeated native resume attempts.
    serial = len(list(log.glob(name + "-*.command.json"))) + 1
    stem = log / f"{name}-{serial:02d}"
    started = now()
    tick = time.monotonic()
    timed_out = False
    with Path(str(stem) + ".stdout").open("wb") as out, Path(str(stem) + ".stderr").open("wb") as err:
        process = subprocess.Popen(command, cwd=root, env=env, stdin=subprocess.PIPE,
                                   stdout=out, stderr=err)
        try:
            process.communicate(None if stdin is None else json.dumps(stdin).encode(), timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            # A hard outer stop also fences the worker subprocess tree on Windows.
            if os.name == "nt":
                subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
            else:
                process.kill()
            process.wait(timeout=20)
    result = {"command": command, "started_at": started, "finished_at": now(),
              "elapsed_seconds": round(time.monotonic() - tick, 3),
              "exit_code": process.returncode, "outer_timeout": timed_out,
              "stdout": file_identity(str(stem) + ".stdout"),
              "stderr": file_identity(str(stem) + ".stderr"),
              "stdin_sha256": None if stdin is None else hashlib.sha256(json.dumps(stdin).encode()).hexdigest()}
    save(str(stem) + ".command.json", result)
    require(not timed_out and process.returncode == 0, name + "_cli_failed")
    return Path(str(stem) + ".stdout"), Path(str(stem) + ".stderr"), result


def batch_request(run_id, source_ref, model, *, reuse=False):
    return {"schema_version": "narrative-batch-request/1", "run_id": run_id,
            "sources": [source_ref], "profile": "P1", "max_seconds": 600,
            "max_tokens": 1 if reuse else 30_000, "max_cost_usd": "0" if reuse else "0.1",
            "model": model,
            "pricing": {"version": "main-ocr-r3-conservative/1",
                        "input_micro_usd_per_million_tokens": 333_334,
                        "output_micro_usd_per_million_tokens": 1_333_334},
            "max_final_bytes": 2 * 1024 * 1024,
            "max_persistent_bytes": 128 * 1024 * 1024,
            "max_scratch_bytes": 256 * 1024 * 1024}


def official_request(attempt, source):
    return {"schema_version": "official-source-import-request/1",
            "request_id": attempt + "-import",
            "source": {"entity": source["entity"], "market": source["market"],
                       "security_id": source["security_id"], "document_kind": "investor_relations",
                       "title": source["title"], "publisher": source["entity"], "source_url": source["url"],
                       "published_date": source["published_date"], "fiscal_year": None,
                       "fiscal_period": None, "language": None},
            "content_sha256": DECK_SHA, "mime_type": PPTX, "max_bytes": DECK_SIZE,
            "capture_receipt": {"capture_method": "local_document", "tool_name": "main-ocr-archive-local-copy",
                                "tool_call_id": attempt + "-archive-observation", "captured_at": now(),
                                "response_bytes": DECK_SIZE, "content_sha256": DECK_SHA}}


def prepare(project, root, attempt):
    from config import Config
    from company_wiki.automation.narrative_http_model import model_options_from_config
    from company_wiki.document_normalization import LocalOCRConfig
    from company_wiki.source_catalog.config import load_catalog_config

    source = source_from_index(project)
    baseline_path = project / "docs/plans/cross-market-rf-e2e-2026-10-08/phase6/main_budget_preparation.json"
    baseline = load(baseline_path)
    require(baseline["ocr_major_node_separate_cap_tokens"] == 30_000
            and baseline["ocr_major_node_separate_cap_micro_usd"] == 100_000,
            "approved_major_node_budget_changed")
    require(baseline["double_counted_native"] is False, "historical_budget_double_counted")
    require(baseline["remaining_tokens"] >= 30_000
            and baseline["remaining_micro_usd_after_fx"] >= 100_000, "cumulative_budget_insufficient")
    ocr_payload = load(project / "config/local_ocr.json")
    ocr = LocalOCRConfig.from_dict(ocr_payload)
    models = {}
    for kind in ("det", "cls", "rec"):
        resource = getattr(ocr, kind)
        resource.verify()  # SHA only; no initialization, OCR, fetch or download.
        models[kind] = file_identity(resource.path)
    config = Config.load(llm_provider="deepseek")
    require(config.llm.provider == "deepseek", "configured_provider_not_deepseek")
    model = model_options_from_config(config.llm)
    require(model["endpoint"].startswith("https://"), "non_https_configured_model")
    (root / "companies").mkdir()
    (root / "config").mkdir()
    (root / "auto").mkdir()
    (root / "requests").mkdir()
    save(root / "config/local_ocr.json", ocr_payload)
    save(root / "config/source_catalog.yaml", {
        "schema_version": "1.0", "catalog_dir": str(root / "catalog"),
        "roots": [{"root_id": "main_ocr_owned", "path": str(root / "companies"),
                   "kind": "company_raw", "read_only": False, "reusable_for_filing": False}]})
    # JSON is valid YAML. Explicit owned config retains actual selected settings.
    save(root / "config.yaml", {"llm": {"provider": "deepseek", "model": config.llm.model,
         "base_url": config.llm.base_url, "max_tokens": config.llm.max_tokens,
         "max_document_chars": config.llm.max_document_chars,
         "temperature": config.llm.temperature, "reasoning_split": config.llm.reasoning_split},
         "paths": {"wiki_root": str(root)}, "search": {"engine": config.search.engine}})
    parsed = load_catalog_config(root / "config/source_catalog.yaml", project_root=root)
    require(parsed.project_root == root and parsed.catalog_dir.is_relative_to(root)
            and all(r.path.is_relative_to(root) for r in parsed.roots), "owned_config_escape")
    env = environment(project, root, config)
    require(model_options_from_config(Config.load(root / "config.yaml", llm_provider="deepseek").llm) == model,
            "owned_model_snapshot_differs")
    preparation = {"schema_version": SCHEMA, "attempt_id": attempt, "created_at": now(),
                   "owned_root": str(root), "project_root": str(project), "source": source,
                   "budget_baseline": baseline, "budget_baseline_file": file_identity(baseline_path),
                   "historical_receipt": file_identity(project / baseline["historical_receipt"]),
                   "ocr_identity": ocr.identity_manifest, "ocr_fingerprint": ocr.fingerprint,
                   "ocr_resources": models, "model": model,
                   "run_ids": {"first": attempt + "-first", "reuse": attempt + "-reuse"},
                   "config_hashes": {str(p.relative_to(root)): file_identity(p)
                                     for p in (root / "config/local_ocr.json", root / "config/source_catalog.yaml", root / "config.yaml")}}
    save(root / "marker.json", preparation)
    return preparation, env


def ledger(root, prepared, which):
    from company_wiki.automation.narrative_run_store import NarrativeRunStore
    db = root / "auto" / (which + ".sqlite3")
    if not db.is_file():
        return {"status": "not_created", "budget": None, "reservations": None, "terminal": False}
    store = NarrativeRunStore(db)
    run_id = prepared["run_ids"][which]
    run = store.get_run(run_id)
    require(run is not None, "origin_run_missing")
    reservations = [asdict(r) for r in store.reservations_for_run(run_id)]
    budget = asdict(store.budget_snapshot(run_id))
    # Read-only SQL avoids AutomationStore's constructor migration on inspection.
    with sqlite3.connect(db.resolve().as_uri() + "?mode=ro", uri=True) as conn:
        ids = list(run.job_ids)
        placeholders = ",".join("?" for _ in ids)
        jobs = conn.execute(f"SELECT job_id,status FROM jobs WHERE job_id IN ({placeholders})", ids).fetchall() if ids else []
        active = conn.execute("SELECT count(*) FROM attempts WHERE finished_at IS NULL").fetchone()[0]
    require(len(jobs) == len(ids), "origin_run_job_missing")
    return {"status": "read", "run_id": run_id, "state": run.state, "block_reason": run.block_reason,
            "input_hash": run.input_hash, "model_id": run.model_id,
            "max_tokens": run.max_tokens, "max_micro_usd": run.max_micro_usd,
            "pricing_version": run.pricing_version, "budget": budget, "reservations": reservations,
            "jobs": [{"job_id": j, "status": s} for j, s in jobs], "active_attempts": active,
            "terminal": active == 0 and all(s in TERMINAL for _, s in jobs)}


def exact_pin(batch_pin, ref):
    return batch_pin == {"artifact_version_id": ref["artifact_version_id"],
                         "content_sha256": ref["artifact_sha256"], "byte_size": ref["byte_size"],
                         "document_id": ref["source_ref"]["document_id"],
                         "source_id": ref["source_ref"]["source_id"],
                         "source_sha256": ref["source_ref"]["content_sha256"]}


def free_checks(project, root, prepared, env):
    from company_wiki.automation.narrative_batch_request import NarrativeBatchRequest
    from company_wiki.automation.narrative_contracts import NarrativeBundle
    from company_wiki.automation.narrative_transport_contracts import NarrativeReadRequest, parse_reference_request
    from company_wiki.source_catalog.official_source_flow import _metadata

    commands = [[sys.executable, "-B", "-m", "company_wiki.source_catalog.official_source_cli", "--help"],
                [sys.executable, "-B", str(project / "scripts/narrative_batch_configured.py"), "--help"],
                [sys.executable, "-B", "-m", "company_wiki.source_catalog.narrative_transport_cli", "--help"]]
    receipts = [execute(root, "help-" + str(i), cmd, env)[2] for i, cmd in enumerate(commands, 1)]
    # Existing delivered real contract fixture validates transport. Its identities
    # are schema fixtures only; live requests use the future real import result.
    golden = load(project / "docs/implementation/pool-w03-official-flow/html-bundle.json")
    NarrativeBundle.from_dict(golden)
    schema_ref = golden["source_ref"]
    for which in ("first", "reuse"):
        NarrativeBatchRequest.from_dict(batch_request(prepared["run_ids"][which], schema_ref,
                                                     prepared["model"], reuse=which == "reuse"))
    parse_reference_request({"schema_version": "narrative-reference-request/1", "source_ref": schema_ref})
    golden_receipt = load(project / "docs/implementation/pool-w03-official-flow/html-read-receipt.json")
    NarrativeReadRequest.from_dict({"schema_version": "narrative-read-request/1",
                                   "narrative_ref": golden_receipt["narrative_ref"], "as_of_date": None,
                                   "expected_source": dict.fromkeys(("canonical_entity_id", "market", "security_id",
                                                                      "document_kind", "fiscal_year", "fiscal_period"))})
    official = official_request(prepared["attempt_id"], prepared["source"])
    _metadata(official["source"])  # Pure metadata validator; import would parse the real deck.
    capture = official["capture_receipt"]
    require(capture["content_sha256"] == prepared["source"]["original"]["sha256"]
            and capture["response_bytes"] == prepared["source"]["original"]["byte_size"]
            and datetime.fromisoformat(capture["captured_at"].replace("Z", "+00:00")).tzinfo is not None,
            "capture_schema_invalid")
    return {"status": "PREPARED_NOT_RUN", "real_cli_help_commands": receipts,
            "contract_checks": ["catalog-owned-root", "official-source-metadata-and-local-capture",
                                "batch-first", "batch-reuse", "existing-bundle", "reference-request", "read-request"],
            "vendor_requests": 0, "deck_normalizations": 0, "ocr_inferences": 0,
            "existing_fixture_is_not_a_live_import_or_http_receipt": True}


def run_batches(project, root, prepared, env):
    from company_wiki.automation.narrative_batch_request import NarrativeBatchRequest
    from company_wiki.automation.narrative_contracts import NarrativeBundle, SourceRefValue
    from company_wiki.automation.narrative_transport_contracts import NarrativeReadRequest, NarrativeRef

    imported_path = root / "import-result.json"
    if not imported_path.exists():
        raw = root / "raw-input" / prepared["source"]["filename"]
        raw.parent.mkdir(exist_ok=True)
        shutil.copy2(prepared["source"]["original"]["path"], raw)
        require(file_identity(raw)["sha256"] == DECK_SHA, "owned_copy_sha_mismatch")
        save(root / "owned-input-observation.json", file_identity(raw))
        req = root / "requests/import.json"
        save(req, official_request(prepared["attempt_id"], prepared["source"]))
        stdout, _, _ = execute(root, "official-import", [sys.executable, "-B", "-m",
            "company_wiki.source_catalog.official_source_cli", "--config", str(root / "config/source_catalog.yaml"),
            "--project-root", str(root), "--request", str(req), "--input-file", str(raw)], env)
        imported = load(stdout)
        require(imported["schema_version"] == "official-source-import-result/1"
                and imported["download_events"] == 0, "official_import_receipt_invalid")
        save(imported_path, imported)
    imported = load(imported_path)
    source_ref = imported["source_ref"]
    SourceRefValue.from_dict(source_ref)
    require(source_ref["content_sha256"] == DECK_SHA and source_ref["byte_size"] == DECK_SIZE
            and source_ref["mime_type"] == PPTX, "real_import_source_binding")
    for field, value in {"document_kind": "investor_relations", "fiscal_year": None,
                         "fiscal_period": None, "published_date": "2026-09-02"}.items():
        require(imported["metadata"].get(field) == value, "official_metadata_" + field)
    results = {}
    refs = {}
    for which in ("first", "reuse"):
        req_path = root / "requests" / (which + ".json")
        expected = batch_request(prepared["run_ids"][which], source_ref, prepared["model"], reuse=which == "reuse")
        NarrativeBatchRequest.from_dict(expected)
        if req_path.exists():
            require(load(req_path) == expected, "origin_request_changed")
        else:
            save(req_path, expected)
        receipt_path = root / (which + "-result.json")
        if not receipt_path.exists():
            stdout, _, _ = execute(root, "batch-" + which, [sys.executable, "-B",
                str(project / "scripts/narrative_batch_configured.py"), "--llm-config", str(root / "config.yaml"),
                "--llm-provider", "deepseek", "--project-root", str(root),
                "--catalog-config", str(root / "config/source_catalog.yaml"),
                "--automation-db", str(root / "auto" / (which + ".sqlite3")),
                "--work-dir", str(root / ("work-" + which)), "--request", str(req_path)], env, timeout=660)
            result = load(stdout)
            require(result["schema_version"] == "narrative-batch-result/1"
                    and result["status"] == "completed", "batch_not_completed")
            save(receipt_path, result)
        result = load(receipt_path)
        require(result["run_id"] == prepared["run_ids"][which]
                and len(result["documents"]) == 1 and result["documents"][0]["status"] == "completed",
                "batch_result_binding")
        command = [sys.executable, "-B", "-m", "company_wiki.source_catalog.narrative_transport_cli",
                   "--config", str(root / "config/source_catalog.yaml")]
        stdout, _, _ = execute(root, "reference-" + which, command + ["--operation", "reference"], env,
                              stdin={"schema_version": "narrative-reference-request/1", "source_ref": source_ref})
        ref = load(stdout)
        NarrativeRef.from_dict(ref)
        require(ref["source_ref"] == source_ref and exact_pin(result["documents"][0]["artifact_ref"], ref),
                "batch_reference_pin_differs")
        read_request = {"schema_version": "narrative-read-request/1", "narrative_ref": ref, "as_of_date": None,
                        "expected_source": {"canonical_entity_id": None, "market": "US", "security_id": "MSFT",
                                            "document_kind": "investor_relations", "fiscal_year": None, "fiscal_period": None}}
        NarrativeReadRequest.from_dict(read_request)
        save(root / "requests" / ("read-" + which + ".json"), read_request)
        stdout, stderr, _ = execute(root, "read-" + which, command + ["--operation", "read"], env,
                                   stdin=read_request, timeout=660)
        artifact = file_identity(stdout)
        require(artifact["sha256"] == ref["artifact_sha256"] and artifact["byte_size"] == ref["byte_size"],
                "public_read_bytes_pin_differs")
        bundle, read_receipt = load(stdout), load(stderr)
        NarrativeBundle.from_dict(bundle)
        require(bundle["source_ref"] == source_ref and read_receipt["narrative_ref"] == ref
                and read_receipt["status"] == "ok" and read_receipt["replay_status"] == "verified",
                "public_read_not_verified")
        require(bundle["selection"]["status"] in {"selected", "partial"} and bundle["selection"]["selected_count"] > 0
                and bundle["selection"]["coverage_complete"] is False, "selected_partial_contract")
        require(bundle["source_metadata"]["language"] == "en"
                and bundle["summary"]["draft"]["language"] == "en"
                and bundle["summary"]["translate"] is False
                and bundle["summary"]["status"] == "completed"
                and bundle["summary"]["model"]["model_id"] == prepared["model"]["model_id"],
                "original_language_configured_summary_contract")
        spans = bundle["evidence_spans"]
        require(any("ocr_used" in s["quality_flags"] for s in spans)
                and all("low_ocr_confidence" not in s["quality_flags"] and s["parse_status"] == "parsed" for s in spans),
                "selected_ocr_evidence_quality")
        require(all(s["parser_version"] == "2.0.0"
                    and s["structured_value"]["ocr_fingerprint"] == prepared["ocr_fingerprint"] for s in spans),
                "selected_ocr_config_or_parser_binding")
        for field in ("fiscal_year", "fiscal_period"):
            require(read_receipt["manifest"].get(field) is None, "public_read_non_filing_period")
        require(read_receipt["manifest"]["published_date"] == "2026-09-02", "public_read_publication_date")
        current = ledger(root, prepared, which)
        require(result["budget"] == {"tokens": current["budget"]["charged_tokens"],
                                     "estimated_micro_usd": current["budget"]["charged_micro_usd"],
                                     "unknown_reservations": current["budget"]["unknown_reservations"],
                                     "unsettled_reservations": current["budget"]["unsettled_reservations"]},
                "batch_and_native_ledger_budget_differ")
        require(current["terminal"] and current["budget"]["unsettled_reservations"] == 0
                and current["budget"]["unknown_reservations"] == 0, "origin_ledger_unresolved")
        if which == "reuse":
            require(result["documents"][0].get("generation_status") == "reused"
                    and ref == refs["first"] and current["reservations"] == []
                    and current["budget"]["charged_tokens"] == 0 and current["budget"]["charged_micro_usd"] == 0
                    and result["budget"] == {"tokens": 0, "estimated_micro_usd": 0,
                                              "unknown_reservations": 0, "unsettled_reservations": 0},
                    "default_cross_run_reuse_not_exact_or_zero_admission")
        refs[which] = ref
        results[which] = {"batch_receipt": result, "narrative_ref": ref, "read_receipt": read_receipt,
                          "ledger": current, "bundle_identity": artifact,
                          "selection": bundle["selection"], "quality_status": bundle["quality_status"],
                          "versions": bundle["versions"], "span_count": len(spans),
                          "span_pages": sorted({s["coordinates"]["page_number"] for s in spans
                                                if s["coordinates"]["page_number"] is not None})}
    first = results["first"]["ledger"]["budget"]
    baseline = prepared["budget_baseline"]
    totals = {"tokens": baseline["cumulative_tokens"] + first["charged_tokens"],
              "estimated_micro_usd": baseline["cumulative_estimated_micro_usd"] + first["charged_micro_usd"],
              "historical_unknown_reservations": baseline["historical_unknown_reservations"],
              "new_unknown_reservations": first["unknown_reservations"],
              "fx_guard_micro_usd": baseline["fx_guard_micro_usd"], "native_historical_counted_again": False}
    require(totals["tokens"] <= baseline["effective_cap_tokens"]
            and totals["estimated_micro_usd"] + totals["fx_guard_micro_usd"] <= baseline["effective_cap_micro_usd"],
            "cumulative_budget_exceeded")
    return {"status": "ENGINEERING_COMPOSITION_PASS", "results": results, "cumulative_accounting": totals,
            "source_download_events": 0, "second_run_provider_admissions": 0,
            "second_run_new_posts": 0, "second_run_zero_post_evidence": "native_exact_pin_reused_and_zero_reservations",
            "first_run_http_post_count": None,
            "first_run_http_post_count_note": "AUTO reservations and usage are recorded; no invented HTTP observer receipt.",
            "product_or_investment_acceptance": "NOT_PERFORMED"}


def owned_root(path):
    root = Path(path).resolve(strict=True)
    temp = Path(tempfile.gettempdir()).resolve()
    require(root.parent == temp and root.name.startswith("mOCR-") and not root.is_symlink()
            and not (hasattr(root, "is_junction") and root.is_junction()), "not_owned_short_temp")
    marker = load(root / "marker.json")
    require(marker["schema_version"] == SCHEMA and marker["owned_root"] == str(root), "owned_marker_binding")
    # Refuse directory links, including Windows junctions, before recursive delete.
    for entry in root.rglob("*"):
        require(not entry.is_symlink() and not (hasattr(entry, "is_junction") and entry.is_junction()), "owned_tree_link")
    return root, marker


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("preflight", "run", "resume", "cleanup"), nargs="?", default="preflight")
    parser.add_argument("--project-root", type=Path, default=Path(__file__).resolve().parents[5])
    parser.add_argument("--owned-root", type=Path, help="Existing origin root; required for resume/cleanup")
    args = parser.parse_args()
    project = args.project_root.resolve()
    destination = Path(__file__).resolve().parent
    require(project / "src" == Path(__file__).resolve().parents[5] / "src", "script_project_binding")
    sys.path[:0] = [str(project / "src"), str(project / "scripts")]
    before = protected(project)
    attempt = "mocr-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S") + "-" + uuid.uuid4().hex[:8]
    report = {"schema_version": SCHEMA, "operation": args.operation, "attempt_id": attempt,
              "started_at": now(), "live_batch_executed": False, "protected_before": before,
              "script_file": file_identity(Path(__file__))}
    root = None
    prepared = None
    try:
        report["head"] = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=project, text=True).strip()
        if args.operation in {"resume", "cleanup"}:
            require(args.owned_root is not None, "origin_owned_root_required")
            root, prepared = owned_root(args.owned_root)
            report["attempt_id"] = prepared["attempt_id"]
            require(prepared["project_root"] == str(project), "origin_project_binding")
            for name, identity in prepared["config_hashes"].items():
                require(file_identity(root / name) == identity, "frozen_owned_config_changed")
            require(file_identity(prepared["source"]["original"]["path"]) == prepared["source"]["original"],
                    "original_changed_since_prepare")
            if args.operation == "cleanup":
                saved = load(root / "acceptance.json")
                require(saved["status"] == "ENGINEERING_COMPOSITION_PASS", "cleanup_requires_completed_acceptance")
                inspected = {w: ledger(root, prepared, w) for w in ("first", "reuse")}
                require(all(v["terminal"] and v["budget"]["unknown_reservations"] == 0
                            and v["budget"]["unsettled_reservations"] == 0 for v in inspected.values()),
                        "cleanup_requires_terminal_settled_origin")
                target = destination / "runs" / prepared["attempt_id"]
                require((target / "acceptance.json").is_file(), "durable_receipt_missing")
                report.update({"status": "TERMINAL_OWNED_ROOT_CLEANED", "terminal_ledgers": inspected,
                               "removed_owned_root": str(root)})
                shutil.rmtree(root)
            else:
                from config import Config
                config = Config.load(root / "config.yaml", llm_provider="deepseek")
                env = environment(project, root, config)
                report["live_batch_executed"] = True
                report.update(run_batches(project, root, prepared, env))
        else:
            require(args.owned_root is None, "run_uses_new_owned_root_use_resume_for_existing")
            if args.operation == "run":
                prior = [load(p) for p in (destination / "runs").glob("*/acceptance.json")]
                require(not any(p.get("live_batch_executed") is True for p in prior),
                        "live_node_already_started_use_origin_resume")
            root = Path(tempfile.mkdtemp(prefix="mOCR-")).resolve()
            prepared, env = prepare(project, root, attempt)
            report["preflight"] = free_checks(project, root, prepared, env)
            if args.operation == "run":
                report["live_batch_executed"] = True
                report.update(run_batches(project, root, prepared, env))
            else:
                report["status"] = "PREPARED_NOT_RUN"
    except Exception as exc:
        report["status"] = "FAILED_RETAIN_ORIGIN"
        report["error"] = str(exc) if isinstance(exc, CheckFailed) else type(exc).__name__
        if prepared is not None and root is not None:
            report["origin_ledgers"] = {}
            for which in ("first", "reuse"):
                try:
                    report["origin_ledgers"][which] = ledger(root, prepared, which)
                except Exception as read_error:
                    report["origin_ledgers"][which] = {"status": "unavailable", "budget": None,
                                                       "unknown_reservations": None, "error": type(read_error).__name__}
    finally:
        report["finished_at"] = now()
        report["protected_after"] = protected(project)
        report["protected_unchanged"] = report["protected_after"] == before
        if not report["protected_unchanged"]:
            report["status"] = "FAILED_PROTECTED_CHANGED"
        if prepared is not None:
            report["preparation"] = prepared
            report["original_after"] = file_identity(prepared["source"]["original"]["path"])
            report["original_unchanged"] = report["original_after"] == prepared["source"]["original"]
            if not report["original_unchanged"]:
                report["status"] = "FAILED_ORIGINAL_CHANGED"
            if "origin_ledgers" in report:
                actual = list(report["origin_ledgers"].values())
                readable = all(v.get("status") in {"read", "not_created"} for v in actual)
                budgets = [v["budget"] for v in actual if v.get("budget") is not None]
                baseline = prepared["budget_baseline"]
                report["failure_cumulative_accounting"] = {
                    "baseline_tokens": baseline["cumulative_tokens"],
                    "baseline_estimated_micro_usd": baseline["cumulative_estimated_micro_usd"],
                    "historical_unknown_reservations": baseline["historical_unknown_reservations"],
                    "new_charged_tokens": sum(b["charged_tokens"] for b in budgets) if readable else None,
                    "new_charged_micro_usd": sum(b["charged_micro_usd"] for b in budgets) if readable else None,
                    "new_unknown_reservations": sum(b["unknown_reservations"] for b in budgets) if readable else None,
                    "new_unsettled_reservations": sum(b["unsettled_reservations"] for b in budgets) if readable else None,
                    "unavailable_ledger_is_not_zero": True, "native_historical_counted_again": False}
        target = destination / "runs" / report["attempt_id"]
        target.mkdir(parents=True, exist_ok=True)
        if root is not None and root.exists():
            report["origin_owned_root"] = str(root)
            report["recovery_command"] = [sys.executable, "-B", str(Path(__file__).resolve()), "resume", "--owned-root", str(root)]
            # Durable evidence contains config references and exact outputs, no raw
            # deck, database copy, runtime environment, API key or fabricated receipt.
            try:
                for name in ("logs", "requests"):
                    if (root / name).exists():
                        shutil.copytree(root / name, target / name, dirs_exist_ok=True)
                for name in ("work-first", "work-reuse"):
                    if (root / name / "logs").exists():
                        shutil.copytree(root / name / "logs", target / name / "logs", dirs_exist_ok=True)
                if (root / "owned-input-observation.json").exists():
                    report["owned_input_observation"] = load(root / "owned-input-observation.json")
                if args.operation != "cleanup":
                    save(root / "acceptance.json", report)
                if args.operation == "preflight" and report["status"] == "PREPARED_NOT_RUN":
                    # No AUTO/jobs/inference; all help children ended. Verify the
                    # resolved final target and links before recursive deletion.
                    validated_root, _ = owned_root(root)
                    require(validated_root == root, "preflight_cleanup_path_changed")
                    shutil.rmtree(root)
                    report["preflight_temp_removed"] = not root.exists()
            except OSError as evidence_error:
                # A permission/storage failure must still produce a durable
                # failure report in CWP and never mask unavailable usage as zero.
                report["origin_evidence_error"] = type(evidence_error).__name__
                report["status"] = "FAILED_RETAIN_ORIGIN"
        report_path = target / ("cleanup.json" if args.operation == "cleanup" else "acceptance.json")
        save(report_path, report)
        print(json.dumps({"status": report["status"], "report": str(report_path),
                          "live_batch_executed": report["live_batch_executed"],
                          "owned_root_retained": str(root) if root is not None and root.exists() else None}))
    return 0 if report["status"] in {"PREPARED_NOT_RUN", "ENGINEERING_COMPOSITION_PASS", "TERMINAL_OWNED_ROOT_CLEANED"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
