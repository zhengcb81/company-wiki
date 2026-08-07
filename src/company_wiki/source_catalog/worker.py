"""Periodic scanner and low-priority, single-document processing worker."""

from __future__ import annotations

import ctypes
from dataclasses import dataclass
from datetime import datetime
import json
import os
from pathlib import Path
import subprocess
import time
from typing import Any, Callable

import yaml

from .code_identity import source_bundle_fingerprint
from .normalizer import DOCUMENT_PARSE_TIMEOUT_CODE
from .scheduler_policy import SourceOnlySchedulerPolicy, SourceOnlyStage


@dataclass(frozen=True)
class WorkerConfig:
    runtime_config: Path
    scan_interval_seconds: int
    export_interval_seconds: int
    poll_interval_seconds: int
    idle_seconds_required: int
    normalize_batch_size: int
    llm_summary_batch_size: int
    llm_max_input_chars: int
    llm_max_output_tokens: int
    llm_retry_backoff_seconds: int
    allow_processing_on_battery: bool
    require_user_idle: bool = False
    active_poll_interval_seconds: int | None = None
    dirty_export_threshold: int = 5
    scan_retry_backoff_max: int = 3600
    normalize_before_scan_when_pending: bool = True
    scan_defer_threshold: int = 5
    # CW-2.28 §12.4.3.6 fingerprint backfill controls
    fingerprint_backfill_batch_size: int = 3
    fingerprint_retry_limit: int = 3
    fingerprint_retry_backoff_seconds: int = 900
    document_parse_timeout_seconds: int = 3600
    parser_heartbeat_interval_seconds: int = 15
    parser_result_max_bytes: int = 268_435_456
    normalization_retry_limit: int = 3
    normalization_retry_backoff_seconds: int = 900
    # Phase 4: section extraction (MD&A / business) batch size
    section_extraction_batch_size: int = 5
    # Phase 2.3: weekly retained-evidence prune (90-day retention default)
    prune_retention_days: int = 90
    prune_check_interval_seconds: int = 604800

    def __post_init__(self) -> None:
        if not isinstance(self.runtime_config, Path):
            raise TypeError("runtime_config must be pathlib.Path")
        if self.active_poll_interval_seconds is None:
            object.__setattr__(
                self, "active_poll_interval_seconds", self.poll_interval_seconds
            )
        for field_name in (
            "scan_interval_seconds",
            "export_interval_seconds",
            "poll_interval_seconds",
            "active_poll_interval_seconds",
            "idle_seconds_required",
            "normalize_batch_size",
            "llm_summary_batch_size",
            "llm_max_input_chars",
            "llm_max_output_tokens",
            "llm_retry_backoff_seconds",
            "fingerprint_backfill_batch_size",
            "fingerprint_retry_limit",
            "fingerprint_retry_backoff_seconds",
            "document_parse_timeout_seconds",
            "parser_heartbeat_interval_seconds",
            "parser_result_max_bytes",
            "normalization_retry_limit",
            "normalization_retry_backoff_seconds",
            "section_extraction_batch_size",
            "prune_retention_days",
            "prune_check_interval_seconds",
        ):
            value = getattr(self, field_name)
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ValueError(f"{field_name} must be a positive integer")
        if not 60 <= self.document_parse_timeout_seconds <= 21_600:
            raise ValueError("document_parse_timeout_seconds must be between 60 and 21600")
        if not 1 <= self.parser_heartbeat_interval_seconds <= 300:
            raise ValueError("parser_heartbeat_interval_seconds must be between 1 and 300")
        if self.parser_heartbeat_interval_seconds >= self.document_parse_timeout_seconds:
            raise ValueError(
                "parser_heartbeat_interval_seconds must be less than document_parse_timeout_seconds"
            )
        if not 1_048_576 <= self.parser_result_max_bytes <= 536_870_912:
            raise ValueError(
                "parser_result_max_bytes must be between 1048576 and 536870912"
            )
        for field_name in ("allow_processing_on_battery", "require_user_idle"):
            if not isinstance(getattr(self, field_name), bool):
                raise TypeError(f"{field_name} must be a boolean")


