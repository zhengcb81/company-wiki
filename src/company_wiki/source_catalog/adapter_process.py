"""Strict JSON subprocess bridge for isolated downloader environments."""

from __future__ import annotations

from contextlib import contextmanager
import json
import os
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
from typing import Any, Sequence

from company_wiki._bounded_process import TransportError, run_json_process

from .acquisition import DownloadCandidate, DownloadReceipt
from .download_budget import AcquisitionBudget
from .acquisition_failure import validated_usage
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
    # False means a hard-killed process supplied only a lower-bound checkpoint.
    acquisition_usage_complete: bool | None = None
    provider_started: bool | None = None
    http_wire_bytes: int | None = None
    http_wire_usage_complete: bool | None = None
    # M3-USAGE: optional observed exchange count and HTTP protocol metadata.
    http_exchanges: int | None = None
    http_observation: dict[str, Any] | None = None
    # CWP's own never-launched proof, not a provider fee statement.
    synthetic_zero_receipt: bool = False

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


@contextmanager
def _scratch_directory():
    """Scratch cleanup must not replace the provider/transport primary cause."""
    directory = TemporaryDirectory(prefix="cwpad-")
    try:
        yield directory.name
    except BaseException as primary:
        try:
            directory.cleanup()
        except Exception as cleanup_error:
            primary.add_note(f"adapter scratch cleanup failed: {type(cleanup_error).__name__}")
        raise
    else:
        directory.cleanup()


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
        response = self._invoke_bounded("discover", request.to_dict(), budget)
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
        bytes_before_fetch = budget.response_bytes_used
        response = self._invoke_bounded("fetch", candidate.to_dict(), budget,
            extra_args=("--staging-dir", str(allocated)))
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
        budget.ensure_new_request()
        timeout_seconds = min(self.timeout_seconds, budget.remaining_seconds)
        if timeout_seconds <= 0:
            budget.ensure_open()
        bounded = dict(payload)
        bounded["acquisition_budget"] = {
            "schema_version": "1.0",
            "max_response_bytes": budget.remaining_transport_bytes,
            "timeout_seconds": timeout_seconds,
            "max_cost_usd": str(budget.remaining_cost_usd),
        }
        return bounded, timeout_seconds

    def _ensure_bounded_support(self) -> None:
        if not self.supports_acquisition_budget:
            raise AdapterProcessError(
                f"adapter {self.name} does not support bounded acquisition"
            )

    def _invoke_bounded(self, action, payload, budget, *, extra_args=()):
        bounded, timeout = self._bounded_request(payload, budget)
        try:
            response = self._run(action, bounded, extra_args=extra_args, timeout_seconds=timeout)
        except AdapterProcessError as exc:
            self._charge_failure_usage(exc, budget)
            raise
        # A schema/identity/version verified final response proves execution,
        # even when its usage or domain payload subsequently fails validation.
        usage = validated_usage(response.get("acquisition_usage"))
        budget.observe_provider(started=True, complete=True if usage is not None else None)
        self._charge_bounded_usage(response, budget)
        return response

    @staticmethod
    def _charge_bounded_usage(response: dict[str, Any], budget: AcquisitionBudget, *,
                              synthetic_cost: bool = False) -> None:
        raw = response.get("acquisition_usage")
        usage = validated_usage(raw)
        if usage is None:
            message = ("bounded adapter reported an invalid acquisition cost"
                       if isinstance(raw, dict) and isinstance(raw.get("cost_usd"), str)
                       and raw.get("response_bytes") is not None
                       else "bounded adapter acquisition_usage is missing or invalid")
            exc = AdapterProcessError(message)
            exc.error_code = "adapter_response_invalid"
            raise exc
        wire = response.get("http_wire_bytes")
        if type(wire) is not int or wire < 0:
            wire = None  # Optional legacy observation is unknown, not a refusal.
        exchanges = response.get("http_exchanges")
        if type(exchanges) is not int or exchanges < 0:
            exchanges = None  # Legacy receipts never turn the count into zero.
        from .acquisition_observation import validated_http_observation
        http_observation = validated_http_observation(response.get("http_observation"))
        if response.get("http_wire_usage_complete", True) is not True:
            budget.wire_usage_complete = False
        budget.record_reported_usage(response_bytes=usage["response_bytes"],
                                     cost_usd=usage["cost_usd"], wire_bytes=wire,
                                     http_exchanges=exchanges,
                                     http_observation=http_observation,
                                     cost_observed=not synthetic_cost)

    @classmethod
    def _charge_failure_usage(cls, exc: AdapterProcessError, budget: AcquisitionBudget) -> None:
        usage = validated_usage(exc.acquisition_usage)
        complete = exc.acquisition_usage_complete
        # An invalid claimed final is unknown, never a final zero receipt.
        if exc.acquisition_usage is not None and usage is None:
            complete = None
            exc.acquisition_usage_complete = None
        budget.observe_provider(started=exc.provider_started, complete=complete)
        if complete is not True:
            exc.retryable = False  # Preserve the existing unknown-charge policy.
            # Incomplete invocation evidence degrades every observed counter
            # to a lower bound, never a complete zero (M3-USAGE).
            budget.wire_usage_complete = False
            budget.http_exchanges_complete = False
        if usage is not None:
            # A synthetic never-launched zero proves byte counts only; its
            # "0" cost is not a provider fee statement, so it can neither
            # mark the fee observed nor clear an earlier real receipt.
            cls._charge_bounded_usage({"acquisition_usage": usage,
                                       "http_wire_bytes": exc.http_wire_bytes,
                                       "http_wire_usage_complete": exc.http_wire_usage_complete,
                                       "http_exchanges": exc.http_exchanges,
                                       "http_observation": exc.http_observation}, budget,
                                      synthetic_cost=exc.synthetic_zero_receipt)

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
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        verified_response = None
        try:
            # The parent owns SDK scratch and the complete OS process tree,
            # including Windows venv redirectors. Reap it before removing files.
            # Successful originals must reside in the explicit staging allocation.
            with _scratch_directory() as scratch:
                environment["CWP_ADAPTER_SCRATCH_ROOT"] = scratch
                completed = run_json_process(
                    command,
                    input=canonical_json(payload),
                    cwd=self.project_root,
                    env=environment,
                    timeout_seconds=(
                        self.timeout_seconds
                        if timeout_seconds is None
                        else min(self.timeout_seconds, timeout_seconds)
                    ),
                )
                verified_response = self._decode_response(completed, action)
                return verified_response
        except subprocess.TimeoutExpired as cause:
            exc = AdapterProcessError(
                f"adapter {self.name} {action} process failed: deadline exceeded"
            )
            exc.error_code = "adapter_timeout"
            exc.retryable = False
            exc.acquisition_usage_complete = False
            detail = cause.stderr or ""
            if isinstance(detail, bytes):
                detail = detail.decode("utf-8", errors="replace")
            self._attach_usage_checkpoint(exc, detail)
            if getattr(cause, "provider_started", None) is False:
                exc.provider_started = False
                exc.acquisition_usage_complete = True
                exc.acquisition_usage = {"schema_version": "1.0", "response_bytes": 0, "cost_usd": "0"}
                exc.http_wire_bytes = 0
                exc.http_wire_usage_complete = True
                exc.http_exchanges = 0
                exc.synthetic_zero_receipt = True
            raise exc from cause
        except (TransportError, UnicodeError) as cause:
            exc = AdapterProcessError(f"adapter {self.name} {action} violated bounded process lifetime")
            exc.error_code = "adapter_output_limit" if type(cause).__name__ == "OutputLimitExceeded" else "adapter_process_failed"
            exc.retryable = False
            # Output caps imply a hard stop; generic transport may have failed
            # during cleanup after a completed invocation, so remains unknown.
            exc.acquisition_usage_complete = False if exc.error_code == "adapter_output_limit" else None
            detail = getattr(cause, "stderr", b"")
            if isinstance(detail, bytes):
                detail = detail.decode("utf-8", errors="replace")
            self._attach_usage_checkpoint(exc, detail)
            if getattr(cause, "provider_started", None) is False:
                exc.provider_started = False
                exc.acquisition_usage_complete = True
                exc.acquisition_usage = {"schema_version": "1.0", "response_bytes": 0, "cost_usd": "0"}
                exc.http_wire_bytes = 0
                exc.http_wire_usage_complete = True
                exc.http_exchanges = 0
                exc.synthetic_zero_receipt = True
            raise exc from cause
        except OSError as cause:
            exc = AdapterProcessError(
                f"adapter {self.name} {action} process failed: cannot launch"
            )
            exc.error_code = "adapter_process_failed"
            # A bare OSError may be cleanup after a completed execution; only a
            # post-response verified receipt proves anything. Without one the
            # invocation stays unknown, never a synthetic zero (pinned contract:
            # test_no_target_execution_evidence_stays_unknown_not_zero).
            if verified_response is not None:
                exc.provider_started = True
                exc.acquisition_usage = validated_usage(verified_response.get("acquisition_usage"))
                exc.http_wire_bytes = verified_response.get("http_wire_bytes")
                exc.http_wire_usage_complete = verified_response.get("http_wire_usage_complete", True)
                exchanges = verified_response.get("http_exchanges")
                exc.http_exchanges = exchanges if type(exchanges) is int and exchanges >= 0 else None
                from .acquisition_observation import validated_http_observation
                exc.http_observation = validated_http_observation(verified_response.get("http_observation"))
                exc.acquisition_usage_complete = True if exc.acquisition_usage is not None else None
            raise exc from cause

    def _decode_response(self, completed, action):
        if completed.returncode != 0:
            detail = completed.stderr.strip()
            exc = AdapterProcessError(
                f"adapter {self.name} {action} exited {completed.returncode}"
            )
            # Try to parse the structured 1.0 error JSON from the *last* line of
            # stderr. Unknown / non-JSON / schema-mismatched stderr degrades to
            # ``adapter_process_failed`` with retryable=None / adapter_version=None.
            error_obj, adapter_obj = _parse_adapter_failure(detail)
            if (
                error_obj
                and adapter_obj
                and adapter_obj.get("name") == self.name
                and adapter_obj.get("version") == self.version
            ):
                exc.provider_started = True
                exc.error_code = error_obj.get("code", "adapter_process_failed")
                retryable_raw = error_obj.get("retryable")
                if isinstance(retryable_raw, bool):
                    exc.retryable = retryable_raw
                    exc.reported_retryable = retryable_raw
                final_payload = json.loads(detail.splitlines()[-1])
                exc.http_wire_bytes = final_payload.get("http_wire_bytes")
                exc.http_wire_usage_complete = final_payload.get("http_wire_usage_complete", True)
                exchanges = final_payload.get("http_exchanges")
                exc.http_exchanges = exchanges if type(exchanges) is int and exchanges >= 0 else None
                from .acquisition_observation import validated_http_observation
                exc.http_observation = validated_http_observation(final_payload.get("http_observation"))
                usage_raw = error_obj.get("acquisition_usage")
                usage = validated_usage(usage_raw)
                if usage is not None:
                    exc.acquisition_usage = usage
                    exc.acquisition_usage_complete = True
                elif usage_raw is not None:
                    exc.acquisition_usage = usage_raw
                    exc.acquisition_usage_complete = None
                self._attach_usage_checkpoint(exc, detail, only_if_missing=True)
                exc.adapter_version = str(adapter_obj["version"])
            else:
                exc.error_code = "adapter_process_failed"
                self._attach_usage_checkpoint(exc, detail)
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

    def _attach_usage_checkpoint(self, exc: AdapterProcessError, detail: str, *, only_if_missing=False) -> None:
        """Read the last complete progress line, even if kill truncated the next.

        A checkpoint reports cumulative usage for THIS subprocess invocation;
        it is charged once, not summed with earlier checkpoints. Its identity
        and version must match the configured process. It remains a lower bound
        after a hard kill, because the final read/flush may have been interrupted.
        Unstructured stderr and URLs are never copied into the public error.
        """
        if only_if_missing and validated_usage(exc.acquisition_usage) is not None:
            return
        for line in reversed(detail.splitlines()):
            try:
                value = json.loads(line)
            except (ValueError, TypeError):
                continue
            if not isinstance(value, dict):
                continue
            if (
                value.get("schema_version") != "1.0"
                or value.get("status") != "progress"
                or value.get("adapter") != {"name": self.name, "version": self.version}
                or validated_usage(value.get("acquisition_usage")) is None
            ):
                continue
            exc.acquisition_usage = validated_usage(value["acquisition_usage"])
            exc.http_wire_bytes = value.get("http_wire_bytes")
            exc.http_wire_usage_complete = False
            checkpoint_exchanges = value.get("http_exchanges")
            exc.http_exchanges = (checkpoint_exchanges if type(checkpoint_exchanges) is int
                                  and checkpoint_exchanges >= 0 else None)
            from .acquisition_observation import validated_http_observation
            exc.http_observation = validated_http_observation(value.get("http_observation"))
            exc.provider_started = True
            exc.acquisition_usage_complete = False
            exc.adapter_version = self.version
            return

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
