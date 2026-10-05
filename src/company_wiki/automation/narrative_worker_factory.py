"""Child-local composition for one bounded, explicitly scoped narrative run."""

from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any

from company_wiki.source_catalog import SourceCatalog
from company_wiki.source_catalog.config import load_catalog_config
from company_wiki.source_catalog.source_reader import SourceVersionReader

from .migrations import InvalidDatabasePathError
from .narrative_http_model import NarrativeHTTPModel
from .narrative_model import NARRATIVE_PROMPT_VERSION
from .narrative_model_caller import BudgetedNarrativeCaller
from .narrative_run_store import NarrativeRunError, NarrativeRunStore
from .narrative_runtime import NarrativeRuntimeDependencies, register_narrative_handlers
from .registry import create_default_registry
from .store import AutomationStoreError
from .worker import HandlerExecutor
from .worker_process import WorkerProcessSpec, WorkerRuntime, validate_runtime


_OPTION_FIELDS = {
    "project_root", "catalog_config_path", "run_id", "expected_run_input_hash", "model",
}
_MODEL_FIELDS = {
    "model_id", "endpoint", "api_key_env", "max_output_tokens", "timeout_seconds",
    "max_request_bytes", "max_response_bytes", "allow_local_http", "thinking",
}
_JOB_TYPES = {"source.narrative_select", "source.narrative_summarize", "source.narrative_verify"}


def _text(value: object) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError("NARRATIVE_RUNTIME_OPTIONS_INVALID")
    return value


def _options(spec: WorkerProcessSpec) -> tuple[dict[str, Any], dict[str, Any]]:
    try:
        options = json.loads(spec.runtime_options_json)
    except (ValueError, TypeError):
        raise ValueError("NARRATIVE_RUNTIME_OPTIONS_INVALID") from None
    if not isinstance(options, dict) or not _OPTION_FIELDS <= options.keys() or not options.keys() <= (_OPTION_FIELDS | {"max_final_bytes"}):
        raise ValueError("NARRATIVE_RUNTIME_OPTIONS_INVALID")
    final_bytes = options.get("max_final_bytes", 2 * 1024 * 1024)
    if type(final_bytes) is not int or not 0 < final_bytes <= 2 * 1024 * 1024:
        raise ValueError("NARRATIVE_RUNTIME_OPTIONS_INVALID")
    for field in _OPTION_FIELDS - {"model"}:
        _text(options[field])
    if not re.fullmatch(r"[0-9a-f]{64}", options["expected_run_input_hash"]):
        raise ValueError("NARRATIVE_RUNTIME_OPTIONS_INVALID")
    model = options["model"]
    if (
        not isinstance(model, dict)
        or not set(model) <= _MODEL_FIELDS
        or not {"model_id", "endpoint", "api_key_env"} <= set(model)
    ):
        raise ValueError("NARRATIVE_RUNTIME_OPTIONS_INVALID")
    _text(model["model_id"])
    return options, model


def create_runtime(spec: WorkerProcessSpec) -> WorkerRuntime:
    """Verify run identity, then construct ports inside the owning worker child.

    Database initialization belongs to the batch coordinator. No credential
    value is accepted in options, and compute roles never construct a model.
    """
    options, model_options = _options(spec)
    if not spec.allowed_job_ids:
        raise ValueError("NARRATIVE_RUN_SCOPE_REQUIRED")
    if not set(spec.allowed_job_types) <= _JOB_TYPES:
        raise ValueError("NARRATIVE_RUNTIME_JOB_TYPES_INVALID")
    try:
        run_store = NarrativeRunStore(Path(spec.db_path))
        run = run_store.get_run(options["run_id"])
    except (NarrativeRunError, AutomationStoreError, InvalidDatabasePathError):
        raise ValueError("NARRATIVE_RUN_STORE_UNAVAILABLE") from None
    if run is None:
        raise ValueError("NARRATIVE_RUN_NOT_FOUND")
    if set(spec.allowed_job_ids) != set(run.job_ids):
        raise ValueError("NARRATIVE_RUN_SCOPE_MISMATCH")
    if run.input_hash != options["expected_run_input_hash"]:
        raise ValueError("NARRATIVE_RUN_INPUT_MISMATCH")
    if run.model_id != model_options["model_id"]:
        raise ValueError("NARRATIVE_RUN_MODEL_MISMATCH")
    if run.prompt_version != NARRATIVE_PROMPT_VERSION:
        raise ValueError("NARRATIVE_RUN_PROMPT_MISMATCH")
    if spec.role in {"model", "mixed"} and run.blocked:
        raise ValueError("NARRATIVE_RUN_BLOCKED")

    project_root = Path(options["project_root"])
    config_path = Path(options["catalog_config_path"])
    catalog = SourceCatalog(load_catalog_config(config_path, project_root=project_root))
    reader = SourceVersionReader(catalog)
    model = None
    caller = None
    if spec.role in {"model", "mixed"}:
        try:
            model = NarrativeHTTPModel(**model_options)
        except (TypeError, ValueError):
            raise ValueError("NARRATIVE_MODEL_CONFIG_INVALID") from None
        caller = BudgetedNarrativeCaller(store=run_store, run_id=options["run_id"], model=model,
                                        final_output_bytes_bound=options.get("max_final_bytes", 2 * 1024 * 1024))
    registry = create_default_registry()
    executor = HandlerExecutor()
    register_narrative_handlers(
        executor,
        NarrativeRuntimeDependencies(reader=reader, model=model, model_caller=caller),
    )
    runtime = WorkerRuntime(registry=registry, executor=executor, model_client=model)
    validate_runtime(runtime, role=spec.role, allowed_job_types=spec.allowed_job_types)
    return runtime


__all__ = ["create_runtime"]
