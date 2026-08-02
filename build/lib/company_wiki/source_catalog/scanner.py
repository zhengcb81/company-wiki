"""Read-only scanners for company raw trees, generic directories, and dayu portfolios."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import json
import mimetypes
import os
from pathlib import Path
import re
import unicodedata
import uuid
from typing import Any, Callable, Iterable

from company_wiki.source_contract import SourceManifest, SourceType

from .models import CatalogConfig, DOCUMENT_EXTENSIONS, SCANNER_VERSION, RootSpec, ScanReport
from .store import CatalogStore, canonical_json


_SKIP_DIRS = frozenset(
    {
        ".git",
        ".hg",
        ".svn",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        "node_modules",
        ".venv",
        "venv",
    }
)
_DATE_RE = re.compile(r"(?<!\d)(20\d{2})[-_.年](0?[1-9]|1[0-2])[-_.月](0?[1-9]|[12]\d|3[01])")
_ACQUISITION_SIDECAR_SUFFIX = ".source.json"


@dataclass(frozen=True)
class _Candidate:
    root: RootSpec
    path: Path
    relative_path: str
    group_key: str
    role: str
    entity_name: str | None
    group_metadata: dict[str, Any]
    source_status: str


@dataclass(frozen=True)
class _ObservedFile:
    candidate: _Candidate
    source_id: str | None
    content_sha256: str | None
    size: int
    mtime_ns: int
    mime_type: str
    manifest_json: str | None
    reused: bool
    error: str | None


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _location_id(root_id: str, relative_path: str) -> str:
    return "urn:company-wiki:location:sha256:" + _sha256_text(root_id + "\0" + relative_path)


def _document_id_for_source(source_id: str) -> str:
    return "urn:company-wiki:document:sha256:" + source_id.rsplit(":", 1)[-1]


def _logical_document_id(root_id: str, group_key: str) -> str:
    return "urn:company-wiki:document-logical:sha256:" + _sha256_text(root_id + "\0" + group_key)


def _mime_type(path: Path) -> str:
    extension = path.suffix.lower()
    overrides = {
        ".md": "text/markdown",
        ".mht": "multipart/related",
        ".xsd": "application/xml",
        ".xml": "application/xml",
        ".json": "application/json",
    }
    if extension in overrides:
        return overrides[extension]
    guessed = mimetypes.guess_type(path.name)[0]
    return (guessed or "application/octet-stream").lower()


def _published_date(text: str) -> str | None:
    match = _DATE_RE.search(text)
    if not match:
        return None
    try:
        return datetime(int(match.group(1)), int(match.group(2)), int(match.group(3))).date().isoformat()
    except ValueError:
        return None


def _classification(path: Path, *, root_kind: str, metadata: dict[str, Any]) -> tuple[str, SourceType]:
    form = str(metadata.get("form_type") or "").casefold()
    text = re.sub(
        r"[_-]+",
        " ",
        path.stem + " " + str(metadata.get("source_title") or "") + " " + form,
    ).casefold()
    if form in {"10-k", "20-f", "40-f"} or any(token in text for token in ("年度报告", "年报", "annual report")):
        return "annual_report", SourceType.REGULATORY_FILING
    if any(token in text for token in ("半年度", "半年报", "interim report")):
        return "semi_annual_report", SourceType.REGULATORY_FILING
    if form in {"10-q", "q1", "q2", "q3", "q4"} or any(
        token in text for token in ("季度报告", "一季报", "三季报", "quarterly report")
    ):
        return "quarterly_report", SourceType.REGULATORY_FILING
    if root_kind == "dayu_portfolio":
        return "regulatory_filing", SourceType.REGULATORY_FILING
    if any(token in text for token in ("投资者关系", "调研", "路演", "业绩说明会", "investor relation")):
        return "investor_relations", SourceType.INVESTOR_RELATIONS
    if any(token in text for token in ("招股", "prospectus")):
        return "prospectus", SourceType.PROSPECTUS
    if root_kind == "directory":
        return "broker_research", SourceType.BROKER_RESEARCH
    if path.suffix.lower() == ".md" and "news" in {part.casefold() for part in path.parts}:
        return "news", SourceType.ORIGINAL_NEWS
    return "other", SourceType.OTHER


def _entity(entity_name: str | None, root_id: str) -> tuple[str, str, str, float, str]:
    if entity_name:
        if re.fullmatch(r"[A-Za-z0-9._-]+", entity_name):
            return f"ticker:{entity_name.upper()}", entity_name, "ticker", 1.0, "path_ticker"
        return f"company-name:{entity_name}", entity_name, "company", 1.0, "company_raw_path"
    return f"unresolved:{root_id}", f"Unresolved ({root_id})", "unresolved", 0.0, "unresolved"


def _walk_files(root: Path) -> Iterable[Path]:
    for current, directories, files in os.walk(root):
        directories[:] = [name for name in directories if name not in _SKIP_DIRS]
        current_path = Path(current)
        for name in files:
            path = current_path / name
            if path.suffix.lower() in DOCUMENT_EXTENSIONS:
                yield path


def _relative(path: Path, root: Path) -> str:
    return unicodedata.normalize("NFC", path.relative_to(root).as_posix())


def _company_names(config: CatalogConfig) -> tuple[str, ...]:
    names: set[str] = set()
    for root in config.roots:
        if root.kind != "company_raw" or not root.path.is_dir():
            continue
        for child in root.path.iterdir():
            if child.is_dir() and (child / "raw").is_dir():
                names.add(unicodedata.normalize("NFC", child.name))
    return tuple(sorted(names, key=lambda value: (-len(value), value.casefold())))


def _infer_company(relative_path: str, names: tuple[str, ...]) -> str | None:
    folded = relative_path.casefold()
    matches = [name for name in names if name.casefold() in folded]
    return matches[0] if len(matches) == 1 else None


def _load_acquisition_metadata(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {"meta_parse_error": True}
    if not isinstance(value, dict):
        return {"meta_parse_error": True}
    return value


def _enumerate_root(root: RootSpec, company_names: tuple[str, ...]) -> tuple[list[_Candidate], int]:
    candidates: list[_Candidate] = []
    excluded = 0
    if root.kind == "company_raw":
        for company in sorted((item for item in root.path.iterdir() if item.is_dir()), key=lambda item: item.name):
            raw = company / "raw"
            if not raw.is_dir():
                continue
            paths = sorted(_walk_files(raw))
            sidecars = {
                str(path)[: -len(_ACQUISITION_SIDECAR_SUFFIX)]: path
                for path in paths
                if path.name.endswith(_ACQUISITION_SIDECAR_SUFFIX)
            }
            primary_paths = [
                path for path in paths if not path.name.endswith(_ACQUISITION_SIDECAR_SUFFIX)
            ]
            for path in primary_paths:
                relative = _relative(path, root.path)
                sidecar = sidecars.get(str(path))
                metadata = _load_acquisition_metadata(sidecar) if sidecar else {}
                candidates.append(
                    _Candidate(
                        root,
                        path,
                        relative,
                        relative,
                        "original_primary",
                        company.name,
                        metadata,
                        "active",
                    )
                )
                if sidecar is not None:
                    candidates.append(
                        _Candidate(
                            root,
                            sidecar,
                            _relative(sidecar, root.path),
                            relative,
                            "metadata",
                            company.name,
                            metadata,
                            "active",
                        )
                    )
            primary_names = {str(path) for path in primary_paths}
            for target, sidecar in sorted(sidecars.items()):
                if target in primary_names:
                    continue
                relative = _relative(sidecar, root.path)
                candidates.append(
                    _Candidate(
                        root,
                        sidecar,
                        relative,
                        relative[: -len(_ACQUISITION_SIDECAR_SUFFIX)],
                        "metadata",
                        company.name,
                        _load_acquisition_metadata(sidecar),
                        "incomplete",
                    )
                )
    elif root.kind == "directory":
        for current, directories, files in os.walk(root.path):
            directories[:] = [name for name in directories if name not in _SKIP_DIRS]
            current_path = Path(current)
            for name in files:
                path = current_path / name
                if path.suffix.lower() not in DOCUMENT_EXTENSIONS:
                    excluded += 1
                    continue
                relative = _relative(path, root.path)
                candidates.append(
                    _Candidate(
                        root,
                        path,
                        relative,
                        relative,
                        "original_primary",
                        _infer_company(relative, company_names),
                        {},
                        "active",
                    )
                )
    else:
        raw_groups: dict[str, list[Path]] = defaultdict(list)
        for path in _walk_files(root.path):
            relative = _relative(path, root.path)
            parts = Path(relative).parts
            if len(parts) >= 3 and parts[1] == "filings":
                if len(parts) >= 4 and parts[2] == ".rejections":
                    group_key = Path(*parts[:4]).as_posix()
                else:
                    group_key = Path(*parts[:3]).as_posix()
            else:
                group_key = relative
            raw_groups[group_key].append(path)
        for group_key, paths in sorted(raw_groups.items()):
            parts = Path(group_key).parts
            ticker = parts[0] if parts else None
            group_dir = root.path.joinpath(*parts) if len(paths) > 1 or Path(group_key).suffix == "" else paths[0].parent
            meta_path = group_dir / "meta.json"
            metadata: dict[str, Any] = {}
            if meta_path.is_file():
                try:
                    loaded = json.loads(meta_path.read_text(encoding="utf-8"))
                    if isinstance(loaded, dict):
                        metadata = loaded
                except (OSError, UnicodeError, json.JSONDecodeError):
                    metadata = {"meta_parse_error": True}
            names = {path.name: path for path in paths}
            selected = str(metadata.get("selected_primary_document") or "")
            primary = str(metadata.get("primary_document") or "")
            preferred: Path | None = None
            for name in (selected, primary):
                if name and name in names and not name.endswith("_docling.json"):
                    preferred = names[name]
                    break
            if preferred is None:
                preferred = next((path for path in paths if path.suffix.lower() == ".pdf"), None)
            if preferred is None:
                preferred = next(
                    (path for path in paths if path.suffix.lower() in {".htm", ".html"} and path.name != "meta.json"),
                    None,
                )
            if preferred is None:
                preferred = next(
                    (path for path in paths if path.name != "meta.json" and not path.name.endswith("_docling.json")),
                    None,
                )
            rejected = ".rejections" in parts
            complete = metadata.get("ingest_complete") is True
            if rejected:
                source_status = "upstream_rejected"
            elif preferred is None:
                source_status = "incomplete"
            else:
                source_status = "active" if complete or len(paths) == 1 else "incomplete"
            for path in sorted(paths):
                if path.name == "meta.json" or path.name.endswith("manifest.json"):
                    role = "metadata"
                elif path.name.endswith("_docling.json"):
                    role = "processed_docling"
                elif preferred is not None and path == preferred:
                    role = "original_primary"
                else:
                    role = "original_attachment"
                candidates.append(
                    _Candidate(
                        root,
                        path,
                        _relative(path, root.path),
                        group_key,
                        role,
                        ticker,
                        metadata,
                        source_status,
                    )
                )
    return candidates, excluded


def _observe_file(
    candidate: _Candidate,
    *,
    existing: Any,
    scan_time: str,
    document_kind: str,
    source_type: SourceType,
    entity_id: str,
) -> _ObservedFile:
    stat = candidate.path.stat()
    if (
        existing is not None
        and existing["source_id"]
        and existing["manifest_json"]
        and existing["observed_size"] == stat.st_size
        and existing["observed_mtime_ns"] == stat.st_mtime_ns
    ):
        manifest = SourceManifest.from_dict(json.loads(existing["manifest_json"]))
        return _ObservedFile(
            candidate,
            manifest.source_id,
            manifest.content_sha256,
            stat.st_size,
            stat.st_mtime_ns,
            manifest.mime_type,
            manifest.canonical_json(),
            True,
            None,
        )
    mime_type = _mime_type(candidate.path)
    try:
        collector_name = f"filesystem-catalog-{candidate.root.root_id}"
        collector_version = SCANNER_VERSION
        retrieved_at = scan_time
        if candidate.role == "original_primary" and candidate.group_metadata:
            collector_name = str(
                candidate.group_metadata.get("adapter_name") or collector_name
            )
            collector_version = str(
                candidate.group_metadata.get("adapter_version") or collector_version
            )
            retrieved_at = str(
                candidate.group_metadata.get("retrieved_at") or retrieved_at
            )
        manifest = SourceManifest.from_file(
            root=candidate.root.path,
            file_path=candidate.path,
            entity_ids=(entity_id,),
            source_type=source_type if candidate.role == "original_primary" else SourceType.OTHER,
            published_date=(
                str(candidate.group_metadata.get("filing_date"))
                if candidate.group_metadata.get("filing_date")
                else _published_date(candidate.path.name)
            ),
            retrieved_at=retrieved_at,
            collector_name=collector_name,
            collector_version=collector_version,
            mime_type=mime_type,
        )
        expected_sha256 = candidate.group_metadata.get("content_sha256")
        if (
            candidate.role == "original_primary"
            and expected_sha256
            and manifest.content_sha256 != expected_sha256
        ):
            raise ValueError("acquisition sidecar SHA-256 does not match source bytes")
    except Exception as exc:
        return _ObservedFile(
            candidate,
            None,
            None,
            stat.st_size,
            stat.st_mtime_ns,
            mime_type,
            None,
            False,
            f"{type(exc).__name__}: {exc}",
        )
    return _ObservedFile(
        candidate,
        manifest.source_id,
        manifest.content_sha256,
        stat.st_size,
        stat.st_mtime_ns,
        manifest.mime_type,
        manifest.canonical_json(),
        False,
        None,
    )


def _scan_catalog_impl(
    config: CatalogConfig,
    store: CatalogStore | None,
    *,
    dry_run: bool = False,
    root_ids: set[str] | None = None,
    progress: Callable[..., None] | None = None,
) -> ScanReport:
    run_id = "scan-" + uuid.uuid4().hex
    scan_time = _utc_now()
    names = _company_names(config)
    files_seen = files_hashed = files_reused = files_excluded = errors = 0
    selected_roots = tuple(
        root for root in config.roots if root_ids is None or root.root_id in root_ids
    )
    if not selected_roots:
        raise ValueError("no configured roots matched root_ids")
    if root_ids is not None:
        unknown = root_ids - {root.root_id for root in config.roots}
        if unknown:
            raise ValueError(f"unknown root_ids: {sorted(unknown)}")
    if not dry_run:
        if store is None:
            raise TypeError("store is required for a non-dry-run scan")
        with store.transaction() as connection:
            connection.execute(
                "UPDATE scan_runs SET completed_at=?,status='interrupted' WHERE status='running'",
                (scan_time,),
            )
            connection.execute(
                "INSERT INTO scan_runs(run_id,started_at,status) VALUES(?,?,?)",
                (run_id, scan_time, "running"),
            )

    for root in selected_roots:
        if not root.path.is_dir():
            errors += 1
            continue
        candidates, excluded = _enumerate_root(root, names)
        files_seen += len(candidates)
        files_excluded += excluded
        if dry_run:
            continue
        with store.transaction() as connection:
            connection.execute(
                """INSERT INTO roots(root_id,path,kind,priority,last_scan_run,last_scanned_at)
                VALUES(?,?,?,?,?,?) ON CONFLICT(root_id) DO UPDATE SET
                path=excluded.path,kind=excluded.kind,priority=excluded.priority,
                last_scan_run=excluded.last_scan_run,last_scanned_at=excluded.last_scanned_at""",
                (root.root_id, str(root.path.resolve()), root.kind, root.priority, run_id, scan_time),
            )
        groups: dict[str, list[_Candidate]] = defaultdict(list)
        for candidate in candidates:
            groups[candidate.group_key].append(candidate)
        existing_locations = {
            row["relative_path"]: row
            for row in store.fetchall(
                """SELECT relative_path,source_id,observed_size,observed_mtime_ns,manifest_json
                FROM locations WHERE root_id=?""",
                (root.root_id,),
            )
        }
        group_items = sorted(groups.items())
        for group_index, (group_key, group) in enumerate(group_items, start=1):
            primary_candidate = next((item for item in group if item.role == "original_primary"), None)
            classification_path = primary_candidate.path if primary_candidate else group[0].path
            if progress is not None:
                progress(
                    current_path=str(classification_path.resolve(strict=False)),
                    current=group_index,
                    total=len(group_items),
                    detail=f"scanning root {root.root_id}",
                )
            metadata = primary_candidate.group_metadata if primary_candidate else group[0].group_metadata
            document_kind, source_type = _classification(
                classification_path, root_kind=root.kind, metadata=metadata
            )
            entity_name = (primary_candidate or group[0]).entity_name
            entity_id, entity_label, entity_kind, confidence, method = _entity(entity_name, root.root_id)
            observed: list[_ObservedFile] = []
            for candidate in group:
                try:
                    item = _observe_file(
                        candidate,
                        existing=existing_locations.get(candidate.relative_path),
                        scan_time=scan_time,
                        document_kind=document_kind,
                        source_type=source_type,
                        entity_id=entity_id,
                    )
                except OSError:
                    errors += 1
                    continue
                observed.append(item)
                if item.reused:
                    files_reused += 1
                elif item.source_id:
                    files_hashed += 1
                if item.error:
                    errors += 1
            primary = next((item for item in observed if item.candidate.role == "original_primary" and item.source_id), None)
            document_id = (
                _document_id_for_source(primary.source_id)
                if primary and primary.source_id
                else _logical_document_id(root.root_id, group_key)
            )
            title = str(metadata.get("source_title") or "").strip() or classification_path.stem
            published = (
                str(metadata.get("filing_date"))
                if metadata.get("filing_date")
                else _published_date(classification_path.name)
            )
            source_status = (primary_candidate or group[0]).source_status
            if primary is None:
                source_status = (
                    "quarantined" if any(item.error for item in observed) else "incomplete"
                )
            document_metadata = {
                "root_id": root.root_id,
                "group_key": group_key,
                "scanner_version": SCANNER_VERSION,
                "dayu_meta": metadata if root.kind == "dayu_portfolio" else None,
                "acquisition": metadata if root.kind == "company_raw" and metadata else None,
            }
            with store.transaction() as connection:
                for item in observed:
                    if item.source_id:
                        connection.execute(
                            "INSERT OR IGNORE INTO sources(source_id,content_sha256,byte_size,mime_type,first_seen_at) VALUES(?,?,?,?,?)",
                            (item.source_id, item.content_sha256, item.size, item.mime_type, scan_time),
                        )
                existing_document = connection.execute(
                    "SELECT metadata_priority FROM documents WHERE document_id=?", (document_id,)
                ).fetchone()
                if existing_document is None:
                    connection.execute(
                        """INSERT INTO documents(document_id,primary_source_id,title,source_type,document_kind,
                        published_date,source_status,metadata_priority,metadata_json,first_seen_at,last_seen_at)
                        VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                        (
                            document_id,
                            primary.source_id if primary else None,
                            title,
                            source_type.value,
                            document_kind,
                            published,
                            source_status,
                            root.priority,
                            canonical_json(document_metadata),
                            scan_time,
                            scan_time,
                        ),
                    )
                elif root.priority <= existing_document["metadata_priority"]:
                    connection.execute(
                        """UPDATE documents SET primary_source_id=COALESCE(?,primary_source_id),title=?,source_type=?,
                        document_kind=?,published_date=COALESCE(?,published_date),source_status=?,metadata_priority=?,
                        metadata_json=?,last_seen_at=? WHERE document_id=?""",
                        (
                            primary.source_id if primary else None,
                            title,
                            source_type.value,
                            document_kind,
                            published,
                            source_status,
                            root.priority,
                            canonical_json(document_metadata),
                            scan_time,
                            document_id,
                        ),
                    )
                else:
                    connection.execute(
                        "UPDATE documents SET last_seen_at=? WHERE document_id=?",
                        (scan_time, document_id),
                    )
                connection.execute(
                    "INSERT OR IGNORE INTO entities(entity_id,name,entity_kind) VALUES(?,?,?)",
                    (entity_id, entity_label, entity_kind),
                )
                connection.execute(
                    """INSERT INTO document_entities(document_id,entity_id,confidence,method) VALUES(?,?,?,?)
                    ON CONFLICT(document_id,entity_id) DO UPDATE SET confidence=MAX(confidence,excluded.confidence),method=excluded.method""",
                    (document_id, entity_id, confidence, method),
                )
                for item in observed:
                    candidate = item.candidate
                    connection.execute(
                        """INSERT INTO locations(location_id,root_id,relative_path,absolute_path,source_id,document_id,
                        role,location_status,observed_size,observed_mtime_ns,last_seen_run,manifest_json,metadata_json,error)
                        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(root_id,relative_path) DO UPDATE SET
                        absolute_path=excluded.absolute_path,source_id=excluded.source_id,document_id=excluded.document_id,
                        role=excluded.role,location_status=excluded.location_status,observed_size=excluded.observed_size,
                        observed_mtime_ns=excluded.observed_mtime_ns,last_seen_run=excluded.last_seen_run,
                        manifest_json=excluded.manifest_json,metadata_json=excluded.metadata_json,error=excluded.error""",
                        (
                            _location_id(root.root_id, candidate.relative_path),
                            root.root_id,
                            candidate.relative_path,
                            str(candidate.path.resolve()),
                            item.source_id,
                            document_id,
                            candidate.role,
                            "active" if item.source_id else "quarantined",
                            item.size,
                            item.mtime_ns,
                            run_id,
                            item.manifest_json,
                            canonical_json({"group_key": group_key, "source_status": source_status}),
                            item.error,
                        ),
                    )
        with store.transaction() as connection:
            connection.execute(
                "UPDATE locations SET location_status='missing' WHERE root_id=? AND last_seen_run<>? AND location_status<>'missing'",
                (root.root_id, run_id),
            )

    if dry_run:
        return ScanReport(
            run_id=run_id,
            files_seen=files_seen,
            files_excluded=files_excluded,
            dry_run=True,
            errors=errors,
        )
    active = store.fetchone("SELECT COUNT(*) AS count FROM locations WHERE location_status='active'")["count"]
    missing = store.fetchone("SELECT COUNT(*) AS count FROM locations WHERE location_status='missing'")["count"]
    report = ScanReport(
        run_id=run_id,
        files_seen=files_seen,
        files_hashed=files_hashed,
        files_reused=files_reused,
        files_excluded=files_excluded,
        locations_active=int(active),
        locations_missing=int(missing),
        errors=errors,
    )
    with store.transaction() as connection:
        completed_at = _utc_now()
        connection.execute(
            "UPDATE scan_runs SET completed_at=?,status=?,report_json=? WHERE run_id=?",
            (completed_at, "completed_with_errors" if errors else "completed", canonical_json(report.to_dict()), run_id),
        )
    return report


def scan_catalog(
    config: CatalogConfig,
    store: CatalogStore | None,
    *,
    dry_run: bool = False,
    root_ids: set[str] | None = None,
    progress: Callable[..., None] | None = None,
) -> ScanReport:
    if dry_run:
        return _scan_catalog_impl(
            config,
            store,
            dry_run=True,
            root_ids=root_ids,
            progress=progress,
        )
    if store is None:
        raise TypeError("store is required for a non-dry-run scan")
    with store.coalesced_transactions(max_operations=250):
        return _scan_catalog_impl(
            config,
            store,
            dry_run=False,
            root_ids=root_ids,
            progress=progress,
        )


__all__ = ["scan_catalog"]
