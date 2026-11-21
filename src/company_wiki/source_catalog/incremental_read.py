"""Bounded reading of exact registered sources for the scheduled refresh.

Two reading tiers over the one shared parsing and selection engine:

- ``local`` reads business passages, locators and quality from the verified
  original with zero model requests, and persists a compact read-result
  artifact under its own role.
- ``summary`` reports the source's current formal summary product.  Producing
  a new summary is the existing configured batch entry's job (the shared
  AUTO engine with its own lease, ledger and budget); this module composes
  that entry instead of building a second execution path.

A read result never shadows the narrative bundle, and a bundle never
substitutes for a read result: they are separate roles in the artifact store.
"""

from __future__ import annotations

from dataclasses import dataclass
import datetime
import hashlib
import json
import re
import time
from typing import Any

from .narrative_artifact_store import (
    NARRATIVE_BUNDLE_ROLE,
    NARRATIVE_READ_RESULT_ROLE,
    NarrativeArtifactDraft,
    NarrativeArtifactError,
    NarrativeArtifactNotVisibleError,
    NarrativeArtifactReader,
    NarrativeArtifactStore,
    NarrativeArtifactVersion,
    NarrativeReadResultVersion,
)
from .narrative_contracts import SourceMetadataValue, SourceRefValue
from .narrative_formats import parser_component, source_class_for
from .narrative_language import (
    NarrativeLanguageError,
    detect_narrative_language,
    narrative_language_family,
)
from company_wiki.source_contract.source_version import SourceReadError

from .narrative_selection import (
    NarrativeMaterialError,
    RawNarrativeSelector,
    verify_selected_material,
)
from .narrative_selector_binding import BoundNarrativeSelector, bind_narrative_selector
from .service import SourceCatalog
from .source_reader import SourceVersionReader


INCREMENTAL_READ_REQUEST_SCHEMA = "cwp-incremental-read-request/1"
INCREMENTAL_READ_SCHEMA = "cwp-incremental-read/1"
READ_RESULT_REF_SCHEMA = "cwp-read-result-ref/1"
BUNDLE_REF_SCHEMA = "cwp-bundle-ref/1"
READ_RESULT_PAYLOAD_SCHEMA = "cwp-read-result/1"
READING_BACKLOG_REQUEST_SCHEMA = "cwp-reading-backlog-request/1"
READING_BACKLOG_SCHEMA = "cwp-reading-backlog/1"

#: Backlog states are derived from the owner's persisted products, never from
#: file names or directory guesses.
BACKLOG_UNREAD = "unread"

READING_LEVEL_LOCAL = "local"
READING_LEVEL_SUMMARY = "summary"

#: Per-source terminal states.  ``read`` and ``summarized`` are products;
#: ``skipped`` is a proven no-narrative result; ``deferred`` awaits the
#: configured summary batch; ``failed`` and ``uncertain`` keep their cause.
STATE_READ = "read"
STATE_SUMMARIZED = "summarized"
STATE_SKIPPED = "skipped"
STATE_DEFERRED = "deferred"
STATE_FAILED = "failed"
STATE_UNCERTAIN = "uncertain"

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_MAX_SOURCES = 256
_MAX_BACKLOG_KINDS = 16
_MAX_BACKLOG_ITEMS = 512


def _optional_date(value: Any, name: str) -> str | None:
    if value is None:
        return None
    text = _text(value, name)
    try:
        parsed = datetime.date.fromisoformat(text)
    except ValueError:
        raise IncrementalReadError(f"{name} must be a canonical YYYY-MM-DD date") from None
    if parsed.isoformat() != text:
        raise IncrementalReadError(f"{name} must be a canonical YYYY-MM-DD date")
    return text


class IncrementalReadError(ValueError):
    """The read request or one source's result cannot be represented."""


def _text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value or value.strip() != value:
        raise IncrementalReadError(f"{name} must be nonempty unpadded text")
    return value


