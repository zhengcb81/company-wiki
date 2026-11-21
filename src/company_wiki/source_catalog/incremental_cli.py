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
    IncrementalReadError,
    IncrementalReadRequest,
    IncrementalReadService,
    READING_LEVEL_SUMMARY,
    ReadingBacklogRequest,
)
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


def _budget(request: dict) -> AcquisitionBudget | None:
    """One bounded metadata budget for this discovery call."""
    limits = request.get("limits") or {}
    max_seconds = limits.get("max_seconds", 120.0)
    if isinstance(max_seconds, (int, float)) and max_seconds > 0:
        seconds = float(max_seconds)
    else:
        seconds = 120.0
    return AcquisitionBudget.from_limits(
        max_response_bytes=16 * 1024 * 1024, max_seconds=seconds, max_cost_usd="0",
    )


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
        response = service.discover(parsed, budget=_budget(request))
        return response.to_dict()
    finally:
        catalog.close()


def _build_summary_generator(args: argparse.Namespace, config_path: Path, parsed):
    """Compose the existing configured batch entry for the summary tier.

    The model settings come from ``--llm-config`` through the project's own
    loader; the batch engine settings (profile, caps, pricing) come from the
    CWP-owned ``--summary-batch-config`` sidecar.  The caller never carries
    model names, prompt text or engine internals across the boundary.  The
    same ``run_id`` resumes the same AUTO batch, so a retried request reads
    its original ledger instead of paying twice.
    """
    from company_wiki.automation.narrative_batch import run_batch
    from company_wiki.automation.narrative_batch_request import NarrativeBatchRequest
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
    automation_db = (
        args.automation_db if args.automation_db is not None
        else _project_root(config_path) / ".source_catalog" / "automation.db"
    )
    work_dir = (
        args.work_dir if args.work_dir is not None
        else _project_root(config_path) / ".source_catalog" / "reading-run-work"
    )
    # The batch engine requires an empty or baseline-carrying work dir; the
    # request files live beside the automation database instead.
    request_dir = automation_db.parent / "summary-requests"
    request_dir.mkdir(parents=True, exist_ok=True)

    def generator(*, run_id: str, sources: list[dict[str, Any]]) -> dict[str, Any]:
        request = NarrativeBatchRequest.from_dict({
            "schema_version": "narrative-batch-request/1",
            "run_id": run_id,
            "sources": sources,
            "profile": batch_config.get("profile", "P2"),
            "max_seconds": batch_config.get("max_seconds", 600),
            "max_tokens": batch_config.get("max_tokens", 200_000),
            "max_cost_usd": batch_config.get("max_cost_usd", "2"),
            "model": {**options, **(batch_config.get("model") or {})},
            "pricing": batch_config["pricing"],
        })
        request_path = request_dir / (
            "summary-" + run_id.replace("/", "_") + ".json"
        )
        request_path.write_text(
            json.dumps(request.to_dict(), ensure_ascii=False), encoding="utf-8"
        )
        return run_batch(
            request, project_root=_project_root(config_path),
            catalog_config_path=config_path, db_path=automation_db,
            work_dir=work_dir,
        )

    return generator


def _run_read(args: argparse.Namespace, request: dict) -> dict:
    config_path = args.config.resolve(strict=True)
    project_root = _project_root(config_path)
    config = load_catalog_config(config_path, project_root=project_root)
    catalog = SourceCatalog(config)
    try:
        service = IncrementalReadService(catalog=catalog)
        schema = request.get("schema_version")
        if schema == "cwp-incremental-read-request/1":
            parsed = IncrementalReadRequest.from_dict(request)
            generator = None
            if (
                parsed.reading_level == READING_LEVEL_SUMMARY
                and args.summary_batch_config is not None
            ):
                generator = _build_summary_generator(args, config_path, parsed)
            return service.read(parsed, summary_generator=generator).to_dict()
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
        if operation == "cwp-incremental-discovery-request/1":
            response = _run_discovery(args, request)
        elif operation in {
            "cwp-incremental-read-request/1", "cwp-reading-backlog-request/1",
        }:
            response = _run_read(args, request)
        else:
            raise ValueError(
                "request schema_version must be a cwp-incremental request"
            )
    except (
        IncrementalDiscoveryError, IncrementalReadError, ValueError, OSError,
        SourceReadError, sqlite3.Error,
    ) as exc:
        print(json.dumps({
            "schema_version": "cwp-incremental-error/1",
            "error": str(exc), "error_type": type(exc).__name__,
        }, ensure_ascii=False), file=sys.stderr)
        return 2
    print(json.dumps(response, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
