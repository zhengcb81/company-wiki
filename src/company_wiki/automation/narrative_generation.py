"""Stable source generation identity and current exact artifact reuse proof."""

from __future__ import annotations
import json
import math
from importlib import import_module
from collections.abc import Mapping, Sequence
from typing import Any
from urllib.parse import urlsplit

from company_wiki.narrative_subject import NarrativeSubject
from .models import canonical_json_hash
from .narrative_contracts import (
    NarrativeBundle,
    BUNDLE_SCHEMA,
    PROJECTED_SELECT_RESULT_SCHEMA,
    SELECT_RESULT_SCHEMA,
    SUMMARY_RESULT_SCHEMA,
)
from .narrative_formats import NORMALIZED_MIME_TYPES, parser_component
from company_wiki.source_catalog.transcript_text_extract import (
    TRANSCRIPT_MATERIAL_EXTRACTOR,
    TRANSCRIPT_JSON_EXTRACTOR,
)
from .narrative_transport import NarrativeTransportReader
from .narrative_transport_contracts import NarrativeReadRequest, EXPECTED_SOURCE_FIELDS
from .narrative_verify import BUNDLE_PRODUCER_VERSION
from .narrative_selection_generation import reading_material_sha256, validate_selection_generation

READING_PROJECTION_UNSET = object()
READING_CONTEXT_PROJECTION_VERSION = "reading-context-projection/1"


def _bind_reading_context_projection(manifest, versions):
    """Invalidate pre-renderer cache entries after public reading-context changes."""
    if versions.get("selector") == "0.9.0":
        manifest["reading_context_projection_version"] = READING_CONTEXT_PROJECTION_VERSION


def with_frozen_model_identity(current, recorded):
    """Validate resume inputs without executing unrelated model software.

    These are historical causal observations, not claims that today's decoder
    is identical. A pending summarize job checks its actual implementation at
    its model boundary. Source, model options and other inputs stay current.
    """
    result = {key: value for key, value in current.items()
              if key not in {"reading_model_boundary", "summary_validation"}}
    for key in ("reading_model_boundary", "summary_validation"):
        if key in recorded:
            result[key] = recorded[key]
    versions = dict(result["execution_versions"])
    for key in ("prompt", "model_request_schema"):
        if key in recorded["execution_versions"]:
            versions[key] = recorded["execution_versions"][key]
    result["execution_versions"] = versions
    return result


def _bind_reading_projection(manifest, versions, reading_model_projection):
    if reading_model_projection is READING_PROJECTION_UNSET:
        from .narrative_model_extractive import EXTRACTIVE_MODEL_PROJECTION_VERSION
        reading_model_projection = (EXTRACTIVE_MODEL_PROJECTION_VERSION
                                    if versions.get("selector") == "0.9.0" else None)
    if reading_model_projection is not None:
        # Historical identities can retain a future/retired software version.
        # Executability is checked by the model boundary before any new POST.
        if (not isinstance(reading_model_projection, str) or not reading_model_projection
                or reading_model_projection.strip() != reading_model_projection
                or len(reading_model_projection) > 256):
            raise ValueError("invalid reading model projection identity")
        manifest["reading_model_projection"] = reading_model_projection
        from .narrative_model import ModelResponseError
        from .narrative_model_runtime import (
            reading_model_boundary_identity,
            resolve_model_boundary,
        )
        projected = manifest["schema_version"] == "narrative-generation/2"
        try:
            boundary = resolve_model_boundary(reading_model_projection, projected=projected)
        except ModelResponseError:
            # Preserve historical unavailable identities without pretending that
            # the current software can execute them. The factory owns that check.
            return
        if boundary.source_owned:
            versions["prompt"] = boundary.prompt_version
            versions["model_request_schema"] = boundary.request_schema
            manifest["reading_model_boundary"] = reading_model_boundary_identity(
                reading_model_projection, projected=projected,
            )
            from .narrative_summarize import reading_summary_validation_identity

            manifest["summary_validation"] = reading_summary_validation_identity()


def _effective_optional_generation(options: Mapping[str, Any]) -> dict[str, Any]:
    """Match HTTP omission rules without resigning existing omitted identities."""
    return {
        key: options[key]
        for key in ("thinking", "reasoning_effort", "temperature", "reasoning_split")
        if options.get(key) is not None
    }


