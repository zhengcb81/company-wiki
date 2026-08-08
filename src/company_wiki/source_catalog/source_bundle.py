"""WU-5.2: SourceBundle — one query returns source + verified artifacts.

``build_source_bundle`` takes the resolved source document and all its
artifacts (any role), validates each artifact through the WU-5.1
fail-closed gates, and returns:

- ``source``: the original handle (lineage anchor);
- ``valid_handles``: role → ArtifactHandle for each PASSING artifact;
- ``invalid``: role → ArtifactHandle(reusable=False) with a reason code;
- ``bundle_hash``: deterministic binding of source + valid handles.

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
    """Validate every artifact for the source; return the bundle."""
    valid: dict[str, ArtifactHandle] = {}
    invalid: dict[str, ArtifactHandle] = {}
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
            valid[role] = handle
        else:
            invalid[role] = handle

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
    return SourceBundle(
        schema_version=SOURCE_BUNDLE_SCHEMA_VERSION,
        source=source,
        valid_handles=valid,
        invalid=invalid,
        bundle_hash=digest.hexdigest(),
    )