def _positive_int(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise IncrementalReadError(f"{name} must be a positive integer")
    return value


@dataclass(frozen=True)
class ReadLimits:
    """The caller's ceiling for one read request."""

    max_sources: int = 32
    max_seconds: float = 600.0

    @classmethod
    def from_dict(cls, value: Any) -> "ReadLimits":
        if value is None:
            return cls()
        if not isinstance(value, dict):
            raise IncrementalReadError("limits must be an object")
        if set(value) - {"max_sources", "max_seconds", "timeout_seconds"}:
            raise IncrementalReadError("limits has unsupported fields")
        seconds = [value[key] for key in ("max_seconds", "timeout_seconds") if key in value]
        if any(type(limit) not in (int, float) or not 0 < limit < float("inf") for limit in seconds):
            raise IncrementalReadError("reading timeout must be positive and finite")
        return cls(
            max_sources=_positive_int(
                value.get("max_sources", cls.max_sources), "limits.max_sources"
            ),
            max_seconds=float(min(seconds, default=cls.max_seconds)),
        )

    def to_dict(self) -> dict[str, Any]:
        return {"max_sources": self.max_sources, "max_seconds": self.max_seconds}


@dataclass(frozen=True)
class IncrementalReadRequest:
    """Exact SourceRef identities at one declared reading level."""

    run_id: str
    reading_level: str
    sources: tuple[SourceRefValue, ...]
    limits: ReadLimits = ReadLimits()

    @classmethod
    def from_dict(cls, value: Any) -> "IncrementalReadRequest":
        from .narrative_contracts import NarrativeContractError

        if not isinstance(value, dict):
            raise IncrementalReadError("read request must be an object")
        allowed = {
            "schema_version", "run_id", "reading_level", "sources", "limits",
        }
        if set(value) != allowed:
            raise IncrementalReadError("read request has unsupported or missing fields")
        if value["schema_version"] != INCREMENTAL_READ_REQUEST_SCHEMA:
            raise IncrementalReadError("unsupported read request schema")
        level = _text(value["reading_level"], "reading_level")
        if level not in {READING_LEVEL_LOCAL, READING_LEVEL_SUMMARY}:
            raise IncrementalReadError("reading_level must be 'local' or 'summary'")
        sources_raw = value["sources"]
        if not isinstance(sources_raw, list) or not sources_raw:
            raise IncrementalReadError("sources must be a nonempty list")
        if len(sources_raw) > _MAX_SOURCES:
            raise IncrementalReadError("sources has too many entries")
        sources: dict[tuple[str, str, str], SourceRefValue] = {}
        try:
            for raw in sources_raw:
                ref = SourceRefValue.from_dict(raw)
                sources[(ref.document_id, ref.source_id, ref.content_sha256)] = ref
        except NarrativeContractError as exc:
            raise IncrementalReadError(f"invalid source reference: {exc}") from exc
        return cls(
            run_id=_text(value["run_id"], "run_id"),
            reading_level=level,
            sources=tuple(sources.values()),
            limits=ReadLimits.from_dict(value["limits"]),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": INCREMENTAL_READ_REQUEST_SCHEMA,
            "run_id": self.run_id,
            "reading_level": self.reading_level,
            "sources": [ref.to_dict() for ref in self.sources],
            "limits": self.limits.to_dict(),
        }


@dataclass(frozen=True)
class ReadResultRef:
    """A compact, pathless pointer at one persisted read product.

    ``source_ref`` stays part of the pointer: the artifact row is keyed by the
    exact original identity, so a ref alone is never resolved by guessing.
    """

    artifact_version_id: str
    artifact_sha256: str
    byte_size: int
    role: str
    source_ref: SourceRefValue

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": (
                READ_RESULT_REF_SCHEMA
                if self.role == NARRATIVE_READ_RESULT_ROLE
                else BUNDLE_REF_SCHEMA
            ),
            "artifact_version_id": self.artifact_version_id,
            "artifact_sha256": self.artifact_sha256,
            "byte_size": self.byte_size,
            "artifact_role": self.role,
            "source_ref": self.source_ref.to_dict(),
        }

    @classmethod
    def from_dict(cls, value: Any) -> "ReadResultRef":
        from .narrative_contracts import NarrativeContractError

        if not isinstance(value, dict):
            raise IncrementalReadError("result_ref must be an object")
        allowed = {
            "schema_version", "artifact_version_id", "artifact_sha256",
            "byte_size", "artifact_role", "source_ref",
        }
        if set(value) != allowed:
            raise IncrementalReadError("result_ref has unsupported or missing fields")
        if value["schema_version"] not in {READ_RESULT_REF_SCHEMA, BUNDLE_REF_SCHEMA}:
            raise IncrementalReadError("unsupported result_ref schema")
        role = _text(value["artifact_role"], "result_ref.artifact_role")
        if role not in {NARRATIVE_READ_RESULT_ROLE, NARRATIVE_BUNDLE_ROLE}:
            raise IncrementalReadError("result_ref artifact_role is not a read product")
        digest = _text(value["artifact_sha256"], "result_ref.artifact_sha256")
        if _SHA256_RE.fullmatch(digest) is None:
            raise IncrementalReadError("result_ref.artifact_sha256 must be a SHA-256")
        size = value["byte_size"]
        if isinstance(size, bool) or not isinstance(size, int) or size <= 0:
            raise IncrementalReadError("result_ref.byte_size must be positive")
        try:
            source_ref = SourceRefValue.from_dict(value["source_ref"])
        except NarrativeContractError as exc:
            raise IncrementalReadError(f"invalid result_ref source: {exc}") from exc
        return cls(
            artifact_version_id=_text(
                value["artifact_version_id"], "result_ref.artifact_version_id"
            ),
            artifact_sha256=digest,
            byte_size=size,
            role=role,
            source_ref=source_ref,
        )


