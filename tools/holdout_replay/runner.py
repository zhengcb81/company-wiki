"""Attempt orchestration: frozen deploy -> subprocess replay -> honest receipts.

Layout under ``--out-dir``::

    attempts/<producer-commit>/<timestamp>-<attempt-n>/
        attempt.json            run receipt (H09)
        <sample>.job.json       exact worker input (pathless bindings aside)
        <sample>.result.json    worker output or failure record

An attempt directory is created fresh; an existing path or an existing result
refuses the run instead of overwriting older evidence (H10/H11).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .manifest import load_manifest, sha256_file, verify_manifest_gold
from .producer import verify_producer
from .resolve import ResolveError, build_source_root_index, load_bindings, resolve_original

ORCHESTRATOR_ROOT = Path(__file__).resolve().parents[2]


class ReplayError(RuntimeError):
    """The replay refused to run (bad inputs, dirty deploy, existing output)."""


def _worker_env(producer_root: Path, extra_pythonpath: list[Path] | None = None) -> dict[str, str]:
    from .producer import import_paths

    paths = [str(p.resolve()) for p in import_paths(producer_root)]
    paths.append(str(ORCHESTRATOR_ROOT))
    for extra in extra_pythonpath or []:
        paths.insert(0, str(Path(extra).resolve()))
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(paths)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env.pop("PYTHONSTARTUP", None)
    return env


def _next_attempt_dir(out_dir: Path, producer_commit: str) -> Path:
    base = out_dir / "attempts" / producer_commit[:12]
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    candidate = base / f"{stamp}-1"
    number = 1
    while candidate.exists():
        number += 1
        candidate = base / f"{stamp}-{number}"
    return candidate


def _invalid_result(payload: Any, sample_id: str, commit: str, sha: str) -> str | None:
    """Validate the observation's binding, without grading product semantics."""
    if not isinstance(payload, dict):
        return "expected object"
    expected = {"schema_version": "w18-holdout-sample-result/1", "sample_id": sample_id,
                "producer_commit": commit, "original_before_sha256": sha,
                "original_after_sha256": sha}
    for key, value in expected.items():
        if payload.get(key) != value:
            return f"{key} mismatch"
    if payload.get("original_unchanged") is not True:
        return "original changed"
    view = payload.get("model_view")
    if not isinstance(view, dict):
        return "model_view must be object"
    if view.get("request_sent"):
        return "worker reports request sent"
    return None


