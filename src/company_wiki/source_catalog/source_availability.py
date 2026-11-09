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
from .source_reader import SourceReadError, SourceRef


AVAILABILITY_RECEIPT_SCHEMA_VERSION = "2.2"
AVAILABILITY_EVIDENCE_SCHEMA_VERSION = "source-availability-evidence/1"
_RESOURCE_LIMIT_REASONS = frozenset({
    "budget_exceeded", "local_discovery_entry_limit", "local_source_group_limit",
})


def _availability_budget(budget):
    if budget is not None:
        return budget  # Never reset or replace an injected parent task's account.
    from .local_inventory import LocalPrepareLimits, LocalReadBudget
    return LocalReadBudget(LocalPrepareLimits())


def verified_open_observation(original) -> dict:
    """Record this owner's already verified buffer, without another hash/read.

    Only the explicit intake writer persists this observation. A query/preview
    never creates it; it says nothing about publication or earlier possession.
    """
    from dataclasses import asdict
    if len(original.data) != original.ref.byte_size:
        raise ValueError("verified buffer size changed")
    return {"schema_version": "source-verified-open/1", "source_ref": asdict(original.ref),
            "verified_at": datetime.now(timezone.utc).isoformat()}


def _open_evidence(observation, ref: SourceRef) -> dict[str, str] | None:
    from dataclasses import asdict
    if not isinstance(observation, dict) or observation.get("schema_version") != "source-verified-open/1":
        return None
    if observation.get("source_ref") != asdict(ref):
        return None
    try:
        at = datetime.fromisoformat(observation["verified_at"].replace("Z", "+00:00"))
        if at.tzinfo is None or at > datetime.now(timezone.utc):
            return None
    except (ValueError, TypeError, KeyError, AttributeError):
        return None
    return {"schema_version": AVAILABILITY_EVIDENCE_SCHEMA_VERSION,
            "source_sha256": ref.content_sha256, "available_by": at.astimezone(timezone.utc).date().isoformat(),
            "basis": "current_verified_open", "evidence_ref": f"source-verified-open:{ref.document_id}:{ref.content_sha256}",
            "locator": "/source_fact_evidence/published_date/verified_open/verified_at"}


def stored_availability_evidence(catalog, ref: SourceRef, *, budget=None) -> dict[str, str] | None:
    """Catalog-only observation made by the existing source-facts writer."""
    from .assertion_service import get_verified_assertion
    budget = _availability_budget(budget)
    budget.check()
    row = get_verified_assertion(catalog.reader, ref.source_id, ref.content_sha256, reader="steady")
    budget.check()
    if not row or row["document_id"] != ref.document_id or row["evidence_basis"] != "source-facts":
        return None
    try:
        raw = row["evidence_json"] or "{}"
        budget.phase = "metadata_read"
        stop = budget.charge(len(raw.encode("utf-8")))
        if stop:
            raise SourceReadError("unavailable", stop)
        fields = json.loads(raw).get("source_fact_evidence", {})
        observation = fields.get("published_date", {})
        opened = _open_evidence(observation.get("verified_open"), ref)
        # Captures are retained in their canonical form; all byte/HTTP
        # bindings are checked again without reading the original.
        captured = observation.get("availability_capture")
        prior = _capture_evidence(json.dumps(captured).encode(), ref) if isinstance(captured, dict) else None
        proofs = [p for p in (opened, prior) if p is not None]
        return min(proofs, key=lambda p: p["available_by"]) if proofs else None
    except (ValueError, TypeError, AttributeError, UnicodeError, RecursionError):
        return None
    finally:
        budget.check()


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
        return _capture_payload_evidence(payload, ref, hashlib.sha256(data).hexdigest())
    except (TypeError, ValueError, UnicodeError, RecursionError):
        return None


def _capture_payload_evidence(payload, ref: SourceRef, provenance_sha256: str) -> dict[str, str] | None:
    """Validate the receipt while preserving the metadata reader's byte digest."""
    try:
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
            "evidence_ref": f"source-provenance:{ref.document_id}:{provenance_sha256}",
            "locator": "/receipt/content_sha256 + /receipt/retrieved_at + /receipt/http_status",
        }
    except (TypeError, ValueError, UnicodeError, RecursionError):
        return None


def _capture_observations(catalog, ref: SourceRef, *, budget):
    locations = catalog.reader.exact_source_locations(ref.document_id, ref.source_id)
    roots = {r.root_id: r.path for r in catalog.config.roots}
    seen: set[Path] = set()
    for loc in locations:
        budget.observe_entry()
        root = roots.get(loc["root_id"])
        path = _provenance_path(root, loc["relative_path"]) if root is not None else None
        if path is None or path in seen:
            continue
        seen.add(path)
        try:
            observed = budget.read_metadata_observation(path, root=root)
        except SourceReadError as exc:
            if exc.reason in {"local_metadata_unreadable", "local_metadata_changed"}:
                continue  # Bad optional provenance never supplies historical proof.
            raise
        except OSError:
            continue
        if observed is not None:
            payload, digest = observed
            proof = _capture_payload_evidence(payload, ref, digest)
            if proof is not None:
                yield proof, payload


def capture_observation(catalog, ref: SourceRef, *, budget) -> dict | None:
    """Copy a validated observed capture under the parent's actual read budget."""
    observations = []
    try:
        for proof, payload in _capture_observations(catalog, ref, budget=budget):
            observations.append((proof["available_by"], payload))
    except SourceReadError as exc:
        if not observations or exc.reason not in _RESOURCE_LIMIT_REASONS:
            raise
        # One valid capture is sufficient; no exhaustive-location claim is made.
        # The shared budget retains its triggered_bound and charged observations.
    budget.check()
    return min(observations, key=lambda item: item[0])[1] if observations else None


def verified_availability_evidence(catalog, ref: SourceRef, *, budget=None) -> dict[str, str] | None:
    """Inspect only exact-version locations; missing reliable proof stays null.

    The public reader has already checked ref against the actual raw buffer.
    Proof lookup is optional and cannot turn an unknown date into publication.
    """
    budget = _availability_budget(budget)
    stored = stored_availability_evidence(catalog, ref, budget=budget) if hasattr(catalog.reader, "fetchone") else None
    proofs = [stored] if stored else []
    try:
        proofs.extend(proof for proof, _payload in _capture_observations(catalog, ref, budget=budget))
    except SourceReadError as exc:
        if not proofs or exc.reason not in _RESOURCE_LIMIT_REASONS:
            raise
    budget.check()
    return min(proofs, key=lambda proof: (proof["available_by"], proof["evidence_ref"])) if proofs else None

__all__ = [
    'verified_availability_evidence',
]