@dataclass(frozen=True)
class ReadItemResult:
    """One source's outcome inside a read request."""

    source_ref: SourceRefValue
    state: str
    result_ref: ReadResultRef | None
    reused: bool
    reason_codes: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_ref": self.source_ref.to_dict(),
            "state": self.state,
            "result_ref": self.result_ref.to_dict() if self.result_ref else None,
            "reused": self.reused,
            "reason_codes": list(self.reason_codes),
        }


@dataclass(frozen=True)
class IncrementalReadResponse:
    """The batch receipt the refresh caller reconciles on."""

    run_id: str
    reading_level: str
    items: tuple[ReadItemResult, ...]
    usage: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": INCREMENTAL_READ_SCHEMA,
            "run_id": self.run_id,
            "reading_level": self.reading_level,
            "items": [item.to_dict() for item in self.items],
            "usage": self.usage,
        }


def _read_result_work_key(
    source_ref: SourceRefValue, policy_sha256: str, parser_identity: tuple[str, str],
    selector_version: str,
) -> str:
    """One logical read product of one exact original and execution identity."""
    payload = json.dumps(
        {
            "schema_version": "cwp-read-work-key/1",
            "document_id": source_ref.document_id,
            "source_id": source_ref.source_id,
            "source_sha256": source_ref.content_sha256,
            "read_policy_sha256": policy_sha256,
            "parser": list(parser_identity),
            "selector_version": selector_version,
            "artifact_role": NARRATIVE_READ_RESULT_ROLE,
        },
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


@dataclass(frozen=True)
class BacklogLimits:
    max_items: int = 64

    @classmethod
    def from_dict(cls, value: Any) -> "BacklogLimits":
        if value is None:
            return cls()
        if not isinstance(value, dict):
            raise IncrementalReadError("limits must be an object")
        if set(value) - {"max_items"}:
            raise IncrementalReadError("limits has unsupported fields")
        max_items = value.get("max_items", cls.max_items)
        if isinstance(max_items, bool) or not isinstance(max_items, int) or not (
            1 <= max_items <= _MAX_BACKLOG_ITEMS
        ):
            raise IncrementalReadError(
                f"limits.max_items must be 1 to {_MAX_BACKLOG_ITEMS}"
            )
        return cls(max_items=max_items)

    def to_dict(self) -> dict[str, Any]:
        return {"max_items": self.max_items}


@dataclass(frozen=True)
class ReadingBacklogRequest:
    """One paged backlog scope over the catalog's registered originals."""

    document_kinds: tuple[str, ...]
    reading_level: str
    entity: str | None = None
    since_date: str | None = None
    as_of_date: str | None = None
    cursor: str | None = None
    limits: BacklogLimits = BacklogLimits()
    source_market: str | None = None
    security_id: str | None = None

    @classmethod
    def from_dict(cls, value: Any) -> "ReadingBacklogRequest":
        if not isinstance(value, dict):
            raise IncrementalReadError("backlog request must be an object")
        allowed = {
            "schema_version", "document_kinds", "reading_level", "entity",
            "since_date", "as_of_date", "cursor", "limits",
        }
        if set(value) != allowed:
            raise IncrementalReadError(
                "backlog request has unsupported or missing fields"
            )
        if value["schema_version"] != READING_BACKLOG_REQUEST_SCHEMA:
            raise IncrementalReadError("unsupported backlog request schema")
        level = _text(value["reading_level"], "reading_level")
        if level not in {READING_LEVEL_LOCAL, READING_LEVEL_SUMMARY}:
            raise IncrementalReadError("reading_level must be 'local' or 'summary'")
        kinds_raw = value["document_kinds"]
        if not isinstance(kinds_raw, list) or not kinds_raw:
            raise IncrementalReadError("document_kinds must be a nonempty list")
        if len(kinds_raw) > _MAX_BACKLOG_KINDS:
            raise IncrementalReadError("document_kinds has too many entries")
        kinds = tuple(_text(kind, "document_kind").lower() for kind in kinds_raw)
        entity = value["entity"]
        if entity is not None:
            entity = _text(entity, "entity")
        cursor = value["cursor"]
        if cursor is not None:
            cursor = _text(cursor, "cursor")
        return cls(
            document_kinds=kinds, reading_level=level, entity=entity,
            since_date=_optional_date(value["since_date"], "since_date"),
            as_of_date=_optional_date(value["as_of_date"], "as_of_date"),
            cursor=cursor,
            limits=BacklogLimits.from_dict(value["limits"]),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": READING_BACKLOG_REQUEST_SCHEMA,
            "document_kinds": list(self.document_kinds),
            "reading_level": self.reading_level,
            "entity": self.entity,
            "since_date": self.since_date,
            "as_of_date": self.as_of_date,
            "cursor": self.cursor,
            "limits": self.limits.to_dict(),
        }


@dataclass(frozen=True)
class ReadingBacklogItem:
    """One registered source, its exact ref and its current tier state."""

    source_ref: SourceRefValue
    state: str
    result_ref: ReadResultRef | None
    document_kind: str
    published_date: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_ref": self.source_ref.to_dict(),
            "state": self.state,
            "result_ref": self.result_ref.to_dict() if self.result_ref else None,
            "document_kind": self.document_kind,
            "published_date": self.published_date,
        }


