"""Create-once collection of one explicit official exchange announcement PDF."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, fields
from datetime import date, datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat as stat_module
import tempfile
import unicodedata
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit, urlunsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from .source_manifest import SourceManifest, SourceType


ANNOUNCEMENT_COLLECTION_SCHEMA_VERSION = "1.0.0"
ANNOUNCEMENT_COLLECTION_ID_PREFIX = (
    "urn:company-wiki:announcement-collection:sha256:"
)
ANNOUNCEMENT_COLLECTOR_NAME = "company-wiki-explicit-announcement"
ANNOUNCEMENT_COLLECTOR_VERSION = "1.0.0"
DEFAULT_MAX_BYTES = 64 * 1024 * 1024
OFFICIAL_EXCHANGE_DOMAINS = ("sse.com.cn", "szse.cn")

_HTTP_TIMEOUT_SECONDS = 30
_PDF_EOF_WINDOW = 2048
_SOURCE_MANIFEST_ROOT = "source_manifests"
_SOURCE_PROVENANCE_ROOT = "source_provenance"


class AnnouncementCollectionError(ValueError):
    """Base error for invalid or unsafe announcement collection."""


class AnnouncementURLPolicyError(AnnouncementCollectionError):
    """Raised before a request to a URL outside the official-domain policy."""


class AnnouncementDownloadError(AnnouncementCollectionError):
    """Raised when the bounded HTTP download cannot complete safely."""


class AnnouncementContentError(AnnouncementCollectionError):
    """Raised when the response is not a bounded PDF document."""


class AnnouncementConflictError(AnnouncementCollectionError):
    """Raised when an existing immutable path disagrees with collected bytes."""


@dataclass(frozen=True)
class DownloadedAnnouncement:
    """Bounded HTTP response material needed for provenance."""

    body: bytes
    final_url: str
    content_type: str
    etag: str | None = None
    last_modified: str | None = None


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _canonical_sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _require_text(value: Any, field_name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be text")
    if not value or value != value.strip():
        raise AnnouncementCollectionError(
            f"{field_name} must be non-empty trimmed text"
        )
    if unicodedata.normalize("NFC", value) != value:
        raise AnnouncementCollectionError(f"{field_name} must use Unicode NFC")
    if any(ord(character) < 32 for character in value):
        raise AnnouncementCollectionError(
            f"{field_name} must not contain control characters"
        )
    return value


def _require_optional_header(value: Any, field_name: str) -> str | None:
    if value is None:
        return None
    return _require_text(value, field_name)


def _require_published_date(value: Any) -> str:
    if not isinstance(value, str):
        raise TypeError("published_date must be YYYY-MM-DD text")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise AnnouncementCollectionError(
            "published_date must be a valid YYYY-MM-DD"
        ) from exc
    if parsed.isoformat() != value:
        raise AnnouncementCollectionError(
            "published_date must be canonical YYYY-MM-DD"
        )
    return value


def _require_max_bytes(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError("max_bytes must be an integer")
    if value <= 0:
        raise AnnouncementCollectionError("max_bytes must be positive")
    return value


def _official_host(hostname: str | None) -> bool:
    if not hostname:
        return False
    normalized = hostname.casefold().rstrip(".")
    return any(
        normalized == domain or normalized.endswith("." + domain)
        for domain in OFFICIAL_EXCHANGE_DOMAINS
    )


def validate_official_announcement_url(url: str) -> str:
    """Return a canonical HTTPS URL only for official SSE/SZSE domains."""

    url = _require_text(url, "announcement URL")
    try:
        parts = urlsplit(url)
        port = parts.port
    except ValueError as exc:
        raise AnnouncementURLPolicyError("announcement URL is invalid") from exc
    if parts.scheme.casefold() != "https":
        raise AnnouncementURLPolicyError("announcement URL must use HTTPS")
    if parts.username is not None or parts.password is not None:
        raise AnnouncementURLPolicyError("announcement URL must not contain credentials")
    if port is not None:
        raise AnnouncementURLPolicyError("announcement URL must use the default HTTPS port")
    if not _official_host(parts.hostname):
        raise AnnouncementURLPolicyError(
            "announcement URL host is not an official SSE/SZSE domain"
        )
    if parts.fragment:
        raise AnnouncementURLPolicyError("announcement URL must not contain a fragment")
    if not parts.path or parts.path == "/":
        raise AnnouncementURLPolicyError("announcement URL must identify a document path")
    if "\\" in parts.path:
        raise AnnouncementURLPolicyError("announcement URL path must not contain backslashes")
    host = (parts.hostname or "").casefold().rstrip(".")
    return urlunsplit(("https", host, parts.path, parts.query, ""))


class _OfficialRedirectHandler(HTTPRedirectHandler):
    """Validate each redirect target before urllib can issue the next request."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        validated = validate_official_announcement_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, validated)