def run_replay(
    *,
    producer_root: Path,
    producer_commit: str,
    manifest_path: Path,
    out_dir: Path,
    bindings_path: Path | None = None,
    source_root: Path | None = None,
    sample_ids: list[str] | None = None,
    lake_config: Path | None = None,
    lake_root: Path | None = None,
    llm_config: Path | None = None,
    llm_provider: str = "minimax",
    per_sample_timeout: float = 900.0,
    external_cwd: Path | None = None,
    extra_pythonpath: list[Path] | None = None,
    compile_selector_version: str = "0.9.0",
) -> dict[str, Any]:
    manifest_path = Path(manifest_path)
    out_dir = Path(out_dir)
    if bindings_path is None and source_root is None:
        raise ReplayError("one of --bindings or --source-root is required")
    if bindings_path is not None and source_root is not None:
        raise ReplayError("use either --bindings or --source-root, not both")
    if (lake_config is None) != (llm_config is None):
        raise ReplayError("--compile needs both --lake-config and --llm-config")

    deploy = verify_producer(Path(producer_root), producer_commit)
    manifest = load_manifest(manifest_path)
    gold_rows = verify_manifest_gold(manifest, manifest_path)

    samples = {s["sample_id"]: s for s in manifest["samples"]}
    if sample_ids is None:
        selected = list(manifest["samples"])
    else:
        missing = [sid for sid in sample_ids if sid not in samples]
        if missing:
            raise ReplayError(f"unknown sample ids: {', '.join(missing)}")
        selected = [samples[sid] for sid in sample_ids]

    bindings = load_bindings(Path(bindings_path)) if bindings_path else None
    source_index = None
    if source_root is not None:
        wanted = {s["source_ref"]["content_sha256"]: int(s["source_ref"]["byte_size"])
                  for s in selected}
        source_index = build_source_root_index(Path(source_root), wanted)

    attempt_dir = _next_attempt_dir(out_dir, producer_commit)
    try:
        attempt_dir.mkdir(parents=True, exist_ok=False)
    except FileExistsError as exc:
        raise ReplayError("ATTEMPT_EXISTS_NOT_OVERWRITING") from exc
    from tools.document_understanding_benchmark import recovery

    sentinel = recovery.install_sentinel(
        attempt_dir,
        {"purpose": "w18-holdout attempt; do not overwrite results",
         "producer_commit": producer_commit, "manifest_sha256": sha256_file(manifest_path)},
        preserve_existing=True,
    )
    recovery.mark_owned(attempt_dir)

    compile_spec = None
    if lake_config is not None:
        compile_spec = {
            "llm_config": str(Path(llm_config).resolve()),
            "llm_provider": llm_provider,
            "project_root": str((Path(lake_root) if lake_root else Path(lake_config).parent).resolve()),
            "catalog_config": str(Path(lake_config).resolve()),
        }

    env = _worker_env(Path(producer_root), extra_pythonpath)
    cwd = Path(external_cwd) if external_cwd else Path.home()

    receipt: dict[str, Any] = {
        "schema_version": "w18-holdout-attempt/1",
        "producer": deploy,
        "manifest_path": str(manifest_path),
        "manifest_sha256": sha256_file(manifest_path),
        "gold_rows": gold_rows,
        "bindings_sha256": sha256_file(Path(bindings_path)) if bindings_path else None,
        "source_root": str(source_root) if source_root else None,
        "compile_spec": {k: compile_spec[k] for k in ("llm_provider", "project_root", "catalog_config")}
                         if compile_spec else None,
        "llm_config_sha256": sha256_file(Path(llm_config)) if llm_config else None,
        "python": sys.version.split()[0],
        "env_pythonpath": env["PYTHONPATH"],
        "worker_cwd": str(cwd),
        "per_sample_timeout_seconds": per_sample_timeout,
        "compile_selector_version": compile_selector_version,
        "samples": [],
        "network_calls": 0,
        "model_posts": 0,
        "zero_network_by_construction": (
            "no network primitive exists in the replay path; the compile stage "
            "serializes the configured wire body (request_bytes) without opening "
            "a connection, so these zeros are guarantees, not measurements"),
    }

    overall_ok = True
    for sample in selected:
        sample_id = sample["sample_id"]
        row: dict[str, Any] = {"sample_id": sample_id, "status": "pending"}
        started = time.monotonic()
        try:
            path, actual_sha = resolve_original(sample, bindings=bindings, source_index=source_index)
        except ResolveError as exc:
            row.update(status="unavailable", reason=f"RESOLVE: {exc}")
            receipt["samples"].append(row)
            overall_ok = False
            continue
        gold_file = manifest_path.parent / sample["gold_file"]
        job = {
            "producer_root": str(Path(producer_root).resolve()),
            "producer_commit": producer_commit,
            "run_id": f"w18-{sample_id}",
            "sample": sample,
            "gold": json.loads(gold_file.read_text(encoding="utf-8")),
            "original_path": str(path),
            "original_sha256": actual_sha,
            "compile_spec": compile_spec,
            "compile_selector_version": compile_selector_version,
        }
        job_path = attempt_dir / f"{sample_id}.job.json"
        result_path = attempt_dir / f"{sample_id}.result.json"
        if result_path.exists():
            row.update(status="refused", reason="RESULT_EXISTS_NOT_OVERWRITING")
            receipt["samples"].append(row)
            overall_ok = False
            continue
        with job_path.open("x", encoding="utf-8") as handle:
            handle.write(json.dumps(job, ensure_ascii=False, indent=1))
        command = [sys.executable, "-B", "-X", "utf8", "-m",
                   "tools.holdout_replay.worker", str(job_path), str(result_path)]
        try:
            completed = subprocess.run(
                command, cwd=str(cwd), env=env, capture_output=True, text=True,
                encoding="utf-8", errors="replace", timeout=per_sample_timeout,
            )
            row["worker_exit"] = completed.returncode
            row["worker_stderr_tail"] = completed.stderr[-800:] if completed.stderr else ""
            if completed.returncode == 0 and result_path.exists():
                try:
                    payload = json.loads(result_path.read_text(encoding="utf-8"))
                except (UnicodeError, json.JSONDecodeError) as exc:
                    row.update(status="failed",
                               reason=f"WORKER_RESULT_UNREADABLE: {type(exc).__name__}: {exc}"[:400])
                    overall_ok = False
                    receipt["samples"].append(row)
                    continue
                invalid = _invalid_result(payload, sample_id, producer_commit, actual_sha)
                if invalid:
                    row.update(status="invalid", reason=f"INVALID_WORKER_RESULT: {invalid}")
                    overall_ok = False
                else:
                    row.update(status="ok", result_path=payload)
            else:
                row.update(status="failed",
                           reason=f"WORKER_EXIT_{completed.returncode}")
                overall_ok = False
        except subprocess.TimeoutExpired:
            row.update(status="timeout",
                       reason=f"WORKER_TIMEOUT_AFTER_{per_sample_timeout}s")
            overall_ok = False
        row["elapsed_seconds"] = round(time.monotonic() - started, 1)
        receipt["samples"].append(row)

    receipt["attempt_dir"] = str(attempt_dir)
    sentinel_receipt = dict(sentinel)
    preexisting = sentinel_receipt.get("preexisting")
    if isinstance(preexisting, dict):
        sentinel_receipt["preexisting"] = {
            key: value for key, value in preexisting.items() if key != "bytes"
        }
    receipt["sentinel"] = sentinel_receipt
    receipt["overall"] = "ok" if overall_ok else "has_failures"
    with (attempt_dir / "attempt.json").open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(receipt, ensure_ascii=False, indent=1) + "\n")
    return receipt
