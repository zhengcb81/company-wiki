"""Frozen reading scope and public receipts over the existing AUTO ledger."""

from __future__ import annotations

from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import sqlite3
from tempfile import NamedTemporaryFile

from company_wiki._file_mutex import os_file_mutex
from company_wiki.automation.migrations import AutomationMigrationError
from company_wiki.automation.narrative_run_store import NarrativeRunError, NarrativeRunStore

from .incremental_read import (
    BACKLOG_UNREAD,
    INCREMENTAL_READ_SCHEMA,
    READING_LEVEL_SUMMARY,
    STATE_DEFERRED,
    IncrementalReadError,
    IncrementalReadRequest,
    IncrementalReadService,
    ReadItemResult,
    ReadResultRef,
    STATE_UNCERTAIN,
)


def _read_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None


def _publish_json(path: Path, payload: dict) -> None:
    temp_path = None
    try:
        with NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                prefix=".reading-", delete=False) as stream:
            temp_path = Path(stream.name)
            json.dump(payload, stream, ensure_ascii=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_path, path)
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


def _native_usage(request: IncrementalReadRequest, automation_db: Path, *,
                  summary_started: bool, prior: dict | None = None) -> dict:
    usage = {
        "model_requests": 0, "model_attempts": 0, "tokens": 0,
        "estimated_micro_usd": 0, "cost_usd": "0", "cost_state": "settled",
        "unknown_reservations": 0, "unsettled_reservations": 0,
    }
    if request.reading_level != READING_LEVEL_SUMMARY or not summary_started:
        return usage
    unavailable = {field: (prior or {}).get(field) for field in usage}
    unavailable["cost_state"] = "unknown"
    if not automation_db.exists():
        return unavailable
    try:
        store = NarrativeRunStore(automation_db)
        if store.get_run(request.run_id) is None:
            return unavailable
        budget = store.budget_snapshot(request.run_id)
        reservations = store.reservations_for_run(request.run_id)
    except (NarrativeRunError, AutomationMigrationError, OSError, ValueError, sqlite3.Error):
        return unavailable
    return {
        "model_requests": sum(record.usage_status == "known" and bool(
            record.input_tokens or record.output_tokens or record.response_sha256
        ) for record in reservations),
        "model_attempts": len(reservations),
        "tokens": budget.charged_tokens,
        "estimated_micro_usd": budget.charged_micro_usd,
        "cost_usd": format(Decimal(budget.charged_micro_usd).scaleb(-6), "f"),
        "cost_state": "unknown" if budget.unknown_reservations or budget.unsettled_reservations else "settled",
        "unknown_reservations": budget.unknown_reservations,
        "unsettled_reservations": budget.unsettled_reservations,
    }


class IncrementalRunReceipts:
    """Bind a caller's run to exact refs and expose read-only recovery.

    AUTO remains the only summary execution and budget owner. This receipt
    stores the caller's scope and resulting references, never a new paid job.
    """

    def __init__(self, service: IncrementalReadService, *, directory: Path, automation_db: Path):
        self._service = service
        self._directory = directory
        self._automation_db = automation_db

    def _path(self, run_id: object) -> Path:
        if not isinstance(run_id, str) or not run_id.strip():
            raise IncrementalReadError("a run_id is required")
        return self._directory / (hashlib.sha256(run_id.encode("utf-8")).hexdigest() + ".json")

    def read(self, request: IncrementalReadRequest, *, summary_runner=None,
             new_summary_configured: bool = False) -> dict:
        path = self._path(request.run_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        with os_file_mutex(path.with_suffix(".lock"), timeout_seconds=0.2):
            scope = request.to_dict()
            record = _read_json(path)
            database = str(self._automation_db) if request.reading_level == READING_LEVEL_SUMMARY else None
            if record is None:
                record = {"request": scope, "automation_db": database}
                _publish_json(path, record)
            elif record["request"] != scope or record.get("automation_db") != database:
                raise IncrementalReadError("reading_run_scope_changed")
            execution = record.get("summary_execution")
            prior_usage = (record.get("receipt") or {}).get("usage")

            def admit(plan):
                if "summary_execution" not in record:
                    record["summary_execution"] = plan
                    _publish_json(path, record)

            def generate(**kwargs):
                if execution is not None and not self._native_run_exists(request.run_id):
                    raise IncrementalReadError("reading_summary_ledger_unavailable")
                return summary_runner(**kwargs, saved_execution=execution, on_admitted=admit)

            receipt = self._service.read(
                request, summary_generator=generate if summary_runner is not None
                and (execution is not None or new_summary_configured) else None,
            ).to_dict()
            receipt["usage"].update(_native_usage(
                request, self._automation_db, summary_started="summary_execution" in record,
                prior=prior_usage,
            ))
            _publish_json(path, {**record, "receipt": receipt})
            return receipt

    def _native_run_exists(self, run_id: str) -> bool:
        if not self._automation_db.exists():
            return False
        return NarrativeRunStore.read_existing_run(self._automation_db, run_id) is not None

    def status(self, run_id: object) -> dict:
        record = _read_json(self._path(run_id))
        if record is None:
            raise IncrementalReadError("reading_run_not_found")
        request = IncrementalReadRequest.from_dict(record["request"])
        receipt = record.get("receipt") or {
            "schema_version": INCREMENTAL_READ_SCHEMA,
            "run_id": request.run_id,
            "reading_level": request.reading_level,
            "items": [],
            "usage": {},
        }
        prior = {(item["source_ref"]["document_id"], item["source_ref"]["source_id"]): item
                 for item in receipt["items"]}
        items = []
        for ref in request.sources:
            item = prior.get((ref.document_id, ref.source_id))
            if item and item.get("result_ref") is not None and not self._service.result_available(
                ReadResultRef.from_dict(item["result_ref"]),
            ):
                items.append(ReadItemResult(
                    ref, STATE_UNCERTAIN, None, False, ("reading_artifact_unavailable",),
                ).to_dict())
                continue
            if item is None or item["state"] in ("deferred", "uncertain"):
                recovered = self._service.existing_product(ref, request.reading_level)
                if recovered is not None and recovered.state != BACKLOG_UNREAD:
                    item = recovered.to_dict()
            items.append(item or ReadItemResult(
                ref, STATE_DEFERRED, None, False, ("reading_not_finished",),
            ).to_dict())
        receipt["items"] = items
        native_db = Path(record["automation_db"]) if record.get("automation_db") else self._automation_db
        receipt["usage"].update(_native_usage(request, native_db,
                                              summary_started="summary_execution" in record,
                                              prior=receipt["usage"]))
        return receipt
