"""Public CLI for bounded incremental discovery and reading (scheduled refresh).

Both commands take one JSON request on stdin and write one JSON response on
stdout.  They reuse the generic catalog configuration and the existing
acquisition adapters; discovery never downloads an original, and the local
reading tier never calls a model.  The ``summary`` reading tier composes the
existing configured batch entry when its sidecar configuration is supplied.

Invoked through ``source_catalog.cli`` as ``discover-incremental`` /
``read-incremental``, or directly as ``python -m
company_wiki.source_catalog.incremental_cli``.
"""

from __future__ import annotations

import argparse
from dataclasses import replace
import json
from pathlib import Path
import sqlite3
import sys
from typing import Any, Sequence

from company_wiki.source_contract.source_version import SourceReadError

from .acquisition import AcquisitionCoordinator
from .acquisition_config import load_acquisition_config
from .config import load_catalog_config
from .download_budget import AcquisitionBudget
from .incremental_discovery import (
    IncrementalDiscoveryError,
    IncrementalDiscoveryRequest,
    IncrementalDiscoveryService,
)
from .incremental_read import (
    BACKLOG_UNREAD,
    INCREMENTAL_READ_REQUEST_SCHEMA,
    IncrementalReadError,
    IncrementalReadRequest,
    IncrementalReadService,
    READING_LEVEL_SUMMARY,
    ReadingBacklogRequest,
    ReadResultRef,
)
from .incremental_run_receipt import IncrementalRunReceipts
from .service import SourceCatalog


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="company-wiki-incremental",
        description="Bounded metadata discovery and bounded reading over exact sources",
    )
    parser.add_argument(
        "--config", type=Path, default=Path("config/source_catalog.yaml"),
        help="versioned source-catalog YAML configuration",
    )
    parser.add_argument("--request-stdin", action="store_true",
                        help="read the JSON request from standard input (the default)")
    parser.add_argument(
        "--acquisition-config", type=Path,
        default=Path("config/source_acquisition.yaml"),
        help="acquisition adapter configuration (discovery only)",
    )
    parser.add_argument(
        "--llm-config", type=Path,
        help="LLM provider configuration; enables the summary reading tier",
    )
    parser.add_argument("--llm-provider", choices=("minimax", "mimo", "deepseek", "openai"))
    parser.add_argument("--allow-local-model-http", action="store_true")
    parser.add_argument(
        "--summary-batch-config", type=Path,
        help=(
            "JSON sidecar with the batch engine settings the summary tier "
            "uses (profile, caps, pricing, model request fields); CWP-owned "
            "configuration, never carried by the caller"
        ),
    )
    parser.add_argument(
        "--automation-db", type=Path,
        help="automation database for the composed summary batch",
    )
    parser.add_argument(
        "--work-dir", type=Path,
        help="run-owned work directory for the composed summary batch",
    )
    return parser


def _read_request() -> dict:
    content = sys.stdin.buffer.read()
    if not content:
        raise ValueError("request body is empty")
    request = json.loads(content.decode("utf-8", errors="strict"))
    if not isinstance(request, dict):
        raise ValueError("request must be a JSON object")
    return request


def _project_root(config_path: Path) -> Path:
    return config_path.parents[1]


def _run_discovery(args: argparse.Namespace, request: dict) -> dict:
    config_path = args.config.resolve(strict=True)
    project_root = _project_root(config_path)
    config = load_catalog_config(config_path, project_root=project_root)
    acquisition_path = args.acquisition_config
    if not acquisition_path.is_absolute():
        acquisition_path = project_root / acquisition_path
    acquisition = load_acquisition_config(
        acquisition_path.resolve(strict=True), project_root=project_root
    )
    catalog = SourceCatalog(config)
    try:
        coordinator = AcquisitionCoordinator(
            catalog=catalog, adapters=acquisition.build_registry(),
            staging_root=acquisition.staging_root,
        )
        service = IncrementalDiscoveryService(catalog=catalog, coordinator=coordinator)
        parsed = IncrementalDiscoveryRequest.from_dict(request)
        budget = AcquisitionBudget.from_limits(
            max_response_bytes=parsed.limits.max_bytes, max_seconds=parsed.limits.max_seconds,
            max_cost_usd=parsed.limits.max_cost_usd,
        )
        response = service.discover(parsed, budget=budget)
        return response.to_dict()
    finally:
        catalog.close()


def _build_summary_request(args: argparse.Namespace, parsed: IncrementalReadRequest,
                           run_id: str, sources: list[dict[str, Any]]) -> dict:
    """Compose the existing configured batch entry for the summary tier.

    The model settings come from ``--llm-config`` through the project's own
    loader; the batch engine settings (profile, caps, pricing) come from the
    CWP-owned ``--summary-batch-config`` sidecar.  The caller never carries
    model names, prompt text or engine internals across the boundary.  The
    same ``run_id`` resumes the same AUTO batch, so a retried request reads
    its original ledger instead of paying twice.
    """
    from company_wiki.automation.narrative_http_model import model_options_from_config
    import company_wiki as _package

    # The project's config loader lives in the repository's scripts/ directory
    # and is imported top-level there (scripts/narrative_batch_configured.py
    # does ``from config import Config``), so composition adds the directory.
    scripts_dir = Path(_package.__file__).resolve().parents[2] / "scripts"
    if scripts_dir.is_dir() and str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    from config import Config

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
        "max_seconds": min(batch_config.get("max_seconds", 600), parsed.limits.max_seconds),
        "max_tokens": batch_config.get("max_tokens", 200_000),
        "max_cost_usd": batch_config.get("max_cost_usd", "2"),
        "model": {**model_limits, **options},
        "pricing": batch_config["pricing"],
    }


