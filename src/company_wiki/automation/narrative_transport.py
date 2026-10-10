"""Read exact persistent narrative artifacts through the source byte broker."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
import sqlite3
from typing import Any

from company_wiki.narrative_subject import NarrativeSubject
from company_wiki.source_catalog.official_json_projection import ProjectionError
from company_wiki.source_catalog.narrative_artifact_store import (
    NarrativeArtifactError,
    NarrativeArtifactConflictError,
    NarrativeArtifactNotVisibleError,
    NarrativeArtifactStore,
    NarrativeArtifactReader,
    NarrativeArtifactVersion,
    NarrativeObjectIntegrityError,
    NarrativeSourceNotCurrentError,
)
from company_wiki.source_catalog.source_reader import (
    SourceReadError,
    SourceRef,
    SourceVersionReader,
)
from company_wiki.source_catalog.reader import CatalogReaderUnavailable
from company_wiki.source_catalog.narrative_normalization import (
    NarrativeNormalization,
    PPTX_MIME,
)
from company_wiki.source_catalog.qualification import qualify_source

from .models import canonical_json, require_canonical_json
from .narrative_contracts import (
    NarrativeBundle,
    NarrativeContractError,
    SourceRefValue,
    assert_no_physical_paths,
)
from .narrative_official_json import (
    OfficialProjectionAdapterError,
    VerifiedProjectionView,
)
from .narrative_replay import (
    NarrativeReplayError,
    replay_narrative_evidence,
    replay_verified_projection,
)
from .narrative_transport_contracts import (
    MAX_RECEIPT_BYTES,
    NARRATIVE_READ_RECEIPT_SCHEMA,
    NARRATIVE_REF_SCHEMA,
    NARRATIVE_PROJECTED_REF_SCHEMA,
    NARRATIVE_PROJECTED_READ_RECEIPT_SCHEMA,
    parse_projected_reference_request,
    NarrativeReadRequest,
    NarrativeRef,
    NarrativeTransportError,
)


@dataclass(frozen=True)
class NarrativeTransportRead:
    data: bytes
    receipt: dict[str, Any]


def _artifact_error(error: NarrativeArtifactError) -> NarrativeTransportError:
    if isinstance(error, NarrativeArtifactConflictError):
        return NarrativeTransportError("unavailable", "artifact_reference_mismatch")
    if isinstance(error, NarrativeSourceNotCurrentError):
        return NarrativeTransportError("blocked", "source_not_current")
    if isinstance(error, NarrativeArtifactNotVisibleError):
        return NarrativeTransportError("not_found", "narrative_artifact_not_visible")
    if isinstance(error, NarrativeObjectIntegrityError):
        return NarrativeTransportError("unavailable", "narrative_artifact_corrupt")
    return NarrativeTransportError("unavailable", "narrative_artifact_unavailable")


def _require_historical_source(manifest: dict[str, Any], as_of_date: str) -> None:
    """Historical availability follows publication, independent of download time."""
    qualification = qualify_source(
        manifest.get("published_date"), as_of_date=as_of_date
    )
    reason = {
        "unknown": "source_publication_unknown",
        "invalid": "source_publication_invalid",
        "after_as_of": "source_after_as_of",
    }.get(qualification.publication_status)
    if reason:
        raise NarrativeTransportError("blocked", reason)


def _require_manifest(
    manifest: dict[str, Any],
    request: NarrativeReadRequest,
    bundle: NarrativeBundle,
) -> None:
    source = request.narrative_ref.source_ref
    if source is None:
        raise NarrativeContractError("raw manifest requires a raw source reference")
    bound_fields = dict(source.to_dict())
    bound_fields.pop("schema_version")
    if any(manifest.get(key) != value for key, value in bound_fields.items()):
        raise NarrativeTransportError("blocked", "source_identity_mismatch")
    if any(
        value is not None and manifest.get(key) != value
        for key, value in request.expected_source.items()
    ):
        raise NarrativeTransportError("blocked", "source_identity_mismatch")
    if request.as_of_date is not None:
        _require_historical_source(manifest, request.as_of_date)


def _bound_bundle(
    version: NarrativeArtifactVersion,
    data: bytes,
    reference: NarrativeRef,
) -> NarrativeBundle:
    if (
        version.content_sha256 != reference.artifact_sha256
        or version.byte_size != reference.byte_size
        or len(data) != reference.byte_size
        or hashlib.sha256(data).hexdigest() != reference.artifact_sha256
    ):
        raise NarrativeTransportError("unavailable", "artifact_reference_mismatch")
    try:
        text = data.decode("utf-8", errors="strict")
        require_canonical_json(text)
        bundle = NarrativeBundle.from_dict(json.loads(text))
    except (UnicodeDecodeError, TypeError, ValueError) as exc:
        raise NarrativeTransportError(
            "unavailable", "narrative_bundle_invalid"
        ) from exc
    if (
        bundle.subject != reference.subject
        or bundle.selection.status != version.selection_status
        or bundle.quality_status != version.quality_status
    ):
        raise NarrativeTransportError("blocked", "artifact_source_mismatch")
    return bundle


class NarrativeTransportReader:
    """Export bounded bundles only after current source and locator verification."""

    def __init__(
        self,
        artifacts: NarrativeArtifactStore | NarrativeArtifactReader,
        reader: SourceVersionReader,
        *,
        normalization: NarrativeNormalization | None = None,
        projection_loader: Callable[[NarrativeSubject], VerifiedProjectionView]
        | None = None,
    ):
        self._artifacts = artifacts
        self._reader = reader
        self._normalization = normalization
        self._projection_loader = projection_loader

    def _current_ref(self, value: SourceRefValue) -> SourceRef:
        current = self._reader.query_ref(
            value.document_id,
            value.source_id,
            value.content_sha256,
        )
        if asdict(current) != value.to_dict():
            raise NarrativeTransportError("blocked", "source_identity_mismatch")
        return current

    def reference(self, source_ref: SourceRefValue) -> NarrativeRef:
        """Return a metadata reference without opening either original or bundle."""
        try:
            source_ref = SourceRefValue.from_dict(source_ref.to_dict())
            self._current_ref(source_ref)
            version = self._artifacts.latest_visible_version(
                document_id=source_ref.document_id,
                source_id=source_ref.source_id,
                source_sha256=source_ref.content_sha256,
            )
            return NarrativeRef.from_dict(
                {
                    "schema_version": NARRATIVE_REF_SCHEMA,
                    "artifact_version_id": version.artifact_version_id,
                    "artifact_sha256": version.content_sha256,
                    "byte_size": version.byte_size,
                    "source_ref": source_ref.to_dict(),
                }
            )
        except NarrativeArtifactError as exc:
            raise _artifact_error(exc) from exc
        except SourceReadError as exc:
            raise NarrativeTransportError(exc.status, exc.reason) from exc
        except CatalogReaderUnavailable as exc:
            raise NarrativeTransportError(
                "unavailable", "narrative_store_unavailable"
            ) from exc
        except (OSError, sqlite3.Error) as exc:
            raise NarrativeTransportError(
                "unavailable", "narrative_store_unavailable"
            ) from exc
        except NarrativeContractError as exc:
            raise NarrativeTransportError(
                "blocked", "narrative_reference_invalid"
            ) from exc

    def reference_subject(
        self, subject: NarrativeSubject, *, generation_sha256: str
    ) -> NarrativeRef:
        """Find exactly this projection generation using catalog relationships only."""
        try:
            subject, generation = parse_projected_reference_request(
                {
                    "schema_version": "narrative-reference-request/2",
                    "subject_binding": subject.to_dict(),
                    "generation_sha256": generation_sha256,
                }
            )
            candidates = self._artifacts.visible_subject_generation_candidates(
                subject=subject, generation_sha256=generation
            )
            if not candidates:
                raise NarrativeArtifactNotVisibleError(
                    "no visible artifact for subject generation"
                )
            version = candidates[0]
            return NarrativeRef.from_dict(
                {
                    "schema_version": NARRATIVE_PROJECTED_REF_SCHEMA,
                    "artifact_version_id": version.artifact_version_id,
                    "artifact_sha256": version.content_sha256,
                    "byte_size": version.byte_size,
                    "subject_binding": subject.to_dict(),
                    "generation_sha256": generation,
                }
            )
        except NarrativeArtifactError as exc:
            raise _artifact_error(exc) from exc
        except (CatalogReaderUnavailable, OSError, sqlite3.Error) as exc:
            raise NarrativeTransportError(
                "unavailable", "narrative_store_unavailable"
            ) from exc
        except NarrativeContractError as exc:
            raise NarrativeTransportError(
                "blocked", "narrative_reference_invalid"
            ) from exc

    def read(self, request: NarrativeReadRequest) -> NarrativeTransportRead:
        try:
            request = NarrativeReadRequest.from_dict(request.to_dict())
            return self._read(request)
        except NarrativeArtifactError as exc:
            raise _artifact_error(exc) from exc
        except SourceReadError as exc:
            raise NarrativeTransportError(exc.status, exc.reason) from exc
        except CatalogReaderUnavailable as exc:
            raise NarrativeTransportError(
                "unavailable", "narrative_store_unavailable"
            ) from exc
        except NarrativeReplayError as exc:
            raise NarrativeTransportError("blocked", "locator_replay_failed") from exc
        except ProjectionError as exc:
            raise NarrativeTransportError("blocked", exc.code) from exc
        except OfficialProjectionAdapterError as exc:
            # Adapter diagnostics are fixed codes, never source text or paths.
            raise NarrativeTransportError("blocked", str(exc)) from exc
        except (OSError, sqlite3.Error) as exc:
            raise NarrativeTransportError(
                "unavailable", "narrative_store_unavailable"
            ) from exc
        except NarrativeContractError as exc:
            raise NarrativeTransportError(
                "blocked", "narrative_request_invalid"
            ) from exc

    def _read(self, request: NarrativeReadRequest) -> NarrativeTransportRead:
        reference = request.narrative_ref
        if reference.schema_version == NARRATIVE_PROJECTED_REF_SCHEMA:
            return self._read_projected(request)
        source = reference.source_ref
        if source is None:
            raise NarrativeContractError("raw read requires a raw source reference")
        current = self._current_ref(source)
        version, data = self._artifacts.read_exact(
            artifact_version_id=reference.artifact_version_id,
            document_id=source.document_id,
            source_id=source.source_id,
            source_sha256=source.content_sha256,
            expected_sha256=reference.artifact_sha256,
            expected_size=reference.byte_size,
        )
        bundle = _bound_bundle(version, data, reference)
        # Persisted generation facts remain lineage. This read observes current
        # facts once and replays locators against the one actually verified buffer.
        opened, manifest = self._reader.open_described_version(
            current, purpose="source_export"
        )
        _require_manifest(manifest, request, bundle)
        normalization = self._normalization or NarrativeNormalization.from_reader(
            self._reader,
            enabled=source.mime_type == PPTX_MIME and bundle.versions.parser == "2.0.0",
        )
        locator_count = replay_narrative_evidence(
            opened.data, bundle, normalization=normalization
        )
        receipt = {
            "schema_version": NARRATIVE_READ_RECEIPT_SCHEMA,
            "status": "ok",
            "narrative_ref": reference.to_dict(),
            "as_of_date": request.as_of_date,
            "manifest": manifest,
            "source_read_policy_sha256": opened.source_read_policy_sha256,
            "read_at": opened.read_at,
            "locator_count": locator_count,
            "selection_status": bundle.selection.status,
            "quality_status": bundle.quality_status,
            "replay_status": "verified",
        }
        assert_no_physical_paths(receipt)
        if len(canonical_json(receipt).encode("utf-8")) > MAX_RECEIPT_BYTES:
            raise NarrativeTransportError("blocked", "narrative_receipt_too_large")
        return NarrativeTransportRead(data=data, receipt=receipt)

    def _read_projected(self, request: NarrativeReadRequest) -> NarrativeTransportRead:
        reference = request.narrative_ref
        subject = reference.subject
        generation = reference.generation_sha256
        if generation is None:
            raise NarrativeContractError("projected read requires generation")
        # This is an internal binding precheck; the source loader below verifies
        # actual parent bytes and projection semantics before public export.
        issuer = subject.issuer or {}
        if request.expected_issuer is not None and any(
            issuer.get(key) != value for key, value in request.expected_issuer.items()
        ):
            raise NarrativeTransportError("blocked", "projection_issuer_mismatch")
        if request.as_of_date is not None and (
            subject.as_of_date is None or request.as_of_date < subject.as_of_date
        ):
            raise NarrativeTransportError("blocked", "projection_after_as_of")
        version, data = self._artifacts.read_current_subject(
            artifact_version_id=reference.artifact_version_id,
            subject=subject,
            generation_sha256=generation,
            expected_sha256=reference.artifact_sha256,
            expected_size=reference.byte_size,
        )
        bundle = _bound_bundle(version, data, reference)
        if self._projection_loader is None:
            raise NarrativeTransportError(
                "unavailable", "projection_loader_unavailable"
            )
        view = self._projection_loader(subject)
        if view.subject != subject:
            raise NarrativeTransportError("blocked", "projection_identity_mismatch")
        locator_count = replay_verified_projection(view, bundle)
        receipt = {
            "schema_version": NARRATIVE_PROJECTED_READ_RECEIPT_SCHEMA,
            "status": "ok",
            "narrative_ref": reference.to_dict(),
            "subject_binding": subject.to_dict(),
            "parent_source_refs": list(subject.parent_source_refs),
            "as_of_date": request.as_of_date,
            "observed_at": datetime.now(timezone.utc)
            .isoformat()
            .replace("+00:00", "Z"),
            "locator_count": locator_count,
            "selection_status": bundle.selection.status,
            "quality_status": bundle.quality_status,
            "replay_status": "verified",
        }
        assert_no_physical_paths(receipt)
        if len(canonical_json(receipt).encode("utf-8")) > MAX_RECEIPT_BYTES:
            raise NarrativeTransportError("blocked", "narrative_receipt_too_large")
        return NarrativeTransportRead(data=data, receipt=receipt)
