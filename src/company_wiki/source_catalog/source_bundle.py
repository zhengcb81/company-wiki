"""WU-5.2: SourceBundle — one query returns source + verified artifacts.

``build_source_bundle`` takes the resolved source document and all its
artifacts (any role), validates each artifact through the WU-5.1
fail-closed gates, and returns:

- ``source``: the original handle (lineage anchor);
- ``valid_handles``: role → ArtifactHandle for each PASSING artifact;
- ``invalid``: role → ArtifactHandle(reusable=False) with a reason code;
- ``bundle_hash``: deterministic binding of source + valid handles +
  invalid role/reason.

An invalid artifact never contaminates a still-valid original or a sibling
role: only the failed role is unusable. Consumers must use the bundle hash
in their own receipts so a role silently changing state is observable.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .artifact_handle import ArtifactHandle, validate_artifact


SOURCE_BUNDLE_SCHEMA_VERSION = "1.0"


@dataclass(frozen=True)
class SourceBundle:
    schema_version: str
    source: dict[str, Any]
    valid_handles: dict[str, ArtifactHandle] = field(default_factory=dict)
    invalid: dict[str, ArtifactHandle] = field(default_factory=dict)
    bundle_hash: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "source": self.source,
            "valid_handles": {
                role: handle.to_dict() for role, handle in self.valid_handles.items()
            },
            "invalid": {
                role: handle.to_dict() for role, handle in self.invalid.items()
            },
            "bundle_hash": self.bundle_hash,
        }


def build_source_bundle(
    *,
    source: dict[str, Any],
    artifacts: list[dict[str, Any]],
    registry: dict[str, set[str]],
    allowed_roots: tuple[Path, ...],
    now: str,
) -> SourceBundle:
    """Validate every artifact for the source; return the bundle.

    Same-role duplicates (reviewer): when a role has several artifacts, the
    newest VALID one wins; any other valid same-role artifact is recorded as
    superseded in ``invalid`` (deterministic, never silent). The bundle hash
    binds source + valid handles + invalid role/reason so a role changing
    state is observable.
    """
    valid: dict[str, ArtifactHandle] = {}
    invalid: dict[str, ArtifactHandle] = {}
    invalid_keys: dict[str, tuple[str, str]] = {}
    valid_by_role: dict[str, list[tuple[ArtifactHandle, str]]] = {}
    for artifact in artifacts:
        role = str(artifact.get("artifact_role") or "unknown")
        handle = validate_artifact(
            artifact,
            source=source,
            registry=registry,
            allowed_roots=allowed_roots,
            now=now,
        )
        if handle.reusable:
            # keep (handle, created_at) so same-role selection is ordered by
            # the artifact's actual creation time, not handle internals.
            valid_by_role.setdefault(role, []).append(
                (handle, str(artifact.get("created_at") or ""))
            )
        else:
            # Deterministic failing-handle selection per role: the one with
            # the earliest (created_at, artifact_id) — input order never
            # changes which explanation the bundle carries.
            key = (str(artifact.get("created_at") or ""), handle.artifact_id)
            previous = invalid_keys.get(role)
            if previous is None or key < previous:
                invalid[role] = handle
                invalid_keys[role] = key
    for role, entries in valid_by_role.items():
        newest, _ = max(entries, key=lambda pair: (pair[1], pair[0].content_sha256))
        valid[role] = newest
        for handle, _ in entries:
            if handle is not newest:
                invalid[role] = _superseded(handle)

    digest = hashlib.sha256()
    digest.update(SOURCE_BUNDLE_SCHEMA_VERSION.encode())
    digest.update(str(source.get("document_id") or "").encode())
    digest.update(str(source.get("primary_source_id") or "").encode())
    digest.update(str(source.get("source_sha256") or "").encode())
    for role in sorted(valid):
        handle = valid[role]
        digest.update(role.encode())
        digest.update(handle.content_sha256.encode())
        digest.update(handle.generator_name.encode())
        digest.update(handle.generator_version.encode())
    for role in sorted(invalid):
        handle = invalid[role]
        digest.update(b"invalid:")
        digest.update(role.encode())
        digest.update((handle.reason or "").encode())
    return SourceBundle(
        schema_version=SOURCE_BUNDLE_SCHEMA_VERSION,
        source=source,
        valid_handles=valid,
        invalid=invalid,
        bundle_hash=digest.hexdigest(),
    )


def _superseded(handle: ArtifactHandle) -> ArtifactHandle:
    """Mark an older valid same-role artifact as superseded."""
    return ArtifactHandle(
        schema_version=handle.schema_version,
        artifact_id=handle.artifact_id,
        document_id=handle.document_id,
        source_id=handle.source_id,
        artifact_role=handle.artifact_role,
        path=handle.path,
        content_sha256=handle.content_sha256,
        generator_name=handle.generator_name,
        generator_version=handle.generator_version,
        reusable=False,
        reason="artifact_superseded_by_newer",
        as_of_date=handle.as_of_date,
    )
