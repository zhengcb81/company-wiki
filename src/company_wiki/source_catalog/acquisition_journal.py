"""Append-only, idempotent acquisition attempt journal and CSV read model."""

from __future__ import annotations

from contextlib import closing
from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import json
import logging
import os
from pathlib import Path
from typing import Any, Callable, Generator

from .lock import CatalogOperationLockedError, acquisition_mutex
from .store import canonical_json


_LOG = logging.getLogger(__name__)
ACQUISITION_JOURNAL_SCHEMA_VERSION = "1.0"
ACQUISITION_OUTCOMES = frozenset(
    {
        "reused_before_download",
        "reused_after_discovery",
        "downloaded_new",
        "imported_original",
        "deduplicated_original",
        "deduplicated_after_download",
        "missing",
        "ambiguous",
        "failed",
        # WU-4.2: metadata-only outcomes (nothing downloaded).
        "gap_plan",
        "gap_plan_provider_unavailable",
    }
)


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _optional(value: str | None) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError("optional journal text must be null or non-empty trimmed text")
    return value


def _attempt_id(values: dict[str, Any]) -> str:
    digest = hashlib.sha256(canonical_json(values).encode("utf-8")).hexdigest()
    return "urn:company-wiki:acquisition-attempt:sha256:" + digest


def _attempt_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value = dict(pairs)
    if len(value) != len(pairs):
        raise ValueError("duplicate acquisition journal field")
    return value


@dataclass(frozen=True)
class AcquisitionAttempt:
    schema_version: str
    attempt_id: str
    recorded_at: str
    request_id: str
    outcome: str
    adapter_name: str | None = None
    candidate_id: str | None = None
    provider: str | None = None
    provider_document_id: str | None = None
    source_url: str | None = None
    content_sha256: str | None = None
    canonical_path: str | None = None
    reason: str | None = None
    error_type: str | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


class AcquisitionJournalReadError(ValueError):
    """Stored journal content cannot be decoded as acquisition attempts."""


def record_acquisition_observation(
    write: Callable[[], AcquisitionAttempt], *, request_id: str,
) -> AcquisitionAttempt | None:
    """Report observation failures separately from a source operation's result."""
    try:
        return write()
    except (OSError, CatalogOperationLockedError, AcquisitionJournalReadError, UnicodeError) as exc:
        _LOG.warning("acquisition_journal_unavailable request_id=%r error_type=%s", request_id, type(exc).__name__)
        return None


def verified_download_attempt(raw: bytes | bytearray) -> AcquisitionAttempt | None:
    """Accept legacy evidence only when this exact success attempt verifies."""
    if not raw.strip():
        return None
    try:
        fields = json.loads(raw, object_pairs_hook=_attempt_object)
        if not isinstance(fields, dict) or fields.get("outcome") not in (
            "downloaded_new", "deduplicated_after_download",
        ):
            return None
        attempt = AcquisitionAttempt(**fields)
        payload = {key: value for key, value in fields.items()
                   if key not in {"schema_version", "attempt_id", "recorded_at"}}
        if (attempt.schema_version == ACQUISITION_JOURNAL_SCHEMA_VERSION
                and isinstance(attempt.content_sha256, str)
                and all(value is None or isinstance(value, str) for value in payload.values())
                and attempt.attempt_id == _attempt_id(payload)):
            return attempt
    except (TypeError, ValueError, RecursionError):
        pass
    return None


class AcquisitionJournal:
    """Persist one deterministic record per effective acquisition outcome."""

    def __init__(self, catalog_dir: Path):
        if not isinstance(catalog_dir, Path):
            raise TypeError("catalog_dir must be pathlib.Path")
        self.catalog_dir = catalog_dir
        self.path = catalog_dir / "acquisition_attempts.jsonl"

    def record(
        self,
        *,
        request_id: str,
        outcome: str,
        adapter_name: str | None = None,
        candidate_id: str | None = None,
        provider: str | None = None,
        provider_document_id: str | None = None,
        source_url: str | None = None,
        content_sha256: str | None = None,
        canonical_path: str | None = None,
        reason: str | None = None,
        error_type: str | None = None,
        error: str | None = None,
    ) -> AcquisitionAttempt:
        if not isinstance(request_id, str) or not request_id.strip():
            raise ValueError("request_id must be non-empty text")
        if outcome not in ACQUISITION_OUTCOMES:
            raise ValueError(f"unsupported acquisition outcome: {outcome}")
        values: dict[str, Any] = {
            "request_id": request_id,
            "outcome": outcome,
            "adapter_name": _optional(adapter_name),
            "candidate_id": _optional(candidate_id),
            "provider": _optional(provider),
            "provider_document_id": _optional(provider_document_id),
            "source_url": _optional(source_url),
            "content_sha256": _optional(content_sha256),
            "canonical_path": _optional(canonical_path),
            "reason": _optional(reason),
            "error_type": _optional(error_type),
            "error": _optional(error),
        }
        attempt = AcquisitionAttempt(
            schema_version=ACQUISITION_JOURNAL_SCHEMA_VERSION,
            attempt_id=_attempt_id(values),
            recorded_at=_utc_now(),
            **values,
        )
        # Append-only with unique attempt_ids: a per-file mutex suffices.
        # The global catalog operation lock must NOT be used here — the
        # worker's long batches hold it for hours, and journaling every
        # acquisition outcome (even read-only MISSING) would block on it.
        with acquisition_mutex(self.path):
            with closing(self._iter_attempts()) as history:
                for existing in history:
                    if existing.attempt_id == attempt.attempt_id:
                        return existing
            self.catalog_dir.mkdir(parents=True, exist_ok=True)
            encoded = (canonical_json(attempt.to_dict()) + "\n").encode("utf-8")
            with self.path.open("ab") as stream:
                stream.write(encoded)
                stream.flush()
                os.fsync(stream.fileno())
        return attempt

    def read_all(self) -> tuple[AcquisitionAttempt, ...]:
        return tuple(self._iter_attempts())

    def _iter_attempts(self) -> Generator[AcquisitionAttempt, None, None]:
        if not self.path.is_file():
            return
        with self.path.open(encoding="utf-8") as stream:
            for line_number, raw in enumerate(stream, start=1):
                if not raw.strip():
                    continue
                try:
                    value = json.loads(raw)
                    yield AcquisitionAttempt(**value)
                except (TypeError, ValueError, RecursionError) as exc:
                    raise AcquisitionJournalReadError(
                        f"invalid acquisition journal line {line_number}: {exc}"
                    ) from exc


__all__ = [
    "ACQUISITION_JOURNAL_SCHEMA_VERSION",
    "ACQUISITION_OUTCOMES",
    "AcquisitionAttempt",
    "AcquisitionJournal",
]