def download_announcement(
    url: str,
    max_bytes: int = DEFAULT_MAX_BYTES,
    *,
    opener=None,
) -> DownloadedAnnouncement:
    """Download one official URL with redirect and byte-count fail-closed gates."""

    validated_url = validate_official_announcement_url(url)
    maximum = _require_max_bytes(max_bytes)
    active_opener = opener or build_opener(_OfficialRedirectHandler())
    request = Request(
        validated_url,
        headers={
            "Accept": "application/pdf",
            "User-Agent": (
                "company-wiki-explicit-announcement/"
                + ANNOUNCEMENT_COLLECTOR_VERSION
            ),
        },
        method="GET",
    )
    try:
        with active_opener.open(request, timeout=_HTTP_TIMEOUT_SECONDS) as response:
            status = getattr(response, "status", None)
            if status != 200:
                raise AnnouncementDownloadError(
                    f"announcement HTTP status must be 200, got {status}"
                )
            final_url = validate_official_announcement_url(response.geturl())
            content_type = response.headers.get("Content-Type", "")
            content_length = response.headers.get("Content-Length")
            if content_length is not None:
                try:
                    declared_length = int(content_length)
                except (TypeError, ValueError) as exc:
                    raise AnnouncementDownloadError(
                        "announcement Content-Length is invalid"
                    ) from exc
                if declared_length > maximum:
                    raise AnnouncementContentError(
                        "announcement exceeds the configured maximum byte size"
                    )
            body = response.read(maximum + 1)
            if len(body) > maximum:
                raise AnnouncementContentError(
                    "announcement exceeds the configured maximum byte size"
                )
            if content_length is not None and declared_length != len(body):
                raise AnnouncementDownloadError(
                    "announcement body length does not match Content-Length"
                )
            return DownloadedAnnouncement(
                body=body,
                final_url=final_url,
                content_type=content_type,
                etag=response.headers.get("ETag"),
                last_modified=response.headers.get("Last-Modified"),
            )
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        raise AnnouncementDownloadError(f"announcement download failed: {exc}") from exc


def _validate_download(
    response: DownloadedAnnouncement,
    *,
    max_bytes: int,
) -> DownloadedAnnouncement:
    if not isinstance(response, DownloadedAnnouncement):
        raise TypeError("fetcher must return DownloadedAnnouncement")
    if not isinstance(response.body, bytes):
        raise TypeError("announcement body must be bytes")
    if not response.body:
        raise AnnouncementContentError("announcement response is empty")
    if len(response.body) > max_bytes:
        raise AnnouncementContentError(
            "announcement exceeds the configured maximum byte size"
        )
    content_type = _require_text(response.content_type, "content type")
    if content_type.split(";", 1)[0].strip().casefold() != "application/pdf":
        raise AnnouncementContentError(
            "announcement content type must be application/pdf"
        )
    if not response.body.startswith(b"%PDF-"):
        raise AnnouncementContentError("announcement is missing PDF magic")
    if b"%%EOF" not in response.body[-_PDF_EOF_WINDOW:]:
        raise AnnouncementContentError("announcement is missing the PDF EOF marker")
    final_url = validate_official_announcement_url(response.final_url)
    return DownloadedAnnouncement(
        body=response.body,
        final_url=final_url,
        content_type=content_type,
        etag=_require_optional_header(response.etag, "ETag"),
        last_modified=_require_optional_header(
            response.last_modified, "Last-Modified"
        ),
    )