def _code_version(project_root: Path) -> str:
    """Short git commit of the code the worker process loaded (Phase 16.3).
    Falls back to 'unknown' when git is unavailable."""
    try:
        result = subprocess.run(
            ["git", "-C", str(project_root), "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass
    return "unknown"


def _resolve(value: Any, *, project_root: Path) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("runtime_config must be non-empty text")
    expanded = value.replace("${PROJECT_ROOT}", str(project_root))
    if "${" in expanded:
        raise ValueError("runtime_config contains an unsupported path token")
    path = Path(expanded).expanduser()
    if not path.is_absolute():
        path = project_root / path
    return path.resolve(strict=False)


def load_worker_config(path: Path, *, project_root: Path) -> WorkerConfig:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("worker config must be an object")
    base_expected = {
        "schema_version",
        "runtime_config",
        "scan_interval_minutes",
        "export_interval_minutes",
        "poll_interval_seconds",
        "idle_seconds_required",
        "normalize_batch_size",
        "llm_summary_batch_size",
        "llm_max_input_chars",
        "llm_max_output_tokens",
        "llm_retry_backoff_minutes",
        "allow_processing_on_battery",
    }
    schema_version = str(payload.get("schema_version"))
    optional: set[str] = set()
    if schema_version == "1.0":
        expected = base_expected
        require_user_idle = True
        active_poll_interval_seconds = payload["poll_interval_seconds"]
    elif schema_version == "1.1":
        expected = base_expected | {"require_user_idle"}
        require_user_idle = payload.get("require_user_idle")
        if not isinstance(require_user_idle, bool):
            raise ValueError("require_user_idle must be a boolean")
        active_poll_interval_seconds = payload["poll_interval_seconds"]
    elif schema_version in {"1.2", "1.3"}:
        expected = base_expected | {
            "require_user_idle",
            "active_poll_interval_seconds",
            "fingerprint_backfill_batch_size",
            "fingerprint_retry_limit",
            "fingerprint_retry_backoff_seconds",
        }
        if schema_version == "1.3":
            expected |= {
                "document_parse_timeout_seconds",
                "parser_heartbeat_interval_seconds",
                "parser_result_max_bytes",
                "normalization_retry_limit",
                "normalization_retry_backoff_seconds",
            }
        optional = {
            "normalize_before_scan_when_pending",
            "scan_defer_threshold",
            "section_extraction_batch_size",
            "prune_retention_days",
            "prune_check_interval_seconds",
        }
        require_user_idle = payload.get("require_user_idle")
        if not isinstance(require_user_idle, bool):
            raise ValueError("require_user_idle must be a boolean")
        active_poll_interval_seconds = payload.get("active_poll_interval_seconds")
    else:
        raise ValueError("worker schema_version must be 1.0, 1.1, 1.2, or 1.3")
    present = set(payload)
    if present - expected - optional:
        raise ValueError(
            f"worker config contains unknown fields: {sorted(present - expected - optional)}"
        )
    missing = expected - present
    if missing:
        raise ValueError(f"worker config is missing required fields: {sorted(missing)}")
    allow_processing_on_battery = payload["allow_processing_on_battery"]
    if not isinstance(allow_processing_on_battery, bool):
        raise ValueError("allow_processing_on_battery must be a boolean")
    return WorkerConfig(
        runtime_config=_resolve(payload["runtime_config"], project_root=project_root),
        scan_interval_seconds=int(payload["scan_interval_minutes"]) * 60,
        export_interval_seconds=int(payload["export_interval_minutes"]) * 60,
        poll_interval_seconds=int(payload["poll_interval_seconds"]),
        idle_seconds_required=int(payload["idle_seconds_required"]),
        normalize_batch_size=int(payload["normalize_batch_size"]),
        llm_summary_batch_size=int(payload["llm_summary_batch_size"]),
        llm_max_input_chars=int(payload["llm_max_input_chars"]),
        llm_max_output_tokens=int(payload["llm_max_output_tokens"]),
        llm_retry_backoff_seconds=int(payload["llm_retry_backoff_minutes"]) * 60,
        allow_processing_on_battery=allow_processing_on_battery,
        require_user_idle=require_user_idle,
        active_poll_interval_seconds=int(active_poll_interval_seconds),
        dirty_export_threshold=(
            max(
                int(payload["normalize_batch_size"]),
                int(payload["llm_summary_batch_size"]),
            )
            * 5
        ),
        fingerprint_backfill_batch_size=int(
            payload.get("fingerprint_backfill_batch_size", 3)
        ),
        fingerprint_retry_limit=int(payload.get("fingerprint_retry_limit", 3)),
        fingerprint_retry_backoff_seconds=int(
            payload.get("fingerprint_retry_backoff_seconds", 900)
        ),
        normalize_before_scan_when_pending=payload.get(
            "normalize_before_scan_when_pending", True
        ),
        scan_defer_threshold=int(payload.get("scan_defer_threshold", 5)),
        document_parse_timeout_seconds=int(
            payload.get("document_parse_timeout_seconds", 3600)
        ),
        parser_heartbeat_interval_seconds=int(
            payload.get("parser_heartbeat_interval_seconds", 15)
        ),
        parser_result_max_bytes=int(
            payload.get("parser_result_max_bytes", 268_435_456)
        ),
        normalization_retry_limit=int(payload.get("normalization_retry_limit", 3)),
        normalization_retry_backoff_seconds=int(
            payload.get("normalization_retry_backoff_seconds", 900)
        ),
        section_extraction_batch_size=int(
            payload.get("section_extraction_batch_size", 5)
        ),
        prune_retention_days=int(payload.get("prune_retention_days", 90)),
        prune_check_interval_seconds=int(
            payload.get("prune_check_interval_seconds", 604800)
        ),
    )


class SystemIdleDetector:
    """Read Windows last-input and AC state without installing another dependency."""

    def idle_seconds(self) -> float:
        if os.name != "nt":
            return 0.0

        class LastInputInfo(ctypes.Structure):
            _fields_ = (("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint32))

        info = LastInputInfo()
        info.cbSize = ctypes.sizeof(info)
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        user32.GetLastInputInfo.argtypes = (ctypes.POINTER(LastInputInfo),)
        user32.GetLastInputInfo.restype = ctypes.c_int
        kernel32.GetTickCount.restype = ctypes.c_uint32
        if not user32.GetLastInputInfo(ctypes.byref(info)):
            return 0.0
        elapsed_ms = (int(kernel32.GetTickCount()) - int(info.dwTime)) & 0xFFFFFFFF
        return elapsed_ms / 1000.0

    def on_battery(self) -> bool:
        if os.name != "nt":
            return False

        class SystemPowerStatus(ctypes.Structure):
            _fields_ = (
                ("ACLineStatus", ctypes.c_ubyte),
                ("BatteryFlag", ctypes.c_ubyte),
                ("BatteryLifePercent", ctypes.c_ubyte),
                ("SystemStatusFlag", ctypes.c_ubyte),
                ("BatteryLifeTime", ctypes.c_uint32),
                ("BatteryFullLifeTime", ctypes.c_uint32),
            )

        status = SystemPowerStatus()
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        if not kernel32.GetSystemPowerStatus(ctypes.byref(status)):
            return False
        return status.ACLineStatus == 0


def set_low_process_priority() -> None:
    """Best-effort lower scheduling priority; failure must not stop the worker."""
    try:
        if os.name == "nt":
            from ctypes import wintypes

            idle_priority_class = 0x00000040
            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            kernel32.GetCurrentProcess.argtypes = []
            kernel32.GetCurrentProcess.restype = wintypes.HANDLE
            kernel32.SetPriorityClass.argtypes = [wintypes.HANDLE, wintypes.DWORD]
            kernel32.SetPriorityClass.restype = wintypes.BOOL
            kernel32.SetPriorityClass(kernel32.GetCurrentProcess(), idle_priority_class)
        elif hasattr(os, "nice"):
            os.nice(10)
    except (OSError, ValueError):
        return


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


class SourceCatalogWorker:
    def __init__(
        self,
        catalog: Any,
        config: WorkerConfig,
        *,
        state_path: Path,
        project_root: Path | None = None,
        idle_detector: Any | None = None,
        llm_client_factory: Callable[[], Any],
        sleep: Callable[[float], None] = time.sleep,
        scheduler_policy: SourceOnlySchedulerPolicy | None = None,
    ):
        self.catalog = catalog
        self.config = config
        self.state_path = state_path
        # Phase 16.10: project_root is injected by the caller (the CLI has it);
        # the catalog.config fallback only serves test doubles that omit it.
        self._project_root = project_root
        self.log_path = state_path.with_name("worker_runs.jsonl")
        self.idle_detector = idle_detector or SystemIdleDetector()
        self.llm_client_factory = llm_client_factory
        self.sleep = sleep
        self.scheduler_policy = scheduler_policy or SourceOnlySchedulerPolicy()
        self.state = self._load_state()

    def _load_state(self) -> dict[str, Any]:
        defaults: dict[str, Any] = {
            "schema_version": "1.0",
            "last_scan_at": None,
            "last_export_at": None,
            "last_export_duration_seconds": None,
            "last_export_progress_total": None,
            "last_export_progress_detail": None,
            "last_cycle_at": None,
            "last_cycle_status": None,
            "normalized_total": 0,
            "llm_summarized_total": 0,
            "dirty_since_last_export": 0,
            "last_error": None,
            "last_error_scope": None,
            "llm_retry_after": None,
            "last_scan_report": None,
            "last_normalize_report": None,
            "parse_timeout_total": 0,
            "last_parse_timeout_document_id": None,
            "last_parse_timeout_path": None,
            "last_llm_summary_report": None,
        }
        if not self.state_path.is_file():
            return defaults
        try:
            loaded = json.loads(self.state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return defaults
        if not isinstance(loaded, dict) or loaded.get("schema_version") != "1.0":
            return defaults
        state = {**defaults, **loaded}
        last_report = state.get("last_llm_summary_report")
        if (
            state.get("llm_retry_after") is not None
            and isinstance(last_report, dict)
            and "failure_scope" not in last_report
        ):
            # Pre-scope releases treated every document-quality failure as global. Retry once
            # immediately so the upgraded classifier can persist the correct scope.
            state["llm_retry_after"] = None
        if (
            state.get("last_error_scope") is None
            and state.get("llm_retry_after") is not None
            and isinstance(last_report, dict)
            and last_report.get("failure_scope") == "global"
        ):
            state["last_error_scope"] = "llm_global"
        return state

    def _write_state(self) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.state_path.with_name(
            self.state_path.name + f".{os.getpid()}.tmp"
        )
        try:
            temporary.write_text(
                json.dumps(self.state, ensure_ascii=False, sort_keys=True) + "\n",
                encoding="utf-8",
                newline="\n",
            )
            os.replace(temporary, self.state_path)
        finally:
            temporary.unlink(missing_ok=True)

    def _append_log(self, payload: dict[str, Any]) -> None:
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        with self.log_path.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(
                json.dumps(_plain(payload), ensure_ascii=False, sort_keys=True) + "\n"
            )

    @staticmethod
    def _processed_count(report: Any) -> int:
        return (
            int(getattr(report, "completed", 0))
            + int(getattr(report, "partial", 0))
            + int(getattr(report, "unsupported", 0))
        )

    def run_cycle(
        self,
        *,
        now: float | None = None,
        activity: Callable[..., None] | None = None,
        should_stop: Callable[[], bool] | None = None,
    ) -> dict[str, Any]:
        timestamp = time.time() if now is None else float(now)
        result: dict[str, Any] = {
            "timestamp": timestamp,
            "scan": None,
            "normalize": None,
            "summarize_llm": None,
            "export": None,
            "work_order": [],
            "background_processing": False,
            "processing_blocked_reason": None,
            "user_idle_required": self.config.require_user_idle,
            "idle_processing": False,
            "idle_seconds": None,
            "on_battery": False,
        }
        work_order: list[str] = []

        def _record_work(stage_name: str) -> None:
            work_order.append(stage_name)
            result["work_order"] = work_order

        progress_last_emitted_at: dict[SourceOnlyStage, float] = {}

        def begin_stage(stage: SourceOnlyStage, *, detail: str | None = None) -> None:
            if activity is None:
                return
            activity(stage.value, progress_detail=detail)
            progress_last_emitted_at[stage] = time.monotonic()

        def report_progress(
            stage: SourceOnlyStage,
            *,
            current_path: str,
            current: int,
            total: int,
            detail: str | None = None,
            **extra: Any,
        ) -> None:
            if activity is None:
                return
            now_monotonic = time.monotonic()
            is_final = total > 0 and current >= total
            if (
                stage is SourceOnlyStage.SCANNING
                and not is_final
                and now_monotonic - progress_last_emitted_at.get(stage, 0.0) < 0.5
            ):
                return
            progress_last_emitted_at[stage] = now_monotonic
            percent = round(current * 100.0 / total, 1) if total > 0 else None
            activity(
                stage.value,
                current_path=current_path,
                progress_current=current,
                progress_total=total,
                progress_percent=percent,
                progress_detail=detail,
                **extra,
            )

        last_scan = self.state["last_scan_at"]
        scan_retry_after = self.state.get("scan_retry_after")
        scan_failed = self.state.get("last_scan_error") is not None
        scan_due = (
            last_scan is None
            or timestamp - float(last_scan) >= self.config.scan_interval_seconds
        )
        scan_backoff = scan_retry_after is not None and timestamp < float(
            scan_retry_after
        )
        # Defer scan when: we have pending Markdown, a prior completed scan exists,
        # and the policy prefers normalize-first.
        scan_deferred_by_policy = False
        if (
            self.config.normalize_before_scan_when_pending
            and not scan_due
            and scan_failed
            and scan_backoff
        ):
            scan_deferred_by_policy = True
        if scan_due and not scan_backoff and not scan_deferred_by_policy:
            scan_stage = self.scheduler_policy.require_dispatch(
                SourceOnlyStage.SCANNING, "scan"
            )
            begin_stage(scan_stage, detail="discovering and hashing source files")
            scan_start = time.monotonic()
            try:
                result["scan"] = self.catalog.scan(
                    progress=lambda **details: report_progress(scan_stage, **details)
                )
                _record_work("scan")
                scan_elapsed = time.monotonic() - scan_start
                self.state["last_scan_report"] = _plain(result["scan"])
                self.state["last_scan_at"] = timestamp
                self.state["last_scan_duration_seconds"] = round(scan_elapsed, 2)
                self.state["last_scan_error"] = None
                self.state["scan_retry_after"] = None
                self.state["scan_failures_consecutive"] = 0
                if hasattr(result["scan"], "files_seen"):
                    self.state["last_scan_stats"] = {
                        "files_seen": int(getattr(result["scan"], "files_seen", 0)),
                        "files_hashed": int(getattr(result["scan"], "files_hashed", 0)),
                        "files_reused": int(getattr(result["scan"], "files_reused", 0)),
                        "files_excluded": int(
                            getattr(result["scan"], "files_excluded", 0)
                        ),
                        "policy_excluded": int(
                            getattr(result["scan"], "policy_excluded", 0)
                        ),
                        "errors": int(getattr(result["scan"], "errors", 0)),
                        "duration_seconds": round(scan_elapsed, 2),
                    }
            except Exception as exc:
                scan_elapsed = time.monotonic() - scan_start
                consecutive = self.state.get("scan_failures_consecutive", 0) + 1
                backoff = min(
                    self.config.scan_interval_seconds * consecutive,
                    self.config.scan_retry_backoff_max,
                )
                self.state["last_scan_error"] = (
                    f"{type(exc).__name__}: {str(exc)[:500]}"
                )
                self.state["last_scan_attempt_at"] = timestamp
                self.state["scan_retry_after"] = timestamp + backoff
                self.state["scan_failures_consecutive"] = consecutive
                if consecutive >= self.config.scan_defer_threshold:
                    self.state["scan_deferred_due_to_repeated_failures"] = True
                self.state["last_scan_stats"] = {
                    "duration_seconds": round(scan_elapsed, 2),
                    "error": self.state["last_scan_error"],
                    "consecutive_failures": consecutive,
                }
                result["scan"] = {
                    "status": "failed",
                    "error": self.state["last_scan_error"],
                }
                _record_work("scan_failed")

        export_due = (
            self.state["last_export_at"] is None
            or timestamp - float(self.state["last_export_at"] or 0)
            >= self.config.export_interval_seconds
        )

        idle_seconds = None
        if self.config.require_user_idle:
            idle_seconds = float(self.idle_detector.idle_seconds())
        on_battery = bool(self.idle_detector.on_battery())
        result["idle_seconds"] = idle_seconds
        result["on_battery"] = on_battery
        input_eligible = (
            not self.config.require_user_idle
            or idle_seconds is not None
            and idle_seconds >= self.config.idle_seconds_required
        )
        power_eligible = self.config.allow_processing_on_battery or not on_battery
        eligible = input_eligible and power_eligible
        if not power_eligible:
            result["processing_blocked_reason"] = "on_battery"
        elif not input_eligible:
            result["processing_blocked_reason"] = "user_active"
        if eligible:
            result["background_processing"] = True
            result["idle_processing"] = True
            normalize_stage = self.scheduler_policy.require_dispatch(
                SourceOnlyStage.NORMALIZING, "normalize"
            )
            begin_stage(normalize_stage, detail="selecting next document")
            result["normalize"] = self.catalog.normalize(
                limit=self.config.normalize_batch_size,
                progress=lambda **details: report_progress(normalize_stage, **details),
                should_stop=should_stop or (lambda: False),
                parser_timeout_seconds=self.config.document_parse_timeout_seconds,
                parser_heartbeat_interval_seconds=(
                    self.config.parser_heartbeat_interval_seconds
                ),
                parser_result_max_bytes=self.config.parser_result_max_bytes,
                retry_limit=self.config.normalization_retry_limit,
                retry_backoff_seconds=(
                    self.config.normalization_retry_backoff_seconds
                ),
            )
            _record_work("normalize")
            self.state["last_normalize_report"] = _plain(result["normalize"])
            normalize_reasons = getattr(result["normalize"], "terminal_reasons", None)
            timeout_increment = (
                int(normalize_reasons.get(DOCUMENT_PARSE_TIMEOUT_CODE, 0))
                if isinstance(normalize_reasons, dict)
                else 0
            )
            if timeout_increment:
                self.state["parse_timeout_total"] = (
                    int(self.state.get("parse_timeout_total") or 0) + timeout_increment
                )
                self.state["last_parse_timeout_document_id"] = getattr(
                    result["normalize"], "last_failed_document_id", None
                )
                self.state["last_parse_timeout_path"] = getattr(
                    result["normalize"], "last_failed_path", None
                )
            normalized = self._processed_count(result["normalize"])
            self.state["normalized_total"] += normalized

            # CW-2.28 §12.4.3.7 — fingerprint backfill (after normalize, before LLM).
            fingerprint_stage = self.scheduler_policy.require_dispatch(
                SourceOnlyStage.FINGERPRINTING, "backfill_text_fingerprints"
            )
            begin_stage(fingerprint_stage, detail="selecting pending documents")
            result["fingerprint"] = self.catalog.backfill_text_fingerprints(
                limit=self.config.fingerprint_backfill_batch_size,
                progress=lambda **details: report_progress(
                    fingerprint_stage, **details
                ),
                should_stop=should_stop or (lambda: False),
                retry_limit=self.config.fingerprint_retry_limit,
                retry_backoff_seconds=self.config.fingerprint_retry_backoff_seconds,
                parser_timeout_seconds=self.config.document_parse_timeout_seconds,
                parser_heartbeat_interval_seconds=(
                    self.config.parser_heartbeat_interval_seconds
                ),
                parser_result_max_bytes=self.config.parser_result_max_bytes,
            )
            self.state["last_fingerprint_report"] = _plain(result["fingerprint"])
            _record_work("fingerprint")

            # Phase 4: extract MD&A / business sections from normalized filings.
            section_stage = self.scheduler_policy.require_dispatch(
                SourceOnlyStage.SECTION_EXTRACTING, "extract_sections"
            )
            begin_stage(section_stage, detail="selecting normalized documents")
            result["sections"] = self.catalog.extract_sections(
                limit=self.config.section_extraction_batch_size,
                progress=lambda **details: report_progress(section_stage, **details),
                should_stop=should_stop or (lambda: False),
            )
            self.state["last_sections_report"] = _plain(result["sections"])
            _record_work("section_extract")

            summarized = 0
            failed = 0
            failure_scope: str | None = None
            retry_after = self.state.get("llm_retry_after")
            if retry_after is None or timestamp >= float(retry_after):
                summarize_stage = self.scheduler_policy.require_dispatch(
                    SourceOnlyStage.SUMMARIZING, "summarize_with_llm"
                )
                begin_stage(summarize_stage, detail="selecting next Markdown document")
                try:
                    result["summarize_llm"] = self.catalog.summarize_with_llm(
                        limit=self.config.llm_summary_batch_size,
                        llm_client_factory=self.llm_client_factory,
                        max_input_chars=self.config.llm_max_input_chars,
                        max_output_tokens=self.config.llm_max_output_tokens,
                        retry_backoff_seconds=self.config.llm_retry_backoff_seconds,
                        progress=lambda **details: report_progress(
                            summarize_stage, **details
                        ),
                    )
                    summarized = int(getattr(result["summarize_llm"], "completed", 0))
                    failed = int(getattr(result["summarize_llm"], "failed", 0))
                    failure_scope = getattr(
                        result["summarize_llm"], "failure_scope", None
                    )
                    if failed:
                        self.state["last_error"] = str(
                            getattr(result["summarize_llm"], "error", None)
                            or "LLM summary batch failed"
                        )
                        self.state["last_error_scope"] = (
                            f"llm_{failure_scope or 'global'}"
                        )
                    if failure_scope == "permanent_document":
                        # Permanent error: never retry this document.
                        self.state["llm_retry_after"] = None
                    elif failed and failure_scope != "document":
                        self.state["llm_retry_after"] = (
                            timestamp + self.config.llm_retry_backoff_seconds
                        )
                    else:
                        self.state["llm_retry_after"] = None
                except Exception as exc:
                    result["summarize_llm"] = {
                        "status": "failed",
                        "error": f"{type(exc).__name__}: {str(exc)[:500]}",
                        "failure_scope": "global",
                    }
                    self.state["llm_retry_after"] = (
                        timestamp + self.config.llm_retry_backoff_seconds
                    )
                    self.state["last_error"] = result["summarize_llm"]["error"]
                    self.state["last_error_scope"] = "llm_global"
                self.state["last_llm_summary_report"] = _plain(result["summarize_llm"])
                _record_work("summarize")
            else:
                result["summarize_llm"] = {
                    "status": "deferred",
                    "retry_after": retry_after,
                }
            self.state["llm_summarized_total"] += summarized
            dirty = (
                normalized
                + summarized
                + (1 if (failed > 0 and failure_scope == "document") else 0)
            )
            self.state["dirty_since_last_export"] = (
                self.state.get("dirty_since_last_export", 0) + dirty
            )
            export_due = export_due or (
                self.state["dirty_since_last_export"]
                >= self.config.dirty_export_threshold
            )
        if scan_due or export_due:
            export_stage = self.scheduler_policy.require_dispatch(
                SourceOnlyStage.EXPORTING, "export_indexes"
            )
            begin_stage(export_stage, detail="updating read-only indexes")
            export_start = time.monotonic()

            def export_progress(**details: Any) -> None:
                total = details.get("total")
                self.state["last_export_progress_total"] = (
                    int(total) if total is not None else None
                )
                self.state["last_export_progress_detail"] = details.get("detail")
                report_progress(export_stage, **details)

            result["export"] = self.catalog.export_indexes(
                progress=export_progress
            )
            _record_work("export")
            self.state["last_export_at"] = timestamp
            self.state["last_export_duration_seconds"] = round(
                time.monotonic() - export_start,
                3,
            )
            self.state["dirty_since_last_export"] = 0
        # Phase 2.3: weekly retained-evidence prune check (90-day retention).
        # The worker is the durable "memory": it checks weekly and auto-recycles
        # once the oldest archive passes the retention window (the archive
        # protects evidence; not-due runs are no-ops).
        if timestamp - int(self.state.get("last_prune_check_at") or 0) >= (
            self.config.prune_check_interval_seconds
        ):
            self.state["last_prune_check_at"] = int(timestamp)
            try:
                from .prune_retired_evidence import prune_retired_evidence

                prune = prune_retired_evidence(
                    self.catalog.config,
                    self.project_root / "source_manifests",
                    apply=True,
                    retention_days=self.config.prune_retention_days,
                )
                self.state["last_prune_report"] = _plain(prune)
            except Exception as exc:
                self.state["last_prune_error"] = (
                    f"{type(exc).__name__}: {str(exc)[:500]}"
                )
        self.state["last_cycle_at"] = timestamp
        self.state["last_cycle_status"] = "completed"
        summary_result = result["summarize_llm"]
        if summary_result is not None:
            deferred_or_failed = isinstance(
                summary_result, dict
            ) and summary_result.get("status") in {"failed", "deferred"}
            report_failed = int(getattr(summary_result, "failed", 0)) > 0
            if not deferred_or_failed and not report_failed:
                self.state["last_error"] = None
                self.state["last_error_scope"] = None
            elif deferred_or_failed and isinstance(summary_result, dict):
                if summary_result.get("status") == "deferred":
                    last_report = self.state.get("last_llm_summary_report")
                    if (
                        self.state.get("llm_retry_after") is not None
                        and isinstance(last_report, dict)
                        and last_report.get("failure_scope") == "global"
                    ):
                        self.state["last_error"] = str(
                            last_report.get("error") or "LLM summary provider failure"
                        )
                        self.state["last_error_scope"] = "llm_global"
                    elif self.state.get("last_error_scope") in {None, "cycle"}:
                        self.state["last_error"] = None
                        self.state["last_error_scope"] = None
        elif self.state.get("last_error_scope") in {None, "cycle"}:
            last_report = self.state.get("last_llm_summary_report")
            retry_after = self.state.get("llm_retry_after")
            global_retry_active = bool(
                retry_after is not None
                and timestamp < float(retry_after)
                and isinstance(last_report, dict)
                and last_report.get("failure_scope") == "global"
            )
            if global_retry_active:
                self.state["last_error"] = str(
                    last_report.get("error") or "LLM summary provider failure"
                )
                self.state["last_error_scope"] = "llm_global"
            else:
                self.state["last_error"] = None
                self.state["last_error_scope"] = None
        self._write_state()
        self._append_log(result)
        return _plain(result)

    def _run_cycle_guarded(
        self,
        *,
        activity: Callable[..., None] | None = None,
        should_stop: Callable[[], bool] | None = None,
    ) -> dict[str, Any]:
        """Run one cycle while keeping scheduler failures non-fatal."""

        try:
            return self.run_cycle(activity=activity, should_stop=should_stop)
        except Exception as exc:
            self.state["last_cycle_at"] = time.time()
            self.state["last_cycle_status"] = "failed"
            self.state["last_error"] = f"{type(exc).__name__}: {str(exc)[:1000]}"
            self.state["last_error_scope"] = "cycle"
            result = {
                "timestamp": self.state["last_cycle_at"],
                "status": "failed",
                "error": self.state["last_error"],
            }
            self._write_state()
            self._append_log(result)
            return result

    def _next_wait_plan(self, cycle: dict[str, Any]) -> dict[str, Any]:
        """Choose the next delay without changing work eligibility or batch size."""

        normal_delay = self.config.poll_interval_seconds
        if cycle.get("status") == "failed":
            return {
                "productive": False,
                "seconds": normal_delay,
                "reason": "cycle_failed",
            }
        blocked_reason = cycle.get("processing_blocked_reason")
        if blocked_reason:
            return {
                "productive": False,
                "seconds": normal_delay,
                "reason": str(blocked_reason),
            }
        summary = cycle.get("summarize_llm")
        if isinstance(summary, dict):
            if summary.get("status") == "deferred":
                return {
                    "productive": False,
                    "seconds": normal_delay,
                    "reason": "llm_deferred",
                }
            failed = int(summary.get("failed") or 0)
            failure_scope = summary.get("failure_scope")
            if summary.get("status") == "failed" or (
                failed > 0 and failure_scope != "document"
            ):
                return {
                    "productive": False,
                    "seconds": normal_delay,
                    "reason": "llm_global_failure",
                }
        normalize = cycle.get("normalize")
        normalized = 0
        if isinstance(normalize, dict):
            normalized = sum(
                int(normalize.get(name) or 0)
                for name in ("completed", "partial", "unsupported")
            )
        summarized = (
            int(summary.get("completed") or 0) if isinstance(summary, dict) else 0
        )
        if normalized > 0 or summarized > 0:
            return {
                "productive": True,
                "seconds": self.config.active_poll_interval_seconds,
                "reason": "productive_cycle",
            }
        return {
            "productive": False,
            "seconds": normal_delay,
            "reason": "no_output",
        }

    def run_forever(
        self,
        *,
        control: Any | None = None,
        startup_delay_seconds: float = 0,
    ) -> dict[str, Any]:
        set_low_process_priority()
        self._write_process_event("process_starting")
        if control is None:
            try:
                while True:
                    cycle = self._run_cycle_guarded()
                    wait_plan = self._next_wait_plan(cycle)
                    self.sleep(wait_plan["seconds"])
            except BaseException as exc:  # noqa: BLE001 - re-raised after event
                self._write_unhandled_exception_event(exc)
                self._write_process_event(
                    "process_exiting", reason="unhandled_exception"
                )
                raise
            self._write_process_event("process_exiting", reason="clean_exit")
            return {"status": "exited"}

        # Use read_desired_state() if available so we do NOT trigger the
        # PowerShell process inventory before the session is even open. Fall
        # back to status().get("desired_state") only for legacy stubs.
        if hasattr(control, "read_desired_state"):
            desired = control.read_desired_state()
        else:
            desired = control.status().get("desired_state")
        if desired == "paused":
            self._write_process_event("process_exiting", reason="persistent_pause")
            return {"status": "paused", "reason": "persistent_pause"}
        try:
            session = control.open_session()
        except RuntimeError as exc:
            if "paused" in str(exc).lower():
                self._write_process_event(
                    "process_exiting", reason="persistent_pause"
                )
                return {"status": "paused", "reason": "persistent_pause"}
            self._write_unhandled_exception_event(exc)
            self._write_process_event(
                "process_exiting", reason="unhandled_exception"
            )
            raise
        self._write_process_event("session_opened")
        try:
            with session:
                project_root = self._project_root
                if project_root is None:
                    try:
                        project_root = self.catalog.config.project_root
                    except AttributeError:
                        project_root = None
                code_identity = (
                    source_bundle_fingerprint(project_root)
                    if project_root is not None
                    else {
                        "fingerprint": None,
                        "error": "project root unavailable",
                        "files": [],
                    }
                )
                session.heartbeat(
                    "starting",
                    code_version=(
                        _code_version(project_root)
                        if project_root is not None
                        else "unknown"
                    ),
                    loaded_code_fingerprint=code_identity["fingerprint"],
                    loaded_code_fingerprint_error=code_identity["error"],
                    loaded_code_files=code_identity["files"],
                )
                if startup_delay_seconds > 0 and not session.wait(
                    startup_delay_seconds
                ):
                    session.heartbeat("stopping")
                    self._write_process_event(
                        "process_exiting", reason="control_request"
                    )
                    return {"status": "stopped", "reason": "control_request"}
                while not session.should_stop():
                    session.heartbeat("running")
                    cycle = self._run_cycle_guarded(
                        activity=session.heartbeat,
                        should_stop=session.should_stop,
                    )
                    wait_plan = self._next_wait_plan(cycle)
                    next_wake_at = time.time() + float(wait_plan["seconds"])
                    session.heartbeat(
                        "waiting",
                        last_cycle_at=self.state.get("last_cycle_at"),
                        last_error=self.state.get("last_error"),
                        cycle_productive=wait_plan["productive"],
                        next_wait_seconds=wait_plan["seconds"],
                        next_wake_reason=wait_plan["reason"],
                        next_wake_at=next_wake_at,
                    )
                    if not session.wait(wait_plan["seconds"]):
                        break
                session.heartbeat("stopping")
                self._write_process_event(
                    "process_exiting", reason="control_request"
                )
                return {"status": "stopped", "reason": "control_request"}
        except BaseException as exc:  # noqa: BLE001 - re-raised after event
            self._write_unhandled_exception_event(exc)
            self._write_process_event(
                "process_exiting", reason="unhandled_exception"
            )
            raise
        return {"status": "stopped", "reason": "control_request"}

    def _write_unhandled_exception_event(self, exc: BaseException) -> None:
        """Record an unhandled exception without leaking full env / commands."""
        try:
            message = str(exc) or repr(exc)
        except Exception:  # pragma: no cover - defensive
            message = repr(exc)
        self._write_process_event(
            "unhandled_exception",
            exception_type=type(exc).__name__,
            message_redacted=message[:200],
        )

    def _write_process_event(self, event: str, **extra: Any) -> None:
        """Write a process lifecycle event for launcher diagnostics."""
        payload = {
            "event": event,
            "pid": os.getpid(),
            "timestamp": datetime.now().isoformat(),
            "catalog_dir": str(self.state_path.parent),
            **extra,
        }
        events_path = self.state_path.parent / "worker_process_events.jsonl"
        try:
            with open(events_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(payload) + "\n")
        except Exception:
            pass


__all__ = [
    "SourceCatalogWorker",
    "SystemIdleDetector",
    "WorkerConfig",
    "load_worker_config",
    "set_low_process_priority",
]
