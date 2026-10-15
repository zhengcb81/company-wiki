"""Child-local composition for one bounded, explicitly scoped narrative run."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import json
from pathlib import Path
import re
from types import MappingProxyType
from typing import Any
from urllib.parse import urlsplit

from company_wiki.source_catalog import SourceCatalog
from company_wiki.source_catalog.config import load_catalog_config
from company_wiki.source_catalog.source_reader import SourceVersionReader
from company_wiki.source_catalog.narrative_normalization import NarrativeNormalization
from company_wiki.source_catalog.narrative_evidence import (
    NarrativeSelectorVersionError, resolve_narrative_selector_version,
)

from .migrations import InvalidDatabasePathError
from .narrative_http_model import NarrativeHTTPModel
from .narrative_model import (
    NARRATIVE_PROMPT_VERSION, PROJECTION_NARRATIVE_PROMPT_VERSION, PROJECTION_MODEL_REQUEST_SCHEMA,
)
from .narrative_official_json import NARRATIVE_OFFICIAL_JSON_ADAPTER_VERSION
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
    "temperature", "reasoning_split", "output_token_field", "reasoning_effort",
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
    if not isinstance(options, dict) or not _OPTION_FIELDS <= options.keys() or not options.keys() <= (_OPTION_FIELDS | {"max_final_bytes", "normalization_config", "normalization_parsers", "normalization_deadline"}):
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


def _contains_projected_work(binding: dict[str, Any], manifests: dict) -> bool:
    """Classify actual frozen source inputs, not the request container version."""
    settings = binding.get("generation_settings", {})
    for manifest in manifests.values():
        if not isinstance(manifest, dict):
            continue
        inputs = manifest.get("source_inputs", manifest)
        subject = inputs.get("subject_binding") if isinstance(inputs, dict) else None
        if isinstance(subject, dict) and subject.get("kind") == "official_json":
            return True
        if manifest.get("schema_version") == "narrative-generation/2":
            return True
        common = settings.get(manifest.get("settings_sha256")) if isinstance(settings, dict) else None
        if isinstance(common, dict) and common.get("schema_version") == "narrative-generation/2":
            return True
    return False


def _decode_binding(binding_json: str | None) -> dict[str, Any] | None:
    """Decode the persisted coordinator identity at the worker composition edge."""
    if binding_json is None:
        return None
    try:
        binding = json.loads(binding_json)
    except (TypeError, json.JSONDecodeError):
        raise ValueError("NARRATIVE_RUN_GENERATION_INVALID") from None
    if not isinstance(binding, dict):
        raise ValueError("NARRATIVE_RUN_GENERATION_INVALID")
    return binding


def _runtime_values(binding: dict[str, Any] | None) -> tuple[dict[str, str], str]:
    if binding is None:
        return {}, resolve_narrative_selector_version()
    try:
        versions = binding.get("execution_versions", {})
        manifests = binding.get("generation_manifests", {})
        if not isinstance(versions, dict) or not isinstance(versions.get("selector"), str):
            raise NarrativeSelectorVersionError("NARRATIVE_RUN_SELECTOR_VERSION_UNAVAILABLE")
        selector_version = resolve_narrative_selector_version(versions["selector"])
        if not isinstance(manifests, dict):
            raise ValueError("NARRATIVE_RUN_GENERATION_INVALID")
        if binding.get("schema_version") == "narrative-run-binding/4":
            if not isinstance(versions, dict):
                raise ValueError("NARRATIVE_RUN_EXECUTION_MISMATCH")
            if _contains_projected_work(binding, manifests):
                current = {
                    "projection_prompt": PROJECTION_NARRATIVE_PROMPT_VERSION,
                    "projection_model_request_schema": PROJECTION_MODEL_REQUEST_SCHEMA,
                    "official_json_adapter": NARRATIVE_OFFICIAL_JSON_ADAPTER_VERSION,
                }
                if any(versions.get(key) != value for key, value in current.items()):
                    raise ValueError("NARRATIVE_RUN_EXECUTION_MISMATCH")
        values = {}
        for item_key, manifest in manifests.items():
            value = manifest.get("generation_sha256") if isinstance(manifest, dict) else None
            if (not isinstance(item_key, str) or not item_key
                    or not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None):
                raise ValueError("NARRATIVE_RUN_GENERATION_INVALID")
            values[item_key] = value
        return values, selector_version
    except (AttributeError, TypeError, json.JSONDecodeError):
        raise ValueError("NARRATIVE_RUN_GENERATION_INVALID") from None


def _runtime_snapshot(binding_json: str | None) -> tuple[dict[str, str], str]:
    """Compatibility seam for callers that only need generation and selector."""
    return _runtime_values(_decode_binding(binding_json))


def _generation_values(binding_json: str | None) -> dict[str, str]:
    """Compatibility seam; runtime reads the complete snapshot exactly once."""
    return _runtime_snapshot(binding_json)[0]


def _reading_projection_identity(manifest: Mapping[str, Any]) -> str | None:
    """Decode a historical choice without requiring its implementation now."""
    from .narrative_model import ModelResponseError

    version = manifest.get("reading_model_projection")
    if (("reading_model_projection" in manifest and version is None)
            or (version is not None and (not isinstance(version, str) or not version
                or version != version.strip() or len(version) > 128))):
        raise ModelResponseError("READING_MODEL_PROJECTION_UNAVAILABLE")
    return version


def _validate_model_software(manifest: Mapping[str, Any]) -> str | None:
    """Validate only the implementation a particular summarize job will use."""
    from .narrative_model import (
        ModelResponseError,
        reading_model_boundary_identity, resolve_model_boundary,
    )

    version = _reading_projection_identity(manifest)
    projected = manifest.get("schema_version") == "narrative-generation/2"
    boundary = resolve_model_boundary(version, projected=projected)
    if boundary.source_owned:
        versions = manifest["execution_versions"]
        if (
            manifest.get("reading_model_boundary") != reading_model_boundary_identity(version, projected=projected)
            or versions.get("prompt") != boundary.prompt_version
            or versions.get("model_request_schema") != boundary.request_schema
        ):
            raise ModelResponseError("READING_MODEL_BOUNDARY_UNAVAILABLE")
        from .narrative_summarize import reading_summary_validation_identity

        if manifest.get("summary_validation") != reading_summary_validation_identity():
            raise ModelResponseError("READING_SUMMARY_VALIDATION_UNAVAILABLE")
    return version


def _reading_projection_values(binding: dict[str, Any] | None) -> dict[str, str | None]:
    """Compatibility inspection explicitly requests every model capability."""
    if binding is None or "generation_settings" not in binding:
        return {}
    from .narrative_batch import _thaw_generations

    return {key: _validate_model_software(manifest) for key, manifest in _thaw_generations(binding).items()}


def _reading_projection_versions(binding_json: str | None) -> dict[str, str | None]:
    """Compatibility seam; the production factory uses the shared worker snapshot."""
    return _reading_projection_values(_decode_binding(binding_json))


def _frozen_model_values(binding: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Read the already signed settings without rebuilding source manifests."""
    if binding is None:
        return []
    try:
        settings = binding.get("generation_settings", {})
        manifests = binding.get("generation_manifests", {})
        models = []
        for record in manifests.values():
            common = settings[record["settings_sha256"]] if "settings_sha256" in record else record
            if "model" in common:
                if not isinstance(common["model"], dict):
                    raise ValueError("NARRATIVE_RUN_GENERATION_INVALID")
                models.append(common["model"])
        return models
    except (KeyError, TypeError, AttributeError, json.JSONDecodeError) as exc:
        raise ValueError("NARRATIVE_RUN_GENERATION_INVALID") from exc


