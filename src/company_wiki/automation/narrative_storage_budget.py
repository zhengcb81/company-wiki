"""Run-owned filesystem budgeting shared by narrative coordinator and workers."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
import time
from typing import TYPE_CHECKING

from company_wiki.file_usage import file_tree_bytes

from .narrative_run_store import NarrativeRunStore, StorageBudgetExceeded

if TYPE_CHECKING:
    from company_wiki.source_catalog.narrative_artifact_store import (
        NarrativeObjectWrite, NarrativeObjectWritePolicy,
    )


@dataclass(frozen=True)
class StorageSnapshot:
    persistent_added_bytes: int
    scratch_bytes: int
    scratch_peak_bytes: int
    run_file_bytes: int = 0


@dataclass(frozen=True)
class LegacyStorageFootprint:
    """Interpret pre-ledger baseline vectors using each owner's measurements."""

    database_sizes: Callable[[], tuple[int, ...]]
    object_bytes: Callable[[], int]
    work_dir: Path
    control_dir: Path | None

    # Three database counters per owner followed by CAS and run work bytes.
    WORK_INDEX = 7

    @property
    def baseline_size(self) -> int:
        return self.WORK_INDEX + 1 + int(self.control_dir is not None)

    def sizes(self) -> tuple[int, ...]:
        values = (*self.database_sizes(), self.object_bytes(), file_tree_bytes(self.work_dir))
        if self.control_dir is not None:
            values += (file_tree_bytes(self.control_dir),)
        return values


