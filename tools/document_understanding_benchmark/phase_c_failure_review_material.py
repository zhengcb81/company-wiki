"""Write-once review material from an isolated native AUTO run, without sources.

The runner owns the isolated database and receipt path. This helper only reads
already persisted selection evidence and actual final generations; it does not
open originals, rebuild prompts, run parsers, or call a model. Native failure
details/usage are retained separately by the runner's existing append_native.
"""
from __future__ import annotations

from contextlib import closing
import gzip
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import tempfile

from company_wiki.automation.narrative_run_store import NarrativeRunStore


class FailureReviewMaterialConflict(ValueError):
    """An existing write-once review differs from this native observation."""


def _native_material(database: Path, run_id: str) -> dict | None:
    if not database.is_file():
        return None
    with closing(sqlite3.connect(database.resolve().as_uri() + "?mode=ro", uri=True)) as connection:
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA query_only=ON")
        rows = connection.execute(
            "SELECT j.subject_id,j.job_id,j.job_type,j.status,a.attempt_id,"
            "a.attempt_no,a.outcome,a.error_code,a.result_json,"
            "EXISTS(SELECT 1 FROM narrative_model_reservations m "
            "WHERE m.run_id=r.run_id AND m.job_id=j.job_id AND m.attempt_id=a.attempt_id) AS native_model,"
            "EXISTS(SELECT 1 FROM narrative_model_reservations m JOIN jobs mj ON mj.job_id=m.job_id "
            "WHERE m.run_id=r.run_id AND mj.subject_id=j.subject_id "
            "AND mj.job_type='source.narrative_summarize') AS native_model_item "
            "FROM narrative_run_jobs r JOIN jobs j ON j.job_id=r.job_id "
            "JOIN attempts a ON a.job_id=j.job_id "
            "WHERE r.run_id=? AND a.finished_at IS NOT NULL "
            "AND j.job_type IN ('source.narrative_select','source.narrative_summarize','source.narrative_verify') "
            "ORDER BY j.subject_id,j.job_id,a.attempt_no",
            (run_id,),
        ).fetchall()

    selections, failures, summaries, verification_failures, successful_bundles = {}, {}, {}, {}, set()
    for row in rows:
        result = json.loads(row["result_json"]) if row["result_json"] else {}
        item_key = row["subject_id"]
        kind = row["job_type"]
        if kind == "source.narrative_verify" and row["outcome"] == "succeeded":
            if result.get("result", {}).get("schema_version") in {
                "narrative-bundle/2.0", "narrative-bundle/3.0",
            }:
                successful_bundles.add(item_key)
        elif (kind == "source.narrative_select" and row["status"] == "succeeded"
              and row["outcome"] == "succeeded"):
            selections[item_key] = {
                "select_job_id": row["job_id"],
                "select_attempt_id": row["attempt_id"],
                "select_result": result["result"],
            }
        elif (kind == "source.narrative_summarize" and row["native_model"]
              and row["outcome"] in {"terminal_failure", "retryable"}
              and row["error_code"] is not None):
            failures.setdefault(item_key, []).append(row["attempt_id"])
        elif (kind == "source.narrative_summarize" and row["native_model"]
              and row["outcome"] == "succeeded"):
            summaries[item_key] = result["result"]
        elif (kind == "source.narrative_verify" and row["native_model_item"]
              and row["outcome"] in {"terminal_failure", "retryable"}
              and row["error_code"] is not None):
            verification_failures.setdefault(item_key, []).append(row["attempt_id"])

    items = sorted((selections.keys() & (failures.keys() | (verification_failures.keys() & summaries.keys())))
                   - successful_bundles)
    if not items:
        return None
    generations = NarrativeRunStore(database).final_generations(run_id)
    return {
        "schema_version": "native-failure-review/1",
        "run_id": run_id,
        "items": [{
            "item_key": item_key,
            **selections[item_key],
            # None honestly represents a legacy selection with no final freeze;
            # never infer its generation from current code or configuration.
            "final_generation": generations.get(item_key),
            "failed_summary_attempt_ids": sorted(failures.get(item_key, [])),
            **({"summary_result": summaries[item_key],
                "failed_verification_attempt_ids": sorted(verification_failures[item_key])}
               if item_key in verification_failures and item_key in summaries else {}),
        } for item_key in items],
    }


def _write_once(path: Path, payload: bytes) -> None:
    if path.exists():
        if path.read_bytes() != payload:
            raise FailureReviewMaterialConflict("existing failure review material differs")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    # Link a complete, flushed staging file exclusively, so interruption cannot
    # expose a partial gzip and concurrent identical observations can reuse it.
    with tempfile.NamedTemporaryFile(prefix=".failure-review-", dir=path.parent, delete=False) as stream:
        staging = Path(stream.name)
        try:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        except BaseException:
            stream.close()
            staging.unlink()
            raise
    try:
        try:
            os.link(staging, path)
        except FileExistsError:
            if path.read_bytes() != payload:
                raise FailureReviewMaterialConflict("existing failure review material differs") from None
    finally:
        staging.unlink()


def preserve_failure_review_material(
    database: Path, run_id: str, output_path: Path,
) -> dict[str, object] | None:
    """Return only path/sha256/bytes, or None for success/pre-model failures.

    Repeated identical observations verify and reuse the exact gzip bytes and
    mtime. Different material raises FailureReviewMaterialConflict; no existing
    file is replaced. The compact JSON stores full native source refs, locators,
    selection coverage/reading context, and the actual persisted generation.
    """
    material = _native_material(database, run_id)
    if material is None:
        return None
    raw = json.dumps(material, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf8")
    payload = gzip.compress(raw, compresslevel=9, mtime=0)
    output_path = output_path.resolve()
    _write_once(output_path, payload)
    return {"path": str(output_path), "sha256": hashlib.sha256(payload).hexdigest(), "bytes": len(payload)}