def _frozen_models(binding_json: str | None) -> list[dict[str, Any]]:
    """Compatibility seam for isolated configuration validation."""
    return _frozen_model_values(_decode_binding(binding_json))


@dataclass(frozen=True)
class _WorkerBindingSnapshot:
    generation_values: Mapping[str, str]
    selector_version: str
    reading_projections: Mapping[str, str | None]
    frozen_models: tuple[Mapping[str, Any], ...]
    frozen_generations: Mapping[str, Mapping[str, Any]]


def _worker_binding_snapshot(binding_json: str | None) -> _WorkerBindingSnapshot:
    """All worker parameters derive from one decoded, immutable run snapshot."""
    binding = _decode_binding(binding_json)
    generations, selector = _runtime_values(binding)
    from .narrative_batch import _thaw_generations

    manifests = _thaw_generations(binding) if binding is not None and "generation_settings" in binding else {}
    readings = {key: _reading_projection_identity(manifest) for key, manifest in manifests.items()}
    models = _frozen_model_values(binding)
    return _WorkerBindingSnapshot(
        MappingProxyType(generations), selector, MappingProxyType(readings),
        tuple(MappingProxyType(dict(model)) for model in models),
        MappingProxyType(manifests),
    )


def _verify_effective_model(model: NarrativeHTTPModel, frozen_models: Sequence[Mapping[str, Any]]) -> None:
    """Compare constructed HTTP behavior with frozen semantic configuration."""
    port = model._port
    authority = model._host
    if ":" in authority:
        authority = "[" + authority + "]"
    if port is not None:
        authority += ":" + str(port)
    effective = {
        "model_id": model.model_id,
        "endpoint": model._scheme + "://" + authority + model._path,
        "max_output_tokens": model.max_output_tokens,
        "output_token_field": model.output_token_field,
    }
    for key in ("thinking", "reasoning_effort", "temperature", "reasoning_split"):
        value = getattr(model, key)
        if value is not None:
            effective[key] = value
    for frozen in frozen_models:
        # A historical omitted HTTP option stays omitted rather than gaining a
        # provider default. Non-content settings and credentials never appear.
        expected = {key: value for key, value in frozen.items() if value is not None}
        endpoint = urlsplit(expected.get("endpoint", ""))
        host = endpoint.hostname or ""
        if ":" in host:
            host = "[" + host + "]"
        if endpoint.port is not None:
            host += ":" + str(endpoint.port)
        expected["endpoint"] = endpoint.scheme + "://" + host + (endpoint.path or "/")
        if effective != expected:
            raise ValueError("NARRATIVE_RUN_MODEL_CONFIG_MISMATCH")