class BatchStorageBudget:
    """Measure only application-owned storage, never a raw document tree."""

    def __init__(self, *, files: tuple[Path, ...], persistent_dirs: tuple[Path, ...],
                 scratch_dirs: tuple[Path, ...], max_persistent_bytes: int, max_scratch_bytes: int,
                 baseline: tuple[int, ...] | None = None,
                 owned_accounting: tuple[Path, str] | None = None,
                 database_sizes: Callable[[], tuple[int, ...]] | None = None,
                 legacy_footprint: LegacyStorageFootprint | None = None):
        self.paths = files + persistent_dirs
        self._legacy_footprint = legacy_footprint
        self._database_sizes = database_sizes
        self.baseline = baseline if baseline is not None else self._persistent_sizes()
        expected = legacy_footprint.baseline_size if legacy_footprint is not None else len(self.paths)
        if len(self.baseline) != expected or any(type(size) is not int or size < 0 for size in self.baseline):
            raise ValueError("BATCH_STORAGE_BASELINE_INVALID")
        self.scratch_dirs = scratch_dirs
        self.max_persistent_bytes = max_persistent_bytes
        self.max_scratch_bytes = max_scratch_bytes
        self.peak = 0
        self.owned_accounting = owned_accounting
        self._last_sample_at = float('-inf')
        self._local_added = 0
        self._scratch = 0
        self._accounting_store: NarrativeRunStore | None = None
        self.shared_database_bytes = 0

    def _persistent_sizes(self) -> tuple[int, ...]:
        if self._legacy_footprint is not None:
            return self._legacy_footprint.sizes()
        return tuple(file_tree_bytes(path) for path in self.paths)

    def adopt_owned_accounting(self, db_path, run_id, work_dir, *, create_floor):
        """Resume old work without rewriting its frozen physical baseline.

        The historical shared delta is conservative and frozen once. All later
        writes use owner accounting, so another writer cannot grow this run.
        """
        if self.owned_accounting is not None:
            return
        accounting = NarrativeRunStore(db_path)
        floor = accounting.legacy_storage_floor(run_id)
        if floor is None and not create_floor:
            return
        legacy = self._legacy_footprint
        index = legacy.WORK_INDEX if legacy is not None else self.paths.index(work_dir)
        work_baseline = self.baseline[index]
        if floor is None:
            local = max(0, file_tree_bytes(work_dir) - work_baseline)
            floor = max(0, self.snapshot().persistent_added_bytes - local)
            accounting.adopt_legacy_storage_floor(run_id, floor)
        if legacy is not None:
            self._database_sizes = legacy.database_sizes
            self._legacy_footprint = None
        self.paths = (work_dir,)
        self.baseline = (work_baseline,)
        self.owned_accounting = (db_path, run_id)
        self._accounting_store = accounting
        self._last_sample_at = float('-inf')

    def accounting_store(self):
        if self.owned_accounting is None:
            return None
        db_path, _run_id = self.owned_accounting
        if self._accounting_store is None and db_path.is_file():
            self._accounting_store = NarrativeRunStore(db_path)
        return self._accounting_store

    def snapshot(self, *, force: bool = True) -> StorageSnapshot:
        now = time.monotonic()
        if force or now - self._last_sample_at >= 5:
            self._local_added = sum(max(0, current - size)
                                    for current, size in zip(self._persistent_sizes(), self.baseline))
            self._scratch = sum(file_tree_bytes(path) for path in self.scratch_dirs)
            if self._database_sizes is not None:
                self.shared_database_bytes = sum(self._database_sizes())
            self._last_sample_at = now
        self.peak = max(self.peak, self._scratch)
        objects = 0
        if self.owned_accounting is not None:
            _, run_id = self.owned_accounting
            accounting = self.accounting_store()
            objects = accounting.storage_bytes(run_id) if accounting is not None else 0
        return StorageSnapshot(self._local_added + objects, self._scratch, self.peak,
                               run_file_bytes=self._local_added)

    def check(self, *, force: bool = True) -> StorageSnapshot:
        result = self.snapshot(force=force)
        if result.persistent_added_bytes > self.max_persistent_bytes:
            raise StorageBudgetExceeded("PERSISTENT_BYTES_EXCEEDED")
        if result.scratch_bytes > self.max_scratch_bytes:
            raise StorageBudgetExceeded("SCRATCH_BYTES_EXCEEDED")
        return result

    def require_response_capacity(self, max_body: int) -> None:
        """Check the configured maximum response once before authorizing a POST."""
        current = self.check()
        if current.persistent_added_bytes + max_body > self.max_persistent_bytes:
            raise StorageBudgetExceeded("PERSISTENT_BYTES_EXCEEDED")
        if current.scratch_bytes + max_body > self.max_scratch_bytes:
            raise StorageBudgetExceeded("SCRATCH_BYTES_EXCEEDED")

    def object_write_policy(self, max_final_bytes: int) -> NarrativeObjectWritePolicy:
        """Apply the run's budget to one logical immutable-object write."""
        def put(store_id: str, size: int, write_object: NarrativeObjectWrite) -> str:
            if size > max_final_bytes:
                raise StorageBudgetExceeded("FINAL_BYTES_EXCEEDED")
            current = self.check()

            def write(admit: Callable[[str, int], None] | None) -> tuple[str, int]:
                def before_create(key: str, create_size: int) -> None:
                    # The owner calls this only when creating a temporary CAS
                    # object. Existing verified bytes need no scratch space.
                    scratch = current.scratch_bytes + create_size
                    if scratch > self.max_scratch_bytes:
                        raise StorageBudgetExceeded("SCRATCH_BYTES_EXCEEDED")
                    if admit is not None:
                        admit(key, create_size)
                    self.peak = max(self.peak, scratch)

                result = write_object(before_create)
                return result.object_key, result.created_bytes

            if self.owned_accounting is None:
                return write(None)[0]
            _, run_id = self.owned_accounting
            accounting = self.accounting_store()
            if accounting is None:
                raise ValueError("BATCH_STORAGE_ACCOUNTING_UNAVAILABLE")

            return accounting.account_storage_write(run_id=run_id, store_id=store_id,
                max_bytes=max(0, self.max_persistent_bytes - current.run_file_bytes),
                write=write)

        return put


__all__ = ["BatchStorageBudget", "LegacyStorageFootprint", "StorageSnapshot"]
