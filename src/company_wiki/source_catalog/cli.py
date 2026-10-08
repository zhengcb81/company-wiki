"""Command-line interface for the multi-root source catalog."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time
from typing import Any, Sequence

from .config import load_catalog_config
from .acquisition import (
    ACQUISITION_SCHEMA_VERSION,
    AcquisitionCoordinator,
    AcquisitionResult,
    AcquisitionStatus,
)
from .acquisition_config import load_acquisition_config
from .acquisition_service import (
    SOURCE_ENSURE_SCHEMA_VERSION,
    SourceAcquisitionService,
    SourceEnsureResult,
    SourceEnsureStatus,
)
from .canonical_writer import CanonicalSourceWriter
from .control import WorkerController
from .duplicate_cleanup import DuplicateCleanupService
from .reconcile_retire_state import ReconcileRetireStateService
from .extraction_quality import ExtractionQualityService
from .maintenance_retirement import RetiredMaintenanceError
from .portfolio_promoter import (
    PromotionIdentity,
    promote_all_for_entity,
    promote_from_portfolio,
)
from .service import SourceCatalog
from .source_read_policy import source_read_policy_sha256
from .resolver import ResolutionResult, ResolutionStatus, SourceRequest, SourceResolver
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
    startup_task_status,
    uninstall_startup_task,
)
from .lock import CatalogOperationLockedError


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


RETIRED_MAINTENANCE_COMMANDS = ('focus-cleanup', 'archive-retired-evidence', 'prune-retired-evidence', 'duplicate-preview', 'duplicate-recycle')


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="company-wiki-source-catalog",
        description="Catalog source versions, verify raw documents, and export read-only indexes.",
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
    register = subparsers.add_parser("register", help="register explicit source groups without root discovery")
    register.add_argument("--root-id", required=True)
    register.add_argument(
        "--relative-path", action="append",
        required=True, help="source group within --root-id; repeatable; no missing sweep",
    )

    source_facts = subparsers.add_parser("source-facts", help="verify bytes and atomically record source facts")
    source_facts.add_argument("--request", type=Path, required=True)

    fingerprint_backfill = subparsers.add_parser(
        "fingerprint-backfill",
        help="compute normalized-text fingerprints for documents lacking one",
    )
    fingerprint_backfill.add_argument("--limit", type=int)

    subparsers.add_parser(
        "export", help="export documents.csv, artifacts.csv, and index.md"
    )
    subparsers.add_parser(
        "policy-export",
        help=(
            "export the root policy snapshot (policy_hash + roots with "
            "${PROJECT_ROOT}-tokenized path_refs) for consumers"
        ),
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
        "preview", help="record a candidate assertion; does not verify it"
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

    reconcile_retire = subparsers.add_parser(
        "reconcile-retire",
        help="align phase-15.6 retire-audit with document status (dry-run default)",
    )
    reconcile_retire.add_argument("--apply", action="store_true")

    subparsers.add_parser(
        "size-report",
        help="read-only catalog size / disk-health report (Phase 4 monitoring)",
    )

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
    resolve.add_argument("--mode", choices=("exact", "latest_as_of"))

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
        "--mode",
        choices=("exact", "latest_as_of"),
        help=(
            "latest_as_of checks current provider metadata; an explicit download "
            "intent can fetch the unique latest source within the supplied limits"
        ),
    )
    ensure.add_argument(
        "--source-ref-v2",
        action="store_true",
        help="emit a pathless versioned operation result for consumer processes",
    )
    ensure.add_argument(
        "--allow-download",
        action="store_true",
        help="explicitly permit adapter discovery/fetch when the catalog has no reusable source",
    )
    ensure.add_argument("--max-download-bytes", type=int)
    ensure.add_argument("--max-download-seconds", type=float)
    ensure.add_argument("--max-download-cost-usd")
    ensure.add_argument("--binding-file", type=Path,
                        help="optional legacy download target scope; hashes/expiry do not grant permission")
    ensure.add_argument(
        "--allow-acquisition-while-paused",
        action="store_true",
        help=(
            "deprecated compatibility flag; a finite explicit download is independent "
            "of legacy background-worker state"
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
        help="deprecated compatibility option; finite acquisition does not read it",
    )

    close_gap = subparsers.add_parser(
        "close-gap",
        help=(
            "fetch a missing source through the same bounded service as ensure; "
            "an optional legacy binding only narrows provider/accession scope"
        ),
    )
    close_gap_identity = close_gap.add_mutually_exclusive_group(required=True)
    close_gap_identity.add_argument("--entity")
    close_gap_identity.add_argument("--company-query")
    close_gap.add_argument("--binding-file", type=Path,
                           help="optional target scope; old hashes/expiry are diagnostic")
    close_gap.add_argument("--max-download-bytes", type=int)
    close_gap.add_argument("--max-download-seconds", type=float)
    close_gap.add_argument("--max-download-cost-usd")
    close_gap.add_argument("--document-kind", required=True)
    close_gap.add_argument("--as-of-date", required=True)
    close_gap.add_argument("--market")
    close_gap.add_argument("--exchange")
    close_gap.add_argument("--security-id")
    close_gap.add_argument("--identity-cache-dir", type=Path)
    close_gap.add_argument("--form-type")
    close_gap.add_argument("--fiscal-year", type=int)
    close_gap.add_argument("--fiscal-period")
    close_gap.add_argument("--language")
    close_gap.add_argument("--provider")
    close_gap.add_argument("--provider-document-id")
    close_gap.add_argument("--mode", choices=("exact", "latest_as_of"))
    close_gap.add_argument("--source-ref-v2", action="store_true",
                           help="emit a pathless versioned operation result for consumer processes")
    close_gap.add_argument(
        "--acquisition-config",
        type=Path,
        default=Path("config/source_acquisition.yaml"),
    )
    close_gap.add_argument(
        "--allow-acquisition-while-paused",
        action="store_true",
        help="deprecated compatibility flag; finite acquisition ignores legacy worker state",
    )
    close_gap.add_argument(
        "--worker-config",
        type=Path,
        default=Path("config/source_catalog_worker.yaml"),
        help="deprecated compatibility option; close-gap does not read it",
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

    def add_worker_control_parser(name: str, help_text: str) -> argparse.ArgumentParser:
        command = subparsers.add_parser(name, help=help_text)
        command.add_argument(
            "--worker-config",
            type=Path,
            default=Path("config/source_catalog_worker.yaml"),
        )
        return command

    worker_status = add_worker_control_parser(
        "worker-status", "inspect any remaining legacy worker and startup-task state"
    )
    worker_status.add_argument("--task-name", default=DEFAULT_TASK_NAME)

    worker_stop = add_worker_control_parser(
        "worker-stop", "stop a remaining legacy worker process"
    )
    worker_stop.add_argument("--graceful-timeout-seconds", type=float, default=5.0)
    worker_stop.add_argument(
        "--no-force",
        action="store_false",
        dest="force",
        help="request a graceful stop without the identity-checked force fallback",
    )
    worker_stop.set_defaults(force=True)

    uninstall = subparsers.add_parser(
        "uninstall-startup", help="remove the Windows logon task"
    )
    uninstall.add_argument("--task-name", default=DEFAULT_TASK_NAME)

    startup = subparsers.add_parser(
        "startup-status", help="show Windows logon task status"
    )
    startup.add_argument("--task-name", default=DEFAULT_TASK_NAME)

    activation = subparsers.add_parser(
        "activation",
        help="preview/apply/rollback cohort-epoch activation (FC-203)",
    )
    activation_sub = activation.add_subparsers(dest="activation_action", required=True)
    act_preview = activation_sub.add_parser(
        "preview", help="read-only: which assertions would flip"
    )
    act_preview.add_argument(
        "--assertion-ids", required=True, help="comma-separated assertion ids"
    )
    act_apply = activation_sub.add_parser(
        "apply", help="flip a batch to active inside one catalog transaction"
    )
    act_apply.add_argument("--epoch", required=True)
    act_apply.add_argument("--cohort", required=True)
    act_apply.add_argument(
        "--assertion-ids", required=True, help="comma-separated assertion ids"
    )
    act_apply.add_argument("--policy-hash", required=True)
    act_apply.add_argument("--reviewer", help="optional actor label; defaults to the process user")
    act_apply.add_argument("--reason", required=True)
    act_rollback = activation_sub.add_parser(
        "rollback", help="revert a prior apply inside one catalog transaction"
    )
    act_rollback.add_argument("--receipt-id", required=True)
    act_rollback.add_argument("--cohort", help="must match the apply receipt")
    act_rollback.add_argument("--reviewer", help="optional actor label; defaults to the process user")
    act_rollback.add_argument("--reason", required=True)

    runtime_policy = subparsers.add_parser(
        "runtime-policy",
        help="show or apply the persistent RuntimePolicySnapshot (FC-201)",
    )
    runtime_policy_sub = runtime_policy.add_subparsers(
        dest="policy_action", required=True
    )
    runtime_policy_sub.add_parser(
        "show", help="load and print the current snapshot (fails closed when absent)"
    )
    policy_apply = runtime_policy_sub.add_parser(
        "apply", help="compare-and-swap apply a new snapshot payload"
    )
    policy_apply.add_argument(
        "--file",
        type=Path,
        required=True,
        help="path to policy JSON (steady schema 2.0 or historical 1.0; snapshot_sha256 optional)",
    )
    # Compatibility names return a named retirement; they are absent from help.
    for command in RETIRED_MAINTENANCE_COMMANDS:
        subparsers.add_parser(command, help=argparse.SUPPRESS, add_help=False)
    subparsers._choices_actions = [
        action for action in subparsers._choices_actions
        if action.dest not in RETIRED_MAINTENANCE_COMMANDS
    ]
    subparsers.metavar = '{' + ','.join(
        name for name in subparsers.choices if name not in RETIRED_MAINTENANCE_COMMANDS
    ) + '}'
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


def _read_only_ensure_result(resolution: ResolutionResult) -> dict[str, Any]:
    """Render an ``ensure``-compatible envelope without a write attempt.

    An exact request without ``--allow-download`` cannot stage, import, or
    journal anything. Keeping it on the reader avoids forcing a writable
    catalog merely to report a reusable or missing source.
    """
    if resolution.status in {
        ResolutionStatus.REUSED_EXACT,
        ResolutionStatus.REUSED_EQUIVALENT,
    }:
        ensure_status = SourceEnsureStatus.REUSED
        acquisition_status = AcquisitionStatus.REUSED
        reason = "existing_catalog_source_reused_before_adapter"
    elif resolution.status is ResolutionStatus.AMBIGUOUS:
        ensure_status = SourceEnsureStatus.AMBIGUOUS
        acquisition_status = AcquisitionStatus.AMBIGUOUS
        reason = resolution.reason
    else:
        ensure_status = SourceEnsureStatus.MISSING
        acquisition_status = AcquisitionStatus.MISSING
        reason = (
            "identity_conflict_no_download"
            if resolution.status is ResolutionStatus.IDENTITY_CONFLICT
            else "download_required_but_not_allowed"
        )
    return SourceEnsureResult(
        schema_version=SOURCE_ENSURE_SCHEMA_VERSION,
        status=ensure_status,
        acquisition=AcquisitionResult(
            schema_version=ACQUISITION_SCHEMA_VERSION,
            status=acquisition_status,
            resolution=resolution,
            reason=reason,
        ),
        resolution=resolution,
        attempt=None,
    ).to_dict()


def _acquisition_budget_from_args(
    args: argparse.Namespace,
    *,
    required: bool,
) -> Any:
    from .download_budget import AcquisitionBudget

    values = (
        getattr(args, "max_download_bytes", None),
        getattr(args, "max_download_seconds", None),
        getattr(args, "max_download_cost_usd", None),
    )
    supplied = tuple(value is not None for value in values)
    if not any(supplied):
        if required:
            raise ValueError(
                "bounded provider access requires --max-download-bytes, "
                "--max-download-seconds, and --max-download-cost-usd"
            )
        return None
    if not all(supplied):
        raise ValueError(
            "the three --max-download-* limits must be supplied together"
        )
    max_bytes, max_seconds, max_cost_usd = values
    return AcquisitionBudget.from_limits(
        max_response_bytes=max_bytes,
        max_seconds=max_seconds,
        max_cost_usd=max_cost_usd,
    )


def _acquisition_binding_from_args(args, request, budget, project_root):
    """Read optional legacy target/cap data shared by both CLI wrappers."""
    from .close_gap import CloseGapBinding

    binding_path = args.binding_file
    if binding_path is None:
        return None
    if not binding_path.is_absolute():
        binding_path = project_root / binding_path
    payload = json.loads(binding_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("acquisition scope must be a JSON object")
    accessions = payload.get("allowed_accessions")
    if not isinstance(accessions, list):
        raise ValueError("allowed_accessions must be an array")
    return CloseGapBinding(
        request_id=str(payload.get("request_id", request.request_id)),
        gap_plan_hash=str(payload.get("gap_plan_hash", "")),
        policy_hash=str(payload.get("policy_hash", "")),
        provider=payload["provider"], allowed_accessions=tuple(accessions),
        max_items=payload.get("max_items", 1),
        max_bytes=payload.get("max_bytes", budget.max_response_bytes),
        expires_at=str(payload.get("expires_at", "")),
    )


def _run_ensure_command(
    args: argparse.Namespace,
    config: Any,
    project_root: Path,
    get_catalog: Any,
    source_request: Any,
) -> dict[str, Any]:
    """Execute the read-only or acquisition-capable ``ensure`` command."""
    request, identity = source_request(allow_download=args.allow_download)
    budget = _acquisition_budget_from_args(
        args,
        required=args.allow_download or request.mode == "latest_as_of",
    )
    if args.binding_file is not None and not args.allow_download:
        raise ValueError("download target scope requires an explicit download operation")
    binding = _acquisition_binding_from_args(args, request, budget, project_root)
    candidate_scope = binding.restrict(budget) if binding is not None else None
    if not args.allow_download and request.mode != "latest_as_of":
        result = _read_only_ensure_result(SourceResolver(get_catalog()).resolve(request))
        return (
            {"identity": identity.to_dict(), "source_ensure": result}
            if identity
            else result
        )

    # Download-capable and latest-as-of ensure remain write flows: the writer
    # initializer may create the catalog before staging.
    _ = get_catalog().store
    acquisition_config_path = args.acquisition_config
    if not acquisition_config_path.is_absolute():
        acquisition_config_path = project_root / acquisition_config_path
    acquisition_config = load_acquisition_config(
        acquisition_config_path.resolve(strict=True), project_root=project_root
    )
    from .acquisition_journal import AcquisitionJournal
    from .resolver import build_resolution_envelope

    ensured = _retry_on_catalog_lock(
        lambda: SourceAcquisitionService(
            coordinator=AcquisitionCoordinator(
                catalog=get_catalog(),
                adapters=acquisition_config.build_registry(),
                staging_root=acquisition_config.staging_root,
            ),
            writer=CanonicalSourceWriter(
                get_catalog(), staging_root=acquisition_config.staging_root
            ),
            journal=AcquisitionJournal(config.catalog_dir),
        ).ensure(request, budget=budget, candidate_scope=candidate_scope),
        action="ensure",
    )

    ensure_policy = None  # Current source operations use steady facts, not rollout permissions.
    ensure_dict = _plain(ensured)
    resolution_dict = ensure_dict.get("resolution")
    if isinstance(resolution_dict, dict):
        resolution_dict["policy_export"] = _policy_export_payload(config)
        resolution_dict["source_read_policy_sha256"] = source_read_policy_sha256(
            config, ensure_policy
        )
        resolution_dict["resolution_envelope"] = build_resolution_envelope(
            ensured.resolution,
            policy_snapshot={"policy_hash": resolution_dict["policy_export"]["policy_hash"]},
            journal=AcquisitionJournal(config.catalog_dir),
            bundle=get_catalog().bundle_for_resolution(ensured.resolution),
            store=get_catalog().store,
            project_root=project_root,
        ).to_dict()
    return (
        {"identity": identity.to_dict(), "source_ensure": ensure_dict}
        if identity
        else ensure_dict
    )


def _run_export_command(command: str, config, get_catalog) -> dict[str, Any]:
    """ZR-405: the ``export``/``policy-export`` dispatch (kept in a helper
    so main()'s branch count stays under the frozen ratchet)."""
    if command == "policy-export":
        return _policy_export_payload(config)
    return get_catalog().export_indexes()


def _policy_export_payload(config) -> dict[str, Any]:
    """ZR-405: the root policy export payload (policy_hash + roots),
    shared by the ``policy-export`` command and the resolve/ensure response
    bodies so consumers validate containment against exactly what the wiki
    exports.

    The payload is the verbatim ``export_policy_2x`` document plus its
    canonical hash: consumers re-compute the hash over the SAME bytes
    (excluding the ``policy_hash`` envelope key) — tokenizing or reshaping
    the roots here would break the byte-for-byte hash contract.  Paths are
    absolute by construction (the wiki->filing channel is a local
    subprocess; the RESOLUTION ENVELOPE carries the redacted copies for
    any external output).
    """
    from .policy_2x import export_policy_2x

    policy_hash, policy = export_policy_2x(config)
    return {
        "schema_version": policy["schema_version"],
        "policy_hash": policy_hash,
        "reusable_root_kinds": list(policy["reusable_root_kinds"]),
        "roots": policy["roots"],
    }


def main(argv: Sequence[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    parser = _parser()
    args, unknown = parser.parse_known_args(argv)
    if args.command in RETIRED_MAINTENANCE_COMMANDS:
        error = RetiredMaintenanceError(args.command)
        print(json.dumps({
            'status': 'failed', 'error_type': 'maintenance_operation_retired',
            'error_code': error.code, 'operation': error.operation,
            'error': str(error), 'retryable': False,
        }, ensure_ascii=False), file=sys.stderr)
        return 1
    if unknown:
        parser.error('unrecognized arguments: ' + ' '.join(unknown))
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
            mode=getattr(args, "mode", None),
            allow_download=allow_download,
        )
        return request, identity

    try:
        if args.command == "scan":
            result: Any = get_catalog().scan(
                dry_run=args.dry_run,
                root_ids=set(args.root_id) if args.root_id else None,
            )
        elif args.command == "register":
            result = get_catalog().register_sources(
                root_id=args.root_id, relative_paths=set(args.relative_path),
            )
        elif args.command == "source-facts":
            from .source_reader import SourceRef

            with args.request.open("rb") as source_facts_stream:
                payload = source_facts_stream.read(131073)
            if len(payload) > 131072:
                raise ValueError("source facts request exceeds byte limit")
            request_object = json.loads(payload.decode("utf-8"))
            if not isinstance(request_object, dict) or set(request_object) != {"source_ref", "facts", "evidence"}:
                raise ValueError("source facts request fields differ")
            result = get_catalog().record_source_facts(
                ref=SourceRef(**request_object["source_ref"]), facts=request_object["facts"],
                evidence=request_object["evidence"],
            )
        elif args.command == "fingerprint-backfill":
            result = get_catalog().backfill_text_fingerprints(limit=args.limit)
        elif args.command in ("export", "policy-export"):
            result = _run_export_command(args.command, config, get_catalog)
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
        elif args.command == "reconcile-retire":
            result = ReconcileRetireStateService(get_catalog().config).reconcile(
                apply=args.apply
            )
        elif args.command == "size-report":
            from .catalog_size_report import catalog_size_report

            result = catalog_size_report(config.database_path)
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
        elif args.command == "resolve":
            from .acquisition_journal import AcquisitionJournal
            from .resolver import build_resolution_envelope
            request, identity = source_request()
            policy = None  # Legacy runtime snapshots require an explicit compatibility caller.
            resolution = SourceResolver(get_catalog(), runtime_policy=policy).resolve(
                request
            )
            source_resolution = resolution.to_dict()
            # ZR-405: the response carries the root policy export so the
            # filing consumer can validate handle containment against the
            # SAME policy the wiki exported (no independent allowlist).
            source_resolution["policy_export"] = _policy_export_payload(config)
            source_resolution["source_read_policy_sha256"] = source_read_policy_sha256(
                config, policy
            )
            # FC-704: journal-reconciled outcome + policy/epoch + bundle
            # status ride on the resolution (read-only: the journal is read,
            # never appended, by the resolve command).
            # FC-902: the snapshot-consistent SourceBundle rides too when a
            # document was reused (SELECT-only; fail-closed on hash drift).
            source_resolution["resolution_envelope"] = build_resolution_envelope(
                resolution,
                policy_snapshot={"policy_hash": source_resolution["policy_export"]["policy_hash"]},
                journal=AcquisitionJournal(config.catalog_dir),
                bundle=get_catalog().bundle_for_resolution(resolution),
                store=get_catalog().reader,
                project_root=project_root,
            ).to_dict()
            result = (
                {"identity": identity.to_dict(), "source_resolution": source_resolution}
                if identity
                else source_resolution
            )
        elif args.command == "ensure":
            result = _run_ensure_command(
                args,
                config,
                project_root,
                get_catalog,
                source_request,
            )
        elif args.command == "close-gap":
            from .acquisition_journal import AcquisitionJournal
            from .close_gap import CloseGapTransaction

            request, identity = source_request()
            budget = _acquisition_budget_from_args(args, required=True)
            binding = _acquisition_binding_from_args(args, request, budget, project_root)
            # Only the actual acquisition writer initializes the catalog.
            _ = get_catalog().store
            acquisition_config_path = args.acquisition_config
            if not acquisition_config_path.is_absolute():
                acquisition_config_path = project_root / acquisition_config_path
            acquisition_config = load_acquisition_config(
                acquisition_config_path.resolve(strict=True),
                project_root=project_root,
            )
            closed = _retry_on_catalog_lock(
                lambda: CloseGapTransaction(
                    catalog=get_catalog(),
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
                ).execute(binding, request, budget=budget),
                action="close-gap",
            )
            result = (
                {"identity": identity.to_dict(), "close_gap": closed.to_dict()}
                if identity
                else closed.to_dict()
            )
        elif args.command == "activation":
            from .activation import (
                apply_activation,
                preview_activation,
                rollback_activation,
            )

            store = get_catalog().store
            if args.activation_action == "preview":
                result = preview_activation(
                    store,
                    assertion_ids=tuple(
                        item.strip()
                        for item in args.assertion_ids.split(",")
                        if item.strip()
                    ),
                )
            elif args.activation_action == "apply":
                from .policy import export_policy

                policy_hash, _ = export_policy(config)
                result = apply_activation(
                    store,
                    epoch=args.epoch,
                    cohort=args.cohort,
                    assertion_ids=tuple(
                        item.strip()
                        for item in args.assertion_ids.split(",")
                        if item.strip()
                    ),
                    policy_hash=args.policy_hash,
                    reviewer=args.reviewer,
                    reason=args.reason,
                    current_policy_hash=policy_hash,
                )
            else:  # rollback
                result = rollback_activation(
                    store,
                    receipt_id=args.receipt_id,
                    cohort=args.cohort,
                    reviewer=args.reviewer,
                    reason=args.reason,
                )
        elif args.command == "runtime-policy":
            from .runtime_policy import (
                RuntimePolicyError,
                build_snapshot,
                load_runtime_policy,
                save_runtime_policy_cas,
            )

            policy_path = config.catalog_dir / "runtime_policy.json"
            if args.policy_action == "show":
                result = load_runtime_policy(policy_path)
            else:  # apply
                payload_path = args.file
                if not payload_path.is_absolute():
                    payload_path = project_root / payload_path
                payload = json.loads(payload_path.read_text(encoding="utf-8"))
                built = build_snapshot(payload)
                try:
                    current = load_runtime_policy(policy_path)
                    expected = current["snapshot_sha256"]
                except RuntimePolicyError:
                    expected = None  # first write
                new_hash = save_runtime_policy_cas(
                    policy_path, built, expected_hash=expected
                )
                result = {
                    "applied": True,
                    "snapshot_sha256": new_hash,
                    "path": str(policy_path),
                }
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
        elif args.command == "worker-stop":
            result = worker_controller().stop(
                graceful_timeout_seconds=args.graceful_timeout_seconds,
                force=args.force,
            )
        elif args.command == "uninstall-startup":
            result = uninstall_startup_task(task_name=args.task_name)
        elif args.command == "startup-status":
            result = startup_task_status(task_name=args.task_name)
        else:  # pragma: no cover - argparse requires a registered command
            raise RuntimeError(f"unsupported source-catalog command: {args.command}")
    except Exception as exc:
        # ZR-204: unified error taxonomy — canonical code + retryable flag.
        from .error_taxonomy import structured_error

        print(
            json.dumps(structured_error(exc), ensure_ascii=False, sort_keys=True),
            file=sys.stderr,
        )
        return 1
    if getattr(args, "source_ref_v2", False):
        try:
            from .source_operation import project_operation_result
            from .source_reader import SourceVersionReader
            result = project_operation_result(
                result, operation=args.command,
                reader=SourceVersionReader(get_catalog()),
            )
        except Exception as exc:
            from .error_taxonomy import structured_error

            print(
                json.dumps(structured_error(exc), ensure_ascii=False, sort_keys=True),
                file=sys.stderr,
            )
            return 1
    print(json.dumps(_plain(result), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["main"]
