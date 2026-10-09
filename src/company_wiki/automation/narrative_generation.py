"""Stable source generation identity and current exact artifact reuse proof."""

from __future__ import annotations
import json
from typing import Any
from .models import canonical_json_hash
from .narrative_contracts import (
    NarrativeBundle,
    BUNDLE_SCHEMA,
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


def generation_manifest(
    request, payload, *, execution_versions, parser_components=None
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
    model = request.model_options
    generation_fields = (
        "model_id",
        "endpoint",
        "max_output_tokens",
        "thinking",
        "temperature",
        "reasoning_split",
    )
    effective_model = {key: model[key] for key in generation_fields if key in model}
    effective_model["output_token_field"] = model.get(
        "output_token_field", "max_tokens"
    )
    result: dict[str, Any] = {
        "schema_version": "narrative-generation/1",
        "source_ref": payload.source_ref.to_dict(),
        "source_metadata": payload.source_metadata.to_dict(),
        "execution_versions": versions,
        "bundle_schema": BUNDLE_SCHEMA,
        "select_schema": SELECT_RESULT_SCHEMA,
        "summary_schema": SUMMARY_RESULT_SCHEMA,
        "parser_component": {"name": parser_name, "version": parser_version},
        "bundle_producer": BUNDLE_PRODUCER_VERSION,
        "profile": request.profile,
        "model": effective_model,
    }
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
    return result


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


def read_reuse_pin(artifacts, reader, payload, pin, facts, manifest=None):
    """The public reader owns byte/hash/current-source and one locator replay."""
    ref = payload.source_ref
    if (pin["document_id"], pin["source_id"], pin["source_sha256"]) != (
        ref.document_id,
        ref.source_id,
        ref.content_sha256,
    ):
        raise ValueError("BATCH_REUSE_PIN_SOURCE_MISMATCH")
    result = NarrativeTransportReader(artifacts, reader).read(
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
    complete = bundle.selection.coverage_complete and (
        (bundle.selection.status == "selected" and bundle.summary.status == "completed")
        or (
            bundle.selection.status == "skipped_no_narrative"
            and bundle.summary.status == "summary_not_needed"
        )
    )
    return complete


def find_reuse_pin(artifacts, reader, payload, manifest, facts):
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
            complete = read_reuse_pin(artifacts, reader, payload, pin, facts, manifest)
        except (KeyError, ValueError) as exc:
            # Never treat a corrupt matching artifact as permission to spend again.
            raise ValueError("BATCH_REUSE_ARTIFACT_INVALID") from exc
        if complete:
            return pin
    return None
