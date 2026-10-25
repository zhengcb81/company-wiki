"""PDF reading implementation boundary: one owner for read, identity and replay.

Schedulers supply logical intent and the existing resource account. Backend
options and compatibility rereads belong here, never in a consumer or handler.
The native backend remains the only enabled production implementation.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
import hashlib
import json
import math
import re
import time
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any, Protocol

from company_wiki.resource_budget import WorkBudget
from company_wiki.source_contract import EvidenceSpan

from . import narrative_evidence as native
from .narrative_document import NarrativeEvidencePackage, NarrativeParseResult


class PdfReadingError(RuntimeError):
    """A concrete reading resource/deployment failure, not corrupt source bytes."""


@dataclass(frozen=True)
class PdfReadingRequest:
    source_id: str
    source_sha256: str
    language: str
    title: str = ""
    document_kind: str = "unknown"


class PdfBytesParser(Protocol):
    def __call__(self, data: bytes, *, source_id: str, source_sha256: str,
                 language: str = "zh", full_table_scan: bool = False,
                 selector_version: str | None = None,
                 work_budget: WorkBudget | None = None,
                 reading_context: Any | None = None,
                 layout_max_seconds: float = 15) -> NarrativeParseResult: ...


class PdfReadingBackend(Protocol):
    def describe_recipe(self) -> Mapping[str, Any]: ...
    def read(self, data: bytes, request: PdfReadingRequest, *, selector_version: str,
             work_budget: WorkBudget | None, full_table_scan: bool = False,
             deadline: float | None = None
             ) -> NarrativeParseResult: ...
    def verify_material(self, parsed: NarrativeParseResult,
                        evidence_spans: Sequence[EvidenceSpan]) -> None: ...
    def replay(self, data: bytes, *, source_id: str, source_sha256: str,
               evidence_spans: Sequence[EvidenceSpan], language: str
               ) -> tuple[tuple[str, ...], tuple[str, ...]]: ...


class NativePdfBackend:
    """Canonical native text/locator contract, including compatible test ports.

    A callback supplied here declares this same native contract. A different
    producer must implement the complete backend, not masquerade as this one.
    """
    def __init__(self, *, parser: PdfBytesParser | None = None,
                 replayer: Callable[..., Any] | None = None,
                 paragraph_enhancement: Any | None = None) -> None:
        self._parser = parser
        self._replayer = replayer
        self._paragraph_enhancement = paragraph_enhancement

    def describe_recipe(self) -> Mapping[str, Any]:
        try:
            runtime_version = version("pymupdf")
        except PackageNotFoundError as exc:
            raise PdfReadingError("PDF_DEPENDENCY_UNAVAILABLE: pymupdf") from exc
        recipe = {
            "format": "pdf",
            "parser_name": native.NARRATIVE_PARSER_NAME,
            "parser_version": native.NARRATIVE_PARSER_VERSION,
            "reader_recipe": "native-pdf/1",
            "runtime": {"pymupdf": runtime_version},
            "reader_implementation_sha256": hashlib.sha256(
                Path(__file__).read_bytes().replace(b"\r\n", b"\n")
            ).hexdigest(),
        }
        if self._paragraph_enhancement is not None:
            recipe["paragraph_enhancement"] = dict(self._paragraph_enhancement.describe_recipe())
        return recipe

    def read(self, data: bytes, request: PdfReadingRequest, *, selector_version: str,
             work_budget: WorkBudget | None, full_table_scan: bool = False,
             deadline: float | None = None
             ) -> NarrativeParseResult:
        parser = self._parser or native.parse_pdf_bytes
        arguments: dict[str, Any] = {
            "source_id": request.source_id, "source_sha256": request.source_sha256,
            "language": request.language, "full_table_scan": full_table_scan,
        }
        if selector_version == "0.9.0":
            from company_wiki.document_understanding.geometry_intent.reading import PdfReadingContext
            arguments.update(
                selector_version=selector_version, work_budget=work_budget,
                layout_max_seconds=(15 if deadline is None else
                                    min(15, _remaining_seconds(deadline))),
                reading_context=PdfReadingContext(
                    request.title, request.document_kind, request.language),
            )
        # No callable-identity branch or TypeError retry: every implementation
        # of the current contract receives the same resource/context inputs.
        parsed = parser(data, **arguments)
        if selector_version == "0.9.0" and self._paragraph_enhancement is not None:
            if work_budget is None:
                raise ValueError("paragraph enhancement requires the shared document work budget")
            parsed = self._paragraph_enhancement.enhance(data, parsed,
                work_budget=work_budget, deadline=deadline)
        return parsed

    def verify_material(self, parsed: NarrativeParseResult,
                        evidence_spans: Sequence[EvidenceSpan]) -> None:
        from .narrative_replay import verify_replayed_pdf_spans
        verified, failed = verify_replayed_pdf_spans(evidence_spans, parsed.units)
        if failed or len(verified) != len(evidence_spans):
            raise ValueError("selected evidence differs from parsed PDF material")

    def replay(self, data: bytes, *, source_id: str, source_sha256: str,
               evidence_spans: Sequence[EvidenceSpan], language: str
               ) -> tuple[tuple[str, ...], tuple[str, ...]]:
        replayer = self._replayer or native.verify_pdf_evidence_spans_bytes
        return replayer(data, source_id=source_id, source_sha256=source_sha256,
                        evidence_spans=evidence_spans, language=language)


class PdfReading:
    """One implementation set shared by reading, publication and cache identity."""
    def __init__(self, backend: PdfReadingBackend | None = None, *,
                 parser: PdfBytesParser | None = None,
                 replayer: Callable[..., Any] | None = None,
                 deadline: float | None = None) -> None:
        if backend is not None and (parser is not None or replayer is not None):
            raise ValueError("provide a complete backend or native-compatible callbacks")
        if backend is None:
            from .narrative_pdf_enhancement import configured_paragraph_runtime
            backend = NativePdfBackend(parser=parser, replayer=replayer,
                paragraph_enhancement=configured_paragraph_runtime())
        self._backend = backend
        self._deadline = _valid_deadline(deadline)
        self._recipe: dict[str, Any] | None = None

    def _descriptor(self) -> dict[str, Any]:
        descriptor = json.loads(json.dumps(dict(self._backend.describe_recipe()), allow_nan=False))
        _validate_descriptor(descriptor)
        if len(json.dumps(descriptor).encode("utf-8")) > 8192:
            raise ValueError("PDF reading recipe exceeds compact descriptor bound")
        if any(not isinstance(descriptor.get(key), str) or not descriptor[key].strip()
               for key in ("parser_name", "parser_version")):
            raise ValueError("PDF reading producer descriptor is invalid")
        return descriptor

    def _check_recipe(self) -> None:
        current = self._descriptor()
        if self._recipe is None:
            self._recipe = current
        elif current != self._recipe:
            raise ValueError("PDF reading implementation drifted from its frozen recipe")

    def validate_frozen_recipe(self, recipe: Mapping[str, Any]) -> None:
        """Check a recorded plan without interpreting it in the scheduler."""
        if dict(recipe) != self.describe_recipe():
            raise ValueError("PDF reading implementation differs from frozen recipe")

    def describe_recipe(self) -> dict[str, Any]:
        self._check_recipe()
        return json.loads(json.dumps(self._recipe))

    def parser_identity(self) -> tuple[str, str]:
        descriptor = self.describe_recipe()
        return str(descriptor["parser_name"]), str(descriptor["parser_version"])

    def read(self, data: bytes, request: PdfReadingRequest, *, selector_version: str,
             work_budget: WorkBudget | None = None,
             deadline: float | None = None) -> NarrativeParseResult:
        return self._read(data, request, selector_version=selector_version,
                          work_budget=work_budget, full_table_scan=False, deadline=deadline)

    def _read(self, data: bytes, request: PdfReadingRequest, *, selector_version: str,
              work_budget: WorkBudget | None, full_table_scan: bool,
              deadline: float | None = None
              ) -> NarrativeParseResult:
        bounds = [v for v in (self._deadline, _valid_deadline(deadline)) if v is not None]
        deadline = min(bounds) if bounds else None
        _remaining_seconds(deadline)
        self._check_recipe()
        if work_budget is not None and (work_budget.exhausted
                or work_budget.used >= work_budget.max_work_units):
            work_budget.charge()  # stop before any backend IO on an empty account
        parsed = self._backend.read(data, request, selector_version=selector_version,
            work_budget=work_budget, full_table_scan=full_table_scan, deadline=deadline)
        _remaining_seconds(deadline)
        self._check_recipe()
        identity = self.parser_identity()
        if work_budget is not None:
            work_budget.charge(len(parsed.units))
        if (parsed.source_id != request.source_id
                or parsed.source_sha256 != request.source_sha256
                or any(unit.source_id != request.source_id
                       or (unit.parser_name, unit.parser_version) != identity
                       for unit in parsed.units)):
            raise ValueError("PDF reader returned a different source or producer")
        return parsed

    def select(self, data: bytes, request: PdfReadingRequest, *, selector: Any,
               work_budget: WorkBudget | None, checkpoint: Callable[[], Any],
               deadline: float | None = None
               ) -> tuple[NarrativeParseResult, NarrativeEvidencePackage]:
        checkpoint()
        parsed = self.read(data, request, selector_version=selector.selector_version,
                           work_budget=work_budget, deadline=deadline)
        checkpoint()
        package = selector(parsed, title=request.title or "untitled",
            existing_kind=request.document_kind, work_budget=work_budget)
        if (selector.selector_version != "0.9.0" and not package.evidence_spans
                and parsed.deferred_table_pages):
            parsed = self._read(data, request, selector_version=selector.selector_version,
                work_budget=work_budget, full_table_scan=True, deadline=deadline)
            checkpoint()
            package = selector(parsed, title=request.title or "untitled",
                existing_kind=request.document_kind, work_budget=work_budget)
        return parsed, package

    def verify_material(self, parsed: NarrativeParseResult,
                        evidence_spans: Sequence[EvidenceSpan]) -> None:
        if self._recipe is not None:
            self._check_recipe()
        self._backend.verify_material(parsed, evidence_spans)

    def replay(self, data: bytes, *, source_id: str, source_sha256: str,
               evidence_spans: Sequence[EvidenceSpan], language: str
               ) -> tuple[tuple[str, ...], tuple[str, ...]]:
        self._check_recipe()
        return self._backend.replay(data, source_id=source_id, source_sha256=source_sha256,
                                   evidence_spans=evidence_spans, language=language)


# Recipe metadata is not a source-content or arbitrary deployment-config dump.
# This validation belongs at the owner boundary, not in individual consumers.
_PRIVATE_RECIPE_KEYS = frozenset({
    "api_key", "apikey", "api_key_env", "access_token", "api_token", "token",
    "authorization", "password", "secret", "credentials", "credential",
    "path", "absolute_path", "local_path", "file_path", "model_path", "root_path",
})


def _validate_descriptor(value: Any) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if key.lower() in _PRIVATE_RECIPE_KEYS:
                raise ValueError("PDF reading recipe contains a private field")
            _validate_descriptor(child)
    elif isinstance(value, list):
        for child in value:
            _validate_descriptor(child)
    elif isinstance(value, str) and (
        value.startswith(("/", "\\", "~"))
        or re.match(r"[A-Za-z]:[\\/]", value)
        or value.lower().startswith("file://")
    ):
        raise ValueError("PDF reading recipe contains a physical location")


def _valid_deadline(value: float | None) -> float | None:
    if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float))
                              or not math.isfinite(value)):
        raise ValueError("PDF reading deadline must be finite")
    return value


def _remaining_seconds(deadline: float | None) -> float:
    remaining = math.inf if deadline is None else deadline - time.monotonic()
    if remaining <= 0:
        raise PdfReadingError("PDF_READING_DEADLINE: absolute task deadline exceeded")
    return remaining