def _require_company_name(value: Any) -> str:
    value = _require_text(value, "company_name")
    if value in {".", ".."} or "/" in value or "\\" in value:
        raise AnnouncementCollectionError(
            "company_name must be one canonical path segment"
        )
    return value


def _resolve_root(root: Path) -> Path:
    if not isinstance(root, Path):
        raise TypeError("root must be pathlib.Path")
    resolved = root.resolve(strict=True)
    if not resolved.is_dir():
        raise AnnouncementCollectionError("root must be an existing directory")
    return resolved


def _resolve_company(root: Path, company_name: str) -> Path:
    companies = root / "companies"
    companies_resolved = companies.resolve(strict=True)
    try:
        companies_resolved.relative_to(root)
    except ValueError as exc:
        raise AnnouncementCollectionError("companies directory escapes root") from exc
    company = companies / company_name
    if company.is_symlink():
        raise AnnouncementCollectionError("company directory must not be a symlink")
    company_resolved = company.resolve(strict=True)
    if not company_resolved.is_dir():
        raise AnnouncementCollectionError("company directory must exist")
    try:
        relative = company_resolved.relative_to(companies_resolved)
    except ValueError as exc:
        raise AnnouncementCollectionError("company directory escapes companies root") from exc
    if len(relative.parts) != 1:
        raise AnnouncementCollectionError("company directory must be a direct child")
    return company_resolved


def _ensure_directory(path: Path, *, root: Path) -> None:
    try:
        relative = path.relative_to(root)
    except ValueError as exc:
        raise AnnouncementCollectionError("collector target escapes root") from exc
    cursor = root
    for part in relative.parts:
        cursor = cursor / part
        if cursor.exists() and cursor.is_symlink():
            raise AnnouncementCollectionError(
                f"collector target traverses a symlink: {cursor}"
            )
    path.mkdir(parents=True, exist_ok=True)
    resolved = path.resolve(strict=True)
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise AnnouncementCollectionError("collector directory escapes root") from exc
    if not resolved.is_dir():
        raise AnnouncementCollectionError("collector parent is not a directory")