def _run_configured_summary(args, config_path, parsed, automation_db, *, run_id, sources,
                            saved_execution, on_admitted):
    from company_wiki.automation.narrative_batch import run_batch
    from company_wiki.automation.narrative_batch_request import NarrativeBatchRequest

    if saved_execution is None:
        raw = _build_summary_request(args, parsed, run_id, sources)
        work_dir = (args.work_dir or automation_db.parent / "reading-run-work").resolve()
    else:
        raw = saved_execution["request"]
        work_dir = Path(saved_execution["work_dir"])
    batch = NarrativeBatchRequest.from_dict(raw)
    execution = {"request": batch.to_dict(), "work_dir": str(work_dir)}
    automation_db.parent.mkdir(parents=True, exist_ok=True)
    return run_batch(
        batch, project_root=_project_root(config_path), catalog_config_path=config_path,
        db_path=automation_db, work_dir=work_dir,
        on_admitted=lambda: on_admitted(execution),
    )


def _scheduled_backlog(catalog: SourceCatalog, service: IncrementalReadService,
                       request: dict) -> dict:
    from .incremental_discovery import DiscoveryIdentity, bind_discovery_identity

    identity = DiscoveryIdentity.from_dict(request.get("identity"))
    market = request["identity"]["market"]
    bound = bind_discovery_identity(catalog, identity, market)
    limits = request.get("limits") or {}
    kinds = request.get("document_kinds")
    if isinstance(kinds, list):
        kinds = ["investor_call_transcript" if kind == "earnings_transcript" else kind for kind in kinds]
    parsed = ReadingBacklogRequest.from_dict({
        "schema_version": "cwp-reading-backlog-request/1",
        "entity": bound.entity,
        "document_kinds": kinds,
        "since_date": request.get("since_date"),
        "as_of_date": request.get("as_of_date"),
        "cursor": request.get("cursor"),
        "reading_level": request.get("reading_level"),
        "limits": {"max_items": limits.get("max_items", 64)},
    })
    page = service.backlog(replace(parsed, source_market=market, security_id=bound.security_id))
    return {
        "schema_version": "cwp-incremental-backlog/1",
        "sources": [item.source_ref.to_dict() for item in page.items if item.state == BACKLOG_UNREAD],
        "next_cursor": page.next_cursor,
        "usage": page.usage,
    }


def _run_read(args: argparse.Namespace, request: dict) -> dict:
    config_path = args.config.resolve(strict=True)
    project_root = _project_root(config_path)
    config = load_catalog_config(config_path, project_root=project_root)
    catalog = SourceCatalog(config)
    try:
        service = IncrementalReadService(catalog=catalog)
        schema = request.get("schema_version")
        if schema == "cwp-incremental-backlog-request/1":
            return _scheduled_backlog(catalog, service, request)
        if schema == "cwp-incremental-read-result-request/1":
            return service.read_result_payload(ReadResultRef.from_dict(request.get("result_ref")))
        automation_db = (args.automation_db or config.catalog_dir / "automation.sqlite3").resolve()
        receipts = IncrementalRunReceipts(service, directory=config.catalog_dir / "reading-runs",
                                          automation_db=automation_db)
        if schema == "cwp-incremental-read-status-request/1":
            return receipts.status(request.get("run_id"))
        if schema == INCREMENTAL_READ_REQUEST_SCHEMA:
            parsed = IncrementalReadRequest.from_dict(request)

            def configured_summary(**kwargs):
                return _run_configured_summary(args, config_path, parsed, automation_db, **kwargs)

            return receipts.read(
                parsed, summary_runner=configured_summary if parsed.reading_level == READING_LEVEL_SUMMARY else None,
                new_summary_configured=args.summary_batch_config is not None,
            )
        backlog = ReadingBacklogRequest.from_dict(request)
        return service.backlog(backlog).to_dict()
    finally:
        catalog.close()


def main(argv: Sequence[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    parser = _parser()
    args, unknown = parser.parse_known_args(argv)
    if unknown:
        parser.error("unrecognized arguments: " + " ".join(unknown))
    try:
        request = _read_request()
        operation = request.get("schema_version", "")
        from company_wiki.automation.narrative_batch_cli import _operation_diagnostics

        with _operation_diagnostics():
            if operation == "cwp-incremental-discovery-request/1":
                response = _run_discovery(args, request)
            elif operation in {
                INCREMENTAL_READ_REQUEST_SCHEMA, "cwp-reading-backlog-request/1",
                "cwp-incremental-backlog-request/1", "cwp-incremental-read-status-request/1",
                "cwp-incremental-read-result-request/1",
            }:
                response = _run_read(args, request)
            else:
                raise ValueError("request schema_version must be a cwp-incremental request")
    except (
        IncrementalDiscoveryError, IncrementalReadError, ValueError, OSError, KeyError,
        SourceReadError, sqlite3.Error,
    ) as exc:
        print(json.dumps({
            "schema_version": "cwp-incremental-error/1",
            "error": str(exc), "error_type": type(exc).__name__,
        }, ensure_ascii=False), file=sys.stderr)
        if args.request_stdin:
            code = str(exc)
            if not code.isascii() or not code.replace("_", "").isalnum():
                code = "incremental_request_failed"
            print(json.dumps({"schema_version": "cwp-incremental-error/1", "error": {"code": code}}))
        return 2
    print(json.dumps(response, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
