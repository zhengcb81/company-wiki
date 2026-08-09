"""Value objects shared by the source catalog pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any


CATALOG_SCHEMA_VERSION = "1.2.0"
SCANNER_VERSION = "1.0.0"
NORMALIZER_VERSION = "1.0.0"
SUMMARIZER_VERSION = "1.0.0"
SECTION_EXTRACTOR_VERSION = "1.0.0"


class FingerprintStatus(str, Enum):
    """Persistent per-document fingerprint state (CW-2.28 §12.3).

    The string values are stored in ``document_fingerprint_state.status`` and
    are part of the on-disk contract; do not rename them.
    """

    PENDING = "pending"
    COMPLETED = "completed"
    UNSUPPORTED_TERMINAL = "unsupported_terminal"
    RETRYABLE_FAILED = "retryable_failed"
    FAILED_TERMINAL = "failed_terminal"


# Statuses that are terminal: the scheduler must never re-select them
# automatically. Only reconciliation (source SHA / normalizer version / location
# change) may reset them to PENDING.
FINGERPRINT_TERMINAL_STATUSES = frozenset(
    {FingerprintStatus.UNSUPPORTED_TERMINAL.value, FingerprintStatus.FAILED_TERMINAL.value}
)

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
class RouteSpec:
    """WU-301: an ordered include/exclude glob route on a root.

    First-match semantics; overlapping routes are rejected at load time.
    """

    include: tuple[str, ...] = ()
    exclude: tuple[str, ...] = ()
    adapter_id: str | None = None
    admission_profile_id: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.include, tuple) or not isinstance(self.exclude, tuple):
            raise TypeError("include/exclude must be tuples of glob strings")
        if self.include and not all(
            isinstance(item, str) and item.strip() for item in self.include
        ):
            raise ValueError("include must be non-empty glob strings")


@dataclass(frozen=True)
class RootSpec:
    root_id: str
    path: Path
    kind: str
    priority: int = 100
    # WU-301 RootPolicy v2 (additive; defaults preserve v1 behavior)
    adapter_id: str | None = None
    adapter_version_range: str | None = None
    admission_profile_id: str | None = None
    read_only: bool = True
    reusable_for_filing: bool | None = None  # None = follow kind policy
    routes: tuple[RouteSpec, ...] = ()
    allowed_document_kinds: tuple[str, ...] = ()
    allowed_statuses: tuple[str, ...] = ()
    symlink_policy: str = "reject"
    max_file_size: int | None = None
    sidecar_suffixes: tuple[str, ...] = ()
    encoding: str = "utf-8"
    privacy_class: str = "public"

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
        if self.adapter_id is not None and not isinstance(self.adapter_id, str):
            raise TypeError("adapter_id must be a string or None")
        if self.read_only not in (True, False):
            raise TypeError("read_only must be a boolean")
        if self.routes and not all(
            isinstance(route, RouteSpec) for route in self.routes
        ):
            raise TypeError("routes must contain RouteSpec objects")


@dataclass(frozen=True)
class CatalogConfig:
    project_root: Path
    catalog_dir: Path
    roots: tuple[RootSpec, ...]
    # Root *kinds* whose indexed documents are canonical reuse candidates for
    # the resolve pipeline (ADR-008). Config-driven: adding a kind here makes
    # every already-indexed document under such roots directly reusable by
    # filing-fetch (no download), provided its location carries capture fields.
    # Default: company_raw only (legacy behavior).
    reusable_root_kinds: tuple[str, ...] = ("company_raw",)

    def __post_init__(self) -> None:
        if not isinstance(self.project_root, Path) or not isinstance(
            self.catalog_dir, Path
        ):
            raise TypeError("project_root and catalog_dir must be pathlib.Path")
        if not isinstance(self.roots, tuple) or not self.roots:
            raise ValueError("roots must be a non-empty tuple")
        if not all(isinstance(item, RootSpec) for item in self.roots):
            raise TypeError("roots must contain RootSpec values")
        root_ids = [item.root_id for item in self.roots]
        if len(root_ids) != len(set(root_ids)):
            raise ValueError("root_id values must be unique")
        if (
            not isinstance(self.reusable_root_kinds, tuple)
            or not self.reusable_root_kinds
            or not all(isinstance(kind, str) and kind.strip() for kind in self.reusable_root_kinds)
        ):
            raise ValueError("reusable_root_kinds must be a non-empty tuple of non-empty strings")

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
    policy_excluded: int = 0
    locations_active: int = 0
    locations_missing: int = 0
    errors: int = 0
    new_errors: int = 0
    known_quarantined: int = 0
    error_details: tuple[dict[str, Any], ...] = ()
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
    eligible: int = 0
    terminal_reasons: dict[str, int] | None = None
    due_retry: int = 0
    terminal: int = 0
    last_failure_code: str | None = None
    last_failed_document_id: str | None = None
    last_failed_path: str | None = None

    @property
    def pending(self) -> int:
        # ``eligible`` is the global backlog (pending + due-retry) read from the
        # persistent state table before the batch; ``completed``/``unsupported``/
        # ``failed`` are this batch's increments. The subtraction therefore
        # yields the remaining global backlog, not a tautology.
        return max(0, self.eligible - self.completed - self.unsupported - self.failed)

    def to_dict(self) -> dict[str, Any]:
        d = dict(self.__dict__)
        if self.terminal_reasons is None:
            d.pop("terminal_reasons", None)
        for optional_name in (
            "last_failure_code",
            "last_failed_document_id",
            "last_failed_path",
        ):
            if d[optional_name] is None:
                d.pop(optional_name)
        d["pending"] = self.pending
        return d


@dataclass(frozen=True)
class FingerprintState:
    """One row of ``document_fingerprint_state`` (CW-2.28 §12.3)."""

    document_id: str
    source_id: str
    source_sha256: str
    status: str
    attempt_count: int = 0
    terminal_reason: str | None = None
    last_error_code: str | None = None
    last_error_message_redacted: str | None = None
    normalizer_version: str = NORMALIZER_VERSION
    last_attempt_at: str | None = None
    next_retry_at: str | None = None
    updated_at: str = ""


__all__ = [
    "CATALOG_SCHEMA_VERSION",
    "CatalogConfig",
    "DOCUMENT_EXTENSIONS",
    "FINGERPRINT_TERMINAL_STATUSES",
    "FingerprintState",
    "FingerprintStatus",
    "NORMALIZER_VERSION",
    "ProcessingReport",
    "ROOT_KINDS",
    "RootSpec",
    "SCANNER_VERSION",
    "SECTION_EXTRACTOR_VERSION",
    "SUMMARIZER_VERSION",
    "ScanReport",
]