def generation_manifest(
    request, payload, *, execution_versions, parser_components=None,
    reading_model_projection=READING_PROJECTION_UNSET,
):
    """Bind only this source's causal inputs; component fingerprints are pathless.

    Normalization owners can provide their actual runtime/model/preprocess
    fingerprint through parser_components. Other carriers ignore that component.
    """
    versions = dict(execution_versions)
    normalized = (
        payload.source_ref.mime_type in NORMALIZED_MIME_TYPES
        and payload.source_metadata.source_class == "filing"
    )
    versions.pop("document_normalization", None)
    if normalized:
        versions.pop("parser", None)
    parser_name, parser_version = parser_component(
        payload.source_ref.mime_type, payload.source_metadata.source_class
    )
    if normalized and parser_components is not None:
        parser_name = parser_components["parser_name"]
        parser_version = parser_components["parser_version"]
    model = request.model_options
    generation_fields = ("model_id", "endpoint", "max_output_tokens")
    effective_model = {key: model[key] for key in generation_fields if key in model}
    effective_model.update(_effective_optional_generation(model))
    effective_model["output_token_field"] = model.get(
        "output_token_field", "max_tokens"
    )
    result: dict[str, Any] = {
        "schema_version": "narrative-generation/1",
        "source_ref": payload.source_ref.to_dict(),
        "source_metadata": payload.source_metadata.to_dict(),
        "execution_versions": versions,
        "bundle_schema": BUNDLE_SCHEMA,
        "select_schema": (
            SELECT_RESULT_SCHEMA
            if versions.get("selector") == "0.9.0"
            else "narrative-select-result/2.0"
        ),
        "summary_schema": SUMMARY_RESULT_SCHEMA,
        "parser_component": {"name": parser_name, "version": parser_version},
        "bundle_producer": BUNDLE_PRODUCER_VERSION,
        "profile": request.profile,
        "model": effective_model,
    }
    _bind_reading_context_projection(result, versions)
    if payload.source_metadata.source_class == "transcript":
        result["material_extractor"] = (
            TRANSCRIPT_JSON_EXTRACTOR
            if payload.source_ref.mime_type == "application/json"
            else TRANSCRIPT_MATERIAL_EXTRACTOR
        )
    if normalized and parser_components is not None:
        # Caller supplies the actual producer fingerprint, never guessed config.
        from .narrative_contracts import assert_no_physical_paths

        assert_no_physical_paths(parser_components)
        result["parser_components"] = json.loads(json.dumps(parser_components))
    _bind_reading_projection(result, versions, reading_model_projection)
    return result


def _projection_identity_json(value: Any) -> Any:
    """Detach finite, compact semantic JSON without storing original records."""
    from .narrative_contracts import assert_no_physical_paths

    forbidden = {
        "api_key",
        "api_key_env",
        "api_token",
        "access_token",
        "authorization",
        "password",
        "secret",
        "credentials",
        "evidence_spans",
        "raw_text",
    }

    def plain(child: Any) -> Any:
        if isinstance(child, Mapping):
            output = {}
            for key, item in child.items():
                if not isinstance(key, str) or key.lower() in forbidden:
                    raise ValueError(
                        "projection generation contains non-semantic or secret fields"
                    )
                # Source coverage legitimately has integer per-page record counts.
                # Lists/objects under this name would copy the full projection.
                if key == "records" and type(item) is not int:
                    raise ValueError(
                        "projection generation cannot contain original records"
                    )
                output[key] = plain(item)
            return output
        if isinstance(child, Sequence) and not isinstance(child, (str, bytes)):
            return [plain(item) for item in child]
        if isinstance(child, str) and child.startswith(("/", "~/", "~\\")):
            raise ValueError("projection generation cannot contain filesystem paths")
        return child

    try:
        assert_no_physical_paths(value)
        detached = plain(value)
        encoded = json.dumps(
            detached,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        )
        encoded.encode("utf-8")
        return json.loads(encoded)
    except (TypeError, ValueError, RecursionError, UnicodeError) as exc:
        raise ValueError(
            "projection generation must be finite pathless compact JSON"
        ) from exc


def _projection_identity_text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value or value.strip() != value:
        raise ValueError(f"projection generation {name} must be nonempty trimmed text")
    return value


