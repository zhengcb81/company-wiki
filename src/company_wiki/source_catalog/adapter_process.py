"""Strict JSON subprocess bridge for isolated downloader environments."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
from typing import Any, Sequence

from .acquisition import DownloadCandidate, DownloadReceipt
from .download_budget import AcquisitionBudget
from .resolver import SourceRequest
from .store import canonical_json


class AdapterProcessError(RuntimeError):
    """Raised when an external adapter violates the JSON process contract.

    CW-2.27D: Carries machine-readable ``error_code`` / ``retryable`` /
    ``adapter_version`` parsed from the adapter's structured 1.0 error JSON
    on stderr. Legacy/unknown stderr degrades to::

      error_code = "adapter_process_failed"
      retryable = None
      adapter_version = None
    """

    error_code: str | None = None
    retryable: bool | None = None
    adapter_version: str | None = None
    acquisition_usage: dict[str, Any] | None = None

    def __init__(self, message: str = "") -> None:
        super().__init__(message)


def _parse_adapter_failure(
    detail: str,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """Return ``(error_obj, adapter_obj)`` parsed from the last stderr JSON line.

    Returns ``(None, None)`` if stderr is not one structured 1.0 error value.
    Conservative: never raises on malformed input.
    """
    if not detail:
        return None, None
    last_line = detail.splitlines()[-1].strip()
    if not last_line or not last_line.startswith("{"):
        return None, None
    try:
        payload = json.loads(last_line)
    except json.JSONDecodeError:
        return None, None
    if not isinstance(payload, dict):
        return None, None
    if payload.get("schema_version") != "1.0" or payload.get("status") != "failed":
        return None, None
    adapter_obj = payload.get("adapter")
    error_obj = payload.get("error")
    if not isinstance(adapter_obj, dict) or not isinstance(error_obj, dict):
        return None, None
    return error_obj, adapter_obj


class JsonCommandAdapter:
    """Run discovery/fetch in an external process without importing private code."""

    def __init__(
        self,
        *,
        name: str,
        version: str,
        command: Sequence[str],
        project_root: Path,
        timeout_seconds: float = 300.0,
        supports_acquisition_budget: bool = False,
    ):
        if not isinstance(name, str) or not name.strip():
            raise ValueError("name must be non-empty text")
        if not isinstance(version, str) or not version.strip():
            raise ValueError("version must be non-empty text")
        if isinstance(command, (str, bytes)) or not command:
            raise ValueError("command must be a non-empty string sequence")
        normalized = tuple(command)
        if not all(isinstance(item, str) and item.strip() for item in normalized):
            raise ValueError("command items must be non-empty strings")
        if not isinstance(project_root, Path):
            raise TypeError("project_root must be pathlib.Path")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if not isinstance(supports_acquisition_budget, bool):
            raise TypeError("supports_acquisition_budget must be bool")
        self.name = name
        self.version = version
        self.command = normalized
        self.project_root = project_root.resolve(strict=True)
        self.timeout_seconds = float(timeout_seconds)
        self.supports_acquisition_budget = supports_acquisition_budget

    def discover(self, request: SourceRequest) -> tuple[DownloadCandidate, ...]:
        if not isinstance(request, SourceRequest):
            raise TypeError("request must be SourceRequest")
        response = self._run("discover", request.to_dict())
        values = response.get("candidates")
        if not isinstance(values, list):
            raise AdapterProcessError("discover response candidates must be an array")
        return tuple(self._candidate(value, request) for value in values)

    def discover_bounded(
        self, request: SourceRequest, budget: AcquisitionBudget
    ) -> tuple[DownloadCandidate, ...]:
        """Run discovery with the caller's remaining shared egress budget."""
        if not isinstance(request, SourceRequest):
            raise TypeError("request must be SourceRequest")
        if not isinstance(budget, AcquisitionBudget):
            raise TypeError("budget must be AcquisitionBudget")
        self._ensure_bounded_support()
        payload, timeout_seconds = self._bounded_request(request.to_dict(), budget)
        try:
            response = self._run(
                "discover", payload, timeout_seconds=timeout_seconds
            )
        except AdapterProcessError as exc:
            self._charge_failure_usage(exc, budget)
            raise
        self._charge_bounded_usage(response, budget)
        values = response.get("candidates")
        if not isinstance(values, list):
            raise AdapterProcessError("discover response candidates must be an array")
        return tuple(self._candidate(value, request) for value in values)

    def fetch(
        self,
        candidate: DownloadCandidate,
        staging_dir: Path,
    ) -> DownloadReceipt:
        if not isinstance(candidate, DownloadCandidate):
            raise TypeError("candidate must be DownloadCandidate")
        if not isinstance(staging_dir, Path):
            raise TypeError("staging_dir must be pathlib.Path")
        staging_dir.mkdir(parents=True, exist_ok=True)
        allocated = staging_dir.resolve(strict=True)
        response = self._run(
            "fetch",
            candidate.to_dict(),
            extra_args=("--staging-dir", str(allocated)),
        )
        value = response.get("receipt")
        if not isinstance(value, dict):
            raise AdapterProcessError("fetch response receipt must be an object")
        return self._receipt(value)

    def fetch_bounded(
        self,
        candidate: DownloadCandidate,
        staging_dir: Path,
        budget: AcquisitionBudget,
    ) -> DownloadReceipt:
        """Fetch through a budget-aware CLI and account its network usage."""
        if not isinstance(candidate, DownloadCandidate):
            raise TypeError("candidate must be DownloadCandidate")
        if not isinstance(staging_dir, Path):
            raise TypeError("staging_dir must be pathlib.Path")
        if not isinstance(budget, AcquisitionBudget):
            raise TypeError("budget must be AcquisitionBudget")
        self._ensure_bounded_support()
        staging_dir.mkdir(parents=True, exist_ok=True)
        allocated = staging_dir.resolve(strict=True)
        payload, timeout_seconds = self._bounded_request(candidate.to_dict(), budget)
        bytes_before_fetch = budget.response_bytes_used
        try:
            response = self._run(
                "fetch",
                payload,
                extra_args=("--staging-dir", str(allocated)),
                timeout_seconds=timeout_seconds,
            )
        except AdapterProcessError as exc:
            self._charge_failure_usage(exc, budget)
            raise
        self._charge_bounded_usage(response, budget)
        value = response.get("receipt")
        if not isinstance(value, dict):
            raise AdapterProcessError("fetch response receipt must be an object")
        receipt = self._receipt(value)
        if receipt.byte_size > budget.response_bytes_used - bytes_before_fetch:
            raise AdapterProcessError(
                "bounded adapter charged fewer response bytes than its staged receipt"
            )
        return receipt

    def _bounded_request(
        self, payload: dict[str, Any], budget: AcquisitionBudget
    ) -> tuple[dict[str, Any], float]:
        self._ensure_bounded_support()
        budget.ensure_open()
        timeout_seconds = min(self.timeout_seconds, budget.remaining_seconds)
        if timeout_seconds <= 0:
            budget.ensure_open()
        bounded = dict(payload)
        bounded["acquisition_budget"] = {
            "schema_version": "1.0",
            "max_response_bytes": budget.remaining_response_bytes,
            "timeout_seconds": timeout_seconds,
            "max_cost_usd": str(budget.remaining_cost_usd),
        }
        return bounded, timeout_seconds

    def _ensure_bounded_support(self) -> None:
        if not self.supports_acquisition_budget:
            raise AdapterProcessError(
                f"adapter {self.name} does not support bounded acquisition"
            )

    @staticmethod
    def _charge_bounded_usage(
        response: dict[str, Any], budget: AcquisitionBudget
    ) -> None:
        usage = response.get("acquisition_usage")
        if (
            not isinstance(usage, dict)
            or set(usage) != {"schema_version", "response_bytes", "cost_usd"}
            or usage.get("schema_version") != "1.0"
        ):
            raise AdapterProcessError(
                "bounded adapter acquisition_usage is missing or invalid"
            )
        response_bytes = usage.get("response_bytes")
        cost_usd = usage.get("cost_usd")
        if (
            isinstance(response_bytes, bool)
            or not isinstance(response_bytes, int)
            or response_bytes < 0
            or not isinstance(cost_usd, str)
        ):
            raise AdapterProcessError(
                "bounded adapter acquisition_usage values are invalid"
            )
        budget.consume_response_bytes(response_bytes)
        try:
            budget.consume_cost_usd(cost_usd)
        except (TypeError, ValueError) as exc:
            raise AdapterProcessError(
                "bounded adapter reported an invalid acquisition cost"
            ) from exc

    @classmethod
    def _charge_failure_usage(
        cls, exc: AdapterProcessError, budget: AcquisitionBudget
    ) -> None:
        if exc.acquisition_usage is not None:
            cls._charge_bounded_usage(
                {"acquisition_usage": exc.acquisition_usage}, budget
            )

    def _run(
        self,
        action: str,
        payload: dict[str, Any],
        *,
        extra_args: tuple[str, ...] = (),
        timeout_seconds: float | None = None,
    ) -> dict[str, Any]:
        command = (*self.command, action, *extra_args)
        environment = dict(os.environ)
        environment["PYTHONUTF8"] = "1"
        creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        try:
            completed = subprocess.run(
                command,
                input=canonical_json(payload),
                text=True,
                encoding="utf-8",
                errors="strict",
                capture_output=True,
                cwd=self.project_root,
                env=environment,
                timeout=(
                    self.timeout_seconds
                    if timeout_seconds is None
                    else min(self.timeout_seconds, timeout_seconds)
                ),
                check=False,
                shell=False,
                creationflags=creationflags,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise AdapterProcessError(
                f"adapter {self.name} {action} process failed: {exc}"
            ) from exc
        if completed.returncode != 0:
            detail = completed.stderr.strip()[-2000:] or "no stderr"
            exc = AdapterProcessError(
                f"adapter {self.name} {action} exited {completed.returncode}: {detail}"
            )
            # Try to parse the structured 1.0 error JSON from the *last* line of
            # stderr. Unknown / non-JSON / schema-mismatched stderr degrades to
            # ``adapter_process_failed`` with retryable=None / adapter_version=None.
            error_obj, adapter_obj = _parse_adapter_failure(detail)
            if (
                error_obj
                and adapter_obj
                and adapter_obj.get("name") == self.name
                and isinstance(adapter_obj.get("version"), str)
                and isinstance(error_obj.get("code"), str)
            ):
                exc.error_code = str(error_obj["code"])
                retryable_raw = error_obj.get("retryable")
                if isinstance(retryable_raw, bool):
                    exc.retryable = retryable_raw
                usage_raw = error_obj.get("acquisition_usage")
                if isinstance(usage_raw, dict):
                    exc.acquisition_usage = usage_raw
                exc.adapter_version = str(adapter_obj["version"])
            else:
                exc.error_code = "adapter_process_failed"
            raise exc
        try:
            response = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            raise AdapterProcessError(
                f"adapter {self.name} {action} stdout is not one JSON value"
            ) from exc
        if not isinstance(response, dict):
            raise AdapterProcessError("adapter response must be a JSON object")
        if response.get("schema_version") != "1.0" or response.get("status") != "ok":
            raise AdapterProcessError("adapter response schema/status is invalid")
        adapter = response.get("adapter")
        if not isinstance(adapter, dict):
            raise AdapterProcessError("adapter response identity is missing")
        if adapter.get("name") != self.name or adapter.get("version") != self.version:
            raise AdapterProcessError("adapter response identity/version mismatch")
        return response

    @staticmethod
    def _candidate(value: Any, request: SourceRequest) -> DownloadCandidate:
        if not isinstance(value, dict):
            raise AdapterProcessError("candidate must be an object")
        try:
            return DownloadCandidate(
                candidate_id=value["candidate_id"],
                provider=value["provider"],
                provider_document_id=value["provider_document_id"],
                market=value["market"],
                entity=request.entity,
                title=value["title"],
                source_url=value["source_url"],
                document_kind=value["document_kind"],
                form_type=value.get("form_type"),
                filing_date=value["filing_date"],
                fiscal_year=value["fiscal_year"],
                fiscal_period=value.get("fiscal_period"),
                language=value.get("language"),
                amended=value.get("amended", False),
                etag=value.get("etag"),
                last_modified=value.get("last_modified"),
                remote_size=value.get("remote_size", value.get("content_length")),
                adapter_payload_json=canonical_json(value),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise AdapterProcessError(f"invalid adapter candidate: {exc}") from exc

    @staticmethod
    def _receipt(value: dict[str, Any]) -> DownloadReceipt:
        try:
            return DownloadReceipt(
                candidate_id=value["candidate_id"],
                provider=value["provider"],
                provider_document_id=value["provider_document_id"],
                source_url=value["source_url"],
                staged_path=value["staged_path"],
                content_sha256=value["content_sha256"],
                byte_size=value["byte_size"],
                mime_type=value["mime_type"],
                retrieved_at=value["retrieved_at"],
                http_status=value["http_status"],
                adapter_name=value["adapter_name"],
                adapter_version=value["adapter_version"],
                etag=value.get("etag"),
                last_modified=value.get("last_modified"),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise AdapterProcessError(f"invalid adapter receipt: {exc}") from exc


__all__ = ["AdapterProcessError", "JsonCommandAdapter"]
