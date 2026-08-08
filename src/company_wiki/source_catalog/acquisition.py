"""Staging-only acquisition contracts and explicit market routing."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Protocol, runtime_checkable

from .gap_plan import GapPlan, build_gap_plan
from .resolver import (
    ResolutionResult,
    ResolutionStatus,
    SourceRequest,
    SourceResolver,
)
from .service import SourceCatalog


ACQUISITION_SCHEMA_VERSION = "1.0"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_UTC_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
_SEMVER_RE = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-[0-9A-Za-z]+(?:[.-][0-9A-Za-z]+)*)?"
    r"(?:\+[0-9A-Za-z]+(?:[.-][0-9A-Za-z]+)*)?$"
)


class AcquisitionError(RuntimeError):
    """Raised when an adapter or staged asset violates the acquisition contract."""


class MarketRoutingError(AcquisitionError):
    """Raised when a security market has no explicitly configured adapter."""


class AcquisitionStatus(str, Enum):
    REUSED = "reused"
    MISSING = "missing"
    AMBIGUOUS = "ambiguous"
    STAGED = "staged"
    GAP = "gap"  # WU-4.2: metadata-only plan returned, nothing downloaded


def _text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError(f"{name} must be non-empty trimmed text")
    return value


def _optional_text(value: Any, name: str) -> str | None:
    if value is None:
        return None
    return _text(value, name)


def _date(value: Any, name: str) -> str:
    value = _text(value, name)
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be a valid YYYY-MM-DD") from exc
    if parsed.isoformat() != value:
        raise ValueError(f"{name} must be canonical YYYY-MM-DD")
    return value


@dataclass(frozen=True)
class DownloadCandidate:
    candidate_id: str
    provider: str
    provider_document_id: str
    market: str
    entity: str
    title: str
    source_url: str
    document_kind: str
    filing_date: str
    fiscal_year: int
    form_type: str | None = None
    fiscal_period: str | None = None
    language: str | None = None
    amended: bool = False
    etag: str | None = None
    last_modified: str | None = None
    remote_size: int | None = None
    adapter_payload_json: str | None = None
    schema_version: str = ACQUISITION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != ACQUISITION_SCHEMA_VERSION:
            raise ValueError(f"schema_version must be {ACQUISITION_SCHEMA_VERSION}")
        for name in (
            "candidate_id",
            "provider",
            "provider_document_id",
            "market",
            "entity",
            "title",
            "source_url",
            "document_kind",
        ):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        object.__setattr__(self, "provider", self.provider.lower())
        object.__setattr__(self, "market", self.market.upper())
        object.__setattr__(self, "document_kind", self.document_kind.lower())
        if self.market not in {"CN", "HK", "US"}:
            raise ValueError("market must be CN, HK, or US")
        if not self.source_url.startswith("https://"):
            raise ValueError("source_url must be HTTPS")
        object.__setattr__(self, "filing_date", _date(self.filing_date, "filing_date"))
        for name in (
            "form_type",
            "fiscal_period",
            "language",
            "etag",
            "last_modified",
            "adapter_payload_json",
        ):
            object.__setattr__(self, name, _optional_text(getattr(self, name), name))
        if self.adapter_payload_json is not None:
            try:
                adapter_payload = json.loads(self.adapter_payload_json)
            except json.JSONDecodeError as exc:
                raise ValueError("adapter_payload_json must be valid JSON") from exc
            if not isinstance(adapter_payload, dict):
                raise ValueError("adapter_payload_json must contain a JSON object")
        if isinstance(self.fiscal_year, bool) or not isinstance(self.fiscal_year, int):
            raise TypeError("fiscal_year must be an integer")
        if not 1900 <= self.fiscal_year <= 2200:
            raise ValueError("fiscal_year is outside the supported range")
        if not isinstance(self.amended, bool):
            raise TypeError("amended must be boolean")
        if self.remote_size is not None and (
            isinstance(self.remote_size, bool)
            or not isinstance(self.remote_size, int)
            or self.remote_size <= 0
        ):
            raise ValueError("remote_size must be a positive integer or null")

    def to_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


@dataclass(frozen=True)
class DownloadReceipt:
    candidate_id: str
    provider: str
    provider_document_id: str
    source_url: str
    staged_path: str
    content_sha256: str
    byte_size: int
    mime_type: str
    retrieved_at: str
    http_status: int
    adapter_name: str
    adapter_version: str
    etag: str | None = None
    last_modified: str | None = None
    schema_version: str = ACQUISITION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != ACQUISITION_SCHEMA_VERSION:
            raise ValueError(f"schema_version must be {ACQUISITION_SCHEMA_VERSION}")
        for name in (
            "candidate_id",
            "provider",
            "provider_document_id",
            "source_url",
            "staged_path",
            "mime_type",
            "retrieved_at",
            "adapter_name",
            "adapter_version",
        ):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        object.__setattr__(self, "provider", self.provider.lower())
        if not self.source_url.startswith("https://"):
            raise ValueError("source_url must be HTTPS")
        if not _SHA256_RE.fullmatch(self.content_sha256):
            raise ValueError("content_sha256 must be lowercase SHA-256")
        if isinstance(self.byte_size, bool) or not isinstance(self.byte_size, int) or self.byte_size <= 0:
            raise ValueError("byte_size must be a positive integer")
        if (
            isinstance(self.http_status, bool)
            or not isinstance(self.http_status, int)
            or not 100 <= self.http_status <= 599
        ):
            raise ValueError("http_status must be an HTTP status integer")
        if not _UTC_RE.fullmatch(self.retrieved_at):
            raise ValueError("retrieved_at must be UTC YYYY-MM-DDTHH:MM:SSZ")
        try:
            datetime.strptime(self.retrieved_at, "%Y-%m-%dT%H:%M:%SZ")
        except ValueError as exc:
            raise ValueError("retrieved_at must be a valid UTC timestamp") from exc
        object.__setattr__(self, "etag", _optional_text(self.etag, "etag"))
        object.__setattr__(
            self, "last_modified", _optional_text(self.last_modified, "last_modified")
        )
        if not _SEMVER_RE.fullmatch(self.adapter_version):
            raise ValueError("adapter_version must be semantic version text")

    def to_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


@runtime_checkable
class DownloadAdapter(Protocol):
    name: str
    version: str

    def discover(self, request: SourceRequest) -> tuple[DownloadCandidate, ...]: ...

    def fetch(
        self,
        candidate: DownloadCandidate,
        staging_dir: Path,
    ) -> DownloadReceipt: ...


def _validate_adapter(adapter: Any, name: str) -> DownloadAdapter:
    if not isinstance(adapter, DownloadAdapter):
        raise TypeError(f"{name} must implement DownloadAdapter")
    _text(adapter.name, f"{name}.name")
    _text(adapter.version, f"{name}.version")
    return adapter


@dataclass(frozen=True)
class AdapterRegistry:
    cn: DownloadAdapter
    hk: DownloadAdapter
    us: DownloadAdapter

    def __post_init__(self) -> None:
        object.__setattr__(self, "cn", _validate_adapter(self.cn, "cn"))
        object.__setattr__(self, "hk", _validate_adapter(self.hk, "hk"))
        object.__setattr__(self, "us", _validate_adapter(self.us, "us"))

    def for_market(self, market: str) -> DownloadAdapter:
        normalized = _text(market, "market").upper()
        if normalized == "CN":
            return self.cn
        if normalized == "HK":
            return self.hk
        if normalized == "US":
            return self.us
        raise MarketRoutingError(f"unsupported market: {market}")


@dataclass(frozen=True)
class AcquisitionResult:
    schema_version: str
    status: AcquisitionStatus
    resolution: ResolutionResult
    adapter_name: str | None = None
    candidate: DownloadCandidate | None = None
    receipt: DownloadReceipt | None = None
    reason: str | None = None
    gap_plan: GapPlan | None = None  # WU-4.2: metadata-only plan (status GAP)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "status": self.status.value,
            "resolution": self.resolution.to_dict(),
            "adapter_name": self.adapter_name,
            "candidate": self.candidate.to_dict() if self.candidate else None,
            "receipt": self.receipt.to_dict() if self.receipt else None,
            "reason": self.reason,
            "gap_plan": self.gap_plan.to_dict() if self.gap_plan else None,
        }


class AcquisitionCoordinator:
    """Reuse catalog sources first; otherwise permit only validated staging writes."""

    def __init__(
        self,
        *,
        catalog: SourceCatalog,
        adapters: AdapterRegistry,
        staging_root: Path,
    ):
        if not isinstance(catalog, SourceCatalog):
            raise TypeError("catalog must be SourceCatalog")
        if not isinstance(adapters, AdapterRegistry):
            raise TypeError("adapters must be AdapterRegistry")
        if not isinstance(staging_root, Path):
            raise TypeError("staging_root must be pathlib.Path")
        self.catalog = catalog
        self.adapters = adapters
        self.staging_root = staging_root

    def resolve_or_stage(self, request: SourceRequest) -> AcquisitionResult:
        resolution = SourceResolver(self.catalog).resolve(request)
        if resolution.status in {
            ResolutionStatus.REUSED_EXACT,
            ResolutionStatus.REUSED_EQUIVALENT,
        }:
            if request.mode == "latest_as_of":
                # WU-4.2: a local reuse is not proof of being up-to-date —
                # the provider must be consulted (metadata only) to decide
                # reuse vs gap. Fall through to the gap-plan path.
                pass
            else:
                return AcquisitionResult(
                    schema_version=ACQUISITION_SCHEMA_VERSION,
                    status=AcquisitionStatus.REUSED,
                    resolution=resolution,
                    reason="existing_catalog_source_reused_before_adapter",
                )
        if resolution.status is ResolutionStatus.AMBIGUOUS:
            return AcquisitionResult(
                schema_version=ACQUISITION_SCHEMA_VERSION,
                status=AcquisitionStatus.AMBIGUOUS,
                resolution=resolution,
                reason=resolution.reason,
            )
        if resolution.status is ResolutionStatus.IDENTITY_CONFLICT:
            return AcquisitionResult(
                schema_version=ACQUISITION_SCHEMA_VERSION,
                status=AcquisitionStatus.MISSING,
                resolution=resolution,
                reason="identity_conflict_no_download",
            )
        if request.mode == "latest_as_of":
            # WU-4.2/4.3: latest_as_of ALWAYS returns the metadata-only gap
            # plan first — even when download is allowed, fetching must be
            # plan-driven and authorization-bound (WU-4.3). Nothing is
            # downloaded here.
            return self._gap_plan_result(request, resolution)
        if not request.allow_download:
            return AcquisitionResult(
                schema_version=ACQUISITION_SCHEMA_VERSION,
                status=AcquisitionStatus.MISSING,
                resolution=resolution,
                reason="download_required_but_not_allowed",
            )
        if request.market is None:
            raise MarketRoutingError("market is required before adapter discovery")
        adapter = self.adapters.for_market(request.market)
        candidates = tuple(adapter.discover(request))
        for candidate in candidates:
            if not isinstance(candidate, DownloadCandidate):
                raise AcquisitionError("adapter returned a non-DownloadCandidate value")
            if candidate.market != request.market:
                raise AcquisitionError("adapter candidate market does not match request")
            if candidate.document_kind != request.document_kind:
                raise AcquisitionError("adapter candidate document_kind does not match request")
            if request.fiscal_year is not None and candidate.fiscal_year != request.fiscal_year:
                raise AcquisitionError("adapter candidate fiscal_year does not match request")
        if not candidates:
            return AcquisitionResult(
                schema_version=ACQUISITION_SCHEMA_VERSION,
                status=AcquisitionStatus.MISSING,
                resolution=resolution,
                adapter_name=adapter.name,
                reason="adapter_discovery_returned_no_candidate",
            )
        if len(candidates) != 1:
            return AcquisitionResult(
                schema_version=ACQUISITION_SCHEMA_VERSION,
                status=AcquisitionStatus.AMBIGUOUS,
                resolution=resolution,
                adapter_name=adapter.name,
                reason="adapter_discovery_returned_multiple_candidates",
            )
        candidate = candidates[0]
        discovered_request = SourceRequest(
            entity=request.entity,
            market=request.market,
            security_id=request.security_id,
            document_kind=request.document_kind,
            form_type=request.form_type or candidate.form_type,
            fiscal_year=request.fiscal_year,
            fiscal_period=request.fiscal_period or candidate.fiscal_period,
            language=request.language or candidate.language,
            provider=candidate.provider,
            provider_document_id=candidate.provider_document_id,
            as_of_date=request.as_of_date,
            allow_download=request.allow_download,
        )
        discovered_resolution = SourceResolver(self.catalog).resolve(discovered_request)
        if discovered_resolution.status in {
            ResolutionStatus.REUSED_EXACT,
            ResolutionStatus.REUSED_EQUIVALENT,
        }:
            return AcquisitionResult(
                schema_version=ACQUISITION_SCHEMA_VERSION,
                status=AcquisitionStatus.REUSED,
                resolution=discovered_resolution,
                adapter_name=adapter.name,
                candidate=candidate,
                reason="existing_catalog_source_reused_after_discovery",
            )
        request_directory = self.staging_root / request.request_id.rsplit(":", 1)[-1]
        request_directory.mkdir(parents=True, exist_ok=True)
        receipt = adapter.fetch(candidate, request_directory)
        self._validate_receipt(candidate, receipt, request_directory)
        return AcquisitionResult(
            schema_version=ACQUISITION_SCHEMA_VERSION,
            status=AcquisitionStatus.STAGED,
            resolution=resolution,
            adapter_name=adapter.name,
            candidate=candidate,
            receipt=receipt,
            reason="missing_source_downloaded_to_staging_pending_canonical_import",
        )

    def _gap_plan_result(
        self, request: SourceRequest, resolution: ResolutionResult
    ) -> AcquisitionResult:
        """WU-4.2: metadata-only discovery for latest_as_of — discover remote
        metadata (never fetch), align with local reusable handles, and return
        a GapPlan. Nothing is downloaded and nothing is written."""
        if request.market is None:
            raise MarketRoutingError("market is required before adapter discovery")
        adapter = self.adapters.for_market(request.market)
        provider_error: str | None = None
        try:
            discovered = tuple(adapter.discover(request))
        except Exception as exc:  # offline / rate-limit / adapter failure
            provider_error = f"{type(exc).__name__}: {exc}"
            discovered = ()
        plan = build_gap_plan(
            request_id=request.request_id,
            as_of_date=request.as_of_date,
            document_kind=request.document_kind,
            entity=request.entity,
            market=request.market,
            local_handles=list(resolution.matches),
            remote_candidates=list(discovered),
            provider_error=provider_error,
        )
        return AcquisitionResult(
            schema_version=ACQUISITION_SCHEMA_VERSION,
            status=AcquisitionStatus.GAP,
            resolution=resolution,
            adapter_name=adapter.name,
            gap_plan=plan,
            reason=(
                "metadata_only_gap_plan"
                if provider_error is None
                else "metadata_only_gap_plan_provider_unavailable"
            ),
        )

    @staticmethod
    def _validate_receipt(
        candidate: DownloadCandidate,
        receipt: DownloadReceipt,
        staging_directory: Path,
    ) -> None:
        if not isinstance(receipt, DownloadReceipt):
            raise AcquisitionError("adapter returned a non-DownloadReceipt value")
        if receipt.candidate_id != candidate.candidate_id:
            raise AcquisitionError("receipt candidate_id does not match candidate")
        if receipt.provider != candidate.provider:
            raise AcquisitionError("receipt provider does not match candidate")
        if receipt.provider_document_id != candidate.provider_document_id:
            raise AcquisitionError("receipt provider_document_id does not match candidate")
        if receipt.source_url != candidate.source_url:
            raise AcquisitionError("receipt source_url does not match candidate")
        path = Path(receipt.staged_path).resolve(strict=True)
        allocated = staging_directory.resolve(strict=True)
        try:
            path.relative_to(allocated)
        except ValueError as exc:
            raise AcquisitionError("receipt path is outside allocated staging") from exc
        if not path.is_file():
            raise AcquisitionError("receipt staged_path is not a regular file")
        stat = path.stat()
        if stat.st_size != receipt.byte_size:
            raise AcquisitionError("receipt byte_size does not match staged file")
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        if digest.hexdigest() != receipt.content_sha256:
            raise AcquisitionError("receipt SHA-256 does not match staged file")
        if receipt.mime_type == "application/pdf" and not path.read_bytes()[:5] == b"%PDF-":
            raise AcquisitionError("staged PDF does not have PDF magic")
        if not 200 <= receipt.http_status < 300:
            raise AcquisitionError("receipt HTTP status is not successful")


__all__ = [
    "ACQUISITION_SCHEMA_VERSION",
    "AcquisitionCoordinator",
    "AcquisitionError",
    "AcquisitionResult",
    "AcquisitionStatus",
    "AdapterRegistry",
    "DownloadAdapter",
    "DownloadCandidate",
    "DownloadReceipt",
    "MarketRoutingError",
]
