"""ZR-304: unique artifact read model — one production read semantics.

Normalizes the three artifact evidence sources into ONE read path:

1. ``artifact_bindings`` (when a binding row exists: its source_id /
   content_sha256 / bundle_hash / visibility_state are authoritative);
2. ``artifacts`` columns (+ metadata_json) when no binding row exists —
   returned honestly marked ``binding='legacy'``;
3. source SHA is MANDATORY on both paths: a row without
   content_sha256/source_sha256 is not readable (fail closed);
4. unknown artifact_role / generator_version is rejected by the
   ArtifactHandle validator (fail closed, never a silent reusable).

Shadow only: reads exclusively through the zero-write ``CatalogReader``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .artifact_handle import ArtifactHandle, validate_artifact
from .reader import CatalogReader

ARTIFACT_READ_MODEL_SCHEMA_VERSION = "1.0"
ARTIFACT_READ_MODEL_SCHEMA = "artifact-read-model-1.0"

# Canonical artifact roles come from the frozen source_bundle taxonomy
# (single source of truth — never re-declared here): an unknown role is
# never silently read — fail closed.
from .source_bundle import KNOWN_ARTIFACT_ROLES  # noqa: E402


@dataclass(frozen=True)
class ReadableArtifact:
    """One normalized artifact with its authoritative binding."""

    artifact_id: str
    document_id: str
    source_id: str
    artifact_role: str
    path: str
    content_sha256: str
    generator_name: str
    generator_version: str
    status: str
    binding: str  # 'bound' | 'legacy'
    bundle_hash: str | None = None
    visibility_state: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": ARTIFACT_READ_MODEL_SCHEMA_VERSION,
            "artifact_id": self.artifact_id,
            "document_id": self.document_id,
            "source_id": self.source_id,
            "artifact_role": self.artifact_role,
            "path": self.path,
            "content_sha256": self.content_sha256,
            "generator_name": self.generator_name,
            "generator_version": self.generator_version,
            "status": self.status,
            "binding": self.binding,
            "bundle_hash": self.bundle_hash,
            "visibility_state": self.visibility_state,
        }


def _binding_row(reader: CatalogReader, artifact_id: str) -> dict[str, Any] | None:
    row = reader.fetchone(
        "SELECT binding_id, artifact_id, source_id, document_id, "
        "content_sha256, generator_name, generator_version, bundle_hash, "
        "visibility_state FROM artifact_bindings WHERE artifact_id=?",
        (artifact_id,),
    )
    if row is None:
        return None
    return {
        "source_id": str(row["source_id"]),
        "document_id": str(row["document_id"]),
        "content_sha256": str(row["content_sha256"]),
        "generator_name": str(row["generator_name"]),
        "generator_version": str(row["generator_version"]),
        "bundle_hash": str(row["bundle_hash"]),
        "visibility_state": str(row["visibility_state"]),
    }


def _artifact_row(reader: CatalogReader, artifact_id: str) -> dict[str, Any] | None:
    row = reader.fetchone(
        "SELECT artifact_id, document_id, source_id, artifact_role, path, "
        "content_sha256, byte_size, mime_type, generator_name, "
        "generator_version, status, metadata_json, created_at "
        "FROM artifacts WHERE artifact_id=?",
        (artifact_id,),
    )
    if row is None:
        return None
    artifact = dict(row)
    # schema_version + source_sha256 live in the producer metadata; the
    # artifacts table has no such columns (same convention as backfill).
    import json

    try:
        metadata = json.loads(str(artifact.get("metadata_json") or "{}"))
        if isinstance(metadata, dict):
            if "schema_version" in metadata:
                artifact["schema_version"] = metadata["schema_version"]
            if "source_sha256" in metadata:
                artifact["source_sha256"] = metadata["source_sha256"]
    except json.JSONDecodeError:
        pass
    return artifact


def _text(value: Any) -> str:
    return str(value or "")


def _merged_fields(
    artifact: dict[str, Any], binding: dict[str, Any] | None,
) -> tuple[str, str, str, str]:
    """(source_id, content_sha, generator_name, generator_version) —
    binding-authoritative when present, artifacts columns otherwise."""
    if binding is not None:
        return (
            _text(binding["source_id"]),
            _text(binding["content_sha256"]),
            _text(binding["generator_name"]),
            _text(binding["generator_version"]),
        )
    return (
        _text(artifact.get("source_id")),
        _text(artifact.get("content_sha256")),
        _text(artifact.get("generator_name")),
        _text(artifact.get("generator_version")),
    )


def _source_sha(reader: CatalogReader, source_id: str) -> str:
    row = reader.fetchone(
        "SELECT content_sha256 FROM sources WHERE source_id=?",
        (source_id,),
    )
    return _text(row["content_sha256"]) if row is not None else ""


def _artifact_dict(
    artifact_id: str, artifact: dict[str, Any], role: str,
    source_id: str, content_sha: str, generator_name: str, generator_version: str,
) -> dict[str, Any]:
    return {
        "artifact_id": artifact_id,
        "document_id": _text(artifact.get("document_id")),
        "source_id": source_id,
        "artifact_role": role,
        "path": _text(artifact.get("path")),
        "content_sha256": content_sha,
        "byte_size": artifact.get("byte_size") or 0,
        "mime_type": _text(artifact.get("mime_type")),
        "generator_name": generator_name,
        "generator_version": generator_version,
        "status": _text(artifact.get("status")),
        "created_at": _text(artifact.get("created_at")),
        "schema_version": _text(artifact.get("schema_version")),
        "source_sha256": _text(artifact.get("source_sha256")),
    }


def read_artifact(
    reader: CatalogReader,
    artifact_id: str,
    *,
    allowed_roots: tuple = (),
    now: str = "2099-12-31T23:59:59Z",
    registry: dict | None = None,
) -> ReadableArtifact | None:
    """Read ONE artifact through the normalized model.

    Returns None when the artifact row does not exist.  Raises
    ``ValueError`` (fail closed) when the row is unreadable: unknown role,
    no source SHA, or the ArtifactHandle validator rejects it.
    """
    artifact = _artifact_row(reader, artifact_id)
    if artifact is None:
        return None
    role = _text(artifact.get("artifact_role"))
    if role not in KNOWN_ARTIFACT_ROLES:
        raise ValueError(f"artifact {artifact_id} has unknown role {role!r} (fail closed)")
    binding = _binding_row(reader, artifact_id)
    source_id, content_sha, generator_name, generator_version = _merged_fields(
        artifact, binding
    )
    if not source_id:
        raise ValueError(f"artifact {artifact_id} has no source_id (fail closed)")
    if not content_sha:
        raise ValueError(f"artifact {artifact_id} has no content_sha256 (fail closed)")
    handle: ArtifactHandle = validate_artifact(
        _artifact_dict(
            artifact_id, artifact, role, source_id, content_sha,
            generator_name, generator_version,
        ),
        source={
            "document_id": _text(artifact.get("document_id")),
            "primary_source_id": source_id,
            "source_sha256": _source_sha(reader, source_id),
            "as_of_date": "",
        },
        registry=registry or {},
        allowed_roots=allowed_roots,
        now=now,
    )
    if not handle.reusable:
        raise ValueError(f"artifact {artifact_id} is not reusable: {handle.reason}")
    return ReadableArtifact(
        artifact_id=artifact_id,
        document_id=_text(binding["document_id"] if binding else artifact.get("document_id")),
        source_id=source_id,
        artifact_role=role,
        path=_text(artifact.get("path")),
        content_sha256=content_sha,
        generator_name=generator_name,
        generator_version=generator_version,
        status=_text(artifact.get("status")),
        binding="bound" if binding is not None else "legacy",
        bundle_hash=binding["bundle_hash"] if binding else None,
        visibility_state=binding["visibility_state"] if binding else None,
    )


def read_artifacts(
    reader: CatalogReader,
    document_id: str,
    *,
    allowed_roots: tuple = (),
    now: str = "2099-12-31T23:59:59Z",
    registry: dict | None = None,
) -> list[ReadableArtifact]:
    """Read ALL artifacts of a document through the normalized model.

    An unreadable artifact row (no source SHA / rejected by the
    validator) raises — fail closed: a consumer must never silently lose
    an artifact.
    """
    rows = reader.fetchall(
        "SELECT artifact_id FROM artifacts WHERE document_id=? "
        "ORDER BY created_at, artifact_id",
        (document_id,),
    )
    result: list[ReadableArtifact] = []
    for row in rows:
        artifact = read_artifact(
            reader,
            str(row["artifact_id"]),
            allowed_roots=allowed_roots,
            now=now,
            registry=registry,
        )
        if artifact is not None:
            result.append(artifact)
    return result


__all__ = [
    "ARTIFACT_READ_MODEL_SCHEMA",
    "ARTIFACT_READ_MODEL_SCHEMA_VERSION",
    "ReadableArtifact",
    "read_artifact",
    "read_artifacts",
]