def _projection_effective_model(options: Mapping[str, Any]) -> dict[str, Any]:
    """Bind exactly the fields emitted by the existing HTTP generation adapter."""
    model_id = _projection_identity_text(options.get("model_id"), "model_id")
    endpoint = _projection_identity_text(options.get("endpoint"), "endpoint")
    try:
        parsed = urlsplit(endpoint)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or "?" in endpoint
            or "#" in endpoint
            or any(char.isspace() for char in endpoint)
        ):
            raise ValueError("invalid endpoint")
        _ = parsed.port  # Validate malformed/out-of-range ports without opening a connection.
    except ValueError as exc:
        raise ValueError(
            "projection generation requires a credential-free HTTP endpoint"
        ) from exc
    limit = options.get("max_output_tokens")
    if type(limit) is not int or limit <= 0:
        raise ValueError(
            "projection generation max_output_tokens must be a positive integer"
        )
    token_field = options.get("output_token_field", "max_tokens")
    if not isinstance(token_field, str) or token_field not in {
        "max_tokens",
        "max_completion_tokens",
    }:
        raise ValueError("projection generation output_token_field is unsupported")
    result = {
        "model_id": model_id,
        "endpoint": endpoint,
        "max_output_tokens": limit,
        "output_token_field": token_field,
    }
    for key, value in _effective_optional_generation(options).items():
        if key == "thinking" and (
            not isinstance(value, str) or value not in {"enabled", "disabled", "adaptive"}
        ):
            raise ValueError("projection generation thinking is unsupported")
        if key == "reasoning_effort" and (
            not isinstance(value, str) or value not in {"low", "high", "max"}
        ):
            raise ValueError("projection generation reasoning_effort is unsupported")
        if key == "temperature" and (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            or not 0 <= value <= 2
        ):
            raise ValueError(
                "projection generation temperature must be finite within [0, 2]"
            )
        if key == "reasoning_split" and type(value) is not bool:
            raise ValueError("projection generation reasoning_split must be boolean")
        result[key] = value
    return result


def projection_generation_manifest(
    request: Any,
    subject: NarrativeSubject,
    *,
    language: str,
    execution_versions: Mapping[str, Any],
    bundle_producer: str,
    narrative_adapter_version: str,
    source_metadata: Mapping[str, Any] | None = None,
    reading_model_projection: Any = READING_PROJECTION_UNSET,
) -> dict[str, Any]:
    """Bind one official projection's semantic generation inputs.

    Source identity is a detached neutral binding, not current-byte proof.
    The source port owns that verification. Explicit projection prompt/handler
    identities come from the caller; raw-global versions are never substituted.
    Runtime caps, credential names and unrelated raw parsers are not content
    inputs. Historical raw generations with omitted effort retain their identity.
    """
    if not isinstance(subject, NarrativeSubject) or subject.kind != "official_json":
        raise ValueError("projection generation requires an official JSON subject")
    if not isinstance(language, str) or language not in {
        "zh",
        "en",
        "mixed",
        "unknown",
    }:
        raise ValueError("projection generation language is unsupported")
    profile = _projection_identity_text(request.profile, "profile")
    if profile not in {"P1", "P2", "P4"}:
        raise ValueError("projection generation profile is unsupported")
    if not isinstance(execution_versions, Mapping):
        raise ValueError("projection generation execution_versions must be a mapping")
    versions = dict(execution_versions)
    versions.pop("parser", None)
    versions.pop("document_normalization", None)
    for key in ("selector", "adapter", "prompt"):
        _projection_identity_text(versions.get(key), key)
    for key in ("model_request_schema",):
        if key in versions:
            _projection_identity_text(versions[key], key)
    if "handlers" in versions and (
        not isinstance(versions["handlers"], Mapping)
        or any(
            not isinstance(key, str)
            or not isinstance(value, str)
            or not value
            or value.strip() != value
            for key, value in versions["handlers"].items()
        )
    ):
        raise ValueError("projection generation handler versions must be explicit text")
    binding = _projection_identity_json(subject.to_dict())
    source_adapter = binding["adapter"]
    for key in (
        "parser",
        "structure_parser_version",
        "layout_id",
        "layout_version",
        "layout_fingerprint",
    ):
        _projection_identity_text(source_adapter.get(key), key)
    parser_name, separator, parser_version = source_adapter["parser"].rpartition("/")
    if not separator or not parser_name or not parser_version:
        raise ValueError(
            "projection generation source parser must include its producer version"
        )
    if not isinstance(request.model_options, Mapping):
        raise ValueError("projection generation model_options must be a mapping")
    result = {
        "schema_version": "narrative-generation/2",
        "subject_binding": binding,
        "source_adapter": source_adapter,
        "language": language,
        "execution_versions": versions,
        "bundle_schema": "narrative-bundle/3.0",
        "select_schema": PROJECTED_SELECT_RESULT_SCHEMA,
        "summary_schema": "narrative-summary-result/3.0",
        "parser_component": {"name": parser_name, "version": parser_version},
        "bundle_producer": _projection_identity_text(
            bundle_producer, "bundle_producer"
        ),
        "narrative_adapter_version": _projection_identity_text(
            narrative_adapter_version, "narrative_adapter_version"
        ),
        "profile": profile,
        "model": _projection_effective_model(request.model_options),
    }
    _bind_reading_context_projection(result, versions)
    if source_metadata is not None:
        from .narrative_contracts import SourceMetadataValue

        metadata = SourceMetadataValue.from_dict(
            source_metadata, projected=True
        ).to_dict()
        if metadata["language"] != language:
            raise ValueError("projection generation metadata language differs")
        result["source_metadata"] = metadata
    _bind_reading_projection(result, versions, reading_model_projection)
    return _projection_identity_json(result)


