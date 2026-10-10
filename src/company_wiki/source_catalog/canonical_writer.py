"""Recoverable writer from validated staging into company-owned immutable raw."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import unicodedata
from typing import TYPE_CHECKING, Any, Mapping

from company_wiki.source_contract import source_id_for_sha256

from .acquisition import DownloadCandidate, DownloadReceipt
from .download_budget import AcquisitionBudget
from .lock import CatalogOperationLock
from .resolver import SourceRequest
from .registration_scope import SourceRegistrationScope, register_catalog_sources
from .service import SourceCatalog
from .store import canonical_json

if TYPE_CHECKING:
    from .source_reader import SourceRef


CANONICAL_IMPORT_SCHEMA_VERSION = "1.0"
CANONICAL_IMPORT_RESULT_SCHEMA_VERSION = "2.0"
MAX_PROVENANCE_EXTENSIONS_BYTES = 16 * 1024
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
    source_ref: SourceRef

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "status": self.status.value,
            "request_id": self.request_id,
            "source_id": self.source_id,
            "content_sha256": self.content_sha256,
            "canonical_path": self.canonical_path,
            "provenance_path": self.provenance_path,
            "source_ref": asdict(self.source_ref),
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
        "investor_call_transcript": Path("investor_relations") / "transcripts",
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
        "application/xhtml+xml": ".html",
        "text/plain": ".txt",
        "application/json": ".json",
    }
    return by_mime.get(receipt.mime_type, ".bin")


@dataclass(frozen=True)
class _OfficialOriginal:
    """Actual source metadata, deliberately not a fiscal DownloadCandidate."""
    entity: str
    market: str | None
    title: str
    source_url: str
    document_kind: str
    filing_date: str | None
    fiscal_year: int | None
    fiscal_period: str | None
    language: str | None
    publisher: str
    provider: str
    provider_document_id: str
    form_type: str | None = None
    amended: bool = False
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {key: value for key, value in asdict(self).items() if key != "metadata"}


@dataclass(frozen=True)
class _OriginalStorageReceipt:
    """Local byte observation; no fabricated HTTP status or download event."""
    staged_path: str
    content_sha256: str
    byte_size: int
    mime_type: str
    retrieved_at: str
    adapter_name: str = "official-original-import"
    adapter_version: str = "1.0.0"
    etag: str | None = None
    last_modified: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class _SharedOriginal:
    """A source-oriented page with no single company owner.

    The storage layer places shared pages in one shared location inside the
    configured company root; consumers reach them through SourceRef 2.0 and
    issuer projections, never through a fabricated company directory.
    """

    title: str
    source_url: str
    document_kind: str
    publisher: str
    provider: str
    provider_document_id: str
    market: str | None = None
    language: str | None = None
    storage_group: str = "_shared"
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {key: value for key, value in asdict(self).items() if key != "metadata"}


@dataclass(frozen=True)
class _SharedImportIntent:
    """Minimal commit intent for shared pages: an id, no company."""

    request_id: str
    document_kind: str
    storage_group: str = "_shared"

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "storage_intent": "shared_source",
            "document_kind": self.document_kind,
            "storage_group": self.storage_group,
        }


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
        *,
        provenance_extensions: Mapping[str, Any] | None = None,
        budget: AcquisitionBudget | None = None,
    ) -> CanonicalImportResult:
        if not isinstance(request, SourceRequest):
            raise TypeError("request must be SourceRequest")
        if not isinstance(candidate, DownloadCandidate):
            raise TypeError("candidate must be DownloadCandidate")
        if not isinstance(receipt, DownloadReceipt):
            raise TypeError("receipt must be DownloadReceipt")
        if provenance_extensions is not None:
            if not isinstance(provenance_extensions, Mapping):
                raise TypeError("provenance_extensions must be a mapping or null")
            if any(
                not isinstance(key, str)
                or not re.fullmatch(r"[a-z][a-z0-9_]{1,63}", key)
                for key in provenance_extensions
            ):
                raise CanonicalImportError("invalid provenance extension name")
            try:
                extension_size = len(canonical_json(dict(provenance_extensions)).encode("utf-8"))
            except (TypeError, ValueError) as exc:
                raise CanonicalImportError("provenance extensions must be canonical JSON") from exc
            if extension_size > MAX_PROVENANCE_EXTENSIONS_BYTES:
                raise CanonicalImportError("provenance extensions exceed byte limit")
        staged = self._validate_staged(request, candidate, receipt)
        return self._commit_staged(request, candidate, receipt, staged,
                                   provenance_extensions=provenance_extensions, budget=budget)

    def _commit_staged(self, request, candidate, receipt, staged, *,
                       provenance_extensions=None, budget=None, reactivate_retired=True, cleanup_staged=True):
        """One immutable commit algorithm shared by provider and local originals."""
        with CatalogOperationLock(
            self.catalog.config.catalog_dir,
            operation="canonical_import",
            budget=budget,
        ):
            if budget is not None:
                budget.ensure_open()
            if reactivate_retired:
                # Explicit provider re-acquisition retains its existing contract.
                self._reactivate_if_retired(receipt.content_sha256)
            else:
                # A local import cannot turn a withdrawal into fresh provider approval.
                document_id = source_id_for_sha256(receipt.content_sha256).replace(
                    "urn:company-wiki:source:", "urn:company-wiki:document:")
                current = (self.catalog.reader.exact_source_version(document_id)
                           if self.catalog.config.database_path.exists() else None)
                if current is not None and current["source_status"] != "active":
                    raise CanonicalImportError("local import requires atomic metadata reconciliation")
            existing = self._existing_original(receipt.content_sha256)
            if existing is not None:
                source_ref = self.source_ref_for_import(request, candidate, receipt.content_sha256)
                if cleanup_staged:
                    self._remove_staged(staged)
                return CanonicalImportResult(
                    schema_version=CANONICAL_IMPORT_RESULT_SCHEMA_VERSION,
                    status=CanonicalImportStatus.DEDUPLICATED_AFTER_DOWNLOAD,
                    request_id=request.request_id,
                    source_id=source_id_for_sha256(receipt.content_sha256),
                    content_sha256=receipt.content_sha256,
                    canonical_path=str(existing),
                    provenance_path=None,
                    source_ref=source_ref,
                )

            destination = self._destination(request, candidate, receipt)
            destination.parent.mkdir(parents=True, exist_ok=True)
            # DEF-MSFT-CANONICAL-DUP: ``destination_preexisting`` marks the
            # case where the computed content path holds byte-identical content — a
            # re-serve of bytes an earlier acquisition committed to this
            # content path. The copy below is then a no-op and the immutable
            # provenance sidecar must NOT be rewritten: it belongs to the
            # first acquisition of these bytes, and request_id/retrieved_at
            # differ on every attempt (writing would die on the immutable
            # sidecar conflict and orphan the file yet again).
            destination_preexisting = False
            if destination.exists():
                if _hash_file(destination) != receipt.content_sha256:
                    raise CanonicalImportError("canonical_content_name_collision")
                # A byte-identical existing final path is a re-acquisition.
                destination_preexisting = destination.exists()
            if not destination.exists():
                self._atomic_copy(staged, destination, receipt)
            provenance = destination.with_name(destination.name + ".source.json")
            if destination_preexisting and provenance.exists():
                self._verify_committed_provenance(provenance, candidate, receipt)
            else:
                self._write_provenance(
                    provenance,
                    request,
                    candidate,
                    receipt,
                    provenance_extensions=provenance_extensions,
                )
            # Registration proves the committed content exists in the catalog.
            # Business identity, reporting periods and historical cutoffs belong
            # to selection; storage returns the exact committed version directly.
            register_catalog_sources(
                self.catalog.config, self.catalog.store,
                SourceRegistrationScope(self.company_root.root_id,
                    frozenset({destination.relative_to(self.company_root.path).as_posix()})),
            )
            source_ref = self.source_ref_for_import(request, candidate, receipt.content_sha256)
            if cleanup_staged:
                self._remove_staged(staged)
            return CanonicalImportResult(
                schema_version=CANONICAL_IMPORT_RESULT_SCHEMA_VERSION,
                # DEF-MSFT-CANONICAL-DUP: when the committed bytes were
                # already on canonical disk this import is a re-acquisition
                # of existing content, not a new document — journal it as
                # the established deduplicated outcome.
                status=(
                    CanonicalImportStatus.DEDUPLICATED_AFTER_DOWNLOAD
                    if destination_preexisting
                    else CanonicalImportStatus.IMPORTED_NEW
                ),
                request_id=request.request_id,
                source_id=source_id_for_sha256(receipt.content_sha256),
                content_sha256=receipt.content_sha256,
                canonical_path=str(destination.resolve()),
                provenance_path=str(provenance.resolve()),
                source_ref=source_ref,
            )

    def import_original_staged(
        self, *, request: SourceRequest, metadata: Mapping[str, Any],
        staged_path: Path, content_sha256: str, byte_size: int, mime_type: str,
        retrieved_at: str, capture_receipt: Mapping[str, Any], cleanup_staged: bool = True,
    ) -> CanonicalImportResult:
        """Commit already verified local original through the same storage path.

        OfficialSourceFlow owns MIME/capture/metadata validation. This storage
        boundary checks the staged byte identity and owns the immutable copy,
        deduplication, provenance and registration. It does not label a local
        import as an HTTP download or manufacture a financial reporting year.
        """
        staged = staged_path.resolve(strict=True)
        staged.relative_to(self.staging_root.resolve(strict=True))
        if (not staged.is_file() or staged.is_symlink() or staged.stat().st_size != byte_size
                or _hash_file(staged) != content_sha256):
            raise CanonicalImportError("staged original byte identity mismatch")
        candidate = _OfficialOriginal(
            entity=request.entity, market=request.market, title=metadata["title"],
            source_url=metadata["source_url"], document_kind=request.document_kind,
            filing_date=metadata.get("filing_date"), fiscal_year=metadata.get("fiscal_year"),
            fiscal_period=metadata.get("fiscal_period"), language=metadata.get("language"),
            publisher=metadata["publisher"], provider="official",
            provider_document_id=metadata.get("provider_document_id") or content_sha256,
            metadata=dict(metadata),
        )
        receipt = _OriginalStorageReceipt(str(staged), content_sha256, byte_size,
                                          mime_type, retrieved_at)
        return self._commit_staged(request, candidate, receipt, staged,
                                  provenance_extensions={"official_capture": dict(capture_receipt)},
                                  reactivate_retired=False, cleanup_staged=cleanup_staged)

    def import_shared_original_staged(
        self, *, request_id: str, document_kind: str, title: str,
        source_url: str, publisher: str, staged_path: Path, content_sha256: str,
        byte_size: int, mime_type: str, retrieved_at: str,
        capture_receipt: Mapping[str, Any], provenance_extensions: Mapping[str, Any],
        cleanup_staged: bool = True, market: str | None = None,
        language: str | None = None, storage_group: str = "_shared",
    ) -> CanonicalImportResult:
        """Commit a shared, source-oriented page without a company owner.

        The same immutable commit algorithm as company originals, but the
        storage intent carries no entity: the destination is one shared group
        inside the configured company root, chosen here by the storage layer.
        """
        staged = staged_path.resolve(strict=True)
        staged.relative_to(self.staging_root.resolve(strict=True))
        if (not staged.is_file() or staged.is_symlink() or staged.stat().st_size != byte_size
                or _hash_file(staged) != content_sha256):
            raise CanonicalImportError("staged original byte identity mismatch")
        candidate = _SharedOriginal(
            title=title, source_url=source_url, document_kind=document_kind,
            publisher=publisher, provider="official",
            provider_document_id=content_sha256, market=market,
            language=language, storage_group=storage_group,
        )
        receipt = _OriginalStorageReceipt(str(staged), content_sha256, byte_size,
                                          mime_type, retrieved_at,
                                          adapter_name="official-json-import")
        intent = _SharedImportIntent(request_id=request_id,
                                     document_kind=document_kind,
                                     storage_group=storage_group)
        return self._commit_staged(intent, candidate, receipt, staged,
                                  provenance_extensions=dict(provenance_extensions),
                                  reactivate_retired=False, cleanup_staged=cleanup_staged)

    def source_ref_for_import(
        self,
        request: SourceRequest,
        candidate: DownloadCandidate,
        sha256: str,
    ) -> SourceRef:
        """Return the committed content version without repeating selection.

        Request/candidate remain in this compatibility signature. Their scope
        was checked at the write boundary; neither capture metadata nor a
        historical cutoff is required to identify committed bytes.
        """
        from .source_reader import SourceReadError, SourceVersionReader

        source_id = source_id_for_sha256(sha256)
        document_id = source_id.replace("urn:company-wiki:source:", "urn:company-wiki:document:")
        try:
            return SourceVersionReader(self.catalog).query_ref(document_id, source_id, sha256)
        except SourceReadError as exc:
            raise CanonicalImportError("committed source was not indexed to its bytes") from exc

    def _validate_staged(
        self,
        request: SourceRequest,
        candidate: DownloadCandidate,
        receipt: DownloadReceipt,
    ) -> Path:
        from .acquisition_validation import candidate_scope_problem, receipt_binding_problem

        problem = candidate_scope_problem(request, candidate)
        if problem is not None:
            raise CanonicalImportError(f"candidate {problem} does not match request")
        problem = receipt_binding_problem(candidate, receipt)
        if problem is not None:
            raise CanonicalImportError(f"receipt {problem} does not match candidate")
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
        # Human title/provider IDs are immutable metadata, never physical names.
        # Count UTF-16 units for the portable Win32 limit and reserve the longest
        # provenance atomic suffix (including a ten-digit PID) before any write.
        if isinstance(candidate, _SharedOriginal):
            directory = (
                self.company_root.path
                / _safe_component(candidate.storage_group, limit=80)
                / "raw"
                / _destination_subdirectory(candidate.document_kind)
            ).resolve(strict=False)
        else:
            directory = (self.company_root.path / _safe_component(request.entity, limit=80)
                         / "raw" / _destination_subdirectory(candidate.document_kind)).resolve(strict=False)
        extension = _extension(receipt)
        suffix_reserve = len(".source.json.9999999999.tmp")
        units = len(str(directory).encode("utf-16-le")) // 2
        available = 259 - units - 1 - len(extension) - suffix_reserve
        if available < 16:
            raise CanonicalImportError("canonical_root_path_limit")
        name = receipt.content_sha256[:min(64, available)] + extension
        return directory / name

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
            with temporary.open("r+b") as committed_bytes:
                os.fsync(committed_bytes.fileno())
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
        *,
        provenance_extensions: Mapping[str, Any] | None = None,
    ) -> None:
        payload = {
            "schema_version": CANONICAL_IMPORT_SCHEMA_VERSION,
            "request_id": request.request_id,
            "company_name": getattr(request, "entity", None),
            # Top-level identity field: the resolver and the scanner's
            # prefer-new metadata merge both read market at top level, while
            # security_id already sits here (portfolio-promotion spike).
            "market": candidate.market,
            "security_id": getattr(request, "security_id", None),
            "source_title": candidate.title,
            "provider": candidate.provider,
            "provider_document_id": candidate.provider_document_id,
            "source_url": candidate.source_url,
            "document_kind": candidate.document_kind,
            "form_type": getattr(candidate, "form_type", None),
            "filing_date": getattr(candidate, "filing_date", None),
            "fiscal_year": getattr(candidate, "fiscal_year", None),
            "fiscal_period": getattr(candidate, "fiscal_period", None),
            "language": candidate.language,
            "amended": getattr(candidate, "amended", False),
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
        if isinstance(candidate, _OfficialOriginal):
            payload.update({"display_name": candidate.entity,
                            "published_date": candidate.metadata["published_date"],
                            "period_end": candidate.metadata.get("period_end"),
                            "publisher": candidate.publisher,
                            "collector_name": "official-original-import",
                            "collector_version": "1.0.0"})
            if candidate.metadata.get("canonical_entity_id") is not None:
                payload["canonical_entity_id"] = candidate.metadata["canonical_entity_id"]
        if isinstance(candidate, _SharedOriginal):
            # No display owner and no publication guess: shared pages carry
            # their subject identity in provenance extensions instead.
            payload.update({"company_name": None,
                            "publisher": candidate.publisher,
                            "collector_name": "official-json-import",
                            "collector_version": "2.0.0"})
        if provenance_extensions is not None:
            payload["provenance_extensions"] = dict(provenance_extensions)
        encoded = (canonical_json(payload) + "\n").encode("utf-8")
        if path.exists():
            if path.read_bytes() != encoded:
                raise CanonicalImportError("immutable provenance sidecar conflict")
            return
        temporary = path.with_name(path.name + f".{os.getpid()}.tmp")
        try:
            with temporary.open("wb") as stream:
                stream.write(encoded)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path)
        finally:
            if temporary.exists():
                temporary.unlink()

    @staticmethod
    def _verify_committed_provenance(
        path: Path,
        candidate: DownloadCandidate,
        receipt: DownloadReceipt,
    ) -> None:
        """DEF-MSFT-CANONICAL-DUP: the canonical file already held these
        exact bytes, so its immutable sidecar belongs to the FIRST
        acquisition of them.  Re-acquisition must not rewrite it — but it
        must also never adopt a sidecar describing a different document.
        Verify the identity binding and fail closed on anything else (the
        error string matches _write_provenance's conflict so the failure
        taxonomy is unchanged)."""
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise CanonicalImportError("immutable provenance sidecar conflict") from exc
        if (
            existing.get("content_sha256") != receipt.content_sha256
            or existing.get("provider") != candidate.provider
            or existing.get("provider_document_id")
            != candidate.provider_document_id
            or existing.get("byte_size") != receipt.byte_size
        ):
            raise CanonicalImportError("immutable provenance sidecar conflict")

    def _remove_staged(self, staged: Path) -> None:
        try:
            staged.resolve(strict=True).relative_to(self.staging_root.resolve(strict=True))
        except (FileNotFoundError, ValueError) as exc:
            raise CanonicalImportError("refusing to remove file outside staging") from exc
        staged.unlink()


__all__ = [
    "CANONICAL_IMPORT_SCHEMA_VERSION",
    "CANONICAL_IMPORT_RESULT_SCHEMA_VERSION",
    "CanonicalImportError",
    "CanonicalImportResult",
    "CanonicalImportStatus",
    "CanonicalSourceWriter",
]
