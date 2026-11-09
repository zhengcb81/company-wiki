"""Validate and read persisted narrative bundles through the source artifact port."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import json
from typing import TYPE_CHECKING

from company_wiki.narrative_subject import NarrativeSubject
from company_wiki.wire_json import canonical_json_hash, parse_canonical_json

from .narrative_artifact_store import (
    NarrativeArtifactNotVisibleError, NarrativeArtifactReader, NarrativeArtifactStore, NarrativeArtifactVersion,
)
from .narrative_contracts import NarrativeBundle, NarrativeContractError
from .narrative_summary_protocols import ASSESSED_BUNDLE, LEGACY_BUNDLE

if TYPE_CHECKING:
    from .narrative_official_json import VerifiedProjectionView


@dataclass(frozen=True)
class NarrativeArtifactRead:
    artifact: NarrativeArtifactVersion
    bundle: NarrativeBundle


class NarrativeProjectionError(ValueError):
    """A stored or proposed bundle cannot be bound to its source."""


def validate_projection_manifest(bundle: NarrativeBundle, manifest: object) -> tuple[dict, str]:
    if (not isinstance(manifest, dict) or manifest.get("schema_version") != "narrative-generation/2"
            or manifest.get("subject_binding") != bundle.subject.to_dict()):
        raise NarrativeProjectionError("projection generation manifest differs from bundle subject")
    metadata = manifest.get("source_metadata")
    if metadata is not None and metadata != bundle.source_metadata.to_dict():
        raise NarrativeProjectionError("projection generation metadata differs from bundle")
    return manifest, canonical_json_hash(manifest)


def decode_stored_narrative_bundle(payload: bytes) -> NarrativeBundle:
    if not payload:
        raise NarrativeProjectionError("stored narrative bundle is empty")
    try:
        return NarrativeBundle.from_dict(parse_canonical_json(payload.decode("utf-8")))
    except (UnicodeDecodeError, TypeError, ValueError, NarrativeContractError) as exc:
        raise NarrativeProjectionError("stored narrative bundle failed its strict wire contract") from exc


def replay_projected_bundle(
    bundle: NarrativeBundle,
    loader: Callable[[NarrativeSubject], VerifiedProjectionView] | None,
) -> None:
    """Revalidate a projected bundle against its current source-owned fields."""
    if bundle.subject.kind != "official_json":
        return
    if loader is None:
        raise NarrativeProjectionError("projection source loader is unavailable")
    from .narrative_material_replay import replay_verified_projection
    from .narrative_official_json import VerifiedProjectionView

    view = loader(bundle.subject)
    if not isinstance(view, VerifiedProjectionView):
        raise NarrativeProjectionError("projection source loader returned an invalid view")
    replay_verified_projection(view, bundle)


class NarrativeBundleReader:
    """Return only hash-checked visible bundles bound to the active source version."""

    def __init__(self, artifacts: NarrativeArtifactStore | NarrativeArtifactReader, *,
                 projection_loader: Callable[[NarrativeSubject], VerifiedProjectionView] | None = None) -> None:
        self._artifacts = artifacts
        self._projection_loader = projection_loader

    def read(
        self,
        *,
        document_id: str,
        source_id: str,
        source_sha256: str,
    ) -> NarrativeArtifactRead:
        artifact = self._artifacts.latest_visible_version(
            document_id=document_id,
            source_id=source_id,
            source_sha256=source_sha256,
        )
        if type(artifact.byte_size) is not int or artifact.byte_size <= 0:
            raise NarrativeProjectionError("stored narrative bundle size must be positive")
        artifact, payload = self._artifacts.read_exact(
            artifact_version_id=artifact.artifact_version_id,
            document_id=document_id, source_id=source_id, source_sha256=source_sha256,
            expected_sha256=artifact.content_sha256, expected_size=artifact.byte_size,
        )
        bundle = decode_stored_narrative_bundle(payload)
        source = bundle.source_ref
        if (
            bundle.schema_version not in {LEGACY_BUNDLE.raw_schema, ASSESSED_BUNDLE.raw_schema}
            or source.document_id != artifact.document_id
            or source.source_id != artifact.source_id
            or source.content_sha256 != artifact.source_sha256
            or source.document_id != document_id
            or source.source_id != source_id
            or source.content_sha256 != source_sha256
            or bundle.selection.status != artifact.selection_status
            or bundle.quality_status != artifact.quality_status
            or bundle.expected_read_policy_sha256 != artifact.policy_sha256
        ):
            raise NarrativeProjectionError(
                "stored narrative bundle does not match its source binding"
            )
        return NarrativeArtifactRead(artifact=artifact, bundle=bundle)
    def read_subject(self, *, subject: NarrativeSubject, generation_sha256: str,
                     artifact_version_id: str | None = None) -> NarrativeArtifactRead:
        """Open the exact subject/generation, then replay one fresh source view."""
        if not isinstance(subject, NarrativeSubject):
            raise TypeError("subject must be NarrativeSubject")
        if artifact_version_id is None:
            candidates = self._artifacts.visible_subject_generation_candidates(
                subject=subject, generation_sha256=generation_sha256)
            if not candidates:
                raise NarrativeArtifactNotVisibleError("no visible bundle for exact subject generation")
            artifact_version_id = candidates[0].artifact_version_id
        artifact, payload = self._artifacts.read_current_subject(
            artifact_version_id=artifact_version_id, subject=subject,
            generation_sha256=generation_sha256)
        bundle = decode_stored_narrative_bundle(payload)
        if (bundle.subject.to_dict() != subject.to_dict()
                or bundle.selection.status != artifact.selection_status
                or bundle.quality_status != artifact.quality_status):
            raise NarrativeProjectionError("stored narrative bundle differs from subject artifact")
        if subject.kind == "official_json":
            metadata = json.loads(artifact.metadata_json)
            _, actual_generation = validate_projection_manifest(bundle, metadata.get("generation_manifest"))
            if (actual_generation != generation_sha256
                    or artifact.policy_sha256 != generation_sha256):
                raise NarrativeProjectionError("stored narrative bundle generation differs")
            replay_projected_bundle(bundle, self._projection_loader)
        elif bundle.expected_read_policy_sha256 != artifact.policy_sha256:
            raise NarrativeProjectionError("stored raw bundle policy differs")
        return NarrativeArtifactRead(artifact=artifact, bundle=bundle)


__all__ = [
    "NarrativeArtifactRead", "NarrativeBundleReader", "NarrativeProjectionError",
    "decode_stored_narrative_bundle", "replay_projected_bundle", "validate_projection_manifest",
]