def _hash_path(path: Path) -> str:
    digest = hashlib.sha256()
    with open(_native_link_path(path), "rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _path_exists(path: Path) -> bool:
    try:
        os.lstat(_native_link_path(path))
        return True
    except FileNotFoundError:
        return False


def _verify_existing(path: Path, content: bytes, *, label: str) -> None:
    try:
        metadata = os.lstat(_native_link_path(path))
    except FileNotFoundError as exc:
        raise AnnouncementConflictError(f"{label} disappeared during verification") from exc
    if stat_module.S_ISLNK(metadata.st_mode) or not stat_module.S_ISREG(
        metadata.st_mode
    ):
        raise AnnouncementConflictError(f"{label} is not a regular immutable file")
    expected_hash = hashlib.sha256(content).hexdigest()
    if metadata.st_size != len(content) or _hash_path(path) != expected_hash:
        raise AnnouncementConflictError(f"{label} conflicts with collected bytes")


def _native_link_path(path: Path) -> str:
    """Give Windows hard-link calls an absolute extended-length path."""

    value = str(path.absolute())
    if os.name == "nt" and not value.startswith("\\\\?\\"):
        return "\\\\?\\" + value
    return value


def _immutable_create_bytes(
    path: Path,
    content: bytes,
    *,
    root: Path,
    mtime_epoch: int | None = None,
    label: str,
) -> bool:
    """Atomically hard-link a prepared temp file without overwrite authority."""

    if not isinstance(content, bytes) or not content:
        raise AnnouncementContentError(f"{label} content must be non-empty bytes")
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise AnnouncementCollectionError("immutable target escapes root") from exc
    _ensure_directory(path.parent, root=root)
    if _path_exists(path):
        _verify_existing(path, content, label=label)
        return False

    temp_parent = root / "tmp"
    temp_directory = temp_parent / "source-collector"
    parent_existed = temp_parent.exists()
    directory_existed = temp_directory.exists()
    _ensure_directory(temp_directory, root=root)
    descriptor, temp_name = tempfile.mkstemp(
        prefix="announcement-",
        suffix=".tmp",
        dir=temp_directory,
    )
    temp_path = Path(temp_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        if mtime_epoch is not None:
            os.utime(temp_path, (mtime_epoch, mtime_epoch))
        try:
            os.link(_native_link_path(temp_path), _native_link_path(path))
        except FileExistsError:
            _verify_existing(path, content, label=label)
            return False
        _verify_existing(path, content, label=label)
        return True
    finally:
        try:
            temp_path.unlink()
        except FileNotFoundError:
            pass
        if not directory_existed:
            try:
                temp_directory.rmdir()
            except OSError:
                pass
        if not parent_existed:
            try:
                temp_parent.rmdir()
            except OSError:
                pass


def _immutable_create_json(path: Path, value: object, *, root: Path) -> bool:
    content = (_canonical_json(value) + "\n").encode("utf-8")
    label = "manifest" if _SOURCE_MANIFEST_ROOT in path.parts else "provenance"
    return _immutable_create_bytes(
        path,
        content,
        root=root,
        label=label,
    )


def _canonical_relative(path: Path, *, root: Path) -> str:
    try:
        relative = path.relative_to(root)
    except ValueError as exc:
        raise AnnouncementCollectionError("collector path escapes root") from exc
    value = unicodedata.normalize("NFC", relative.as_posix())
    if PurePosixPath(value).as_posix() != value:
        raise AnnouncementCollectionError("collector path is not canonical")
    return value


def _retrieved_at_from_raw(path: Path) -> str:
    timestamp = path.stat().st_mtime_ns // 1_000_000_000
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )


def _now_epoch(now: Callable[[], datetime]) -> int:
    moment = now()
    if not isinstance(moment, datetime):
        raise TypeError("now must return datetime")
    if moment.tzinfo is None or moment.utcoffset() is None:
        raise AnnouncementCollectionError("now must return a timezone-aware datetime")
    return int(moment.astimezone(timezone.utc).timestamp())


@dataclass(frozen=True)
class AnnouncementCollectionReceipt:
    schema_version: str
    collection_id: str
    collector_name: str
    collector_version: str
    source_url: str
    final_url: str
    title: str
    published_date: str
    retrieved_at: str
    content_type: str
    etag: str | None
    last_modified: str | None
    manifest_path: str
    provenance_path: str
    manifest: SourceManifest

    @classmethod
    def create(
        cls,
        *,
        source_url: str,
        final_url: str,
        title: str,
        published_date: str,
        retrieved_at: str,
        content_type: str,
        etag: str | None,
        last_modified: str | None,
        manifest_path: str,
        provenance_path: str,
        manifest: SourceManifest,
    ) -> "AnnouncementCollectionReceipt":
        payload = {
            "schema_version": ANNOUNCEMENT_COLLECTION_SCHEMA_VERSION,
            "collector_name": ANNOUNCEMENT_COLLECTOR_NAME,
            "collector_version": ANNOUNCEMENT_COLLECTOR_VERSION,
            "source_url": source_url,
            "final_url": final_url,
            "title": title,
            "published_date": published_date,
            "retrieved_at": retrieved_at,
            "content_type": content_type,
            "etag": etag,
            "last_modified": last_modified,
            "manifest_path": manifest_path,
            "provenance_path": provenance_path,
            "manifest": manifest.to_dict(),
        }
        return cls(
            collection_id=(
                ANNOUNCEMENT_COLLECTION_ID_PREFIX + _canonical_sha256(payload)
            ),
            manifest=manifest,
            **{key: value for key, value in payload.items() if key != "manifest"},
        )

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "AnnouncementCollectionReceipt":
        if not isinstance(data, Mapping):
            raise TypeError("announcement collection receipt must be an object")
        known = {field.name for field in fields(cls)}
        supplied = set(data)
        if supplied != known:
            raise AnnouncementCollectionError(
                "announcement collection receipt fields do not match v1"
            )
        manifest = SourceManifest.from_dict(data["manifest"])
        prepared = dict(data)
        prepared["manifest"] = manifest
        receipt = cls(**prepared)
        expected = cls.create(
            source_url=receipt.source_url,
            final_url=receipt.final_url,
            title=receipt.title,
            published_date=receipt.published_date,
            retrieved_at=receipt.retrieved_at,
            content_type=receipt.content_type,
            etag=receipt.etag,
            last_modified=receipt.last_modified,
            manifest_path=receipt.manifest_path,
            provenance_path=receipt.provenance_path,
            manifest=receipt.manifest,
        )
        if receipt.collection_id != expected.collection_id:
            raise AnnouncementCollectionError(
                "announcement collection_id does not match canonical payload"
            )
        receipt._validate()
        return receipt

    def _validate(self) -> None:
        if self.schema_version != ANNOUNCEMENT_COLLECTION_SCHEMA_VERSION:
            raise AnnouncementCollectionError("unsupported announcement schema version")
        if self.collector_name != ANNOUNCEMENT_COLLECTOR_NAME:
            raise AnnouncementCollectionError("unexpected announcement collector name")
        if self.collector_version != ANNOUNCEMENT_COLLECTOR_VERSION:
            raise AnnouncementCollectionError("unexpected announcement collector version")
        validate_official_announcement_url(self.source_url)
        validate_official_announcement_url(self.final_url)
        _require_text(self.title, "title")
        _require_published_date(self.published_date)
        _require_text(self.retrieved_at, "retrieved_at")
        _require_text(self.content_type, "content_type")
        _require_optional_header(self.etag, "ETag")
        _require_optional_header(self.last_modified, "Last-Modified")
        _require_text(self.manifest_path, "manifest_path")
        _require_text(self.provenance_path, "provenance_path")
        if self.manifest.source_type is not SourceType.COMPANY_ANNOUNCEMENT:
            raise AnnouncementCollectionError("manifest is not a company announcement")
        if self.manifest.published_date != self.published_date:
            raise AnnouncementCollectionError("manifest published_date mismatch")
        if self.manifest.retrieved_at != self.retrieved_at:
            raise AnnouncementCollectionError("manifest retrieved_at mismatch")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "collection_id": self.collection_id,
            "collector_name": self.collector_name,
            "collector_version": self.collector_version,
            "source_url": self.source_url,
            "final_url": self.final_url,
            "title": self.title,
            "published_date": self.published_date,
            "retrieved_at": self.retrieved_at,
            "content_type": self.content_type,
            "etag": self.etag,
            "last_modified": self.last_modified,
            "manifest_path": self.manifest_path,
            "provenance_path": self.provenance_path,
            "manifest": self.manifest.to_dict(),
        }

    def canonical_json(self) -> str:
        return _canonical_json(self.to_dict())


