"""Immutable model prompt bindings shared by run accounting and terminal storage."""

from __future__ import annotations

import json

__all__ = [
    "NarrativeRunError",
    "RunConflictError",
    "RunScopeError",
    "job_prompt_versions",
    "model_prompt_version",
    "require_run_name",
]


class NarrativeRunError(RuntimeError):
    code = "narrative_run_error"


class RunConflictError(NarrativeRunError):
    code = "narrative_run_conflict"


class RunScopeError(NarrativeRunError):
    code = "run_scope_mismatch"


def require_run_name(value: str, name: str) -> None:
    if not isinstance(value, str) or not value or value.strip() != value:
        raise ValueError(f"{name} must be non-empty unpadded text")


def job_prompt_versions(binding_json: str | None) -> dict[str, str] | None:
    """Optional immutable model-job prompts; old bindings keep the run default.

    This ledger knows only job IDs, types and accounting. The owner of a run
    binding chooses the actual prompt version; source/model modules are not
    imported or interpreted here.
    """
    if binding_json is None:
        return None
    try:
        binding = json.loads(binding_json)
        if not isinstance(binding, dict) or "job_prompt_versions" not in binding:
            return None
        versions = binding["job_prompt_versions"]
        if not isinstance(versions, dict):
            raise ValueError("job_prompt_versions must be an object")
        for job_id, prompt in versions.items():
            require_run_name(job_id, "job_prompt_versions job_id")
            require_run_name(prompt, "job_prompt_versions prompt")
        return versions
    except (TypeError, ValueError) as exc:
        raise RunConflictError("invalid immutable job prompt binding") from exc


def model_prompt_version(
    binding_json: str | None, *, job_id: str, default_prompt: str,
) -> str:
    """Resolve one frozen model job prompt without database or source reads.

    Admission and terminal compaction must use the same binding. A map that
    exists never falls back for an unbound job; only legacy absent maps use
    the immutable run default.
    """
    versions = job_prompt_versions(binding_json)
    if versions is None:
        return default_prompt
    if job_id not in versions:
        raise RunScopeError("job has no immutable model prompt binding")
    return versions[job_id]
