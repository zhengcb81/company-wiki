"""Deterministic, add-only export bundles for immutable source contracts."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
from typing import Any, TypeVar

from .evidence_span import EVIDENCE_SPAN_SCHEMA_VERSION, EvidenceSpan
from .source_manifest import SOURCE_MANIFEST_SCHEMA_VERSION, SourceManifest


SOURCE_EXPORT_SCHEMA_VERSION = "1.0.0"
SOURCE_EXPORT_ID_PREFIX = "urn:company-wiki:source-export:sha256:"

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_EXPORT_ID_RE = re.compile(
    rf"^{re.escape(SOURCE_EXPORT_ID_PREFIX)}[0-9a-f]{{64}}$"
)
_BUNDLE_FIELDS = {
    "schema_version",
    "export_id",
    "bundle_sha256",
    "source_manifest_schema_version",
    "evidence_span_schema_version",
    "counts",
    "manifests",
    "evidence_spans",
}


class SourceExportError(ValueError):
    """Base error for invalid or unsafe source exports."""


class SourceExportConflictError(SourceExportError):
    """Raised when add-only merge inputs disagree about an existing identity."""


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _canonical_sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _payload_dict(
    manifests: Sequence[SourceManifest],
    evidence_spans: Sequence[EvidenceSpan],
) -> dict[str, Any]:
    return {
        "schema_version": SOURCE_EXPORT_SCHEMA_VERSION,
        "source_manifest_schema_version": SOURCE_MANIFEST_SCHEMA_VERSION,
        "evidence_span_schema_version": EVIDENCE_SPAN_SCHEMA_VERSION,
        "counts": {
            "source_manifests": len(manifests),
            "evidence_spans": len(evidence_spans),
        },
        "manifests": [item.to_dict() for item in manifests],
        "evidence_spans": [item.to_dict() for item in evidence_spans],
    }


def _require_sequence(value: Any, field_name: str) -> Sequence[Any]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise TypeError(f"{field_name} must be an array")
    return value


T = TypeVar("T", SourceManifest, EvidenceSpan)


def _merge_by_identity(
    existing: Sequence[T],
    incoming: Sequence[T],
    *,
    identity_name: str,
    label: str,
) -> tuple[T, ...]:
    merged: dict[str, T] = {}
    canonical: dict[str, str] = {}
    for item in (*existing, *incoming):
        identity = getattr(item, identity_name)
        text = item.canonical_json()
        if identity in merged and canonical[identity] != text:
            raise SourceExportConflictError(
                f"{label} conflict for existing identity {identity}"
            )
        merged[identity] = item
        canonical[identity] = text
    return tuple(merged[key] for key in sorted(merged))


def _validate_relationships(
    manifests: Sequence[SourceManifest],
    evidence_spans: Sequence[EvidenceSpan],
) -> None:
    source_ids = {item.source_id for item in manifests}
    orphan_ids = sorted(
        item.span_id for item in evidence_spans if item.source_id not in source_ids
    )
    if orphan_ids:
        raise SourceExportError(f"orphan evidence spans: {orphan_ids}")

    by_locator: dict[tuple[str, str], EvidenceSpan] = {}
    for item in evidence_spans:
        key = (item.source_id, item.locator)
        existing = by_locator.get(key)
        if existing is not None and existing.span_id != item.span_id:
            raise SourceExportConflictError(
                f"locator conflict for source {item.source_id}: {item.locator}"
            )
        by_locator[key] = item


def _resolve_root(root: Path) -> Path:
    if not isinstance(root, Path):
        raise TypeError("root must be pathlib.Path")
    resolved = root.resolve(strict=True)
    if not resolved.is_dir():
        raise SourceExportError("root must be an existing directory")
    return resolved


@dataclass(frozen=True)
class SourceExportBundle:
    """A content-addressed snapshot of manifests and evidence spans."""

    schema_version: str
    export_id: str
    bundle_sha256: str
    source_manifest_schema_version: str
    evidence_span_schema_version: str
    manifests: tuple[SourceManifest, ...]
    evidence_spans: tuple[EvidenceSpan, ...]

    def __post_init__(self) -> None:
        if self.schema_version != SOURCE_EXPORT_SCHEMA_VERSION:
            raise SourceExportError(
                f"schema_version must be {SOURCE_EXPORT_SCHEMA_VERSION}"
            )
        if self.source_manifest_schema_version != SOURCE_MANIFEST_SCHEMA_VERSION:
            raise SourceExportError(
                "source_manifest_schema_version is not supported"
            )
        if self.evidence_span_schema_version != EVIDENCE_SPAN_SCHEMA_VERSION:
            raise SourceExportError("evidence_span_schema_version is not supported")
        if not isinstance(self.manifests, tuple) or not all(
            isinstance(item, SourceManifest) for item in self.manifests
        ):
            raise TypeError("manifests must be a tuple of SourceManifest values")
        if not isinstance(self.evidence_spans, tuple) or not all(
            isinstance(item, EvidenceSpan) for item in self.evidence_spans
        ):
            raise TypeError("evidence_spans must be a tuple of EvidenceSpan values")

        manifest_ids = [item.source_id for item in self.manifests]
        if manifest_ids != sorted(set(manifest_ids)):
            raise SourceExportError("manifests must be sorted and unique by source_id")
        span_ids = [item.span_id for item in self.evidence_spans]
        if span_ids != sorted(set(span_ids)):
            raise SourceExportError("evidence_spans must be sorted and unique by span_id")
        _validate_relationships(self.manifests, self.evidence_spans)

        if not isinstance(self.bundle_sha256, str) or not _SHA256_RE.fullmatch(
            self.bundle_sha256
        ):
            raise SourceExportError(
                "bundle_sha256 must be a lowercase 64-character SHA-256"
            )
        expected_hash = _canonical_sha256(
            _payload_dict(self.manifests, self.evidence_spans)
        )
        if self.bundle_sha256 != expected_hash:
            raise SourceExportError("bundle_sha256 must match canonical bundle payload")
        if not isinstance(self.export_id, str) or not _EXPORT_ID_RE.fullmatch(
            self.export_id
        ):
            raise SourceExportError("export_id must be the canonical SHA-256 URN")
        if self.export_id != SOURCE_EXPORT_ID_PREFIX + expected_hash:
            raise SourceExportError("export_id must match bundle_sha256")

    @property
    def counts(self) -> dict[str, int]:
        return {
            "source_manifests": len(self.manifests),
            "evidence_spans": len(self.evidence_spans),
        }

    @classmethod
    def build(
        cls,
        *,
        root: Path,
        manifests: Sequence[SourceManifest],
        evidence_spans: Sequence[EvidenceSpan],
        base: "SourceExportBundle | None" = None,
    ) -> "SourceExportBundle":
        root_resolved = _resolve_root(root)
        if base is not None and not isinstance(base, cls):
            raise TypeError("base must be SourceExportBundle or null")
        manifests = _require_sequence(manifests, "manifests")
        evidence_spans = _require_sequence(evidence_spans, "evidence_spans")
        if not all(isinstance(item, SourceManifest) for item in manifests):
            raise TypeError("manifests must contain SourceManifest values")
        if not all(isinstance(item, EvidenceSpan) for item in evidence_spans):
            raise TypeError("evidence_spans must contain EvidenceSpan values")

        merged_manifests = _merge_by_identity(
            base.manifests if base else (),
            manifests,
            identity_name="source_id",
            label="manifest",
        )
        merged_spans = _merge_by_identity(
            base.evidence_spans if base else (),
            evidence_spans,
            identity_name="span_id",
            label="span",
        )
        _validate_relationships(merged_manifests, merged_spans)

        for manifest in merged_manifests:
            source_path = root_resolved.joinpath(
                *PurePosixPath(manifest.original_path).parts
            )
            manifest.verify_file(root=root_resolved, file_path=source_path)

        payload = _payload_dict(merged_manifests, merged_spans)
        bundle_sha256 = _canonical_sha256(payload)
        return cls(
            schema_version=SOURCE_EXPORT_SCHEMA_VERSION,
            export_id=SOURCE_EXPORT_ID_PREFIX + bundle_sha256,
            bundle_sha256=bundle_sha256,
            source_manifest_schema_version=SOURCE_MANIFEST_SCHEMA_VERSION,
            evidence_span_schema_version=EVIDENCE_SPAN_SCHEMA_VERSION,
            manifests=merged_manifests,
            evidence_spans=merged_spans,
        )

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "SourceExportBundle":
        if not isinstance(data, Mapping):
            raise TypeError("source export input must be an object")
        supplied = set(data)
        unknown = supplied - _BUNDLE_FIELDS
        if unknown:
            raise SourceExportError(f"source export unknown fields: {sorted(unknown)}")
        missing = _BUNDLE_FIELDS - supplied
        if missing:
            raise SourceExportError(f"source export missing fields: {sorted(missing)}")

        manifests = tuple(
            SourceManifest.from_dict(item)
            for item in _require_sequence(data["manifests"], "manifests")
        )
        evidence_spans = tuple(
            EvidenceSpan.from_dict(item)
            for item in _require_sequence(data["evidence_spans"], "evidence_spans")
        )
        bundle = cls(
            schema_version=data["schema_version"],
            export_id=data["export_id"],
            bundle_sha256=data["bundle_sha256"],
            source_manifest_schema_version=data[
                "source_manifest_schema_version"
            ],
            evidence_span_schema_version=data["evidence_span_schema_version"],
            manifests=manifests,
            evidence_spans=evidence_spans,
        )
        counts = data["counts"]
        if not isinstance(counts, Mapping) or set(counts) != {
            "source_manifests",
            "evidence_spans",
        }:
            raise SourceExportError("counts must contain exact v1 count fields")
        if any(
            isinstance(value, bool) or not isinstance(value, int) or value < 0
            for value in counts.values()
        ):
            raise SourceExportError("counts values must be non-negative integers")
        if dict(counts) != bundle.counts:
            raise SourceExportError("counts must match exported records")
        return bundle

    def verify_sources(self, *, root: Path) -> None:
        root_resolved = _resolve_root(root)
        for manifest in self.manifests:
            source_path = root_resolved.joinpath(
                *PurePosixPath(manifest.original_path).parts
            )
            manifest.verify_file(root=root_resolved, file_path=source_path)

    def to_dict(self) -> dict[str, Any]:
        payload = _payload_dict(self.manifests, self.evidence_spans)
        return {
            "schema_version": self.schema_version,
            "export_id": self.export_id,
            "bundle_sha256": self.bundle_sha256,
            "source_manifest_schema_version": payload[
                "source_manifest_schema_version"
            ],
            "evidence_span_schema_version": payload[
                "evidence_span_schema_version"
            ],
            "counts": payload["counts"],
            "manifests": payload["manifests"],
            "evidence_spans": payload["evidence_spans"],
        }

    def canonical_json(self) -> str:
        return _canonical_json(self.to_dict())