def generation_sha256(manifest):
    return canonical_json_hash(manifest)


def artifact_pin(version):
    return {
        "artifact_version_id": version.artifact_version_id,
        "content_sha256": version.content_sha256,
        "byte_size": version.byte_size,
        "document_id": version.document_id,
        "source_id": version.source_id,
        "source_sha256": version.source_sha256,
    }


def read_reuse_pin(artifacts, reader, payload, pin, facts, manifest=None, *, normalization=None):
    """The public reader owns byte/hash/current-source and one locator replay."""
    if manifest is not None and manifest.get("execution_versions", {}).get("selector") == "0.9.0" and "selection_generation" not in manifest:
        manifest = pinned_reading_manifest(artifacts, payload, pin, manifest)
    ref = payload.source_ref
    if (pin["document_id"], pin["source_id"], pin["source_sha256"]) != (
        ref.document_id,
        ref.source_id,
        ref.content_sha256,
    ):
        raise ValueError("BATCH_REUSE_PIN_SOURCE_MISMATCH")
    result = NarrativeTransportReader(artifacts, reader, normalization=normalization).read(
        NarrativeReadRequest.from_dict(
            {
                "schema_version": "narrative-read-request/1",
                "as_of_date": None,
                "expected_source": {
                    key: (
                        facts.get(
                            "document_kind", payload.source_metadata.document_kind
                        )
                        if key == "document_kind"
                        else facts.get(key)
                    )
                    for key in EXPECTED_SOURCE_FIELDS
                },
                "narrative_ref": {
                    "schema_version": "narrative-ref/1",
                    "artifact_version_id": pin["artifact_version_id"],
                    "artifact_sha256": pin["content_sha256"],
                    "byte_size": pin["byte_size"],
                    "source_ref": ref.to_dict(),
                },
            }
        )
    )
    bundle = NarrativeBundle.from_dict(json.loads(result.data))
    if manifest is not None and "selection_generation" in manifest:
        verify_reading_bundle_generation(bundle, manifest)
    if manifest is not None:
        if (
            bundle.source_metadata.to_dict() != manifest["source_metadata"]
            or bundle.versions.parser != manifest["parser_component"]["version"]
            or bundle.versions.bundle_producer != manifest["bundle_producer"]
            or bundle.schema_version != manifest["bundle_schema"]
            or bundle.versions.selector != manifest["execution_versions"]["selector"]
            or (
                bundle.summary.model is not None
                and (
                    bundle.summary.model.model_id != manifest["model"]["model_id"]
                    or bundle.summary.model.adapter_id
                    != manifest["execution_versions"]["adapter"]
                    or bundle.summary.model.prompt_version
                    != manifest["execution_versions"]["prompt"]
                )
            )
        ):
            raise ValueError("BATCH_REUSE_BUNDLE_GENERATION_MISMATCH")
        if bundle.versions.parser == "2.0.0":
            fingerprint = manifest.get("parser_components", {}).get("ocr_fingerprint")
            if not isinstance(fingerprint, str) or len(fingerprint) != 64 or any(
                span.structured_value.get("ocr_fingerprint") != fingerprint
                for span in bundle.evidence_spans
            ):
                raise ValueError("BATCH_REUSE_BUNDLE_GENERATION_MISMATCH")
    return (
        bundle.selection.status in {"selected", "partial"}
        and bundle.summary.status == "completed"
        and bool(bundle.evidence_spans)
        and not any({"low_ocr_confidence", "locator_unstable"}.intersection(span.quality_flags)
                    for span in bundle.evidence_spans)
    ) or (
        bundle.selection.coverage_complete and bundle.selection.status == "skipped_no_narrative"
        and bundle.summary.status == "summary_not_needed" and not bundle.evidence_spans
        and bundle.selection.selected_count == 0
    )



