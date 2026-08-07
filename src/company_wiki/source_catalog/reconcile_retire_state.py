"""Reconcile phase-15.6 retire-audit state (catalog-space-remediation Phase 1.2).

Brings ``documents.source_status`` in line with ``document_retire_audit``:
- A: already retired -> skipped.
- B: audit exists but document still active -> soft-retire (retire_document),
  so the audit vs status mismatch becomes zero.
- C: 59-byte placeholder stubs (never downloaded) -> physically delete the
  placeholder file and its rows (instant recycle; spans are ~0 for stubs).

Default is dry-run; ``--apply`` is explicit and writes a receipt (artifact
row + JSONL of affected document_ids), matching the artifacts/gates pattern.

This is a single-threaded governance operation: call it only while the
normalize worker is paused (CatalogOperationLock is held by the caller).
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any

from .lock import CatalogOperationLock
from .models import CatalogConfig
from .store import CatalogStore
from .store import retire_document

STUB_BYTE_SIZE_LIMIT = 200
GOVERNANCE_ACTOR = "reconcile-retire-20260806"


@dataclass(frozen=True)
class RetireReconcileReport:
    dry_run: bool
    already_retired: int = 0
    retire_candidates: int = 0
    stub_physically_deleted: int = 0
    mismatch_remaining: int = 0
    receipt_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d = dict(self.__dict__)
        if self.receipt_path is None:
            d.pop("receipt_path", None)
        return d


class ReconcileRetireStateService:
    """Phase 1.2 governance: align retire-audit with document status."""

    def __init__(self, config: CatalogConfig):
        self.config = config
        self._store: CatalogStore | None = None

    @property
    def store(self) -> CatalogStore:
        if self._store is None:
            self._store = CatalogStore(self.config.database_path)
        return self._store

    def _audit_documents(self) -> list[dict[str, Any]]:
        return self.store.fetchall(
            """SELECT d.document_id, d.source_status, d.primary_source_id,
                      s.byte_size
               FROM document_retire_audit a
               JOIN documents d ON d.document_id = a.document_id
               JOIN sources s ON s.source_id = d.primary_source_id"""
        )

    def reconcile(self, *, apply: bool = False) -> RetireReconcileReport:
        if apply:
            with CatalogOperationLock(
                self.config.catalog_dir, operation="reconcile_retire_state"
            ):
                return self._reconcile_core(apply=True)
        return self._reconcile_core(apply=False)

    def _reconcile_core(self, *, apply: bool) -> RetireReconcileReport:
        rows = self._audit_documents()
        already_retired = 0
        stubs: list[dict[str, Any]] = []
        active_non_stub: list[dict[str, Any]] = []
        for row in rows:
            if row["source_status"] == "retired":
                already_retired += 1
            elif (row["byte_size"] or 0) <= STUB_BYTE_SIZE_LIMIT:
                stubs.append(row)
            else:
                active_non_stub.append(row)

        if not apply:
            return RetireReconcileReport(
                dry_run=True,
                already_retired=already_retired,
                retire_candidates=len(active_non_stub),
                stub_physically_deleted=len(stubs),
                mismatch_remaining=len(active_non_stub) + len(stubs),
            )

        affected: list[str] = []
        now = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
        # 1. Physically delete stub placeholders (file + rows, FK order).
        with self.store.transaction() as conn:
            for stub in stubs:
                self._delete_document_rows(conn, stub["document_id"])
                affected.append(stub["document_id"])
        stub_count = len(stubs)

        # 2. Soft-retire active non-stub audit documents (B class).
        retired_count = 0
        for row in active_non_stub:
            retire_document(
                self.store,
                document_id=row["document_id"],
                reason="phase-15.6 audit reconciliation (reconcile-retire)",
                created_by=GOVERNANCE_ACTOR,
            )
            affected.append(row["document_id"])
            retired_count += 1

        # 3. Receipt: JSONL of affected ids (artifacts/gates file convention;
        #    no artifacts DB row — governance receipts are files, not artifacts).
        receipt_path = (
            self.config.catalog_dir
            / "artifacts"
            / "gates"
            / f"reconcile-retire-{now}.jsonl"
        )
        receipt_path.parent.mkdir(parents=True, exist_ok=True)
        with receipt_path.open("w", encoding="utf-8", newline="\n") as fh:
            fh.write(
                json.dumps(
                    {
                        "actor": GOVERNANCE_ACTOR,
                        "retired": retired_count,
                        "stubs_deleted": stub_count,
                        "affected": len(affected),
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
            for document_id in affected:
                fh.write(
                    json.dumps({"document_id": document_id}, ensure_ascii=False) + "\n"
                )

        mismatch = self._mismatch_count()
        return RetireReconcileReport(
            dry_run=False,
            already_retired=already_retired,
            retire_candidates=retired_count,
            stub_physically_deleted=stub_count,
            mismatch_remaining=mismatch,
            receipt_path=str(receipt_path.resolve()),
        )

    def _mismatch_count(self) -> int:
        row = self.store.fetchone(
            """SELECT COUNT(*) AS n FROM documents d
               JOIN document_retire_audit a ON a.document_id = d.document_id
               WHERE d.source_status != 'retired'"""
        )
        return int(row["n"]) if row else 0

    def _delete_document_rows(self, conn: Any, document_id: str) -> None:
        """Physically delete a stub placeholder document (FK order)."""
        row = conn.execute(
            "SELECT primary_source_id FROM documents WHERE document_id=?",
            (document_id,),
        ).fetchone()
        source_id = row["primary_source_id"] if row else None
        for table, column in (
            ("evidence_spans", "document_id"),
            ("document_fingerprint_state", "document_id"),
            ("artifacts", "document_id"),
            ("document_entities", "document_id"),
            ("llm_summary_failures", "document_id"),
            ("source_metadata_assertions", "document_id"),
            ("document_retire_audit", "document_id"),
            ("document_restore_audit", "document_id"),
        ):
            conn.execute(
                f"DELETE FROM {table} WHERE {column}=?", (document_id,)
            )
        loc = conn.execute(
            "SELECT absolute_path FROM locations WHERE document_id=?",
            (document_id,),
        ).fetchone()
        conn.execute(
            "DELETE FROM locations WHERE document_id=?", (document_id,)
        )
        conn.execute(
            "DELETE FROM documents WHERE document_id=?", (document_id,)
        )
        if source_id is not None:
            conn.execute(
                "DELETE FROM sources WHERE source_id=?", (source_id,)
            )
        # Placeholder file, best-effort.
        if loc is not None and loc["absolute_path"]:
            try:
                os.remove(loc["absolute_path"])
            except OSError:
                pass


__all__ = [
    "GOVERNANCE_ACTOR",
    "ReconcileRetireStateService",
    "RetireReconcileReport",
]
