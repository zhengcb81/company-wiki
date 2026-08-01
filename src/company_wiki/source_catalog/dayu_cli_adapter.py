"""Invoke Dayu's existing CLI and read its public storage without modifying Dayu."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
import hashlib
import json
import mimetypes
import os
from pathlib import Path
import re
import shutil
import subprocess
from tempfile import TemporaryDirectory
import time
from typing import Any, Sequence

from .acquisition import DownloadCandidate, DownloadReceipt
from .resolver import SourceRequest
from .store import canonical_json


_MARKETS = frozenset({"HK", "US"})
_SAFE_COMPONENT_RE = re.compile(r"[^A-Za-z0-9._-]+")
_SHA256_RE = re.compile(r"[0-9a-f]{64}")
_US_ANNUAL_FORMS = ("10-K", "20-F")
_US_QUARTERLY_FORMS = ("10-Q", "10-Q/A")


class DayuCliAdapterError(RuntimeError):
    """Raised when Dayu CLI execution or its public storage contract is invalid."""


@dataclass(frozen=True)
class _DownloadedAsset:
    candidate_id: str
    source_path: Path
    content_sha256: str
    byte_size: int
    mime_type: str


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _required_text(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DayuCliAdapterError(f"Dayu meta {field_name} must be non-empty text")
    return value.strip()


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise DayuCliAdapterError("Dayu optional meta text must be text or null")
    normalized = value.strip()
    return normalized or None


def _safe_component(value: str) -> str:
    cleaned = _SAFE_COMPONENT_RE.sub("_", value).strip("._")
    if not cleaned:
        raise DayuCliAdapterError("Dayu source filename is unsafe")
    return cleaned[:180]


def _mime_type(filename: str, configured: Any) -> str:
    if isinstance(configured, str) and configured.strip():
        return configured.strip().lower().split(";", 1)[0]
    guessed, _encoding = mimetypes.guess_type(filename)
    return guessed or "application/octet-stream"


def _forms_for_request(request: SourceRequest) -> tuple[str, ...]:
    if request.form_type:
        return (request.form_type,)
    if request.market == "HK":
        if request.fiscal_period:
            return (request.fiscal_period,)
        if request.document_kind == "annual_report":
            return ("FY",)
        if request.document_kind == "semi_annual_report":
            return ("H1",)
        if request.document_kind == "quarterly_report":
            return ("Q1", "Q2", "Q3", "Q4")
    if request.market == "US":
        if request.document_kind == "annual_report":
            return _US_ANNUAL_FORMS
        if request.document_kind == "quarterly_report":
            return _US_QUARTERLY_FORMS
    raise DayuCliAdapterError(
        f"Dayu CLI does not support {request.market}/{request.document_kind}"
    )


class DayuCliDownloadAdapter:
    """Run ``python -m dayu.cli download`` in an isolated temporary workspace."""

    def __init__(
        self,
        *,
        name: str,
        version: str,
        market: str,
        command: Sequence[str],
        project_root: Path,
        config_root: Path,
        workspace_parent: Path,
        timeout_seconds: float = 600.0,
    ):
        if not isinstance(name, str) or not name.strip():
            raise ValueError("name must be non-empty text")
        if not isinstance(version, str) or not version.strip():
            raise ValueError("version must be non-empty text")
        normalized_market = str(market).strip().upper()
        if normalized_market not in _MARKETS:
            raise ValueError("Dayu CLI adapter market must be HK or US")
        if isinstance(command, (str, bytes)) or not command:
            raise ValueError("command must be a non-empty string sequence")
        normalized_command = tuple(command)
        if not all(isinstance(item, str) and item.strip() for item in normalized_command):
            raise ValueError("command items must be non-empty strings")
        if "company_wiki_adapter" in " ".join(normalized_command):
            raise ValueError("Dayu CLI command must not depend on a company-wiki Dayu module")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        self.name = name.strip()
        self.version = version.strip()
        self.market = normalized_market
        self.command = normalized_command
        self.project_root = project_root.resolve(strict=True)
        self.config_root = config_root.resolve(strict=True)
        if not self.config_root.is_dir():
            raise ValueError("config_root must be an existing directory")
        self.workspace_parent = workspace_parent.resolve(strict=False)
        self.timeout_seconds = float(timeout_seconds)
        self._temporary: TemporaryDirectory[str] | None = None
        self._workspace: Path | None = None
        self._assets: dict[str, _DownloadedAsset] = {}

    def discover(self, request: SourceRequest) -> tuple[DownloadCandidate, ...]:
        if not isinstance(request, SourceRequest):
            raise TypeError("request must be SourceRequest")
        if request.market != self.market:
            raise DayuCliAdapterError("request market does not match Dayu CLI adapter")
        if not request.security_id:
            raise DayuCliAdapterError("Dayu CLI download requires security_id")
        if request.fiscal_year is None:
            raise DayuCliAdapterError("Dayu CLI download requires fiscal_year")
        self.close()
        self.workspace_parent.mkdir(parents=True, exist_ok=True)
        self._temporary = TemporaryDirectory(
            prefix=f"dayu-{self.market.lower()}-",
            dir=self.workspace_parent,
        )
        self._workspace = Path(self._temporary.name).resolve(strict=True)
        forms = _forms_for_request(request)
        command = [
            *self.command,
            "download",
            "--ticker",
            request.security_id,
            "--forms",
            *forms,
            "--start",
            f"{request.fiscal_year}-01-01",
            "--end",
            request.as_of_date,
            "--base",
            str(self._workspace),
            "--config",
            str(self.config_root),
            "--quiet",
        ]
        environment = dict(os.environ)
        environment["PYTHONUTF8"] = "1"
        creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        # Use Popen + poll so we can read meta.json as soon as it is written,
        # without waiting for dayu's slow Docling/RapidOCR post-processing.
        try:
            process = subprocess.Popen(
                command,
                text=True,
                encoding="utf-8",
                errors="replace",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=self.project_root,
                env=environment,
                shell=False,
                creationflags=creationflags,
            )
        except OSError as exc:
            self.close()
            raise DayuCliAdapterError(f"Dayu CLI process failed: {exc}") from exc
        candidates: tuple[DownloadCandidate, ...] = ()
        elapsed = 0.0
        poll_interval = 3.0
        while process.poll() is None and elapsed < self.timeout_seconds:
            time.sleep(poll_interval)
            elapsed += poll_interval
            if (self._workspace / "portfolio").is_dir():
                try:
                    candidates = self._read_candidates(request)
                except Exception:
                    candidates = ()
                if candidates:
                    break
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        cli_stderr = ""
        if process.returncode is not None and process.returncode != 0:
            cli_stderr = ((process.stderr.read() or "").strip())[-3000:]
        try:
            if not candidates:
                candidates = self._read_candidates(request)
        except Exception:
            self.close()
            raise
        if process.returncode not in (None, 0) and not candidates:
            self.close()
            raise DayuCliAdapterError(
                f"Dayu CLI exited {process.returncode}: {cli_stderr or 'no output'}"
            )
        if not candidates:
            self.close()
        return candidates

    def fetch(
        self,
        candidate: DownloadCandidate,
        staging_dir: Path,
    ) -> DownloadReceipt:
        if not isinstance(candidate, DownloadCandidate):
            raise TypeError("candidate must be DownloadCandidate")
        if not isinstance(staging_dir, Path):
            raise TypeError("staging_dir must be pathlib.Path")
        asset = self._assets.get(candidate.candidate_id)
        if asset is None or self._workspace is None:
            raise DayuCliAdapterError("Dayu CLI candidate workspace is unavailable")
        try:
            source = asset.source_path.resolve(strict=True)
            source.relative_to(self._workspace)
            if not source.is_file():
                raise DayuCliAdapterError("Dayu primary source is not a regular file")
            digest = _sha256_file(source)
            if digest != asset.content_sha256 or source.stat().st_size != asset.byte_size:
                raise DayuCliAdapterError("Dayu primary source no longer matches its meta")
            if asset.mime_type == "application/pdf":
                with source.open("rb") as stream:
                    if stream.read(5) != b"%PDF-":
                        raise DayuCliAdapterError("Dayu PDF failed magic validation")
            staging_dir.mkdir(parents=True, exist_ok=True)
            allocated = staging_dir.resolve(strict=True)
            destination = (allocated / _safe_component(source.name)).resolve(strict=False)
            destination.relative_to(allocated)
            temporary = destination.with_name(destination.name + f".{os.getpid()}.tmp")
            try:
                shutil.copyfile(source, temporary)
                if _sha256_file(temporary) != digest:
                    raise DayuCliAdapterError("staged copy hash differs from Dayu source")
                os.replace(temporary, destination)
            finally:
                temporary.unlink(missing_ok=True)
            return DownloadReceipt(
                candidate_id=candidate.candidate_id,
                provider=candidate.provider,
                provider_document_id=candidate.provider_document_id,
                source_url=candidate.source_url,
                staged_path=str(destination),
                content_sha256=digest,
                byte_size=asset.byte_size,
                mime_type=asset.mime_type,
                retrieved_at=_utc_now(),
                http_status=200,
                adapter_name=self.name,
                adapter_version=self.version,
                etag=candidate.etag,
                last_modified=candidate.last_modified,
            )
        finally:
            self.close()

    def close(self) -> None:
        self._assets.clear()
        self._workspace = None
        temporary, self._temporary = self._temporary, None
        if temporary is not None:
            temporary.cleanup()

    def _read_candidates(self, request: SourceRequest) -> tuple[DownloadCandidate, ...]:
        if self._workspace is None:
            raise DayuCliAdapterError("Dayu CLI workspace is unavailable")
        portfolio = self._workspace / "portfolio"
        if not portfolio.is_dir():
            return ()
        candidates: list[DownloadCandidate] = []
        for meta_path in sorted(portfolio.glob("*/filings/*/meta.json")):
            candidate = self._candidate_from_meta(request, meta_path)
            if candidate is not None:
                candidates.append(candidate)
        return tuple(
            sorted(
                candidates,
                key=lambda item: (
                    item.provider_document_id,
                    item.filing_date,
                    item.candidate_id,
                ),
            )
        )

    def _candidate_from_meta(
        self,
        request: SourceRequest,
        meta_path: Path,
    ) -> DownloadCandidate | None:
        try:
            value = json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise DayuCliAdapterError(f"invalid Dayu meta {meta_path}: {exc}") from exc
        if not isinstance(value, dict):
            raise DayuCliAdapterError("Dayu filing meta must be an object")
        if value.get("is_deleted") is True:
            return None
        # Accept filings where the primary PDF exists, even if post-processing (docling) failed
        primary_doc = value.get("primary_document")
        filing_dir = meta_path.parent
        pdf_exists = primary_doc and (filing_dir / primary_doc).is_file()
        if not pdf_exists:
            # HK filings may not have primary_document; check files array instead
            files = value.get("files")
            if isinstance(files, list):
                pdf_exists = any(
                    isinstance(f, dict) and f.get("source") == "original"
                    and str(f.get("name", "")).lower().endswith(".pdf")
                    for f in files
                )
        if value.get("ingest_complete") is not True and not pdf_exists:
            return None
        fiscal_year = value.get("fiscal_year")
        if isinstance(fiscal_year, bool) or not isinstance(fiscal_year, int):
            return None
        if fiscal_year != request.fiscal_year:
            return None
        fiscal_period = _optional_text(value.get("fiscal_period"))
        if request.fiscal_period and fiscal_period != request.fiscal_period:
            return None
        form_type = _required_text(value.get("form_type"), "form_type")
        allowed_forms = _forms_for_request(request)
        if form_type not in allowed_forms:
            return None
        filing_date = _required_text(value.get("filing_date"), "filing_date")
        try:
            parsed_filing_date = date.fromisoformat(filing_date)
        except ValueError as exc:
            raise DayuCliAdapterError("Dayu filing_date must be YYYY-MM-DD") from exc
        if parsed_filing_date > date.fromisoformat(request.as_of_date):
            return None
        if self.market == "HK":
            provider = _required_text(value.get("source_provider"), "source_provider").lower()
            if provider != "hkexnews":
                return None
            provider_document_id = _required_text(value.get("source_id"), "source_id")
            source_url = _required_text(value.get("source_url"), "source_url")
            file_entry = self._hk_primary_entry(value)
            language = _optional_text(value.get("source_language")) or "zh"
        else:
            provider = "sec"
            provider_document_id = _required_text(
                value.get("accession_number"), "accession_number"
            )
            file_entry = self._us_primary_entry(value)
            source_url = _required_text(file_entry.get("source_url"), "files[].source_url")
            language = "en"
        if request.provider and request.provider.lower() != provider:
            return None
        if (
            request.provider_document_id
            and request.provider_document_id != provider_document_id
        ):
            return None
        filename = _required_text(file_entry.get("name"), "files[].name")
        source_path = (meta_path.parent / filename).resolve(strict=True)
        source_path.relative_to(self._workspace)
        if not source_path.is_file():
            raise DayuCliAdapterError("Dayu meta primary file is missing")
        byte_size = file_entry.get("size")
        if isinstance(byte_size, bool) or not isinstance(byte_size, int) or byte_size <= 0:
            byte_size = source_path.stat().st_size
        configured_hash = str(file_entry.get("sha256") or "").strip().lower()
        content_sha256 = (
            configured_hash if _SHA256_RE.fullmatch(configured_hash) else _sha256_file(source_path)
        )
        mime_type = _mime_type(filename, file_entry.get("content_type"))
        candidate_id = f"{provider}:{provider_document_id}"
        title = (
            _optional_text(value.get("source_title"))
            or f"{request.entity} {form_type} {value.get('report_date') or filing_date}"
        )
        candidate = DownloadCandidate(
            candidate_id=candidate_id,
            provider=provider,
            provider_document_id=provider_document_id,
            market=self.market,
            entity=request.entity,
            title=title,
            source_url=source_url,
            document_kind=request.document_kind,
            form_type=form_type,
            filing_date=filing_date,
            fiscal_year=fiscal_year,
            fiscal_period=fiscal_period,
            language=language,
            amended=bool(value.get("amended", False)),
            etag=_optional_text(file_entry.get("http_etag")),
            last_modified=_optional_text(file_entry.get("http_last_modified")),
            remote_size=byte_size,
            adapter_payload_json=canonical_json(
                {
                    "dayu_document_id": value.get("document_id"),
                    "primary_filename": filename,
                    "content_sha256": content_sha256,
                }
            ),
        )
        self._assets[candidate_id] = _DownloadedAsset(
            candidate_id=candidate_id,
            source_path=source_path,
            content_sha256=content_sha256,
            byte_size=byte_size,
            mime_type=mime_type,
        )
        return candidate

    @staticmethod
    def _hk_primary_entry(meta: dict[str, Any]) -> dict[str, Any]:
        files = meta.get("files")
        if not isinstance(files, list):
            raise DayuCliAdapterError("Dayu HK meta files must be an array")
        originals = [
            item
            for item in files
            if isinstance(item, dict) and item.get("source") == "original"
        ]
        pdf = next(
            (
                item
                for item in originals
                if str(item.get("name", "")).lower().endswith(".pdf")
            ),
            None,
        )
        if pdf is None:
            raise DayuCliAdapterError("Dayu HK meta has no original PDF")
        return pdf

    @staticmethod
    def _us_primary_entry(meta: dict[str, Any]) -> dict[str, Any]:
        primary = _required_text(meta.get("primary_document"), "primary_document")
        files = meta.get("files")
        if not isinstance(files, list):
            raise DayuCliAdapterError("Dayu SEC meta files must be an array")
        entry = next(
            (
                item
                for item in files
                if isinstance(item, dict) and item.get("name") == primary
            ),
            None,
        )
        if entry is None:
            raise DayuCliAdapterError("Dayu SEC primary document is missing from files")
        return entry


__all__ = [
    "DayuCliAdapterError",
    "DayuCliDownloadAdapter",
]