def _generation_resolver(run_store: NarrativeRunStore, run_id: str, base: Mapping[str, str], *, selector_version: str):
    """Refresh final selection identities at use time, after compute commits."""
    if selector_version != "0.9.0":
        # Historical generations already have a complete immutable identity;
        # they neither depend on nor need to reread the new selection column.
        return lambda subject: base[subject.item_key]
    def resolve(subject):
        final = run_store.final_generations(run_id).get(subject.item_key)
        if final is not None:
            from .models import canonical_json_hash

            return canonical_json_hash(final)
        raise ValueError("NARRATIVE_RUN_SELECTION_NOT_FROZEN")
    return resolve


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

    snapshot = _worker_binding_snapshot(run.binding_json)
    generation_values, selector_version = snapshot.generation_values, snapshot.selector_version
    reading_projections = snapshot.reading_projections

    def validate_model_execution(subject) -> None:
        _validate_model_software(snapshot.frozen_generations[subject.item_key])
    project_root = Path(options["project_root"])
    config_path = Path(options["catalog_config_path"])
    catalog = SourceCatalog(load_catalog_config(config_path, project_root=project_root))
    reader = SourceVersionReader(catalog)
    normalization = NarrativeNormalization.from_snapshot(
        options.get("normalization_config"), deadline=options.get("normalization_deadline"),
        parser_versions=options.get("normalization_parsers"))
    model = None
    caller = None
    if spec.role in {"model", "mixed"}:
        try:
            model = NarrativeHTTPModel(**model_options)
        except (TypeError, ValueError):
            raise ValueError("NARRATIVE_MODEL_CONFIG_INVALID") from None
        _verify_effective_model(model, snapshot.frozen_models)
        caller = BudgetedNarrativeCaller(store=run_store, run_id=options["run_id"], model=model,
                                        final_output_bytes_bound=options.get("max_final_bytes", 2 * 1024 * 1024))
    registry = create_default_registry()
    executor = HandlerExecutor()
    register_narrative_handlers(
        executor,
        NarrativeRuntimeDependencies(reader=reader, model=model, model_caller=caller, normalization=normalization,
            projection_catalog=catalog, selector_version=selector_version,
            reading_model_projection=(lambda subject: reading_projections[subject.item_key])
                if reading_projections else None,
            validate_model_execution=validate_model_execution if snapshot.frozen_generations else None,
            generation_sha256=_generation_resolver(run_store, options["run_id"], generation_values,
                                                   selector_version=selector_version) if generation_values else None),
    )
    runtime = WorkerRuntime(registry=registry, executor=executor, model_client=model)
    validate_runtime(runtime, role=spec.role, allowed_job_types=spec.allowed_job_types)
    return runtime


__all__ = ["create_runtime"]
