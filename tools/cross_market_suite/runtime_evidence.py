"""Bounded, source-text-free snapshots of actual AUTO state before fixture cleanup.

Read only; no migrations, job completion, billing writes, or capability decisions.
Unknown/missing native evidence stays unknown. Arrays carry exact total counts.
"""
from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import sqlite3

SCHEMA = "cmrf-runtime-evidence/1"
MAX_BYTES = 32768
MAX_ROWS = 9
SELECTION = ("status", "coverage_complete", "source_units", "candidate_count", "selected_count",
             "omitted_candidate_count", "dropped_financial_count", "pages_total", "pages_read",
             "lines_total", "tables_total", "tables_scanned")
BUDGET = ("tokens", "estimated_micro_usd", "unknown_reservations", "unsettled_reservations")
PIN = ("artifact_version_id", "content_sha256", "byte_size", "effect_id", "document_id", "source_id", "source_sha256")


def _fields(value, keys):
    if not isinstance(value, dict):
        return None
    return {key: (item[:256] if isinstance(item, str) else item)
            for key in keys if key in value
            for item in [value[key]] if item is None or isinstance(item, (str, int, float, bool))}


def _receipt(value):
    docs = value.get("documents")
    return {"status": value.get("status"), "error": value.get("error"),
            "budget": _fields(value.get("budget"), BUDGET),
            "document_count": len(docs) if isinstance(docs, list) else None,
            "documents": [{**(_fields(doc, ("document_id", "status", "generation_status")) or {}),
                           "artifact_ref": _fields(doc.get("artifact_ref"), PIN),
                           "errors": [code[:256] for code in doc.get("errors", [])[:MAX_ROWS]
                                      if isinstance(code, str)] if isinstance(doc.get("errors"), list) else None}
                          for doc in docs[:MAX_ROWS] if isinstance(doc, dict)] if isinstance(docs, list) else None}


def public_quality(view, *, replay_status=None):
    """Counters from an actual public read, never summary text or model prompts."""
    spans = view.get("evidence_spans", [])
    summary = view.get("summary", {})
    claims = summary.get("draft", {}).get("claims", [])
    return {"selection": _fields(view.get("selection"), SELECTION),
            "summary": {**(_fields(summary, ("status", "translate", "language")) or {}),
                        "claim_count": len(claims),
                        "claims_needing_review": sum(claim.get("needs_review") is True for claim in claims)},
            "span_count": len(spans), "parse_status_counts": dict(Counter(span.get("parse_status") for span in spans)),
            "quality_flag_counts": dict(Counter(flag for span in spans for flag in span.get("quality_flags", []))),
            "source_language": view.get("source_metadata", {}).get("language"),
            "public_replay_status": replay_status}


