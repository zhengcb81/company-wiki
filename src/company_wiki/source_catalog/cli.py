"""Command-line interface for the multi-root source catalog."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import time
from typing import Any, Sequence

from .config import load_catalog_config
from .acquisition import AcquisitionCoordinator
from .acquisition_config import load_acquisition_config
from .acquisition_journal import AcquisitionJournal
from .acquisition_service import SourceAcquisitionService
from .canonical_writer import CanonicalSourceWriter
from .control import WorkerController
from .duplicate_cleanup import DuplicateCleanupService
from .evidence_query import EvidenceQueryService
from .extraction_quality import ExtractionQualityService
from .focus_cleanup import FocusScopeCleanupService
from .llm_summarizer import build_configured_llm_client
from .portfolio_promoter import (
    PromotionIdentity,
    promote_all_for_entity,
    promote_from_portfolio,
)
from .service import SourceCatalog
from .resolver import SourceRequest, SourceResolver
from .security_identity import (
    IdentityResult,
    IdentityStatus,
    OfficialSecurityMasterRefresher,
    SECURITY_MARKETS,
    SecurityIdentityResolutionError,
    SecurityIdentityResolver,
    SecurityMasterStore,
    load_identity_master,
)
from .store import read_pipeline_status
from .startup import (
    DEFAULT_TASK_NAME,
    install_startup_task,
    startup_task_status,
    uninstall_startup_task,
)
from .lock import CatalogOperationLockedError
from .worker import SourceCatalogWorker, load_worker_config, set_low_process_priority


def _retry_on_catalog_lock(
    fn: Any,
    *,
    action: str,
    deadline_seconds: float = 300.0,
    base_seconds: float = 5.0,
    factor: float = 2.0,
) -> Any:
    """Retry a catalog-write call with exponential backoff when the background
    worker holds the global operation lock (ADR-008 lock robustness).

    filing-fetch wraps its downloads in a worker pause-around, so this matters
    mainly for direct CLI usage while the worker's long batch holds the lock.
    The retry is deadline-bounded; exhaustion re-raises the lock error.
    """
    attempt = 1
    backoff = base_seconds
    deadline = time.monotonic() + max(0.0, deadline_seconds)
    while True:
        try:
            return fn()
        except CatalogOperationLockedError as exc:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise
            wait = min(backoff, remaining)
            print(
                f"[source-catalog] {action} blocked by the catalog lock "
                f"(attempt {attempt}); retrying in {wait:.1f}s: {exc}",
                file=sys.stderr,
            )
            time.sleep(wait)
            attempt += 1
            backoff *= factor


def _append_paused_acquisition_audit(
    catalog_dir: Path,
    *,
    entity: str | None,
    document_kind: str,
    pid: int,
) -> None:
    """Append one audit line when a download runs while the worker is paused.

    Best-effort: an audit failure warns on stderr but never blocks acquisition.
    """
    record = {
        "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "entity": entity,
        "document_kind": document_kind,
        "pid": pid,
    }
    try:
        path = catalog_dir / "paused_acquisition.log"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(record, ensure_ascii=False) + "\n")
    except OSError as exc:
        print(
            f"[ensure] warning: paused-acquisition audit log failed: {exc}",
            file=sys.stderr,
        )


def _read_recent_worker_events(catalog_dir: Path) -> dict[str, Any]:
    """Return ``recent_process_event`` + ``recent_launcher_event`` fields.

    Used by ``worker-status`` so callers can see the most recent Python
    worker process lifecycle event and the most recent PowerShell launcher
    event without scrolling JSONL files. Parse failures are communicated as
    ``recent_process_event_error`` / ``recent_launcher_event_error`` and
    never raise.
    """
    out: dict[str, Any] = {}

    def _read_last(path: Path) -> tuple[dict[str, Any] | None, str | None]:
        if not path.is_file():
            return (None, None)
        try:
            raw = path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            return (None, f"OSError: {exc}")
        if raw.startswith("\ufeff"):
            raw = raw.lstrip("\ufeff")
        lines = [ln for ln in raw.splitlines() if ln.strip()]
        if not lines:
            return (None, None)
        last = lines[-1].strip()
        try:
            return (json.loads(last), None)
        except json.JSONDecodeError as exc:
            return (None, f"JSONDecodeError: {exc.msg}")

    process_event, process_error = _read_last(
        catalog_dir / "worker_process_events.jsonl"
    )
    if process_event is not None:
        out["recent_process_event"] = process_event
    else:
        out["recent_process_event"] = None
        if process_error is not None:
            out["recent_process_event_error"] = process_error

    launcher_event, launcher_error = _read_last(
        catalog_dir / "worker_launcher_events.jsonl"
    )
    if launcher_event is not None:
        out["recent_launcher_event"] = launcher_event
    else:
        out["recent_launcher_event"] = None
        if launcher_error is not None:
            out["recent_launcher_event_error"] = launcher_error

    return out


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="company-wiki-source-catalog",
        description="Scan read-only source roots and build normalized/summary Markdown indexes.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config/source_catalog.yaml"),
        help="versioned source-catalog YAML configuration",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    scan = subparsers.add_parser("scan", help="scan and hash configured source roots")
    scan.add_argument(
        "--dry-run",
        action="store_true",
        help="count candidates without creating catalog files",
    )
    scan.add_argument(
        "--root-id", action="append", help="scan only this configured root; repeatable"
    )

    normalize = subparsers.add_parser(
        "normalize", help="create normalized Markdown and EvidenceSpans"
    )
    normalize.add_argument("--limit", type=int)
    normalize.add_argument("--force", action="store_true")

    summarize = subparsers.add_parser(
        "summarize", help="create deterministic source-only summaries"
    )
    summarize.add_argument("--limit", type=int)
    summarize.add_argument("--force", action="store_true")

    fingerprint_backfill = subparsers.add_parser(
        "fingerprint-backfill",
        help="compute normalized-text fingerprints for documents lacking one",
    )
    fingerprint_backfill.add_argument("--limit", type=int)

    subparsers.add_parser(
        "export", help="export documents.csv, artifacts.csv, and index.md"
    )
    derived_audit = subparsers.add_parser(
        "derived-audit", help="audit detached derived files against current catalog"
    )
    derived_audit.add_argument(
        "--limit",
        type=int,
        default=0,
        help="limit the number of derived files to audit (0=all)",
    )
    subparsers.add_parser("status", help="show catalog counts")

    focus_cleanup = subparsers.add_parser(
        "focus-cleanup",
        help="dry-run or apply the exact dropbox_stock/重点关注 admission cleanup",
    )
    focus_cleanup.add_argument("--root-id", required=True)
    focus_cleanup.add_argument("--relative-prefix", required=True)
    focus_cleanup.add_argument("--apply", action="store_true")
    focus_cleanup.add_argument("--confirmation-token")
    focus_cleanup.add_argument("--snapshot-path", type=Path)
    focus_cleanup.add_argument("--receipt-path", type=Path)
    focus_cleanup.add_argument("--archive-dir", type=Path)

    documents_cmd = subparsers.add_parser(
        "documents", help="manage catalog documents (retire, ...)"
    )
    documents_sub = documents_cmd.add_subparsers(dest="document_action")
    retire_cmd = documents_sub.add_parser(
        "retire", help="soft-delete a document: retired + audit, nothing removed"
    )
    retire_cmd.add_argument("--document-id", required=True)
    retire_cmd.add_argument("--reason", required=True)
    retire_cmd.add_argument("--created-by", default="cli")
    restore_cmd = documents_sub.add_parser(
        "restore", help="reactivate a retired document: active + audit"
    )
    restore_cmd.add_argument("--document-id", required=True)
    restore_cmd.add_argument("--reason", required=True)
    restore_cmd.add_argument("--created-by", default="cli")

    identity_enrich = subparsers.add_parser(
        "identity-enrichment",
        help="manage source metadata assertions: preview, verify, reject",
    )
    identity_enrich_sub = identity_enrich.add_subparsers(dest="enrichment_action")
    id_preview = identity_enrich_sub.add_parser(
        "preview", help="preview a candidate assertion without writing"
    )
    id_preview.add_argument("--source-id", required=True)
    id_preview.add_argument("--document-id", required=True)
    id_preview.add_argument("--content-sha256", required=True)
    id_preview.add_argument("--entity")
    id_preview.add_argument("--market")
    id_preview.add_argument("--security-id")
    id_preview.add_argument("--document-kind")
    id_preview.add_argument("--provider")
    id_preview.add_argument("--provider-document-id")
    id_preview.add_argument("--evidence-basis", required=True)
    id_preview.add_argument("--evidence-json")
    id_verify = identity_enrich_sub.add_parser(
        "verify", help="promote a candidate assertion to verified"
    )
    id_verify.add_argument("--assertion-id", required=True)
    id_verify.add_argument("--current-sha256", required=True)
    id_verify.add_argument("--confirmed-by", default="cw-2.28-automation")
    id_reject = identity_enrich_sub.add_parser(
        "reject", help="reject a candidate assertion"
    )
    id_reject.add_argument("--assertion-id", required=True)
    id_reject.add_argument("--reason", required=True)
    id_reject.add_argument("--rejected-by", default="cw-2.28-automation")

    identify = subparsers.add_parser(
        "identify",
        help="resolve a company name, alias, or ticker to one verified listed security",
    )
    identify.add_argument("--query", required=True)
    identify.add_argument("--market", choices=SECURITY_MARKETS)
    identify.add_argument("--exchange")
    identify.add_argument("--identity-cache-dir", type=Path)
    identify.add_argument("--refresh", action="store_true")

    query = subparsers.add_parser(
        "query", help="query catalog metadata and artifact paths"
    )
    query.add_argument("--text")
    query.add_argument("--entity")
    query.add_argument("--document-kind")
    query.add_argument("--source-status")
    query.add_argument("--limit", type=int, default=100)

    evidence = subparsers.add_parser(
        "evidence", help="look up one exact EvidenceSpan by source ID and locator"
    )
    evidence.add_argument("--source-id", required=True)
    evidence.add_argument("--locator", required=True)

    evidence_list = subparsers.add_parser(
        "evidence-list", help="list bounded EvidenceSpans for one source or document"
    )
    evidence_identity = evidence_list.add_mutually_exclusive_group(required=True)
    evidence_identity.add_argument("--source-id")
    evidence_identity.add_argument("--document-id")
    evidence_list.add_argument("--limit", type=int, default=100)
    evidence_list.add_argument("--offset", type=int, default=0)

    extraction_quality = subparsers.add_parser(
        "extraction-quality",
        help="assess deterministic source/extraction quality without span bodies",
    )
    extraction_identity = extraction_quality.add_mutually_exclusive_group(required=True)
    extraction_identity.add_argument("--source-id")
    extraction_identity.add_argument("--document-id")
    extraction_quality.add_argument("--locator-limit", type=int, default=100)

    duplicates = subparsers.add_parser(
        "duplicates",
        help="list exact-copy groups and their protected canonical locations",
    )
    duplicates.add_argument(
        "--text", help="filter by company, title, kind, date, or path"
    )
    duplicates.add_argument("--limit", type=int, default=50)
    duplicates.add_argument("--offset", type=int, default=0)
    duplicates.add_argument(
        "--include-semantic",
        action="store_true",
        help="also list semantic (same-text, different-bytes) groups; review-only, not recyclable",
    )

    duplicate_preview = subparsers.add_parser(
        "duplicate-preview",
        help="revalidate one indexed noncanonical exact-copy and issue a confirmation token",
    )
    duplicate_preview.add_argument("--location-id", required=True)

    duplicate_recycle = subparsers.add_parser(
        "duplicate-recycle",
        help="move one revalidated exact-copy location to the Windows Recycle Bin",
    )
    duplicate_recycle.add_argument("--location-id", required=True)
    duplicate_recycle.add_argument("--confirmation-token", required=True)

    resolve = subparsers.add_parser(
        "resolve",
        help="resolve an existing source before any downloader is considered",
    )
    resolve_identity = resolve.add_mutually_exclusive_group(required=True)
    resolve_identity.add_argument("--entity")
    resolve_identity.add_argument("--company-query")
    resolve.add_argument("--document-kind", required=True)
    resolve.add_argument("--as-of-date", required=True)
    resolve.add_argument("--market")
    resolve.add_argument("--exchange")
    resolve.add_argument("--security-id")
    resolve.add_argument("--identity-cache-dir", type=Path)
    resolve.add_argument("--form-type")
    resolve.add_argument("--fiscal-year", type=int)
    resolve.add_argument("--fiscal-period")
    resolve.add_argument("--language")
    resolve.add_argument("--provider")
    resolve.add_argument("--provider-document-id")

    ensure = subparsers.add_parser(
        "ensure",
        help="resolve first and optionally acquire one missing source through configured adapters",
    )
    ensure_identity = ensure.add_mutually_exclusive_group(required=True)
    ensure_identity.add_argument("--entity")
    ensure_identity.add_argument("--company-query")
    ensure.add_argument("--document-kind", required=True)
    ensure.add_argument("--as-of-date", required=True)
    ensure.add_argument("--market")
    ensure.add_argument("--exchange")
    ensure.add_argument("--security-id")
    ensure.add_argument("--identity-cache-dir", type=Path)
    ensure.add_argument("--form-type")
    ensure.add_argument("--fiscal-year", type=int)
    ensure.add_argument("--fiscal-period")
    ensure.add_argument("--language")
    ensure.add_argument("--provider")
    ensure.add_argument("--provider-document-id")
    ensure.add_argument(
        "--allow-download",
        action="store_true",
        help="explicitly permit adapter discovery/fetch when the catalog has no reusable source",
    )
    ensure.add_argument(
        "--allow-acquisition-while-paused",
        action="store_true",
        help=(
            "permit adapter download even when the background worker is paused; "
            "intended for orchestrators (filing-fetch) that deliberately paused the "
            "worker to release the catalog lock and will resume it afterwards"
        ),
    )
    ensure.add_argument(
        "--acquisition-config",
        type=Path,
        default=Path("config/source_acquisition.yaml"),
    )
    ensure.add_argument(
        "--worker-config",
        type=Path,
        default=Path("config/source_catalog_worker.yaml"),
        help="control state used to refuse downloads while the worker is paused",
    )

    import_portfolio = subparsers.add_parser(
        "import-portfolio",
        help=(
            "promote already-indexed dayu-portfolio documents into company_raw "
            "canonical sources so filing-fetch reuses them without re-downloading"
        ),
    )
    ip_identity = import_portfolio.add_mutually_exclusive_group(required=True)
    ip_identity.add_argument("--entity")
    ip_identity.add_argument("--company-query")
    import_portfolio.add_argument("--market")
    import_portfolio.add_argument("--exchange")
    import_portfolio.add_argument("--security-id")
    import_portfolio.add_argument("--document-id")
    import_portfolio.add_argument("--document-kind")
    import_portfolio.add_argument("--fiscal-year", type=int)
    import_portfolio.add_argument(
        "--as-of-date",
        help="information date used for the SourceRequest (default: today)",
    )
    import_portfolio.add_argument(
        "--all",
        action="store_true",
        help="promote every matching portfolio document of the entity",
    )
    import_portfolio.add_argument("--dry-run", action="store_true")
    import_portfolio.add_argument(
        "--acquisition-config",
        type=Path,
        default=Path("config/source_acquisition.yaml"),
    )

    run = subparsers.add_parser(
        "run", help="scan, normalize, summarize, and export in order"
    )
    run.add_argument("--limit", type=int, help="optional normalize/summary batch limit")
    run.add_argument("--force", action="store_true")

    worker = subparsers.add_parser(
        "worker", help="periodically scan and process low-priority background batches"
    )
    worker.add_argument(
        "--worker-config",
        type=Path,
        default=Path("config/source_catalog_worker.yaml"),
    )
    worker.add_argument(
        "--once", action="store_true", help="run one scheduling cycle and exit"
    )
    worker.add_argument(
        "--startup-delay-seconds",
        type=int,
        default=0,
        help="interruptible delay used by the Windows logon fallback",
    )

    def add_worker_control_parser(name: str, help_text: str) -> argparse.ArgumentParser:
        command = subparsers.add_parser(name, help=help_text)
        command.add_argument(
            "--worker-config",
            type=Path,
            default=Path("config/source_catalog_worker.yaml"),
        )
        return command

    worker_status = add_worker_control_parser(
        "worker-status", "show startup, persistent pause, process, and scheduler state"
    )
    worker_status.add_argument("--task-name", default=DEFAULT_TASK_NAME)

    worker_start = add_worker_control_parser(
        "worker-start", "start the background worker now if it is enabled"
    )
    worker_start.add_argument("--wait-seconds", type=float, default=5.0)
    worker_start.add_argument("--startup-delay-seconds", type=int, default=0)

    worker_resume = add_worker_control_parser(
        "worker-resume", "clear persistent pause and start the background worker"
    )
    worker_resume.add_argument("--wait-seconds", type=float, default=5.0)
    worker_resume.add_argument("--startup-delay-seconds", type=int, default=0)

    for name, help_text in (
        ("worker-pause", "persistently pause the worker and stop it now"),
        ("worker-stop", "stop this run but keep the next-logon auto-start enabled"),
    ):
        command = add_worker_control_parser(name, help_text)
        command.add_argument("--graceful-timeout-seconds", type=float, default=5.0)
        command.add_argument(
            "--no-force",
            action="store_false",
            dest="force",
            help="request a graceful stop without the identity-checked force fallback",
        )
        command.set_defaults(force=True)

    install = subparsers.add_parser(
        "install-startup",
        help="install a Windows logon task without starting it immediately",
    )
    install.add_argument("--task-name", default=DEFAULT_TASK_NAME)

    uninstall = subparsers.add_parser(
        "uninstall-startup", help="remove the Windows logon task"
    )
    uninstall.add_argument("--task-name", default=DEFAULT_TASK_NAME)

    startup = subparsers.add_parser(
        "startup-status", help="show Windows logon task status"
    )
    startup.add_argument("--task-name", default=DEFAULT_TASK_NAME)
    return parser


def _plain(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if hasattr(value, "to_dict"):
        return _plain(value.to_dict())
    if isinstance(value, dict):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    return value


def main(argv: Sequence[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    args = _parser().parse_args(argv)
    config_path = args.config.resolve(strict=True)
    project_root = config_path.parents[1]
    config = load_catalog_config(config_path, project_root=project_root)

    def worker_config_path() -> Path:
        path = args.worker_config
        if not path.is_absolute():
            path = project_root / path
        return path.resolve(strict=True)

    def worker_controller() -> WorkerController:
        return WorkerController(
            catalog_dir=config.catalog_dir,
            project_root=project_root,
            config_path=config_path,
            worker_config_path=worker_config_path(),
            python_executable=Path(sys.executable),
        )

    catalog: SourceCatalog | None = None

    def get_catalog() -> SourceCatalog:
        nonlocal catalog
        if catalog is None:
            catalog = SourceCatalog(config)
        return catalog

    def security_master_store() -> SecurityMasterStore:
        configured = getattr(args, "identity_cache_dir", None)
        path = configured or (config.catalog_dir / "security_master")
        if not path.is_absolute():
            path = project_root / path
        return SecurityMasterStore(path)

    def identify_company() -> IdentityResult:
        store = security_master_store()
        result = SecurityIdentityResolver(
            load_identity_master(store, market=args.market)
        ).identify(
            args.company_query,
            market=args.market,
            exchange=args.exchange,
        )
        if result.status is not IdentityStatus.RESOLVED or result.resolved is None:
            raise SecurityIdentityResolutionError(result)
        if (
            args.security_id
            and args.security_id.casefold() != result.resolved.security_id.casefold()
        ):
            raise SecurityIdentityResolutionError(
                IdentityResult(
                    query=result.query,
                    normalized_query=result.normalized_query,
                    market_hint=result.market_hint,
                    exchange_hint=result.exchange_hint,
                    status=IdentityStatus.CONFLICT,
                    reason="explicit_security_id_conflicts_with_verified_identity",
                    resolved=None,
                    candidates=result.candidates,
                )
            )
        return result

    def source_request(
        *, allow_download: bool = False
    ) -> tuple[SourceRequest, IdentityResult | None]:
        identity = identify_company() if args.company_query else None
        resolved = identity.resolved if identity else None
        request = SourceRequest(
            entity=resolved.canonical_name if resolved else args.entity,
            market=resolved.market if resolved else args.market,
            security_id=resolved.security_id if resolved else args.security_id,
            document_kind=args.document_kind,
            form_type=args.form_type,
            fiscal_year=args.fiscal_year,
            fiscal_period=args.fiscal_period,
            language=args.language,
            provider=args.provider,
            provider_document_id=args.provider_document_id,
            as_of_date=args.as_of_date,
            allow_download=allow_download,
        )
        return request, identity

    try:
        if args.command == "scan":
            result: Any = get_catalog().scan(
                dry_run=args.dry_run,
                root_ids=set(args.root_id) if args.root_id else None,
            )
        elif args.command == "normalize":
            result = get_catalog().normalize(limit=args.limit, force=args.force)
        elif args.command == "summarize":
            result = get_catalog().summarize(limit=args.limit, force=args.force)
        elif args.command == "fingerprint-backfill":
            result = get_catalog().backfill_text_fingerprints(limit=args.limit)
        elif args.command == "export":
            result = get_catalog().export_indexes()
        elif args.command == "derived-audit":
            from .reconciliation import reconcile_artifacts

            derived_dir = config.catalog_dir / "derived"
            result = reconcile_artifacts(
                config.database_path,
                derived_dir,
                limit=getattr(args, "limit", 0),
            )
        elif args.command == "status":
            result = get_catalog().status()
        elif args.command == "focus-cleanup":
            cleanup = FocusScopeCleanupService(get_catalog())
            receipt_path = args.receipt_path
            snapshot_path = args.snapshot_path
            if receipt_path is not None and not receipt_path.is_absolute():
                receipt_path = (project_root / receipt_path).resolve(strict=False)
            if snapshot_path is not None and not snapshot_path.is_absolute():
                snapshot_path = (project_root / snapshot_path).resolve(strict=False)
            if args.apply:
                if (
                    not args.confirmation_token
                    or snapshot_path is None
                    or receipt_path is None
                ):
                    raise ValueError(
                        "--apply requires --confirmation-token, --snapshot-path, "
                        "and --receipt-path"
                    )
                result = cleanup.apply(
                    root_id=args.root_id,
                    relative_prefix=args.relative_prefix,
                    confirmation_token=args.confirmation_token,
                    snapshot_path=snapshot_path,
                    receipt_path=receipt_path,
                    archive_dir=args.archive_dir,
                )
            else:
                result = cleanup.preview(
                    root_id=args.root_id,
                    relative_prefix=args.relative_prefix,
                    receipt_path=receipt_path,
                )
        elif args.command == "documents":
            if getattr(args, "document_action", None) == "retire":
                from .store import retire_document

                result = retire_document(
                    get_catalog().store,
                    document_id=args.document_id,
                    reason=args.reason,
                    created_by=getattr(args, "created_by", "cli"),
                )
            elif getattr(args, "document_action", None) == "restore":
                from .store import restore_document

                result = restore_document(
                    get_catalog().store,
                    document_id=args.document_id,
                    reason=args.reason,
                    created_by=getattr(args, "created_by", "cli"),
                )
            else:
                return 2
        elif args.command == "identity-enrichment":
            from .assertion_service import (
                preview_assertion,
                verify_assertion,
                reject_assertion,
            )

            store = get_catalog().store
            if args.enrichment_action == "preview":
                evidence_json = (
                    json.loads(args.evidence_json)
                    if getattr(args, "evidence_json", None)
                    else None
                )
                result = preview_assertion(
                    store,
                    source_id=args.source_id,
                    document_id=args.document_id,
                    content_sha256=args.content_sha256,
                    entity=getattr(args, "entity", None),
                    market=getattr(args, "market", None),
                    security_id=getattr(args, "security_id", None),
                    document_kind=getattr(args, "document_kind", None),
                    provider=getattr(args, "provider", None),
                    provider_document_id=getattr(args, "provider_document_id", None),
                    evidence_basis=args.evidence_basis,
                    evidence_json=evidence_json,
                )
            elif args.enrichment_action == "verify":
                result = verify_assertion(
                    store,
                    assertion_id=args.assertion_id,
                    current_sha256=args.current_sha256,
                    confirmed_by=getattr(args, "confirmed_by", "cw-2.28-automation"),
                )
            elif args.enrichment_action == "reject":
                result = reject_assertion(
                    store,
                    assertion_id=args.assertion_id,
                    reason=args.reason,
                    rejected_by=getattr(args, "rejected_by", "cw-2.28-automation"),
                )
            else:
                return 2
        elif args.command == "identify":
            store = security_master_store()
            refresh = None
            if args.refresh:
                markets = (args.market,) if args.market else SECURITY_MARKETS
                refresh = OfficialSecurityMasterRefresher(store).refresh(
                    markets=markets
                )
            identity = SecurityIdentityResolver(
                load_identity_master(store, market=args.market)
            ).identify(
                args.query,
                market=args.market,
                exchange=args.exchange,
            )
            result = identity.to_dict()
            if refresh is not None:
                result["refresh"] = refresh
        elif args.command == "query":
            result = get_catalog().query(
                text=args.text,
                entity=args.entity,
                document_kind=args.document_kind,
                source_status=args.source_status,
                limit=args.limit,
            )
        elif args.command == "evidence":
            result = EvidenceQueryService(config.database_path).lookup(
                source_id=args.source_id,
                locator=args.locator,
            )
        elif args.command == "evidence-list":
            result = EvidenceQueryService(config.database_path).list_spans(
                source_id=args.source_id,
                document_id=args.document_id,
                limit=args.limit,
                offset=args.offset,
            )
        elif args.command == "extraction-quality":
            result = ExtractionQualityService(config.database_path).assess(
                source_id=args.source_id,
                document_id=args.document_id,
                locator_limit=args.locator_limit,
            )
        elif args.command == "duplicates":
            result = DuplicateCleanupService(get_catalog()).list_groups(
                text=args.text,
                limit=args.limit,
                offset=args.offset,
                include_semantic=args.include_semantic,
            )
        elif args.command == "duplicate-preview":
            result = DuplicateCleanupService(get_catalog()).preview(args.location_id)
        elif args.command == "duplicate-recycle":
            result = DuplicateCleanupService(get_catalog()).recycle(
                args.location_id,
                confirmation_token=args.confirmation_token,
            )
        elif args.command == "resolve":
            request, identity = source_request()
            source_resolution = SourceResolver(get_catalog()).resolve(request).to_dict()
            result = (
                {"identity": identity.to_dict(), "source_resolution": source_resolution}
                if identity
                else source_resolution
            )
        elif args.command == "ensure":
            request, identity = source_request(allow_download=args.allow_download)
            desired_state = worker_controller().status()["desired_state"]
            if (
                args.allow_download
                and desired_state == "paused"
                and not args.allow_acquisition_while_paused
            ):
                raise RuntimeError(
                    "source acquisition is paused; run worker-resume before allowing downloads"
                )
            if args.allow_download and desired_state == "paused":
                _append_paused_acquisition_audit(
                    config.catalog_dir,
                    entity=request.entity,
                    document_kind=request.document_kind,
                    pid=os.getpid(),
                )
            acquisition_config_path = args.acquisition_config
            if not acquisition_config_path.is_absolute():
                acquisition_config_path = project_root / acquisition_config_path
            acquisition_config = load_acquisition_config(
                acquisition_config_path.resolve(strict=True),
                project_root=project_root,
            )
            ensured = _retry_on_catalog_lock(
                lambda: SourceAcquisitionService(
                    coordinator=AcquisitionCoordinator(
                        catalog=get_catalog(),
                        adapters=acquisition_config.build_registry(),
                        staging_root=acquisition_config.staging_root,
                    ),
                    writer=CanonicalSourceWriter(
                        get_catalog(),
                        staging_root=acquisition_config.staging_root,
                    ),
                    journal=AcquisitionJournal(config.catalog_dir),
                ).ensure(request),
                action="ensure",
            )
            result = (
                {"identity": identity.to_dict(), "source_ensure": _plain(ensured)}
                if identity
                else ensured
            )
        elif args.command == "import-portfolio":
            identity = identify_company() if args.company_query else None
            resolved = identity.resolved if identity else None
            if resolved is not None:
                promotion_identity = PromotionIdentity(
                    canonical_name=resolved.canonical_name,
                    market=resolved.market,
                    security_id=resolved.security_id,
                )
            else:
                promotion_identity = PromotionIdentity(
                    canonical_name=args.entity,
                    market=args.market,
                    security_id=args.security_id,
                )
            acquisition_config_path = args.acquisition_config
            if not acquisition_config_path.is_absolute():
                acquisition_config_path = project_root / acquisition_config_path
            acquisition_config = load_acquisition_config(
                acquisition_config_path.resolve(strict=True),
                project_root=project_root,
            )
            writer = CanonicalSourceWriter(
                get_catalog(),
                staging_root=acquisition_config.staging_root,
            )
            portfolio_root = next(
                (root.path for root in config.roots if root.kind == "dayu_portfolio"),
                None,
            )
            if portfolio_root is None:
                raise RuntimeError("no dayu_portfolio root configured")
            as_of_date = args.as_of_date or time.strftime("%Y-%m-%d")

            def _run_promotions() -> list:
                if args.document_id:
                    return [
                        promote_from_portfolio(
                            get_catalog(),
                            writer,
                            portfolio_root,
                            promotion_identity,
                            document_id=args.document_id,
                            as_of_date=as_of_date,
                            dry_run=args.dry_run,
                        )
                    ]
                if args.all or args.fiscal_year is not None or args.document_kind:
                    return promote_all_for_entity(
                        get_catalog(),
                        writer,
                        portfolio_root,
                        promotion_identity,
                        as_of_date=as_of_date,
                        dry_run=args.dry_run,
                        document_kind=args.document_kind,
                        fiscal_year=args.fiscal_year,
                    )
                raise RuntimeError(
                    "import-portfolio requires --document-id, --all, "
                    "--fiscal-year, or --document-kind"
                )

            promotions = _retry_on_catalog_lock(
                _run_promotions, action="import-portfolio"
            )
            result = {"promotions": [promotion.to_dict() for promotion in promotions]}
            if identity:
                result["identity"] = identity.to_dict()
        elif args.command == "worker-status":
            controller = worker_controller()
            result = controller.status()
            result["startup"] = startup_task_status(task_name=args.task_name)
            state_path = config.catalog_dir / "worker_state.json"
            scheduler: dict[str, Any] = {}
            if state_path.is_file():
                scheduler = json.loads(state_path.read_text(encoding="utf-8"))
                result["scheduler"] = scheduler
            pipeline = read_pipeline_status(config.database_path)
            live = result.get("runtime_state") == "running"
            stage = str(
                result.get("worker_status") or ("waiting" if live else "stopped")
            )
            if stage == "idle":
                stage = "waiting"
                result["worker_status"] = stage
            active_documents = 0
            if pipeline["available"] and live:
                if stage == "normalizing" and pipeline["markdown"]["pending"] > 0:
                    pipeline["markdown"]["in_progress"] = 1
                    active_documents = 1
                elif stage == "summarizing" and pipeline["llm_summary"]["pending"] > 0:
                    pipeline["llm_summary"]["in_progress"] = 1
                    active_documents = 1
            retry_after = scheduler.get("llm_retry_after")
            retry_active = bool(
                retry_after is not None and float(retry_after) > time.time()
            )
            pipeline["llm_summary"]["deferred"] = retry_active
            last_llm_report = scheduler.get("last_llm_summary_report")
            global_report = (
                last_llm_report
                if isinstance(last_llm_report, dict)
                and last_llm_report.get("failure_scope") == "global"
                else None
            )
            global_deferred = bool(
                retry_active
                and (
                    global_report is not None
                    or scheduler.get("last_error_scope") == "llm_global"
                )
            )
            pipeline["llm_summary"].update(
                {
                    "global_deferred": global_deferred,
                    "global_retry_after": retry_after if global_deferred else None,
                    "global_error": (
                        str(global_report.get("error") or scheduler.get("last_error"))
                        if global_deferred and global_report is not None
                        else scheduler.get("last_error")
                        if global_deferred
                        else None
                    ),
                }
            )
            pipeline["current"] = {
                "stage": stage if live else "stopped",
                "active_documents": active_documents,
                "path": result.get("current_path") if live else None,
                "current": int(result.get("progress_current") or 0) if live else 0,
                "total": int(result.get("progress_total") or 0) if live else 0,
                "percent": result.get("progress_percent") if live else None,
                "detail": result.get("progress_detail") if live else None,
                "updated_at": result.get("updated_at") if live else None,
            }
            pipeline["recent_batches"] = {
                "scan": scheduler.get("last_scan_report"),
                "markdown": scheduler.get("last_normalize_report"),
                "llm_summary": scheduler.get("last_llm_summary_report"),
            }
            result["pipeline"] = pipeline
            result.update(_read_recent_worker_events(config.catalog_dir))
        elif args.command == "worker-start":
            result = worker_controller().start(
                wait_seconds=args.wait_seconds,
                startup_delay_seconds=args.startup_delay_seconds,
            )
        elif args.command == "worker-resume":
            result = worker_controller().resume(
                wait_seconds=args.wait_seconds,
                startup_delay_seconds=args.startup_delay_seconds,
            )
        elif args.command == "worker-pause":
            result = worker_controller().pause(
                graceful_timeout_seconds=args.graceful_timeout_seconds,
                force=args.force,
            )
        elif args.command == "worker-stop":
            result = worker_controller().stop(
                graceful_timeout_seconds=args.graceful_timeout_seconds,
                force=args.force,
            )
        elif args.command == "worker":
            worker_config = load_worker_config(
                worker_config_path(), project_root=project_root
            )
            state_path = config.catalog_dir / "worker_state.json"

            def factory() -> Any:
                return build_configured_llm_client(
                    project_root, worker_config.runtime_config
                )

            if not args.once and worker_controller().read_desired_state() == "paused":
                result = {"status": "paused", "reason": "persistent_pause"}
            else:
                worker = SourceCatalogWorker(
                    get_catalog(),
                    worker_config,
                    state_path=state_path,
                    project_root=project_root,
                    llm_client_factory=factory,
                )
                if args.once:
                    set_low_process_priority()
                    result = worker.run_cycle()
                else:
                    result = worker.run_forever(
                        control=worker_controller(),
                        startup_delay_seconds=args.startup_delay_seconds,
                    )
        elif args.command == "install-startup":
            result = install_startup_task(
                project_root=project_root,
                launcher_path=project_root / "scripts" / "source_catalog_worker.ps1",
                python_executable=Path(sys.executable),
                task_name=args.task_name,
            )
        elif args.command == "uninstall-startup":
            result = uninstall_startup_task(task_name=args.task_name)
        elif args.command == "startup-status":
            result = startup_task_status(task_name=args.task_name)
        else:
            result = {
                "scan": get_catalog().scan(),
                "normalize": get_catalog().normalize(
                    limit=args.limit, force=args.force
                ),
                "summarize": get_catalog().summarize(
                    limit=args.limit, force=args.force
                ),
                "export": get_catalog().export_indexes(),
                "status": get_catalog().status(),
            }
    except Exception as exc:
        print(
            json.dumps(
                {
                    "status": "failed",
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                },
                ensure_ascii=False,
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 1
    print(json.dumps(_plain(result), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["main"]
