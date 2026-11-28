"""CWP owner for isolated T3 source acquisition and reuse assurance."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import file_digest, sha256
import json
from os import fstat
from pathlib import Path
import shutil
from typing import Any

from company_wiki.atomic_file import atomic_output
from company_wiki.file_mutex import os_file_mutex

from .acquisition_config import AdapterCommandSpec, load_acquisition_config
from .acquisition_journal import AcquisitionJournal
from .config import load_catalog_config
from .models import COMPANY_RAW_ROOT_KIND
from .security_code import security_codes_equivalent
from .security_identity import SecurityMasterStore
from .service import SourceCatalog
from .source_reader import SourceVersionReader
from .source_request import SourceRequest

CASE_MARKETS = {"cn_annual": "CN", "hk_annual": "HK", "us_annual": "US", "corrupt_original": "CN"}
CASE_PREFIX = "t3-"
_CATALOG_DIR = ".source_catalog"
_CORRUPT_CONTROL = b"invalid original bytes for isolated T3 checksum verification\n"


class WorkspaceError(RuntimeError):
    """A workspace problem reported without local physical file details."""


@dataclass(frozen=True)
class CaseBinding:
    run_id: str
    case_id: str

    @property
    def workspace_id(self) -> str:
        key = json.dumps([self.run_id, self.case_id], ensure_ascii=True).encode()
        return CASE_PREFIX + sha256(key).hexdigest()[:32]

    @property
    def market(self) -> str:
        return CASE_MARKETS[self.case_id]


def _json(path: Path) -> dict[str, Any]:
    if path.resolve() != path:
        raise WorkspaceError("workspace_record_path_mismatch")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise WorkspaceError("invalid_workspace_record")
    return value


def _write_json(path: Path, value: object) -> None:
    with atomic_output(path) as stream:
        stream.write(json.dumps(value, ensure_ascii=True, separators=(",", ":")).encode())


def _safe_case_path(root: Path, workspace_id: str) -> Path:
    candidate = root / workspace_id
    if candidate.resolve() != candidate:
        raise WorkspaceError("workspace_path_mismatch")
    return candidate


def _corrupt_seed(root: Path) -> dict[str, str]:
    candidate = Path("companies/宁德时代/raw/financial_reports/annual/t3-original.pdf")
    source = root / candidate
    source.parent.mkdir(parents=True)
    source.write_bytes(b"%PDF-1.4\nSynthetic Ningde Shidai 2024 annual source for T3 assurance\n%%EOF\n")
    _write_json(source.with_name(source.name + ".source.json"), {
        "market": "CN", "security_id": "300750", "company_name": "宁德时代",
        "source_title": "宁德时代2024年年度报告", "provider": "cninfo",
        "provider_document_id": "t3-synthetic-cn-2024",
        "source_url": "https://www.cninfo.com.cn/t3-fixture-2024.pdf",
        "published_date": "2025-03-14", "filing_date": "2025-03-14",
        "fiscal_year": 2024, "form_type": "FY", "document_kind": "annual_report",
    })
    catalog = SourceCatalog(load_catalog_config(_catalog_path(root)))
    try:
        catalog.scan()
    finally:
        catalog.close()
    source.write_bytes(_CORRUPT_CONTROL)
    return {"relative_path": candidate.as_posix(), "sha256": sha256(_CORRUPT_CONTROL).hexdigest()}


def _catalog_path(root: Path) -> Path:
    return root / "config" / "source_catalog.yaml"


def _adapter(spec: AdapterCommandSpec, catalog_root: Path) -> dict[str, Any]:
    config = asdict(spec)
    config["project_root"] = str(spec.project_root)
    config["config_root"] = str(spec.config_root) if spec.config_root is not None else None
    command = list(spec.command)
    if spec.interface == "dayu_sdk_bounded_v1":
        state = str(catalog_root / "provider-state" / "dayu")
        flag = "--provider-state-root"
        # Argparse accepts both forms; a later duplicate must still use the
        # isolated state destination.
        for index, argument in enumerate(command):
            if argument == flag:
                if index + 1 == len(command):
                    raise WorkspaceError("provider_state_argument_incomplete")
                command[index + 1] = state
            elif argument.startswith(flag + "="):
                command[index] = flag + "=" + state
        if not any(argument == flag or argument.startswith(flag + "=") for argument in command):
            command.extend((flag, state))
    config["command"] = command
    return config


def _no_residue(catalog_root: Path) -> bool:
    return (not (catalog_root / "operation.lock").exists()
            and not any(path.is_file() for path in (catalog_root / "staging").rglob("*")))


def _current_file(path: Path) -> tuple[str, int]:
    with path.open("rb") as file:
        return file_digest(file, "sha256").hexdigest(), fstat(file.fileno()).st_mtime_ns


@dataclass(frozen=True)
class WorkspaceService:
    workspaces: Path
    owner_root: Path
    acquisition_config: Path
    identity_cache: Path

    def open(self, binding: CaseBinding) -> Path:
        root = self.workspaces.resolve()
        root.mkdir(parents=True, exist_ok=True)
        case = _safe_case_path(root, binding.workspace_id)
        with os_file_mutex(root / (binding.workspace_id + ".lock"), timeout_seconds=5.0):
            if (root / (binding.workspace_id + ".closed")).exists():
                raise WorkspaceError("workspace_closed")
            if (case / "binding.json").exists():
                self._check_binding(case, binding)
                return case
            if case.exists():
                raise WorkspaceError("workspace_open_incomplete")
            case.mkdir()
            self._prepare(case, binding)
        return case

    def _prepare(self, case: Path, binding: CaseBinding) -> None:
        catalog_root = case / _CATALOG_DIR
        case.joinpath("config").mkdir()
        case.joinpath("companies").mkdir()
        case.joinpath("runtime").mkdir()
        identity = SecurityMasterStore(self.identity_cache)
        staged_identity = SecurityMasterStore(catalog_root / "security_master")
        snapshot = staged_identity.path_for(binding.market)
        snapshot.parent.mkdir(parents=True)
        shutil.copyfile(identity.path_for(binding.market), snapshot)
        _write_json(_catalog_path(case), {
            "schema_version": "1.0",
            "catalog_dir": str(catalog_root),
            "roots": [{"root_id": "t3-originals", "kind": COMPANY_RAW_ROOT_KIND,
                       "path": str(case / "companies"), "priority": 10}],
        })
        acquisition = load_acquisition_config(self.acquisition_config, project_root=self.owner_root)
        _write_json(case / "config" / "source_acquisition.yaml", {
            "schema_version": acquisition.schema_version,
            "staging_root": str(catalog_root / "staging"),
            "timeout_seconds": acquisition.timeout_seconds,
            "adapters": {market: _adapter(getattr(acquisition, market), catalog_root)
                         for market in ("cn", "hk", "us")},
        })
        record: dict[str, object] = asdict(binding)
        if binding.case_id == "corrupt_original":
            record["corrupt"] = _corrupt_seed(case)
        # Publish readiness last. If a process stops before this commit, the
        # binding still identifies the incomplete directory for explicit close.
        _write_json(case / "binding.json", record)

    @staticmethod
    def _check_binding(case: Path, binding: CaseBinding) -> dict[str, Any]:
        record = _json(case / "binding.json")
        if any(record.get(field) != value for field, value in asdict(binding).items()):
            raise WorkspaceError("workspace_binding_mismatch")
        return record

    def observe(self, binding: CaseBinding, checkpoint: str) -> dict[str, Any]:
        root = self.workspaces.resolve()
        case = _safe_case_path(root, binding.workspace_id)
        record = self._check_binding(case, binding)
        catalog_root = case / _CATALOG_DIR
        rows = AcquisitionJournal(catalog_root).read_all()
        downloads = [row for row in rows if row.outcome == "downloaded_new"]
        facts: dict[str, Any] = {"downloaded_new": len(downloads), "no_residue": _no_residue(catalog_root)}
        if checkpoint == "corrupt":
            target = (case / record["corrupt"]["relative_path"]).resolve(strict=True)
            target.relative_to(case / "companies")
            facts["corrupt_original_unchanged"] = _current_file(target)[0] == record["corrupt"]["sha256"]
        else:
            if len(downloads) != 1:
                raise WorkspaceError("one_download_observation_unavailable")
            downloader = downloads[0]
            if downloader.canonical_path is None:
                raise WorkspaceError("canonical_download_path_unavailable")
            target = Path(downloader.canonical_path).resolve(strict=True)
            target.relative_to(case / "companies")
            digest, mtime = _current_file(target)
            if digest != downloader.content_sha256:
                raise WorkspaceError("downloaded_source_integrity_mismatch")
            meta = _json(target.with_name(target.name + ".source.json"))
            request = SourceRequest(**meta["request"])
            facts.update(source_id=_lookup_source_id(case, request, digest), sha256=digest, mtime_ns=mtime)
            if checkpoint == "first":
                facts["provenance_complete"] = _provenance(meta, request, binding, digest)
            else:
                facts["reused_before_download"] = any(row.outcome == "reused_before_download"
                                                      and row.request_id == downloader.request_id
                                                      and row.content_sha256 in {None, digest} for row in rows)
        return facts

    def close(self, binding: CaseBinding) -> None:
        root = self.workspaces.resolve()
        case = _safe_case_path(root, binding.workspace_id)
        if not root.is_dir():
            return
        with os_file_mutex(root / (binding.workspace_id + ".lock"), timeout_seconds=5.0):
            if (case / "binding.json").exists():
                self._check_binding(case, binding)
            # Seal first so an interrupted cleanup cannot reopen and re-dispatch.
            closed = root / (binding.workspace_id + ".closed")
            if not closed.exists():
                _write_json(closed, asdict(binding))
            if case.exists():
                shutil.rmtree(case)


def _lookup_source_id(case: Path, request: SourceRequest, digest: str) -> str:
    catalog = SourceCatalog(load_catalog_config(_catalog_path(case)))
    try:
        result = SourceVersionReader(catalog).query_local(request)
    finally:
        catalog.close()
    matches = {ref.source_id for ref in result.matches if ref.content_sha256 == digest}
    if len(matches) != 1:
        raise WorkspaceError("canonical_source_identity_unavailable")
    return matches.pop()


def _provenance(meta: dict[str, Any], request: SourceRequest, binding: CaseBinding, digest: str) -> bool:
    market = binding.market
    observed_security_id = meta.get("security_id")
    requested_security_id = request.security_id
    return bool(
        meta.get("market") == request.market == market
        and isinstance(observed_security_id, str)
        and requested_security_id is not None
        and security_codes_equivalent(observed_security_id, requested_security_id,
                                      left_market=market, right_market=market)
        and meta.get("document_kind") == request.document_kind == "annual_report"
        and meta.get("fiscal_year") == request.fiscal_year
        and str(meta.get("source_url") or "").startswith("https://")
        and meta.get("filing_date") and meta.get("content_sha256") == digest
        and meta.get("retrieved_at") and meta.get("adapter_name") and meta.get("adapter_version")
    )
