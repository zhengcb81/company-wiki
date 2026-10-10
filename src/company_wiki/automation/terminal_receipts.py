"""Compact published terminal DAGs after checking their exact final artifact."""

from __future__ import annotations

from collections.abc import Callable
import hashlib
import json

from company_wiki.source_catalog.lock import CatalogOperationLock
from company_wiki.source_catalog.narrative_artifact_store import (
    NarrativeArtifactConflictError,
    NarrativeArtifactStore,
    NarrativeArtifactVersion,
)

from .models import canonical_json, require_canonical_json, require_utc_timestamp
from company_wiki.narrative_subject import NarrativeSubject
from .narrative_official_json import VerifiedProjectionView
from .narrative_projection import NarrativeBundleReader
from .narrative_contracts import NarrativeBundle
from .store import AutomationStore
from .terminal_receipt_contracts import (
    FinalArtifactPin,
    TerminalCompactionResult,
    terminal_job_scope,
)


def _matches(version: NarrativeArtifactVersion, pin: FinalArtifactPin) -> bool:
    if pin.subject_binding is not None:
        try:
            metadata = json.loads(version.metadata_json)
            if (metadata.get("subject_binding") != pin.subject_binding.to_dict()
                    or metadata.get("generation_sha256") != pin.generation_sha256):
                return False
        except (ValueError, TypeError, AttributeError):
            return False
    return (
        version.effect_id,
        version.artifact_version_id,
        version.content_sha256,
        version.byte_size,
        version.document_id,
        version.source_id,
        version.source_sha256,
    ) == (
        pin.effect_id,
        pin.artifact_version_id,
        pin.artifact_sha256,
        pin.byte_size,
        pin.document_id,
        pin.source_id,
        pin.source_sha256,
    )


def compact_terminal_narrative_jobs(
    automation: AutomationStore,
    artifacts: NarrativeArtifactStore,
    *,
    job_ids: tuple[str, ...],
    final_artifact: FinalArtifactPin,
    compacted_at: str,
    projection_loader: Callable[[NarrativeSubject], VerifiedProjectionView] | None = None,
) -> TerminalCompactionResult:
    """Read/hash outside the lock; recheck visibility and commit under a short lock."""
    scope = terminal_job_scope(job_ids)
    if not scope:
        return TerminalCompactionResult((), 0, 0, 0)
    if not isinstance(final_artifact, FinalArtifactPin):
        raise TypeError("final_artifact must be FinalArtifactPin")
    require_utc_timestamp(compacted_at)
    if final_artifact.subject_binding is not None:
        if final_artifact.generation_sha256 is None:
            raise NarrativeArtifactConflictError("projected final pin has no generation")
        read = NarrativeBundleReader(artifacts, projection_loader=projection_loader).read_subject(
            artifact_version_id=final_artifact.artifact_version_id,
            subject=final_artifact.subject_binding, generation_sha256=final_artifact.generation_sha256)
        version = read.artifact
        data = canonical_json(read.bundle.to_dict()).encode("utf-8")
    else:
        version, data = artifacts.read_exact(
            artifact_version_id=final_artifact.artifact_version_id,
            document_id=final_artifact.document_id,
            source_id=final_artifact.source_id,
            source_sha256=final_artifact.source_sha256,
            expected_sha256=final_artifact.artifact_sha256,
            expected_size=final_artifact.byte_size,
        )
    if (
        not _matches(version, final_artifact)
        or len(data) != final_artifact.byte_size
        or (hashlib.sha256(data).hexdigest() != final_artifact.artifact_sha256)
    ):
        raise NarrativeArtifactConflictError(
            "final artifact does not match its exact effect pin"
        )
    text = data.decode("utf-8", errors="strict")
    require_canonical_json(text)
    bundle = NarrativeBundle.from_dict(json.loads(text))
    if final_artifact.subject_binding is not None:
        if bundle.subject.to_dict() != final_artifact.subject_binding.to_dict():
            raise NarrativeArtifactConflictError("final bundle subject differs from its pin")
    elif (
        bundle.source_ref.document_id,
        bundle.source_ref.source_id,
        bundle.source_ref.content_sha256,
    ) != (
        final_artifact.document_id,
        final_artifact.source_id,
        final_artifact.source_sha256,
    ):
        raise NarrativeArtifactConflictError("final bundle source differs from its pin")
    with CatalogOperationLock(
        artifacts.catalog_dir, operation="narrative-terminal-compaction"
    ):
        current = artifacts.visible_version_for_effect(final_artifact.effect_id)
        if not _matches(current, final_artifact):
            raise NarrativeArtifactConflictError(
                "final artifact changed before terminal compaction"
            )
        return automation.compact_terminal_narrative_jobs(
            job_ids=scope,
            final_artifact=final_artifact,
            compacted_at=compacted_at,
        )


__all__ = ["compact_terminal_narrative_jobs"]
