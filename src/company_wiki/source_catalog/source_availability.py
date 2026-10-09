"""Optional historical availability from existing, byte-bound HTTP provenance.

Called after an exact raw read. This reads bounded metadata only: it neither
rescans roots nor hashes the original a second time. Local possession dates,
bare sidecars and unknown capture formats cannot establish availability.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath, PureWindowsPath
from urllib.parse import urlsplit

from .acquisition import DownloadReceipt
from .source_reader import SourceRef


AVAILABILITY_RECEIPT_SCHEMA_VERSION = "2.2"
AVAILABILITY_EVIDENCE_SCHEMA_VERSION = "source-availability-evidence/1"
_MAX_PROVENANCE_BYTES = 64 * 1024
_MAX_LOCATIONS = 64


def _provenance_path(root: Path, relative: str) -> Path | None:
    normalized = relative.replace("\\", "/")
    parts = normalized.split("/")
    if (PureWindowsPath(relative).drive or PurePosixPath(normalized).is_absolute()
            or any(part in {"", ".", ".."} for part in parts)
            or any(ord(char) < 32 for char in relative)):
        return None
    candidate = root.joinpath(*parts)
    sidecar = candidate.with_name(candidate.name + ".source.json")
    try:
        if sidecar.is_symlink() or not sidecar.is_file():
            return None
        sidecar.resolve(strict=True).relative_to(root.resolve(strict=True))
    except (OSError, ValueError):
        return None
    return sidecar


def _capture_evidence(data: bytes, ref: SourceRef) -> dict[str, str] | None:
    try:
        payload = json.loads(data)
        if not isinstance(payload, dict) or payload.get("schema_version") != "1.0":
            return None
        candidate = payload.get("candidate")
        capture = payload.get("receipt")
        if not isinstance(candidate, dict) or not isinstance(capture, dict):
            return None
        # This is the existing canonical acquisition receipt, not an invented
        # availability credential. It validates actual HTTP/date/byte fields.
        receipt = DownloadReceipt(**capture)
        if (not 200 <= receipt.http_status < 300
                or receipt.content_sha256 != ref.content_sha256
                or receipt.byte_size != ref.byte_size or receipt.mime_type != ref.mime_type):
            return None
        for key in ("content_sha256", "byte_size", "mime_type", "retrieved_at",
                    "provider", "provider_document_id", "source_url", "adapter_name", "adapter_version"):
            if payload.get(key) != getattr(receipt, key):
                return None
        for key in ("provider", "provider_document_id", "source_url"):
            if candidate.get(key) != getattr(receipt, key):
                return None
        url = urlsplit(receipt.source_url)
        if not url.hostname or url.username or url.password:
            return None
        captured = datetime.fromisoformat(receipt.retrieved_at.replace("Z", "+00:00"))
        return {
            "schema_version": AVAILABILITY_EVIDENCE_SCHEMA_VERSION,
            "source_sha256": ref.content_sha256,
            "available_by": captured.astimezone(timezone.utc).date().isoformat(),
            "basis": "prior_verified_capture",
            "evidence_ref": f"source-provenance:{ref.document_id}:{hashlib.sha256(data).hexdigest()}",
            "locator": "/receipt/content_sha256 + /receipt/retrieved_at + /receipt/http_status",
        }
    except (TypeError, ValueError, UnicodeError):
        return None


def verified_availability_evidence(catalog, ref: SourceRef) -> dict[str, str] | None:
    """Inspect only exact-version locations; missing reliable proof stays null.

    The public reader has already checked ref against the actual raw buffer.
    Proof lookup is optional and cannot turn an unknown date into publication.
    """
    locations = catalog.reader.exact_source_locations(ref.document_id, ref.source_id)
    if len(locations) > _MAX_LOCATIONS:
        return None
    roots = {root.root_id: root.path for root in catalog.config.roots}
    proofs = []
    for location in locations:
        root = roots.get(location["root_id"])
        relative = location["relative_path"]
        if root is None or not isinstance(relative, str):
            continue
        path = _provenance_path(root, relative)
        if path is None:
            continue
        try:
            with path.open("rb") as stream:
                data = stream.read(_MAX_PROVENANCE_BYTES + 1)
            if len(data) > _MAX_PROVENANCE_BYTES:
                continue
        except OSError:
            continue
        evidence = _capture_evidence(data, ref)
        if evidence is not None:
            proofs.append(evidence)
    return min(proofs, key=lambda proof: (proof["available_by"], proof["evidence_ref"])) if proofs else None