@dataclass(frozen=True)
class ReadingBacklogResponse:
    """One paged backlog listing; ``next_cursor`` resumes at the same order."""

    reading_level: str
    items: tuple[ReadingBacklogItem, ...]
    next_cursor: str | None
    usage: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": READING_BACKLOG_SCHEMA,
            "reading_level": self.reading_level,
            "items": [item.to_dict() for item in self.items],
            "next_cursor": self.next_cursor,
            "usage": self.usage,
        }


class IncrementalReadService:
    """Read exact sources at the declared level through the shared engine."""

    def __init__(
        self,
        *,
        catalog: SourceCatalog,
        artifacts: NarrativeArtifactStore | None = None,
        selector: RawNarrativeSelector | None = None,
    ) -> None:
        if not isinstance(catalog, SourceCatalog):
            raise TypeError("catalog must be SourceCatalog")
        self._catalog = catalog
        self._artifacts = artifacts or catalog.open_narrative_artifact_store()
        if not isinstance(self._artifacts, NarrativeArtifactStore):
            raise TypeError("artifacts must be NarrativeArtifactStore")
        self._reader = SourceVersionReader(catalog)
        self._bound_selector: BoundNarrativeSelector | None = None
        if selector is None:
            self._bound_selector = bind_narrative_selector()
            self._selector = RawNarrativeSelector(selector=self._bound_selector)
        else:
            self._selector = selector

    def read(
        self, request: IncrementalReadRequest, *, summary_generator=None,
    ) -> IncrementalReadResponse:
        """Read every exact source; one failure never blocks its siblings.

        ``summary_generator`` is the composed configured-batch entry (the
        shared AUTO engine behind ``scripts/narrative_batch_configured.py``).
        At the ``summary`` level, sources without a formal bundle are handed
        to it as exact SourceRef dicts and its per-source receipt is mapped
        back; without one they stay honestly ``deferred``.
        """
        if not isinstance(request, IncrementalReadRequest):
            raise TypeError("request must be IncrementalReadRequest")
        if len(request.sources) > request.limits.max_sources:
            raise IncrementalReadError("sources exceed the request's own limit")
        started = time.monotonic()
        deadline = started + request.limits.max_seconds
        generator_usage: dict[str, Any] | None = None
        if request.reading_level == READING_LEVEL_LOCAL:
            items = [self._read_local(ref, deadline=deadline) for ref in request.sources]
        else:
            cached = {ref: self._summary_bundle_state(ref) for ref in request.sources}
            pending = [ref for ref, item in cached.items() if item is None]
            if pending and summary_generator is not None:
                # AUTO owns per-source reuse. Its run identity must bind the full
                # original scope even after one sibling has published a bundle.
                generated, generator_usage = self._run_summary_generator(
                    request, request.sources, summary_generator,
                )
                items = [cached[item.source_ref] or item for item in generated]
            else:
                items = [cached[ref] or ReadItemResult(
                    ref, STATE_DEFERRED, None, False, ("summary_batch_required",),
                ) for ref in request.sources]
        usage: dict[str, Any] = {
            "sources": len(items),
            "model_requests": 0,
            "seconds": round(time.monotonic() - started, 6),
        }
        if generator_usage is not None:
            usage["summary_batch"] = generator_usage
        return IncrementalReadResponse(
            run_id=request.run_id,
            reading_level=request.reading_level,
            items=tuple(items),
            usage=usage,
        )

    def _run_summary_generator(self, request, sources, summary_generator):
        """Hand exact refs to the composed batch entry and map its receipt."""
        try:
            receipt = summary_generator(
                run_id=request.run_id,
                sources=[ref.to_dict() for ref in sources],
            )
        except Exception as exc:  # noqa: BLE001 - one engine failure stays per-batch
            code = getattr(exc, "error_code", None) or f"summary_batch_{type(exc).__name__}"
            return (
                [ReadItemResult(ref, STATE_UNCERTAIN, None, False, (str(code),))
                 for ref in sources],
                {"status": "failed", "error": str(code)},
            )
        if not isinstance(receipt, dict):
            raise IncrementalReadError(
                "summary generator must return a narrative-batch receipt dict"
            )
        by_document: dict[str, dict[str, Any]] = {}
        for document in receipt.get("documents", []) or []:
            if isinstance(document, dict) and isinstance(document.get("document_id"), str):
                by_document[document["document_id"]] = document
        by_source: dict[str, dict[str, Any]] = {}
        for item in receipt.get("items", []) or []:
            if isinstance(item, dict) and isinstance(item.get("item_key"), str):
                by_source[item["item_key"]] = item
        mapped: list[ReadItemResult] = []
        for ref in sources:
            document = by_document.get(ref.document_id) or by_source.get(ref.document_id)
            if document is None:
                mapped.append(ReadItemResult(
                    ref, STATE_UNCERTAIN, None, False, ("summary_batch_no_receipt",),
                ))
                continue
            mapped.append(self._map_summary_receipt(ref, document))
        budget = receipt.get("budget") if isinstance(receipt.get("budget"), dict) else None
        usage = {
            "status": receipt.get("status"),
            "run_id": receipt.get("run_id"),
            "budget": budget,
        }
        return mapped, usage

    def _map_summary_receipt(self, ref: SourceRefValue, document: dict[str, Any]) -> ReadItemResult:
        artifact = document.get("artifact_ref")
        errors = tuple(
            str(code) for code in (document.get("errors") or []) if code
        )
        if artifact is not None and isinstance(artifact, dict):
            try:
                result_ref = ReadResultRef(
                    artifact_version_id=str(artifact["artifact_version_id"]),
                    artifact_sha256=str(artifact["content_sha256"]),
                    byte_size=int(artifact["byte_size"]),
                    role=NARRATIVE_BUNDLE_ROLE,
                    source_ref=ref,
                )
            except (KeyError, TypeError, ValueError):
                return ReadItemResult(
                    ref, STATE_UNCERTAIN, None, False, ("summary_bundle_ref_invalid",),
                )
            return ReadItemResult(ref, STATE_SUMMARIZED, result_ref, False, errors)
        if errors:
            return ReadItemResult(ref, STATE_FAILED, None, False, errors)
        status = document.get("status")
        if status == "skipped":
            return ReadItemResult(
                ref, STATE_SKIPPED, None, False, ("summary_batch_skipped",),
            )
        return ReadItemResult(
            ref, STATE_UNCERTAIN, None, False, ("summary_batch_incomplete",),
        )

    # ------------------------------------------------------------------
    # Local tier: parse + select through the shared engine, zero model.
    # ------------------------------------------------------------------
    def _read_local(self, ref: SourceRefValue, *, deadline: float) -> ReadItemResult:
        def checkpoint() -> None:
            if time.monotonic() >= deadline:
                raise TimeoutError("local_read_deadline")

        try:
            checkpoint()
            return self._read_local_inner(ref, checkpoint=checkpoint)
        except TimeoutError:
            return ReadItemResult(ref, STATE_DEFERRED, None, False, ("local_read_deadline",))
        except NarrativeMaterialError as exc:
            return ReadItemResult(ref, STATE_FAILED, None, False,
                                  (exc.code, "local_read_failed"))
        except NarrativeLanguageError as exc:
            return ReadItemResult(ref, STATE_FAILED, None, False,
                                  (exc.code, "local_read_failed"))
        except SourceReadError as exc:
            # The source owner refused this exact version (unindexed,
            # unavailable, policy mismatch).  That is uncertainty about the
            # identity, not a completed read.
            return ReadItemResult(ref, STATE_UNCERTAIN, None, False,
                                  (exc.reason, "source_owner_refused"))
        except NarrativeArtifactError as exc:
            # The reading product could not be persisted or reused (for
            # example the previous row was retired).  One poisoned item must
            # never abort its batch siblings.  The exception type carries no
            # code attribute; the concrete class name is the diagnostic.
            return ReadItemResult(ref, STATE_UNCERTAIN, None, False,
                                  (type(exc).__name__, "read_store_error"))
        except OSError as exc:
            return ReadItemResult(ref, STATE_UNCERTAIN, None, False,
                                  (f"io_error:{type(exc).__name__}",))

    def _read_local_inner(self, ref: SourceRefValue, *, checkpoint) -> ReadItemResult:
        current = self._reader.query_ref(ref.document_id, ref.source_id, ref.content_sha256)
        if (current.document_id, current.source_id, current.content_sha256,
                current.byte_size, current.mime_type) != (
            ref.document_id, ref.source_id, ref.content_sha256, ref.byte_size, ref.mime_type,
        ):
            return ReadItemResult(ref, STATE_UNCERTAIN, None, False, ("source_ref_changed",))
        policy = self._reader.read_policy_sha256(current)
        described = self._reader.describe_version(current)
        # describe_version projects display facts as str|int|None; the three
        # fields consumed here are owner-controlled text.
        kind = str(described["document_kind"] or "unknown")
        declared_raw = described.get("language")
        declared = str(declared_raw) if declared_raw is not None else None
        title_raw = described.get("title")
        title = str(title_raw) if title_raw is not None else None
        source_class = source_class_for(current.mime_type, kind)
        parser_identity = parser_component(current.mime_type, source_class)
        if self._bound_selector is not None:
            selector_version = self._bound_selector.selector_version
        else:
            from .narrative_evidence import NARRATIVE_SELECTOR_VERSION

            selector_version = NARRATIVE_SELECTOR_VERSION
        work_key = _read_result_work_key(ref, policy, parser_identity, selector_version)
        opened = self._reader.open_version(
            current, purpose="narrative_derivation",
            expected_read_policy_sha256=policy,
        )
        existing = self._visible_read_result(ref)
        if existing is not None and existing.work_key == work_key:
            cached = self._local_product(ref, existing, reused=True)
            if self.result_available(cached.result_ref):
                return cached
        checkpoint()
        if declared in {None, "unknown"}:
            language = detect_narrative_language(opened.data, current.mime_type)
        else:
            assert declared is not None
            language = narrative_language_family(declared)
        metadata = SourceMetadataValue(
            source_class=source_class,
            title=title,
            document_kind=kind,
            language=language,
            declared_language=(
                declared if declared not in {None, "unknown", language} else None
            ),
        )
        work = self._selector.select(
            opened, source_ref=ref, source_metadata=metadata, checkpoint=checkpoint,
        )
        checkpoint()
        package = work.package
        if package.status == "blocked":
            return ReadItemResult(ref, STATE_FAILED, None, False,
                                  ("PARSER_INCOMPLETE", "local_read_failed"))
        # Only reliable parsed evidence is persisted.  The same proof the
        # batch select handler applies before any model call applies here.
        verify_selected_material(work.parsed, package, mime_type=ref.mime_type)
        payload = self._read_result_payload(
            ref, kind, language, policy, parser_identity, selector_version, package,
        )
        draft = NarrativeArtifactDraft(
            effect_id=f"read-{work_key}",
            work_key=work_key,
            document_id=ref.document_id,
            source_id=ref.source_id,
            source_sha256=ref.content_sha256,
            producer_name="company_wiki.incremental_read",
            producer_version=selector_version,
            policy_sha256=policy,
            selection_status=package.status,
            quality_status=(
                "skipped_no_narrative"
                if package.status == "skipped_no_narrative"
                else "verified" if package.coverage_complete else "needs_review"
            ),
            metadata_json=json.dumps(
                {
                    "schema_version": READ_RESULT_PAYLOAD_SCHEMA,
                    "document_kind": kind,
                    "language": language,
                    "reading_level": READING_LEVEL_LOCAL,
                },
                ensure_ascii=False,
                sort_keys=True,
            ),
            created_at=_utc_now(),
            artifact_role=NARRATIVE_READ_RESULT_ROLE,
        )
        encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
        version = self._artifacts.prepare_read_result(draft, encoded)
        # A read result has no outbox verify job; its proof ran above.  The
        # prepared row becomes the visible product under its work key.
        self._artifacts.activate_read_result(
            draft.work_key, verified_after_hash=version.content_sha256,
            activated_at=_utc_now(),
        )
        return self._local_product(ref, version, reused=False)

    @staticmethod
    def _local_product(ref: SourceRefValue, version: NarrativeReadResultVersion, *, reused: bool):
        reasons: tuple[str, ...] = ()
        if version.selection_status == "skipped_no_narrative":
            state = STATE_SKIPPED
        elif version.selection_status == "partial":
            state = STATE_READ
            reasons = ("selection_partial",)
        elif version.selection_status == "needs_review":
            state = STATE_READ
            reasons = ("selection_needs_review",)
        else:
            state = STATE_READ
        return ReadItemResult(
            ref, state, ReadResultRef(
                artifact_version_id=version.artifact_version_id,
                artifact_sha256=version.content_sha256,
                byte_size=version.byte_size,
                role=NARRATIVE_READ_RESULT_ROLE,
                source_ref=ref,
            ), reused, reasons,
        )

    @staticmethod
    def _read_result_payload(
        ref: SourceRefValue, kind: str, language: str, policy: str,
        parser_identity: tuple[str, str], selector_version: str, package,
    ) -> dict[str, Any]:
        """The compact local reading product: selection plus located evidence."""
        return {
            "schema_version": READ_RESULT_PAYLOAD_SCHEMA,
            "source_ref": ref.to_dict(),
            "expected_read_policy_sha256": policy,
            "source_metadata": {"document_kind": kind, "language": language},
            "parser": {"name": parser_identity[0], "version": parser_identity[1]},
            "selector": {"version": selector_version},
            "selection": {
                "status": package.status,
                "coverage_complete": package.coverage_complete,
                "source_units": package.source_units,
                "candidate_count": package.candidate_count,
                "selected_count": len(package.evidence_spans),
                "omitted_candidate_count": package.omitted_candidate_count,
            },
            "evidence_spans": [span.to_dict() for span in package.evidence_spans],
            "reading_level": READING_LEVEL_LOCAL,
            "model_requests": 0,
        }

    def _visible_read_result(self, ref: SourceRefValue):
        try:
            return self._artifacts.latest_visible_read_result(
                document_id=ref.document_id, source_id=ref.source_id,
                source_sha256=ref.content_sha256,
            )
        except NarrativeArtifactNotVisibleError:
            return None

    # ------------------------------------------------------------------
    # Summary tier: bundle-first.  A source below the summary tier is handed
    # to the composed configured batch entry (see ``read``); without one it
    # stays deferred.  A persisted local read never substitutes for a formal
    # summary.
    # ------------------------------------------------------------------
    def _summary_bundle_state(self, ref: SourceRefValue) -> ReadItemResult | None:
        """Return the source's summary item, or None when it needs a summary."""
        try:
            bundle = self._artifacts.latest_visible_version(
                document_id=ref.document_id, source_id=ref.source_id,
                source_sha256=ref.content_sha256,
            )
        except NarrativeArtifactNotVisibleError:
            return None
        item = ReadItemResult(
            ref, STATE_SUMMARIZED,
            ReadResultRef(bundle.artifact_version_id, bundle.content_sha256,
                          bundle.byte_size, NARRATIVE_BUNDLE_ROLE, ref),
            True, (),
        )
        return item if self.result_available(item.result_ref) else None

    def existing_product(self, ref: SourceRefValue, level: str) -> ReadItemResult | None:
        """Look up this exact source's visible product without running the parser."""
        if level == READING_LEVEL_SUMMARY:
            return self._summary_bundle_state(ref)
        return self._backlog_local_state(ref)

    def result_available(self, result_ref: ReadResultRef | None) -> bool:
        """Verify that an automatically selected artifact can actually be opened."""
        if result_ref is None:
            return False
        try:
            self.read_result_payload(result_ref)
        except (NarrativeArtifactError, SourceReadError, OSError):
            return False
        return True

    # ------------------------------------------------------------------
    # Public read-back of one persisted product at its exact identity.
    # ------------------------------------------------------------------
    def read_result_payload(self, result_ref: ReadResultRef) -> dict[str, Any]:
        """Return the persisted product with its identity and evidence."""
        ref = result_ref.source_ref
        reader = self._result_reader()
        bundle_version: NarrativeArtifactVersion | None = None
        data = b""
        try:
            if result_ref.role == NARRATIVE_READ_RESULT_ROLE:
                _read_version, data = reader.read_exact_read_result(
                    artifact_version_id=result_ref.artifact_version_id,
                    document_id=ref.document_id,
                    source_id=ref.source_id,
                    source_sha256=ref.content_sha256,
                    expected_sha256=result_ref.artifact_sha256,
                    expected_size=result_ref.byte_size,
                )
            else:
                bundle_version, _data = reader.read_exact(
                    artifact_version_id=result_ref.artifact_version_id,
                    document_id=ref.document_id,
                    source_id=ref.source_id,
                    source_sha256=ref.content_sha256,
                    expected_sha256=result_ref.artifact_sha256,
                    expected_size=result_ref.byte_size,
                )
        finally:
            reader.close()
        if result_ref.role == NARRATIVE_BUNDLE_ROLE:
            assert bundle_version is not None
            return {
                "schema_version": "cwp-bundle-reference/1",
                "result_ref": result_ref.to_dict(),
                "artifact_version_id": bundle_version.artifact_version_id,
                "note": "bundle_read_via_narrative_transport",
            }
        payload = json.loads(data.decode("utf-8"))
        return {
            "schema_version": READ_RESULT_PAYLOAD_SCHEMA,
            "result_ref": result_ref.to_dict(),
            "artifact_version_id": result_ref.artifact_version_id,
            "source_metadata": payload.get("source_metadata"),
            "parser": payload.get("parser"),
            "selector": payload.get("selector"),
            "selection": payload.get("selection"),
            "evidence_spans": payload.get("evidence_spans", []),
            "reading_level": payload.get("reading_level"),
            "model_requests": payload.get("model_requests", 0),
        }

    def _result_reader(self) -> NarrativeArtifactReader:
        return self._catalog.open_narrative_artifact_reader()

    # ------------------------------------------------------------------
    # Incremental backlog: paged exact refs for registered sources below
    # the declared reading tier, derived from this owner's own indexes.
    # ------------------------------------------------------------------
    def backlog(self, request: "ReadingBacklogRequest") -> "ReadingBacklogResponse":
        """Page exact SourceRefs of registered sources below the tier.

        States derive from persisted products: ``unread`` has neither a read
        result nor a bundle, and already-read sources stay listed with their
        state so a caller can verify rather than reprocess.
        """
        if not isinstance(request, ReadingBacklogRequest):
            raise TypeError("request must be ReadingBacklogRequest")
        reader = self._catalog.reader
        parameters: list[object] = []
        where = [
            "d.source_status='active'", "d.primary_source_id IS NOT NULL",
        ]
        kind_placeholders = ",".join("?" for _ in request.document_kinds)
        where.append(f"d.document_kind IN ({kind_placeholders})")
        parameters.extend(request.document_kinds)
        if request.entity is not None and request.source_market is None:
            where.append(
                "EXISTS (SELECT 1 FROM document_entities de JOIN entities e "
                "ON e.entity_id=de.entity_id WHERE de.document_id=d.document_id "
                "AND e.name=?)"
            )
            parameters.append(request.entity)
        # For the scheduled local queue, a catalog observation is sufficient
        # to find recently available undated originals. It never supplies a
        # publication date for historical eligibility or forecast evidence.
        dated_at = ("COALESCE(d.published_date, substr(d.first_seen_at, 1, 10))"
                    if request.source_market is not None else "d.published_date")
        if request.since_date is not None:
            where.append(f"{dated_at} >= ?")
            parameters.append(request.since_date)
        if request.as_of_date is not None:
            where.append(f"{dated_at} <= ?")
            parameters.append(request.as_of_date)
        if request.cursor is not None:
            where.append("d.document_id > ?")
            parameters.append(request.cursor)
        identity_filter = ""
        if request.entity is not None and request.source_market is not None:
            from .identity_candidates import identity_candidate_clause
            from .resolver import SourceResolver

            tokens = SourceResolver(self._catalog).issuer_identity_tokens(
                request.entity, market=request.source_market, security_id=request.security_id,
            )
            identity_filter, identity_parameters = identity_candidate_clause(reader, tokens)
            parameters.extend(identity_parameters)
        sql = (
            "SELECT d.document_id, d.primary_source_id, d.document_kind, "
            "d.published_date, d.title, s.content_sha256, s.byte_size, s.mime_type "
            "FROM documents d JOIN sources s ON s.source_id=d.primary_source_id "
            "WHERE " + " AND ".join(where) + " " + identity_filter +
            " ORDER BY d.document_id LIMIT ?"
        )
        parameters.append(request.limits.max_items + 1)
        rows = reader.fetchall(sql, tuple(parameters))
        has_more = len(rows) > request.limits.max_items
        rows = rows[:request.limits.max_items]
        items: list[ReadingBacklogItem] = []
        for row in rows:
            ref = SourceRefValue(
                schema_version="2.0", document_id=row["document_id"],
                source_id=row["primary_source_id"],
                content_sha256=row["content_sha256"], byte_size=row["byte_size"],
                mime_type=row["mime_type"],
            )
            if request.source_market is not None:
                from .security_code import canonical_security_code

                try:
                    current = self._reader.query_ref(ref.document_id, ref.source_id, ref.content_sha256)
                    source = self._reader.describe_version(current)
                except SourceReadError:
                    continue
                security_id = source.get("security_id")
                if source.get("market") != request.source_market or canonical_security_code(
                    None if security_id is None else str(security_id), request.source_market,
                ) != request.security_id:
                    continue
            state = self.existing_product(ref, request.reading_level) or ReadItemResult(
                ref, BACKLOG_UNREAD, None, False, (),
            )
            items.append(ReadingBacklogItem(
                source_ref=ref, state=state.state, result_ref=state.result_ref,
                document_kind=row["document_kind"],
                published_date=row["published_date"],
            ))
        next_cursor = rows[-1]["document_id"] if has_more and rows else None
        return ReadingBacklogResponse(
            reading_level=request.reading_level, items=tuple(items),
            next_cursor=next_cursor,
            usage={"listed": len(items), "model_requests": 0},
        )

    def _backlog_local_state(self, ref: SourceRefValue) -> ReadItemResult:
        version = self._visible_read_result(ref)
        if version is not None:
            item = self._local_product(ref, version, reused=True)
            if self.result_available(item.result_ref):
                return item
        return ReadItemResult(ref, BACKLOG_UNREAD, None, False, ())


__all__ = [
    "BACKLOG_UNREAD",
    "BUNDLE_REF_SCHEMA",
    "BacklogLimits",
    "INCREMENTAL_READ_REQUEST_SCHEMA",
    "INCREMENTAL_READ_SCHEMA",
    "READ_RESULT_PAYLOAD_SCHEMA",
    "READ_RESULT_REF_SCHEMA",
    "READING_BACKLOG_REQUEST_SCHEMA",
    "READING_BACKLOG_SCHEMA",
    "READING_LEVEL_LOCAL",
    "READING_LEVEL_SUMMARY",
    "STATE_DEFERRED",
    "STATE_FAILED",
    "STATE_READ",
    "STATE_SKIPPED",
    "STATE_SUMMARIZED",
    "STATE_UNCERTAIN",
    "IncrementalReadError",
    "IncrementalReadRequest",
    "IncrementalReadResponse",
    "IncrementalReadService",
    "ReadItemResult",
    "ReadLimits",
    "ReadResultRef",
    "ReadingBacklogItem",
    "ReadingBacklogRequest",
    "ReadingBacklogResponse",
]