def find_reuse_pin(artifacts, reader, payload, manifest, facts, *, normalization=None):
    if manifest.get("execution_versions", {}).get("selector") == "0.9.0":
        for version in artifacts.visible_base_generation_candidates(
                subject=payload.subject, base_generation_sha256=generation_sha256(manifest)):
            stored = reading_candidate_manifest(version, manifest)
            if not current_reading_decision_matches(stored):
                continue
            pin = artifact_pin(version)
            if read_reuse_pin(artifacts, reader, payload, pin, facts, stored, normalization=normalization):
                return pin
        return None
    digest = generation_sha256(manifest)
    versions = artifacts.visible_generation_candidates(
        document_id=payload.source_ref.document_id,
        source_id=payload.source_ref.source_id,
        source_sha256=payload.source_ref.content_sha256,
        generation_sha256=digest,
    )
    for version in versions:
        metadata = json.loads(version.metadata_json)
        if metadata.get("generation_manifest") != manifest:
            raise ValueError("BATCH_REUSE_MANIFEST_INVALID")
        pin = artifact_pin(version)
        try:
            complete = read_reuse_pin(artifacts, reader, payload, pin, facts, manifest, normalization=normalization)
        except (KeyError, ValueError) as exc:
            # Never treat a corrupt matching artifact as permission to spend again.
            raise ValueError("BATCH_REUSE_ARTIFACT_INVALID") from exc
        if complete:
            return pin
    return None


def reading_candidate_manifest(version, base: Mapping[str, Any]) -> dict[str, Any]:
    metadata = json.loads(version.metadata_json)
    manifest = metadata.get("generation_manifest")
    if (not isinstance(manifest, dict) or "selection_generation" not in manifest
            or {key: value for key, value in manifest.items()
                if key not in {"selection_generation", "reading_dependencies"}} != base
            or metadata.get("generation_sha256") != generation_sha256(manifest)):
        raise ValueError("BATCH_REUSE_MANIFEST_INVALID")
    validate_selection_generation(manifest)
    return manifest


def pinned_reading_manifest(artifacts, payload, pin, base) -> dict[str, Any]:
    version = artifacts.visible_subject_metadata(subject=payload.subject,
                                                 artifact_version_id=pin["artifact_version_id"])
    content = pin.get("content_sha256", pin.get("artifact_sha256"))
    if version.content_sha256 != content or version.byte_size != pin["byte_size"]:
        raise ValueError("BATCH_REUSE_PIN_ARTIFACT_MISMATCH")
    return reading_candidate_manifest(version, base)


def current_reading_decision_matches(manifest: Mapping[str, Any]) -> bool:
    dependencies = manifest.get("reading_dependencies")
    if not isinstance(dependencies, Mapping) or dependencies.get("status") != "complete":
        return False
    from .models import require_sha256
    digest = dependencies.get("decision_digest")
    if not isinstance(digest, str):
        raise ValueError("BATCH_REUSE_DECISION_DIGEST_INVALID")
    require_sha256(digest, field_name="decision_digest")
    if dependencies.get("decision_digest") != manifest.get("selection_generation", {}).get("decision_digest"):
        raise ValueError("BATCH_REUSE_DECISION_DIGEST_INVALID")
    try:
        port = import_module("company_wiki.document_understanding.decision_dependencies")
    except ModuleNotFoundError as exc:
        if exc.name != "company_wiki.document_understanding.decision_dependencies":
            raise
        return False
    from company_wiki.document_understanding.decision_inventory import current_decision_trace
    current = current_decision_trace(dependencies)
    if not current["inventory_complete"]:
        return False
    return port.compare_decision_dependencies(dependencies, current)["status"] == "same"


def verify_reading_bundle_generation(bundle: NarrativeBundle, manifest: Mapping[str, Any]) -> None:
    validate_selection_generation(manifest)
    frozen = manifest["selection_generation"]
    if (bundle.reading_context is None
            or bundle.reading_context["reading_policy_version"] != frozen["reading_policy_version"]
            or canonical_json_hash([span.to_dict() for span in bundle.evidence_spans]) != frozen["evidence_sha256"]
            or reading_material_sha256(bundle) != frozen["material_sha256"]):
        raise ValueError("BATCH_REUSE_SELECTION_GENERATION_MISMATCH")
