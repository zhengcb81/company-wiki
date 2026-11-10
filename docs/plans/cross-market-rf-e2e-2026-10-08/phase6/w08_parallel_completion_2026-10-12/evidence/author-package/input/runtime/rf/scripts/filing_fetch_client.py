"""Thin subprocess client for the standalone filing-fetch skill.

Revenue-forecast no longer owns identity resolution, reuse-first lookup, market
routing, staging, dedup, or canonical write.  Those responsibilities belong to
``filing-fetch`` (which delegates to ``company-wiki``).  This module merely
constructs a request, calls the filing-fetch CLI, validates the response, and
returns a capture-ready handle.  ``company_wiki_source.py`` then converts that
handle into a revenue source/capture record.

Run as a CLI exactly as SKILL.md documents::

    echo '<request-json>' | python scripts/filing_fetch_client.py [--allow-download]

or with an explicit request file::

    python scripts/filing_fetch_client.py --request-file req.json
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from filing_upstream_cause import FAILURE_STATUSES, failure_detail, failure_observation, safe_failure_message, validated_failure_candidates


class _ClientError(RuntimeError):
    """Raised when filing-fetch cannot return a capture-ready handle.

    Carries the structured upstream error fields (``status`` / ``error_code`` /
    ``retryable`` / ``candidates``) when filing-fetch emitted a JSON error
    document, so callers and the CLI surface diagnostics instead of a bare
    ``"no stderr"`` string.
    """

    def __init__(
        self,
        message: str,
        *,
        status: str | None = None,
        error_code: str | None = None,
        retryable: bool | None = None,
        candidates: list | None = None,
        upstream_cause: dict[str, Any] | None = None,
        acquisition_failure: dict[str, Any] | None = None,
        stage: str | None = None,
        attempts: int | None = None,
        calls: int | None = None,
        downloads: int | None = None,
        source_failure_reason: str | None = None,
        acquisition_observation: dict[str, Any] | None = None,
        request_diagnostic: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.status = status if isinstance(status, str) and status in FAILURE_STATUSES else None
        self.error_code = error_code if isinstance(error_code, str) and error_code in FAILURE_STATUSES else None
        self.retryable = retryable if type(retryable) is bool else None
        self.candidates = validated_failure_candidates(candidates)
        observed = failure_observation({"upstream_cause": upstream_cause, "acquisition_failure": acquisition_failure,
                                       "stage": stage, "attempts": attempts, "calls": calls, "downloads": downloads,
                                       "source_failure_reason": source_failure_reason,
                                       "acquisition_observation": acquisition_observation, "request_diagnostic": request_diagnostic})
        self.request_diagnostic = observed.get("request_diagnostic")
        self.upstream_cause = observed.get("upstream_cause")
        self.acquisition_failure = observed.get("acquisition_failure")
        self.acquisition_observation = observed.get("acquisition_observation")
        self.stage = observed.get("stage")
        self.attempts = observed.get("attempts")
        self.calls = observed.get("calls")
        self.downloads = observed.get("downloads")
        self.source_failure_reason = observed.get("source_failure_reason")


# The location of the standalone filing-fetch canonical repo comes from an
# explicit config file (FC-1202: no implicit sibling-directory lookup).
# ``config/filing_fetch.json`` may use ${SKILL_ROOT}/${USER_PROFILE} tokens
# and must resolve to an absolute directory containing scripts/fetch_filing.py.
# A caller may override via the *filing_fetch_root* keyword argument.
_SKILL_ROOT = Path(__file__).resolve().parents[1]
FILING_FETCH_CONFIG_SCHEMA_VERSION = "1.0"
_DEFAULT_FILING_FETCH_CONFIG = _SKILL_ROOT / "config" / "filing_fetch.json"


def load_filing_fetch_root(*, config_path: Path | None = None) -> Path:
    """Load and validate the explicit filing-fetch root configuration.

    Fail closed: a missing config, an extra field (e.g. a smuggled-back
    allowlist), a relative root, or a root without ``scripts/fetch_filing.py``
    raises ``_ClientError(error_code="config_error")``.
    """
    if config_path is not None and not isinstance(config_path, Path):
        raise TypeError("config_path must be pathlib.Path or None")
    selected = config_path or _DEFAULT_FILING_FETCH_CONFIG
    try:
        selected = selected.expanduser().resolve(strict=True)
    except OSError as exc:
        raise _ClientError(
            f"filing-fetch config does not exist: {selected}",
            error_code="config_error",
            retryable=False,
        ) from exc
    if not selected.is_file():
        raise _ClientError(
            "filing-fetch config must be a file",
            error_code="config_error",
            retryable=False,
        )
    try:
        payload = json.loads(selected.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise _ClientError(
            f"invalid filing-fetch config: {exc}",
            error_code="config_error",
            retryable=False,
        ) from exc
    if not isinstance(payload, dict):
        raise _ClientError(
            "filing-fetch config must be an object",
            error_code="config_error",
            retryable=False,
        )
    if set(payload) != {"schema_version", "filing_fetch_root"}:
        raise _ClientError(
            "filing-fetch config must contain exactly schema_version/"
            "filing_fetch_root (FC-1202: no independent allowlist, no "
            "implicit location)",
            error_code="config_error",
            retryable=False,
        )
    if payload["schema_version"] != FILING_FETCH_CONFIG_SCHEMA_VERSION:
        raise _ClientError(
            f"filing-fetch config schema_version must be "
            f"{FILING_FETCH_CONFIG_SCHEMA_VERSION}",
            error_code="config_error",
            retryable=False,
        )
    configured = payload["filing_fetch_root"]
    if (
        not isinstance(configured, str)
        or not configured.strip()
        or configured != configured.strip()
    ):
        raise _ClientError(
            "filing-fetch config filing_fetch_root must be non-empty trimmed text",
            error_code="config_error",
            retryable=False,
        )
    tokens = {
        "SKILL_ROOT": str(_SKILL_ROOT),
        "USER_PROFILE": os.environ.get("USERPROFILE") or str(Path.home()),
    }
    expanded = re.sub(
        r"\$\{(SKILL_ROOT|USER_PROFILE)\}", lambda m: tokens[m.group(1)], configured
    )
    if "${" in expanded:
        raise _ClientError(
            f"unsupported token in filing_fetch_root: {configured}",
            error_code="config_error",
            retryable=False,
        )
    root = Path(expanded).expanduser()
    if not root.is_absolute():
        raise _ClientError(
            "filing-fetch config filing_fetch_root must be absolute after "
            "token expansion",
            error_code="config_error",
            retryable=False,
        )
    try:
        resolved = root.resolve(strict=True)
    except OSError as exc:
        raise _ClientError(
            f"configured filing_fetch_root does not exist: {root}",
            error_code="config_error",
            retryable=False,
        ) from exc
    if not resolved.is_dir():
        raise _ClientError(
            "configured filing_fetch_root must be a directory",
            error_code="config_error",
            retryable=False,
        )
    if not (resolved / "scripts" / "fetch_filing.py").is_file():
        raise _ClientError(
            f"configured filing_fetch_root lacks scripts/fetch_filing.py: "
            f"{resolved}",
            error_code="config_error",
            retryable=False,
        )
    return resolved


def _try_loads(text: str) -> Any:
    """Parse *text* as JSON, returning ``None`` when it is empty or not JSON."""
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def resolve_filing_result(
    request: dict[str, Any],
    *,
    allow_download: bool = False,
    timeout_seconds: float = 900.0,
    filing_fetch_root: Path | None = None,
    company_wiki_config: Path | None = None,
    source_ref_v2: bool = False,
) -> dict[str, Any]:
    """Resolve (or, when authorized, ensure) a filing via filing-fetch.

    Returns the complete validated machine result on success, or raises
    ``_ClientError`` carrying the upstream status / error_code / retryable /
    candidates when filing-fetch fails.
    """
    root = filing_fetch_root or load_filing_fetch_root()
    script = root / "scripts" / "fetch_filing.py"
    if not script.is_file():
        raise _ClientError(
            f"filing-fetch script not found at {script}; "
            "install the skill or override filing_fetch_root"
        )
    cmd = [sys.executable, str(script)]
    if allow_download:
        cmd.append("--allow-download")
    if source_ref_v2:
        cmd.append("--source-ref-v2")
    if company_wiki_config is not None:
        cmd.extend(["--config", str(company_wiki_config)])
    cmd.extend(["--timeout-seconds", str(timeout_seconds)])
    environment = dict(os.environ)
    environment["PYTHONUTF8"] = "1"
    creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0  # type: ignore[attr-defined]
    try:
        completed = subprocess.run(
            cmd,
            input=json.dumps(request, ensure_ascii=False),
            text=True,
            encoding="utf-8",
            errors="strict",
            capture_output=True,
            timeout=timeout_seconds + 10,  # small grace beyond the deadline
            cwd=root,
            env=environment,
            check=False,
            shell=False,
            creationflags=creationflags,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise _ClientError("filing-fetch subprocess failed") from exc
    if completed.returncode != 0:
        # filing-fetch writes its structured error document to STDOUT and exits
        # non-zero (stderr is typically empty). Parse stdout first so callers
        # receive error_code / retryable / candidates; fall back to stderr only
        # when stdout is not a JSON object.
        payload = _try_loads(completed.stdout)
        if isinstance(payload, dict):
            detail = failure_detail(payload)
            raise _ClientError(
                safe_failure_message(payload, prefix=f"filing-fetch exited {completed.returncode}"),
                status=payload.get("status"),
                error_code=payload.get("error_code"),
                retryable=detail.get("retryable"),
                candidates=detail.get("candidates"),
                **failure_observation(payload),
            )
        raise _ClientError(f"filing-fetch exited {completed.returncode}: invalid upstream error document")
    try:
        response = json.loads(completed.stdout)
    except json.JSONDecodeError:
        raise _ClientError("filing-fetch stdout is not valid JSON")
    if not isinstance(response, dict):
        raise _ClientError("filing-fetch response must be an object")
    status = response.get("status")
    if response.get("schema_version") == "2.0":
        filing = response.get("filing")
        if (status == "source_candidate" and isinstance(filing, dict)
                and filing.get("status") == "source_candidate"
                and isinstance(filing.get("source_ref"), dict)):
            _validate_pathless_result(response)
            return response
        raise _ClientError(
            safe_failure_message(response, prefix="filing-fetch returned"),
            status=status, error_code=status,
            retryable=filing.get("retryable", False) if isinstance(filing, dict) else False,
            candidates=filing.get("candidates") if isinstance(filing, dict) else None,
            **failure_observation(response),
        )
    if status != "capture_ready":
        raise _ClientError(
            safe_failure_message(response, prefix="filing-fetch returned"),
            status=status,
            error_code=response.get("error_code"),
            retryable=response.get("retryable"),
            candidates=response.get("candidates"),
            **failure_observation(response),
        )
    handle = response.get("handle")
    if not isinstance(handle, dict):
        raise _ClientError("filing-fetch response missing 'handle' object")
    return response


def _validate_pathless_result(value: Any) -> None:
    """The v2 result has no storage locations; usage stays producer-owned."""
    if isinstance(value, dict):
        forbidden = {"path", "canonical_path", "relative_path", "storage_path",
                     "canonical_location_id", "root_path", "filesystem_path"}
        if forbidden & set(value):
            raise _ClientError("filing-fetch v2 result contains a storage location")
        for child in value.values():
            _validate_pathless_result(child)
    elif isinstance(value, list):
        for child in value:
            _validate_pathless_result(child)


def select_filing(result: dict[str, Any]) -> dict[str, Any]:
    """Select the filing once, preserving the legacy handle interface."""
    if result.get("schema_version") == "2.0":
        return result["filing"]
    if "handle" in result:
        return result["handle"]
    # Historical injected source-preparation fixtures already hold a handle.
    if "source_ref" in result:
        return result
    raise _ClientError("filing-fetch result missing filing handle")


def resolve_filing(
    request: dict[str, Any], *, allow_download: bool = False,
    timeout_seconds: float = 900.0, filing_fetch_root: Path | None = None,
    company_wiki_config: Path | None = None, source_ref_v2: bool = False,
) -> dict[str, Any]:
    """Compatibility API: return only the selected capture-ready filing."""
    return select_filing(resolve_filing_result(
        request, allow_download=allow_download, timeout_seconds=timeout_seconds,
        filing_fetch_root=filing_fetch_root, company_wiki_config=company_wiki_config,
        source_ref_v2=source_ref_v2,
    ))


def _emit_error(
    error_code: str,
    message: str,
    *,
    retryable: bool | None = False,
    candidates: list | None = None,
    upstream_cause: dict[str, Any] | None = None,
    acquisition_failure: dict[str, Any] | None = None,
    stage: str | None = None,
    attempts: int | None = None,
    calls: int | None = None,
    downloads: int | None = None,
    source_failure_reason: str | None = None,
    acquisition_observation: dict[str, Any] | None = None,
    request_diagnostic: dict[str, Any] | None = None,
) -> None:
    """Write a structured error document to stderr (success stream on stdout)."""
    payload: dict[str, Any] = {
        "error_code": error_code,
        "error": message,
        "retryable": bool(retryable),
    }
    safe_candidates = validated_failure_candidates(candidates)
    if safe_candidates:
        payload["candidates"] = safe_candidates
    payload.update(failure_observation({"upstream_cause": upstream_cause, "acquisition_failure": acquisition_failure,
                                       "stage": stage, "attempts": attempts, "calls": calls, "downloads": downloads,
                                       "source_failure_reason": source_failure_reason,
                                       "acquisition_observation": acquisition_observation, "request_diagnostic": request_diagnostic}))
    sys.stderr.write(json.dumps(payload, ensure_ascii=False))
    sys.stderr.write("\n")


def main(argv: list[str] | None = None) -> int:
    """CLI entry: read a request, resolve it, print the handle JSON to stdout."""
    # Speak UTF-8 on Windows regardless of the platform default (matches
    # filing-fetch's own stdin/stdout handling): handles and requests routinely
    # carry non-ASCII issuer names and canonical paths.
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(
        description="Resolve (or ensure) a filing via the standalone filing-fetch skill.",
    )
    parser.add_argument(
        "--request-file",
        help="Path to a request JSON file. If omitted, the request is read from stdin.",
    )
    parser.add_argument(
        "--allow-download",
        action="store_true",
        help="Authorize filing-fetch to download when no reusable source is found.",
    )
    parser.add_argument("--result-envelope", action="store_true",
                        help="return the complete filing-fetch machine result")
    parser.add_argument(
        "--source-ref-v2",
        action="store_true",
        help="request a pathless SourceRef for a later verified company-wiki read",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=900.0,
        help="Overall deadline forwarded to filing-fetch (default: 900).",
    )
    parser.add_argument(
        "--filing-fetch-root",
        help="Override the filing-fetch skill root (advanced; defaults to "
        "config/filing_fetch.json).",
    )
    parser.add_argument(
        "--company-wiki-config",
        type=Path,
        default=None,
        help="Override the company-wiki config passed to filing-fetch (E2E fixtures).",
    )
    args = parser.parse_args(argv)

    if args.request_file:
        try:
            request_text = Path(args.request_file).read_text(encoding="utf-8")
        except OSError as exc:
            _emit_error("config_error", f"cannot read request file: {exc}", retryable=False)
            return 1
    else:
        request_text = sys.stdin.read()

    request = _try_loads(request_text)
    if not isinstance(request, dict):
        _emit_error("config_error", "request must be a JSON object", retryable=False)
        return 1

    root = Path(args.filing_fetch_root) if args.filing_fetch_root else None
    try:
        resolver = resolve_filing_result if args.result_envelope else resolve_filing
        handle = resolver(
            request,
            allow_download=args.allow_download,
            timeout_seconds=args.timeout_seconds,
            filing_fetch_root=root,
            company_wiki_config=args.company_wiki_config,
            source_ref_v2=args.source_ref_v2,
        )
    except _ClientError as exc:
        _emit_error(
            exc.error_code or exc.status or "fatal",
            str(exc),
            retryable=exc.retryable,
            candidates=exc.candidates,
            upstream_cause=exc.upstream_cause,
            acquisition_failure=exc.acquisition_failure,
            stage=exc.stage, attempts=exc.attempts, calls=exc.calls, downloads=exc.downloads,
            source_failure_reason=exc.source_failure_reason,
            acquisition_observation=exc.acquisition_observation,
            request_diagnostic=exc.request_diagnostic,
        )
        return 2

    sys.stdout.write(json.dumps(handle, ensure_ascii=False))
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