def _snapshot(connection, run_id, evidence):
    run = connection.execute("SELECT state,block_reason,max_tokens,max_micro_usd,last_runtime_generation,input_hash,scope_sha256 "
                             "FROM narrative_runs WHERE run_id=?", (run_id,)).fetchone()
    if run is None:
        evidence["database_evidence"] = "unavailable_run"
        return
    evidence["run"] = dict(run)
    binding = connection.execute("SELECT json_valid(binding_json),json_type(binding_json,'$.normalization_config') "
                                 "FROM narrative_runs WHERE run_id=?", (run_id,)).fetchone()
    evidence["normalization_binding"] = None
    if binding[0]:
        evidence["normalization_binding"] = {
            "ocr_config_present": None if binding[1] is None else binding[1] != "null",
            "parsers": [dict(row) for row in connection.execute(
                "SELECT key AS document_id,COALESCE(json_extract(value,'$.source_inputs.parser_component.name'),json_extract(value,'$.parser_component.name')) AS parser_name,"
                "COALESCE(json_extract(value,'$.source_inputs.parser_component.version'),json_extract(value,'$.parser_component.version')) AS parser_version "
                "FROM narrative_runs,json_each(binding_json,'$.generation_manifests') "
                "WHERE run_id=? ORDER BY key LIMIT ?", (run_id, MAX_ROWS))],
        }
    evidence["job_count"] = connection.execute("SELECT COUNT(*) FROM narrative_run_jobs WHERE run_id=?", (run_id,)).fetchone()[0]
    rows = connection.execute("SELECT j.job_id,j.job_type,j.status,j.handler_version,j.last_error_code "
                              "FROM jobs j JOIN narrative_run_jobs r ON r.job_id=j.job_id "
                              "WHERE r.run_id=? ORDER BY j.job_type,j.job_id LIMIT ?", (run_id, MAX_ROWS))
    jobs = []
    for row in rows:
        job = dict(row)
        job["attempt_count"] = connection.execute("SELECT COUNT(*) FROM attempts WHERE job_id=?", (row["job_id"],)).fetchone()[0]
        attempt = connection.execute("SELECT attempt_id,attempt_no,started_at,finished_at,outcome,error_code,runtime_generation "
                                     "FROM attempts WHERE job_id=? ORDER BY attempt_no DESC LIMIT 1", (row["job_id"],)).fetchone()
        job["latest_attempt"] = dict(attempt) if attempt is not None else None
        if attempt is not None:
            # Extract scalar paths in SQL. Never retrieve a whole selection, summary, original or lease.
            paths = ["schema_version", "status", "parser.name", "parser.version", "selector.version"]
            paths += ["selection." + key for key in SELECTION]
            expressions = ",".join("json_extract(result_json,'$.result." + key + "')" for key in paths)
            values = connection.execute("SELECT " + expressions + " FROM attempts "
                                        "WHERE attempt_id=? AND json_valid(result_json)", (attempt["attempt_id"],)).fetchone()
            if values is not None:
                extracted = dict(zip(paths, values))
                job["latest_attempt"].update(result_schema=extracted["schema_version"], result_status=extracted["status"],
                    parser_name=extracted["parser.name"], parser_version=extracted["parser.version"],
                    selector_version=extracted["selector.version"],
                    selection={key: extracted["selection." + key] for key in SELECTION}
                              if extracted["selection.status"] is not None else None)
        jobs.append(job)
    evidence["jobs"] = jobs
    evidence["reservation_count"] = connection.execute("SELECT COUNT(*) FROM narrative_model_reservations WHERE run_id=?", (run_id,)).fetchone()[0]
    evidence["reservations"] = [dict(row) for row in connection.execute(
        "SELECT attempt_id,job_id,usage_status,input_tokens_bound,max_output_tokens,reserved_micro_usd,"
        "input_tokens,output_tokens,estimated_micro_usd,error_code,reserved_at,usage_settled_at,output_settled_at,"
        "CASE WHEN usage_status='known' THEN input_tokens+output_tokens ELSE input_tokens_bound+max_output_tokens END AS charged_tokens,"
        "COALESCE(estimated_micro_usd,reserved_micro_usd) AS charged_micro_usd "
        "FROM narrative_model_reservations WHERE run_id=? ORDER BY attempt_id LIMIT ?", (run_id, MAX_ROWS))]
    evidence["database_evidence"] = "available"


def capture_runtime_evidence(db_path, receipt, *, run_id, returncode=None):
    evidence = {"schema_version": SCHEMA, "run_id": run_id, "returncode": returncode,
                "receipt": _receipt(receipt), "database_evidence": "unavailable_database",
                "jobs": None, "reservations": None, "job_count": None, "reservation_count": None}
    path = Path(db_path).resolve()
    if path.is_file():
        connection = None
        try:
            connection = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=2)
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA query_only=ON")
            connection.execute("BEGIN")
            _snapshot(connection, run_id, evidence)
        except sqlite3.Error as exc:
            evidence.update(database_evidence="unavailable_database_schema", database_error=type(exc).__name__)
        finally:
            if connection is not None:
                connection.close()
    if len(json.dumps(evidence, ensure_ascii=False).encode("utf-8")) > MAX_BYTES:
        evidence.update(jobs=None, reservations=None, details_omitted="evidence_size_cap")
    if len(json.dumps(evidence, ensure_ascii=False).encode("utf-8")) > MAX_BYTES:
        raise ValueError("runtime evidence exceeds bounded metadata cap")
    return evidence


def runtime_properties(properties):
    result = {}
    for prop, key in (("cmrf_runtime_evidence", "runtime_evidence"), ("cmrf_public_quality", "public_quality")):
        raw = properties.get(prop)
        if raw is not None:
            if len(raw.encode("utf-8")) > MAX_BYTES:
                raise ValueError("runtime evidence property too large")
            value = json.loads(raw)
            if not isinstance(value, dict):
                raise ValueError("runtime evidence must be an object")
            result[key] = value
    return result
