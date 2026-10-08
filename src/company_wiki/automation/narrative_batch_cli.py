"""Explicit finite narrative batches; stdout contains only a small JSON receipt."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from company_wiki.source_catalog.source_reader import SourceReadError
from company_wiki.source_catalog.narrative_language import NarrativeLanguageError

from .models import canonical_json
from .narrative_batch import BatchPreparationDeadlineExceeded, BatchResumeError, run_batch
from .narrative_batch_request import NarrativeBatchRequest
from .narrative_run_store import NarrativeRunStore


def _failure_receipt(request, db_path, status, error):
    # A refusal can occur after a paid request. Read the actual ledger rather
    # than reporting zero simply because the application returned an error.
    budget: dict[str, int | None] = {"tokens": 0, "estimated_micro_usd": 0, "unknown_reservations": 0, "unsettled_reservations": 0}
    if db_path.exists():
        try:
            runs = NarrativeRunStore(db_path)
            if runs.get_run(request.run_id) is not None:
                actual = runs.budget_snapshot(request.run_id)
                budget = {"tokens": actual.charged_tokens, "estimated_micro_usd": actual.charged_micro_usd,
                          "unknown_reservations": actual.unknown_reservations, "unsettled_reservations": actual.unsettled_reservations}
        except Exception:
            budget = {field: None for field in budget}
    return {"schema_version": "narrative-batch-result/1", "run_id": request.run_id, "status": status, "error": error,
            "documents": [{"document_id": ref.document_id, "status": status, "artifact_ref": None} for ref in request.sources],
            "budget": budget}


def main(
    argv: Sequence[str] | None = None, *, loaded_model_options: dict | None = None,
) -> int:
    parser = argparse.ArgumentParser(description="Process explicit source references without translation")
    for argument in ("project-root", "catalog-config", "automation-db", "work-dir", "request"):
        parser.add_argument("--" + argument, required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        with args.request.open("rb") as stream:
            content = stream.read(262145)
        if len(content) > 262144:
            raise ValueError("request exceeds byte limit")
        raw = json.loads(content.decode("utf-8", errors="strict"))
        if loaded_model_options is not None and isinstance(raw, dict):
            # Composition owns model settings. The finite run hash pins the
            # configured values, not a competing copy in a request file.
            limits = raw.get("model", {})
            limits = {field: limits[field] for field in (
                "timeout_seconds", "max_request_bytes", "max_response_bytes",
            ) if isinstance(limits, dict) and field in limits}
            # Per-operation transport caps remain effective. They are not
            # competing provider/model/generation configuration.
            raw["model"] = {**limits, **loaded_model_options}
        request = NarrativeBatchRequest.from_dict(raw)
    except (OSError, TypeError, ValueError):
        print(canonical_json({"schema_version": "narrative-batch-result/1", "status": "failed",
                              "error": "NARRATIVE_BATCH_INVALID_REQUEST"}))
        return 1
    try:
        receipt = run_batch(request, project_root=args.project_root, catalog_config_path=args.catalog_config,
                            db_path=args.automation_db, work_dir=args.work_dir)
    except BatchPreparationDeadlineExceeded:
        print(canonical_json(_failure_receipt(request, args.automation_db, "failed",
                                              "BATCH_PREPARATION_DEADLINE_EXCEEDED")))
        return 2
    except NarrativeLanguageError as exc:
        print(canonical_json(_failure_receipt(request, args.automation_db, "failed", exc.code)))
        return 2
    except SourceReadError as exc:
        print(canonical_json(_failure_receipt(request, args.automation_db, "failed", exc.reason)))
        return 2
    except BatchResumeError as exc:
        print(canonical_json(_failure_receipt(request, args.automation_db, "failed", exc.code)))
        return 2
    except ValueError as exc:
        status = "storage_exhausted" if str(exc) in {
            "PERSISTENT_BYTES_EXCEEDED", "SCRATCH_BYTES_EXCEEDED", "FINAL_BYTES_EXCEEDED",
        } else "failed"
        print(canonical_json(_failure_receipt(request, args.automation_db, status, "NARRATIVE_BATCH_" + type(exc).__name__)))
        return 2
    except Exception as exc:
        # Provider bodies, paths and credentials never become a CLI error detail.
        print(canonical_json(_failure_receipt(request, args.automation_db, "failed", "NARRATIVE_BATCH_" + type(exc).__name__)))
        return 1
    print(canonical_json(receipt))
    return 0 if receipt["status"] == "completed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