def _load_receipt(path: Path) -> AnnouncementCollectionReceipt:
    try:
        with open(_native_link_path(path), "r", encoding="utf-8") as stream:
            data = json.load(stream)
        return AnnouncementCollectionReceipt.from_dict(data)
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise AnnouncementConflictError(
            "existing provenance is not a valid immutable receipt"
        ) from exc


def collect_announcement(
    *,
    root: Path,
    company_name: str,
    entity_ids: Sequence[str],
    source_url: str,
    title: str,
    published_date: str,
    max_bytes: int = DEFAULT_MAX_BYTES,
    fetcher: Callable[[str, int], DownloadedAnnouncement] | None = None,
    now: Callable[[], datetime] | None = None,
) -> AnnouncementCollectionReceipt:
    """Collect, verify and create one immutable announcement source version."""

    root_resolved = _resolve_root(root)
    company = _require_company_name(company_name)
    company_directory = _resolve_company(root_resolved, company)
    validated_url = validate_official_announcement_url(source_url)
    normalized_title = _require_text(title, "title")
    normalized_date = _require_published_date(published_date)
    maximum = _require_max_bytes(max_bytes)
    active_fetcher = fetcher or download_announcement
    response = _validate_download(
        active_fetcher(validated_url, maximum),
        max_bytes=maximum,
    )

    content_sha256 = hashlib.sha256(response.body).hexdigest()
    raw_path = (
        company_directory
        / "raw"
        / "announcements"
        / f"{content_sha256}.pdf"
    )
    clock = now or (lambda: datetime.now(timezone.utc))
    _immutable_create_bytes(
        raw_path,
        response.body,
        root=root_resolved,
        mtime_epoch=_now_epoch(clock),
        label="existing raw",
    )
    retrieved_at = _retrieved_at_from_raw(raw_path)
    manifest = SourceManifest.from_file(
        root=root_resolved,
        file_path=raw_path,
        entity_ids=entity_ids,
        source_type=SourceType.COMPANY_ANNOUNCEMENT,
        published_date=normalized_date,
        retrieved_at=retrieved_at,
        collector_name=ANNOUNCEMENT_COLLECTOR_NAME,
        collector_version=ANNOUNCEMENT_COLLECTOR_VERSION,
        mime_type="application/pdf",
    )

    manifest_path = (
        root_resolved
        / _SOURCE_MANIFEST_ROOT
        / "companies"
        / company
        / f"{content_sha256}.json"
    )
    _immutable_create_json(manifest_path, manifest.to_dict(), root=root_resolved)

    provenance_key = hashlib.sha256(
        (content_sha256 + "\0" + validated_url).encode("utf-8")
    ).hexdigest()
    provenance_path = (
        root_resolved
        / _SOURCE_PROVENANCE_ROOT
        / "companies"
        / company
        / "announcements"
        / f"{provenance_key}.json"
    )
    receipt = AnnouncementCollectionReceipt.create(
        source_url=validated_url,
        final_url=response.final_url,
        title=normalized_title,
        published_date=normalized_date,
        retrieved_at=retrieved_at,
        content_type=response.content_type,
        etag=response.etag,
        last_modified=response.last_modified,
        manifest_path=_canonical_relative(manifest_path, root=root_resolved),
        provenance_path=_canonical_relative(provenance_path, root=root_resolved),
        manifest=manifest,
    )
    receipt._validate()

    if _path_exists(provenance_path):
        stored = _load_receipt(provenance_path)
        if (
            stored.source_url != receipt.source_url
            or stored.title != receipt.title
            or stored.published_date != receipt.published_date
            or stored.manifest.canonical_json() != receipt.manifest.canonical_json()
            or stored.manifest_path != receipt.manifest_path
            or stored.provenance_path != receipt.provenance_path
        ):
            raise AnnouncementConflictError(
                "existing provenance conflicts with collection identity"
            )
        stored.manifest.verify_file(root=root_resolved, file_path=raw_path)
        return stored

    _immutable_create_json(provenance_path, receipt.to_dict(), root=root_resolved)
    return receipt


__all__ = [
    "ANNOUNCEMENT_COLLECTION_ID_PREFIX",
    "ANNOUNCEMENT_COLLECTION_SCHEMA_VERSION",
    "ANNOUNCEMENT_COLLECTOR_NAME",
    "ANNOUNCEMENT_COLLECTOR_VERSION",
    "DEFAULT_MAX_BYTES",
    "OFFICIAL_EXCHANGE_DOMAINS",
    "AnnouncementCollectionError",
    "AnnouncementCollectionReceipt",
    "AnnouncementConflictError",
    "AnnouncementContentError",
    "AnnouncementDownloadError",
    "AnnouncementURLPolicyError",
    "DownloadedAnnouncement",
    "collect_announcement",
    "download_announcement",
    "validate_official_announcement_url",
]
