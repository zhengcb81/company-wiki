"""WU-5.1: ArtifactHandle validator — fail-closed artifact consumption gate.

A processed artifact (normalized / summary / sections) is reusable ONLY when
every gate passes:

- status == "completed" (pending / failed / stale rejected);
- source_id == the document's primary source (wrong binding rejected);
- the artifact file exists and its sha256 matches content_sha256;
- generator_name/version are registered in the compatibility registry;
- created_at is not in the future relative to ``now``;
- the artifact path lives inside one of the allowed roots.

Any failure returns an ArtifactHandle with reusable=False and a stable
reason code; nothing is silently trusted.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ARTIFACT_HANDLE_SCHEMA_VERSION = "1.0"
_UTC_RE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")


@dataclass(frozen=True)
class ArtifactHandle:
    schema_version: str
    artifact_id: str
    document_id: str
    source_id: str
    artifact_role: str
    path: str
    content_sha256: str
    generator_name: str
    generator_version: str
    reusable: bool
    reason: str | None = None
    as_of_date: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "artifact_id": self.artifact_id,
            "document_id": self.document_id,
            "source_id": self.source_id,
            "artifact_role": self.artifact_role,
            "path": self.path,
            "content_sha256": self.content_sha256,
            "generator_name": self.generator_name,
            "generator_version": self.generator_version,
            "reusable": self.reusable,
            "reason": self.reason,
            "as_of_date": self.as_of_date,
        }


def _reject(artifact: dict[str, Any], reason: str) -> ArtifactHandle:
    return ArtifactHandle(
        schema_version=ARTIFACT_HANDLE_SCHEMA_VERSION,
        artifact_id=str(artifact.get("artifact_id") or ""),
        document_id=str(artifact.get("document_id") or ""),
        source_id=str(artifact.get("source_id") or ""),
        artifact_role=str(artifact.get("artifact_role") or ""),
        path=str(artifact.get("path") or ""),
        content_sha256=str(artifact.get("content_sha256") or ""),
        generator_name=str(artifact.get("generator_name") or ""),
        generator_version=str(artifact.get("generator_version") or ""),
        reusable=False,
        reason=reason,
    )


def validate_artifact(
    artifact: dict[str, Any],
    *,
    source: dict[str, Any],
    registry: dict[str, set[str]],
    allowed_roots: tuple[Path, ...],
    now: str,
) -> ArtifactHandle:
    """Return an ArtifactHandle; reusable=True only when every gate passes."""
    status = str(artifact.get("status") or "")
    if status != "completed":
        return _reject(artifact, "artifact_status_not_completed")
    schema = str(artifact.get("schema_version") or "")
    if schema != ARTIFACT_HANDLE_SCHEMA_VERSION:
        return _reject(artifact, "artifact_schema_unsupported")
    source_id = str(artifact.get("source_id") or "")
    if source_id != str(source.get("primary_source_id") or ""):
        return _reject(artifact, "artifact_source_binding_mismatch")
    # The artifact must derive from the exact source bytes the catalog holds
    # (wrong source_sha = stale/mismatched derivation even with matching id).
    # A missing source_sha is also rejected (fail-closed): an artifact that
    # cannot prove its source-byte binding must never be reusable.
    artifact_source_sha = str(artifact.get("source_sha256") or "")
    if not artifact_source_sha:
        return _reject(artifact, "artifact_source_sha_missing")
    if artifact_source_sha != str(source.get("source_sha256") or ""):
        return _reject(artifact, "artifact_source_sha_mismatch")
    path = Path(str(artifact.get("path") or ""))
    if not path.is_file():
        return _reject(artifact, "artifact_file_missing")
    expected_sha = str(artifact.get("content_sha256") or "")
    if len(expected_sha) != 64 or not all(c in "0123456789abcdef" for c in expected_sha):
        return _reject(artifact, "artifact_hash_malformed")
    actual_sha = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual_sha != expected_sha:
        return _reject(artifact, "artifact_hash_mismatch")
    generator = str(artifact.get("generator_name") or "")
    version = str(artifact.get("generator_version") or "")
    if generator not in registry or version not in registry.get(generator, set()):
        return _reject(artifact, "artifact_generator_unregistered")
    created_at = str(artifact.get("created_at") or "")
    if not created_at or not _UTC_RE.fullmatch(created_at):
        return _reject(artifact, "artifact_created_at_malformed")
    if created_at > now:
        return _reject(artifact, "artifact_created_at_future")
    as_of = str(source.get("as_of_date") or "")
    if as_of and as_of > now[:10]:
        return _reject(artifact, "artifact_source_as_of_future")
    resolved = path.resolve(strict=False)
    if not any(
        resolved == root.resolve(strict=False)
        or root.resolve(strict=False) in resolved.parents
        for root in allowed_roots
    ):
        return _reject(artifact, "artifact_path_outside_allowed_root")
    return ArtifactHandle(
        schema_version=ARTIFACT_HANDLE_SCHEMA_VERSION,
        artifact_id=str(artifact.get("artifact_id") or ""),
        document_id=str(artifact.get("document_id") or ""),
        source_id=source_id,
        artifact_role=str(artifact.get("artifact_role") or ""),
        path=str(path),
        content_sha256=expected_sha,
        generator_name=generator,
        generator_version=version,
        reusable=True,
        as_of_date=str(source.get("as_of_date") or ""),
    )
