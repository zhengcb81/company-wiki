"""Pure identity helpers for the selection persisted by the existing AUTO store."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .models import canonical_json_hash, require_sha256


def reading_material_sha256(value: Any) -> str:
    """Hash the actual material shared by a SelectResult and its published Bundle.

    The whole select-result hash remains the Store's audit identity. A Bundle
    intentionally omits its parser name and selection-time review diagnostics,
    so it cannot reconstruct that hash. This proof instead binds all material
    consumed by the model and retained in the Bundle, including role/locator,
    selection coverage and actual sent reading instructions.
    """
    wire = value.to_dict()
    return canonical_json_hash({
        "subject": value.subject.to_dict(),
        **{key: wire.get(key) for key in (
            "source_metadata", "selection", "evidence_spans", "reading_context",
            "transcript_lineage", "transcript_byte_bindings",
        )},
    })


def validate_selection_generation(manifest: Mapping[str, Any]) -> None:
    """Validate compact final identity without reading sources or selecting again."""
    part = manifest.get("selection_generation")
    if not isinstance(part, Mapping) or part.get("schema_version") != "narrative-selection-generation/1":
        raise ValueError("BATCH_REUSE_SELECTION_GENERATION_INVALID")
    fields = {"schema_version", "select_result_sha256", "evidence_sha256",
              "material_sha256", "reading_policy_version"}
    for key in ("select_result_sha256", "evidence_sha256", "material_sha256"):
        require_sha256(part.get(key), field_name=key)
    policy = part.get("reading_policy_version")
    if not isinstance(policy, str) or not policy.startswith("du-sent-policy/1+"):
        raise ValueError("BATCH_REUSE_READING_POLICY_GENERATION_INVALID")
    require_sha256(policy.removeprefix("du-sent-policy/1+"), field_name="reading_policy_version")
    dependencies = manifest.get("reading_dependencies")
    if dependencies is not None:
        if not isinstance(dependencies, Mapping) or dependencies.get("schema_version") != "du-decision-dependencies/1":
            raise ValueError("BATCH_REUSE_DECISION_GENERATION_INVALID")
        if dependencies.get("status") == "complete":
            fields.add("decision_digest")
            require_sha256(dependencies.get("decision_digest"), field_name="decision_digest")
            if dependencies["decision_digest"] != part.get("decision_digest"):
                raise ValueError("BATCH_REUSE_DECISION_DIGEST_INVALID")
        elif dependencies.get("status") != "partial":
            raise ValueError("BATCH_REUSE_DECISION_GENERATION_INVALID")
        elif dependencies.get("decision_digest") is not None:
            # A partial producer may retain an audit digest. It never enters
            # the reusable decision field and cannot certify a cache hit.
            require_sha256(dependencies["decision_digest"], field_name="decision_digest")
    if set(part) != fields:
        raise ValueError("BATCH_REUSE_SELECTION_GENERATION_INVALID")
