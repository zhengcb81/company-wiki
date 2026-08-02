"""Value objects shared by the source catalog pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


CATALOG_SCHEMA_VERSION = "1.0.0"
SCANNER_VERSION = "1.0.0"
NORMALIZER_VERSION = "1.0.0"
SUMMARIZER_VERSION = "1.0.0"

ROOT_KINDS = frozenset({"company_raw", "directory", "dayu_portfolio"})
DOCUMENT_EXTENSIONS = frozenset(
    {
        ".pdf",
        ".md",
        ".txt",
        ".html",
        ".htm",
        ".mht",
        ".doc",
        ".docx",
        ".xls",
        ".xlsx",
        ".ppt",
        ".pptx",
        ".xml",
        ".xsd",
        ".json",
        ".csv",
        ".jpg",
        ".jpeg",
        ".png",
    }
)


@dataclass(frozen=True)
class RootSpec:
    root_id: str
    path: Path
    kind: str
    priority: int = 100

    def __post_init__(self) -> None:
        if not isinstance(self.root_id, str) or not self.root_id.strip():
            raise ValueError("root_id must be non-empty text")
        if self.root_id != self.root_id.strip():
            raise ValueError("root_id must be trimmed")
        if not isinstance(self.path, Path):
            raise TypeError("path must be pathlib.Path")
        if self.kind not in ROOT_KINDS:
            raise ValueError(f"unsupported root kind: {self.kind}")
        if isinstance(self.priority, bool) or not isinstance(self.priority, int):
            raise TypeError("priority must be an integer")


@dataclass(frozen=True)
class CatalogConfig:
    project_root: Path
    catalog_dir: Path
    roots: tuple[RootSpec, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.project_root, Path) or not isinstance(self.catalog_dir, Path):
            raise TypeError("project_root and catalog_dir must be pathlib.Path")
        if not isinstance(self.roots, tuple) or not self.roots:
            raise ValueError("roots must be a non-empty tuple")
        if not all(isinstance(item, RootSpec) for item in self.roots):
            raise TypeError("roots must contain RootSpec values")
        root_ids = [item.root_id for item in self.roots]
        if len(root_ids) != len(set(root_ids)):
            raise ValueError("root_id values must be unique")

    @property
    def database_path(self) -> Path:
        return self.catalog_dir / "catalog.sqlite3"

    @property
    def derived_dir(self) -> Path:
        return self.catalog_dir / "derived"

    @property
    def export_dir(self) -> Path:
        return self.catalog_dir / "index"


@dataclass(frozen=True)
class ScanReport:
    run_id: str
    files_seen: int = 0
    files_hashed: int = 0
    files_reused: int = 0
    files_excluded: int = 0
    locations_active: int = 0
    locations_missing: int = 0
    errors: int = 0
    dry_run: bool = False

    def to_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


@dataclass(frozen=True)
class ProcessingReport:
    operation: str
    completed: int = 0
    skipped: int = 0
    partial: int = 0
    unsupported: int = 0
    failed: int = 0

    def to_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


__all__ = [
    "CATALOG_SCHEMA_VERSION",
    "CatalogConfig",
    "DOCUMENT_EXTENSIONS",
    "NORMALIZER_VERSION",
    "ProcessingReport",
    "ROOT_KINDS",
    "RootSpec",
    "SCANNER_VERSION",
    "SUMMARIZER_VERSION",
    "ScanReport",
]
