"""Recoverable writer from validated staging into company-owned immutable raw."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import os
from pathlib import Path
import re
import shutil
import unicodedata
from typing import Any

from company_wiki.source_contract import source_id_for_sha256

from .acquisition import DownloadCandidate, DownloadReceipt
from .lock import CatalogOperationLock
from .resolver import ResolutionResult, ResolutionStatus, SourceRequest, SourceResolver
from .scanner import scan_catalog, v2_scan_shadow_from_snapshot
from .service import SourceCatalog
from .store import canonical_json


CANONICAL_IMPORT_SCHEMA_VERSION = "1.0"
_INVALID_WINDOWS_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]+')
_SAFE_EXTENSION = re.compile(r"^\.[a-z0-9]{1,10}$")
_RESERVED_WINDOWS_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{index}" for index in range(1, 10)),
    *(f"LPT{index}" for index in range(1, 10)),
}


class CanonicalImportError(RuntimeError):
    """Raised when staged bytes cannot be safely committed as canonical raw."""


class CanonicalImportStatus(str, Enum):
    IMPORTED_NEW = "imported_new"
    DEDUPLICATED_AFTER_DOWNLOAD = "deduplicated_after_download"


@dataclass(frozen=True)
class CanonicalImportResult:
    schema_version: str
    status: CanonicalImportStatus
    request_id: str
    source_id: str
    content_sha256: str
    canonical_path: str
    provenance_path: str | None
    resolution: ResolutionResult

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "status": self.status.value,
            "request_id": self.request_id,
            "source_id": self.source_id,
            "content_sha256": self.content_sha256,
            "canonical_path": self.canonical_path,
            "provenance_path": self.provenance_path,
            "resolution": self.resolution.to_dict(),
        }


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_component(value: str, *, limit: int) -> str:
    normalized = unicodedata.normalize("NFC", value).strip()
    normalized = _INVALID_WINDOWS_CHARS.sub("_", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip(" .")
    if not normalized:
        normalized = "document"
    if normalized.upper() in _RESERVED_WINDOWS_NAMES:
        normalized = "_" + normalized
    return normalized[:limit].rstrip(" .") or "document"


def _destination_subdirectory(document_kind: str) -> Path:
    mapping = {
        "annual_report": Path("financial_reports") / "annual",
        "semi_annual_report": Path("financial_reports") / "semi_annual",
        "quarterly_report": Path("financial_reports") / "quarterly",
        "prospectus": Path("prospectus"),
        "broker_research": Path("research"),
        "research": Path("research"),
        "investor_relations": Path("investor_relations"),
        "news": Path("news"),
    }
    return mapping.get(document_kind, Path("other"))


def _extension(receipt: DownloadReceipt) -> str:
    suffix = Path(receipt.staged_path).suffix.lower()
    if _SAFE_EXTENSION.fullmatch(suffix):
        return suffix
    by_mime = {
        "application/pdf": ".pdf",
        "text/html": ".html",
        "text/plain": ".txt",
        "application/json": ".json",
    }
    return by_mime.get(receipt.mime_type, ".bin")


class CanonicalSourceWriter:
    """Own canonical paths, immutable provenance, hash reuse, and catalog registration."""

    def __init__(self, catalog: SourceCatalog, *, staging_root: Path | None = None):
        if not isinstance(catalog, SourceCatalog):
            raise TypeError("catalog must be SourceCatalog")
        if staging_root is not None and not isinstance(staging_root, Path):
            raise TypeError("staging_root must be pathlib.Path or null")
        company_roots = tuple(
            root for root in catalog.config.roots if root.kind == "company_raw"
        )
        if len(company_roots) != 1:
            raise CanonicalImportError("exactly one company_raw root is required")
        self.catalog = catalog
        self.company_root = company_roots[0]
        self.staging_root = (
            staging_root or catalog.config.catalog_dir / "staging"
        ).resolve(strict=False)

    def import_staged(
        self,
        request: SourceRequest,
        candidate: DownloadCandidate,
        receipt: DownloadReceipt,
    ) -> CanonicalImportResult:
        if not isinstance(request, SourceRequest):
            raise TypeError("request must be SourceRequest")
        if not isinstance(candidate, DownloadCandidate):
            raise TypeError("candidate must be DownloadCandidate")
        if not isinstance(receipt, DownloadReceipt):
            raise TypeError("receipt must be DownloadReceipt")
        staged = self._validate_staged(request, candidate, receipt)
        with CatalogOperationLock(
            self.catalog.config.catalog_dir,
            operation="canonical_import",
        ):
            self._reactivate_if_retired(receipt.content_sha256)
            existing = self._existing_original(receipt.content_sha256)
            if existing is not None:
                self._remove_staged(staged)
                resolution = SourceResolver(self.catalog).resolve(request)
                return CanonicalImportResult(
                    schema_version=CANONICAL_IMPORT_SCHEMA_VERSION,
                    status=CanonicalImportStatus.DEDUPLICATED_AFTER_DOWNLOAD,
                    request_id=request.request_id,
                    source_id=source_id_for_sha256(receipt.content_sha256),
                    content_sha256=receipt.content_sha256,
                    canonical_path=str(existing),
                    provenance_path=None,
                    resolution=resolution,
                )

            destination = self._destination(request, candidate, receipt)
            destination.parent.mkdir(parents=True, exist_ok=True)
            if destination.exists():
                if _hash_file(destination) != receipt.content_sha256:
                    destination = destination.with_name(
                        destination.stem
                        + "__"
                        + receipt.content_sha256[:12]
                        + destination.suffix
                    )
                if destination.exists() and _hash_file(destination) != receipt.content_sha256:
                    raise CanonicalImportError("canonical filename collision after hash suffix")
            if not destination.exists():
                self._atomic_copy(staged, destination, receipt)
            provenance = destination.with_name(destination.name + ".source.json")
            self._write_provenance(provenance, request, candidate, receipt)
            scan_catalog(
                self.catalog.config,
                self.catalog.store,
                dry_run=False,
                root_ids={self.company_root.root_id},
                v2_scan_shadow=v2_scan_shadow_from_snapshot(
                    self.catalog.config.catalog_dir
                ),
            )
            exact_request = SourceRequest(
                entity=request.entity,
                market=request.market,
                security_id=request.security_id,
                document_kind=request.document_kind,
                form_type=request.form_type or candidate.form_type,
                fiscal_year=request.fiscal_year or candidate.fiscal_year,
                fiscal_period=request.fiscal_period or candidate.fiscal_period,
                language=request.language or candidate.language,
                provider=candidate.provider,
                provider_document_id=candidate.provider_document_id,
                as_of_date=request.as_of_date,
                allow_download=request.allow_download,
            )
            resolution = SourceResolver(self.catalog).resolve(exact_request)
            if resolution.status is not ResolutionStatus.REUSED_EXACT:
                raise CanonicalImportError(
                    "canonical file was written but exact provider identity did not resolve"
                )
            self._remove_staged(staged)
            return CanonicalImportResult(
                schema_version=CANONICAL_IMPORT_SCHEMA_VERSION,
                status=CanonicalImportStatus.IMPORTED_NEW,
                request_id=request.request_id,
                source_id=source_id_for_sha256(receipt.content_sha256),
                content_sha256=receipt.content_sha256,
                canonical_path=str(destination.resolve()),
                provenance_path=str(provenance.resolve()),
                resolution=resolution,
            )

    def _validate_staged(
        self,
        request: SourceRequest,
        candidate: DownloadCandidate,
        receipt: DownloadReceipt,
    ) -> Path:
        if candidate.entity != request.entity:
            raise CanonicalImportError("candidate entity does not match request")
        if candidate.candidate_id != receipt.candidate_id:
            raise CanonicalImportError("receipt candidate_id does not match candidate")
        if candidate.provider != receipt.provider:
            raise CanonicalImportError("receipt provider does not match candidate")
        if candidate.provider_document_id != receipt.provider_document_id:
            raise CanonicalImportError("receipt provider identity does not match candidate")
        if candidate.source_url != receipt.source_url:
            raise CanonicalImportError("receipt source URL does not match candidate")
        staged = Path(receipt.staged_path).resolve(strict=True)
        staging_root = self.staging_root.resolve(strict=True)
        try:
            staged.relative_to(staging_root)
        except ValueError as exc:
            raise CanonicalImportError("staged file is outside configured staging root") from exc
        if not staged.is_file():
            raise CanonicalImportError("staged path is not a regular file")
        if staged.stat().st_size != receipt.byte_size:
            raise CanonicalImportError("staged byte_size does not match receipt")
        if _hash_file(staged) != receipt.content_sha256:
            raise CanonicalImportError("staged SHA-256 does not match receipt")
        return staged

    def _reactivate_if_retired(self, content_sha256: str) -> None:
        """Phase 15.6: a user-authorized re-download of bytes whose
        content-addressed document was retired must bring that document back
        to active (identical document_id, both the import and the dedup
        paths).  Plain rescans never revive retired documents — this is the
        explicit re-acquisition path only."""
        document_id = source_id_for_sha256(content_sha256).replace(
            "urn:company-wiki:source:", "urn:company-wiki:document:"
        )
        with self.catalog.store.transaction() as connection:
            connection.execute(
                "UPDATE documents SET source_status='active' "
                "WHERE document_id=? AND source_status='retired'",
                (document_id,),
            )
            connection.execute(
                "UPDATE locations SET location_status='active' "
                "WHERE document_id=? AND location_status='retired'",
                (document_id,),
            )

    def _existing_original(self, content_sha256: str) -> Path | None:
        # Only canonical company_raw locations are dedup targets: dayu
        # portfolio ingestion lives outside the companies/ subtree and its
        # paths are rejected by the filing-fetch handle contract (MongoDB
        # finding).
        rows = self.catalog.store.fetchall(
            """SELECT l.absolute_path FROM sources s
            JOIN locations l ON l.source_id=s.source_id
            JOIN roots r ON r.root_id=l.root_id
            WHERE s.content_sha256=? AND l.role='original_primary'
            AND l.location_status='active' AND r.kind='company_raw'
            ORDER BY r.priority,l.root_id,l.relative_path""",
            (content_sha256,),
        )
        for row in rows:
            path = Path(row["absolute_path"])
            if path.is_file() and _hash_file(path) == content_sha256:
                return path.resolve()
        return None

    def _destination(
        self,
        request: SourceRequest,
        candidate: DownloadCandidate,
        receipt: DownloadReceipt,
    ) -> Path:
        company = _safe_component(request.entity, limit=80)
        filename = "_".join(
            (
                candidate.filing_date,
                _safe_component(candidate.provider, limit=24),
                _safe_component(candidate.provider_document_id, limit=64),
                _safe_component(candidate.title, limit=90),
            )
        ) + _extension(receipt)
        return (
            self.company_root.path
            / company
            / "raw"
            / _destination_subdirectory(candidate.document_kind)
            / filename
        ).resolve(strict=False)

    @staticmethod
    def _atomic_copy(
        staged: Path,
        destination: Path,
        receipt: DownloadReceipt,
    ) -> None:
        temporary = destination.with_name(
            destination.name + f".{os.getpid()}.importing"
        )
        try:
            shutil.copyfile(staged, temporary)
            if temporary.stat().st_size != receipt.byte_size:
                raise CanonicalImportError("temporary canonical copy has wrong size")
            if _hash_file(temporary) != receipt.content_sha256:
                raise CanonicalImportError("temporary canonical copy has wrong SHA-256")
            os.replace(temporary, destination)
        finally:
            if temporary.exists():
                temporary.unlink()

    @staticmethod
    def _write_provenance(
        path: Path,
        request: SourceRequest,
        candidate: DownloadCandidate,
        receipt: DownloadReceipt,
    ) -> None:
        payload = {
            "schema_version": CANONICAL_IMPORT_SCHEMA_VERSION,
            "request_id": request.request_id,
            "company_name": request.entity,
            # Top-level identity field: the resolver and the scanner's
            # prefer-new metadata merge both read market at top level, while
            # security_id already sits here (portfolio-promotion spike).
            "market": request.market,
            "security_id": request.security_id,
            "source_title": candidate.title,
            "provider": candidate.provider,
            "provider_document_id": candidate.provider_document_id,
            "source_url": candidate.source_url,
            "document_kind": candidate.document_kind,
            "form_type": candidate.form_type,
            "filing_date": candidate.filing_date,
            "fiscal_year": candidate.fiscal_year,
            "fiscal_period": candidate.fiscal_period,
            "language": candidate.language,
            "amended": candidate.amended,
            "content_sha256": receipt.content_sha256,
            "byte_size": receipt.byte_size,
            "mime_type": receipt.mime_type,
            "retrieved_at": receipt.retrieved_at,
            "adapter_name": receipt.adapter_name,
            "adapter_version": receipt.adapter_version,
            "etag": receipt.etag,
            "last_modified": receipt.last_modified,
            "request": request.to_dict(),
            "candidate": candidate.to_dict(),
            "receipt": receipt.to_dict(),
        }
        encoded = (canonical_json(payload) + "\n").encode("utf-8")
        if path.exists():
            if path.read_bytes() != encoded:
                raise CanonicalImportError("immutable provenance sidecar conflict")
            return
        temporary = path.with_name(path.name + f".{os.getpid()}.tmp")
        try:
            temporary.write_bytes(encoded)
            os.replace(temporary, path)
        finally:
            if temporary.exists():
                temporary.unlink()

    def _remove_staged(self, staged: Path) -> None:
        try:
            staged.resolve(strict=True).relative_to(self.staging_root.resolve(strict=True))
        except (FileNotFoundError, ValueError) as exc:
            raise CanonicalImportError("refusing to remove file outside staging") from exc
        staged.unlink()


__all__ = [
    "CANONICAL_IMPORT_SCHEMA_VERSION",
    "CanonicalImportError",
    "CanonicalImportResult",
    "CanonicalImportStatus",
    "CanonicalSourceWriter",
]
