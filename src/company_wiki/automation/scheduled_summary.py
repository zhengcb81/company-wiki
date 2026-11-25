"""Public summary execution and read-only usage for scheduled reading."""

from __future__ import annotations

import argparse
from decimal import Decimal
import json
from pathlib import Path
import sqlite3
from typing import Any


__all__ = ["ConfiguredReadingSummaries"]


def _build_summary_request(args: argparse.Namespace, max_seconds: int,
                           run_id: str, sources: list[dict[str, Any]]) -> dict:
    """Compose the existing configured batch entry for the summary tier.

    The model settings come from ``--llm-config`` through the project's own
    loader; the batch engine settings (profile, caps, pricing) come from the
    CWP-owned ``--summary-batch-config`` sidecar.  The caller never carries
    model names, prompt text or engine internals across the boundary.  The
    same ``run_id`` resumes the same AUTO batch, so a retried request reads
    its original ledger instead of paying twice.
    """
    from company_wiki.runtime_config import Config
    from .narrative_http_model import model_options_from_config

    batch_config = json.loads(
        args.summary_batch_config.resolve(strict=True).read_text(encoding="utf-8")
    )
    if not isinstance(batch_config, dict):
        raise ValueError("summary batch config must be a JSON object")
    options = model_options_from_config(
        Config.load(args.llm_config, llm_provider=args.llm_provider,
                    validation_scope="llm").llm
    )
    if args.allow_local_model_http:
        options["allow_local_http"] = True
    model_limits = {
        key: value for key, value in (batch_config.get("model") or {}).items()
        if key in {"timeout_seconds", "max_request_bytes", "max_response_bytes"}
    }

    return {
        "schema_version": "narrative-batch-request/1",
        "run_id": run_id,
        "sources": sources,
        "profile": batch_config.get("profile", "P2"),
        "max_seconds": min(batch_config.get("max_seconds", 600), max_seconds),
        "max_tokens": batch_config.get("max_tokens", 200_000),
        "max_cost_usd": batch_config.get("max_cost_usd", "2"),
        "model": {**model_limits, **options},
        "pricing": batch_config["pricing"],
    }


class ConfiguredReadingSummaries:
    """AUTO owns admission, retained attempts and cost reconciliation."""

    def run(self, args, config_path, max_seconds, automation_db, *, run_id, sources,
                                saved_execution, on_admitted):
        from .narrative_batch import run_batch
        from .narrative_batch_request import NarrativeBatchRequest

        if saved_execution is None:
            raw = _build_summary_request(args, max_seconds, run_id, sources)
            work_dir = (args.work_dir or automation_db.parent / "reading-run-work").resolve()
        else:
            raw = saved_execution["request"]
            work_dir = Path(saved_execution["work_dir"])
        batch = NarrativeBatchRequest.from_dict(raw)
        execution = {"request": batch.to_dict(), "work_dir": str(work_dir)}
        automation_db.parent.mkdir(parents=True, exist_ok=True)
        return run_batch(
            batch, project_root=config_path.parents[1], catalog_config_path=config_path,
            db_path=automation_db, work_dir=work_dir,
            on_admitted=lambda: on_admitted(execution),
        )

    def exists(self, database: Path, run_id: str) -> bool:
        from .narrative_run_store import NarrativeRunStore

        return database.exists() and NarrativeRunStore.read_existing_run(database, run_id) is not None

    def usage(self, automation_db: Path, run_id: str) -> dict | None:
        from .migrations import AutomationMigrationError
        from .narrative_run_store import NarrativeRunError, NarrativeRunStore

        if not automation_db.exists():
            return None
        try:
            store = NarrativeRunStore(automation_db)
            if store.get_run(run_id) is None:
                return None
            budget = store.budget_snapshot(run_id)
            reservations = store.reservations_for_run(run_id)
        except (NarrativeRunError, AutomationMigrationError, OSError, ValueError, sqlite3.Error):
            return None
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
