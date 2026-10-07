"""Read exact persistent narrative artifacts through the source byte broker."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
import hashlib
import json
import re
import sqlite3
from typing import Any

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
from company_wiki.source_catalog.source_reader import SourceReadError, SourceRef, SourceVersionReader
from company_wiki.source_catalog.reader import CatalogReaderUnavailable

from .models import canonical_json, require_canonical_json
from .narrative_contracts import (
    NarrativeBundle,
    NarrativeContractError,
    SourceRefValue,
    assert_no_physical_paths,
)
from .narrative_replay import NarrativeReplayError, replay_narrative_evidence
from .narrative_transport_contracts import (
    MAX_RECEIPT_BYTES,
    NARRATIVE_READ_RECEIPT_SCHEMA,
    NARRATIVE_REF_SCHEMA,
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


def _publication_date(published: object) -> date:
    if not published:
        raise NarrativeTransportError("blocked", "source_publication_unknown")
    if not isinstance(published, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", published):
        raise NarrativeTransportError("blocked", "source_publication_invalid")
    try:
        return date.fromisoformat(published)
    except (TypeError, ValueError) as exc:
        raise NarrativeTransportError("blocked", "source_publication_invalid") from exc


def _require_historical_source(manifest: dict[str, Any], as_of_date: str) -> None:
    """Historical availability follows publication, independent of download time."""
    cutoff = date.fromisoformat(as_of_date)
    published = _publication_date(manifest.get("published_date"))
    if published > cutoff:
        raise NarrativeTransportError("blocked", "source_after_as_of")


def _require_manifest(
    manifest: dict[str, Any], request: NarrativeReadRequest, bundle: NarrativeBundle,
) -> None:
    source = request.narrative_ref.source_ref
    bound_fields = dict(source.to_dict())
    bound_fields.pop("schema_version")
    bound_fields.update({
        "document_kind": bundle.source_metadata.document_kind,
        "language": bundle.source_metadata.language,
    })
    if any(manifest.get(key) != value for key, value in bound_fields.items()):
        raise NarrativeTransportError("blocked", "source_identity_mismatch")
    if any(
        value is not None and manifest.get(key) != value
        for key, value in request.expected_source.items()
    ):
        raise NarrativeTransportError("blocked", "source_identity_mismatch")
    _require_historical_source(manifest, request.as_of_date)


def _bound_bundle(
    version: NarrativeArtifactVersion, data: bytes, reference: NarrativeRef,
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
        raise NarrativeTransportError("unavailable", "narrative_bundle_invalid") from exc
    if (
        bundle.source_ref != reference.source_ref
        or bundle.selection.status != version.selection_status
        or bundle.quality_status != version.quality_status
    ):
        raise NarrativeTransportError("blocked", "artifact_source_mismatch")
    return bundle


class NarrativeTransportReader:
    """Export bounded bundles only after current source and locator verification."""

    def __init__(
        self, artifacts: NarrativeArtifactStore | NarrativeArtifactReader,
        reader: SourceVersionReader,
    ):
        self._artifacts = artifacts
        self._reader = reader

    def _current_ref(self, value: SourceRefValue) -> SourceRef:
        current = self._reader.query_ref(
            value.document_id, value.source_id, value.content_sha256,
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
                document_id=source_ref.document_id, source_id=source_ref.source_id,
                source_sha256=source_ref.content_sha256,
            )
            return NarrativeRef.from_dict({
                "schema_version": NARRATIVE_REF_SCHEMA,
                "artifact_version_id": version.artifact_version_id,
                "artifact_sha256": version.content_sha256,
                "byte_size": version.byte_size,
                "source_ref": source_ref.to_dict(),
            })
        except NarrativeArtifactError as exc:
            raise _artifact_error(exc) from exc
        except SourceReadError as exc:
            raise NarrativeTransportError(exc.status, exc.reason) from exc
        except CatalogReaderUnavailable as exc:
            raise NarrativeTransportError("unavailable", "narrative_store_unavailable") from exc
        except (OSError, sqlite3.Error) as exc:
            raise NarrativeTransportError("unavailable", "narrative_store_unavailable") from exc
        except NarrativeContractError as exc:
            raise NarrativeTransportError("blocked", "narrative_reference_invalid") from exc

    def read(self, request: NarrativeReadRequest) -> NarrativeTransportRead:
        try:
            request = NarrativeReadRequest.from_dict(request.to_dict())
            return self._read(request)
        except NarrativeArtifactError as exc:
            raise _artifact_error(exc) from exc
        except SourceReadError as exc:
            raise NarrativeTransportError(exc.status, exc.reason) from exc
        except CatalogReaderUnavailable as exc:
            raise NarrativeTransportError("unavailable", "narrative_store_unavailable") from exc
        except NarrativeReplayError as exc:
            raise NarrativeTransportError("blocked", "locator_replay_failed") from exc
        except (OSError, sqlite3.Error) as exc:
            raise NarrativeTransportError("unavailable", "narrative_store_unavailable") from exc
        except NarrativeContractError as exc:
            raise NarrativeTransportError("blocked", "narrative_request_invalid") from exc

    def _read(self, request: NarrativeReadRequest) -> NarrativeTransportRead:
        reference = request.narrative_ref
        source = reference.source_ref
        current = self._current_ref(source)
        version, data = self._artifacts.read_exact(
            artifact_version_id=reference.artifact_version_id,
            document_id=source.document_id, source_id=source.source_id,
            source_sha256=source.content_sha256,
            expected_sha256=reference.artifact_sha256, expected_size=reference.byte_size,
        )
        bundle = _bound_bundle(version, data, reference)
        # The generation pin remains lineage. Current policy governs this read.
        read_pin = self._reader.read_policy_sha256(current)
        opened = self._reader.open_version(
            current, purpose="source_export", expected_read_policy_sha256=read_pin,
        )
        if (
            opened.document_id != source.document_id or opened.source_id != source.source_id
            or opened.content_sha256 != source.content_sha256
            or opened.byte_size != source.byte_size
        ):
            raise NarrativeTransportError("blocked", "source_identity_mismatch")
        manifest = self._reader.describe_version(current)
        _require_manifest(manifest, request, bundle)
        locator_count = replay_narrative_evidence(opened.data, bundle)
        # Replaying can be expensive: recheck identity, metadata and policy after it.
        self._current_ref(source)
        if self._reader.describe_version(current) != manifest:
            raise NarrativeTransportError("blocked", "source_metadata_changed")
        if self._reader.read_policy_sha256(current) != opened.source_read_policy_sha256:
            raise NarrativeTransportError("blocked", "read_policy_mismatch")
        receipt = {
            "schema_version": NARRATIVE_READ_RECEIPT_SCHEMA,
            "status": "ok", "narrative_ref": reference.to_dict(),
            "as_of_date": request.as_of_date, "manifest": manifest,
            "source_read_policy_sha256": opened.source_read_policy_sha256,
            "read_at": opened.read_at, "locator_count": locator_count,
            "selection_status": bundle.selection.status,
            "quality_status": bundle.quality_status, "replay_status": "verified",
        }
        assert_no_physical_paths(receipt)
        if len(canonical_json(receipt).encode("utf-8")) > MAX_RECEIPT_BYTES:
            raise NarrativeTransportError("blocked", "narrative_receipt_too_large")
        return NarrativeTransportRead(data=data, receipt=receipt)
