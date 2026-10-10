"""Versioned JSON entry for the CWP-owned, bounded Dayu SDK bridge.

No Dayu CLI initialization, translation, Docling or LLM pipeline is invoked.
The parent allocates ephemeral scratch and hard deadline. SEC's tiny shared
throttle state/OS mutex lives under the explicit CWP provider-state root.
"""

from __future__ import annotations

import argparse
import asyncio
from contextlib import redirect_stdout
from dataclasses import fields
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
from typing import Any
from urllib.parse import urlsplit

import httpx

from company_wiki._file_mutex import os_file_mutex
from .acquisition import DownloadCandidate
from .bounded_http import (
    BudgetedAsyncHTTPTransport, BudgetedHTTPTransport, ProviderBudgetStop,
    bounded_sleep, usage_receipt,
)
from .dayu_fiscal_metadata import verify_sec_primary
from .dayu_sdk_bridge import DayuBridgeError, discover_hk, discover_sec
from .download_budget import AcquisitionBudget
from .resolver import SourceRequest


def _budget(payload: dict[str, Any]) -> AcquisitionBudget:
    value = payload.get("acquisition_budget")
    if not isinstance(value, dict) or set(value) != {
        "schema_version", "max_response_bytes", "timeout_seconds", "max_cost_usd",
    } or value["schema_version"] != "1.0":
        raise DayuBridgeError("invalid_budget", "a complete acquisition budget is required")
    return AcquisitionBudget.from_limits(max_response_bytes=value["max_response_bytes"],
        max_seconds=value["timeout_seconds"], max_cost_usd=value["max_cost_usd"])


def _candidate(payload: dict[str, Any], market: str) -> tuple[DownloadCandidate, dict[str, Any]]:
    candidate = DownloadCandidate(**{
        field.name: payload[field.name] for field in fields(DownloadCandidate) if field.name in payload
    })
    raw = json.loads(candidate.adapter_payload_json or "null")
    if not isinstance(raw, dict) or candidate.market != market:
        raise DayuBridgeError("invalid_candidate", "candidate SDK payload or market is invalid")
    for key in ("candidate_id", "provider", "provider_document_id", "entity", "title", "market",
                "source_url", "document_kind", "filing_date", "fiscal_year", "fiscal_period",
                "form_type", "language", "amended"):
        if raw.get(key) != getattr(candidate, key):
            raise DayuBridgeError("invalid_candidate", "candidate differs from its discovery metadata")
    url = urlsplit(candidate.source_url)
    domain = (url.hostname or "").lower()
    expected = "sec.gov" if market == "US" else "hkexnews.hk"
    if url.scheme != "https" or url.username or url.password or not (
        domain == expected or domain.endswith("." + expected)
    ):
        raise DayuBridgeError("invalid_candidate", "candidate is not an official provider URL")
    return candidate, raw


class _OriginalResponse:
    """Actual GET headers, distinct from discovery HEAD and SDK return types."""

    def __init__(self):
        self.response = None

    def observe(self, response: httpx.Response) -> None:
        if response.request.method != "GET" or not 200 <= response.status_code < 300:
            return
        if response.status_code != 200 or "content-range" in response.headers:
            raise ProviderBudgetStop("incomplete_response", "original requires a complete HTTP 200 response")
        self.response = response

    async def observe_async(self, response: httpx.Response) -> None:
        self.observe(response)

    def receipt_headers(self, data: bytes) -> dict[str, Any]:
        if self.response is None:
            raise DayuBridgeError("missing_response", "SDK did not fetch through the bounded client")
        declared = self.response.headers.get("content-length")
        if declared is not None:
            try:
                complete = int(declared) == len(data)
            except ValueError:
                complete = False
            if not complete:
                raise ProviderBudgetStop("incomplete_response", "original size differs from GET length")
        return {"http_status": self.response.status_code,
                "etag": self.response.headers.get("etag"),
                "last_modified": self.response.headers.get("last-modified")}


def _stage(data: bytes, candidate: DownloadCandidate, staging: Path, identity: dict[str, str],
           *, mime: str, suffix: str, response: _OriginalResponse) -> dict[str, Any]:
    response_headers = response.receipt_headers(data)
    digest = hashlib.sha256(data).hexdigest()
    path = staging / (digest + suffix)
    temporary = path.with_suffix(path.suffix + ".part")
    if path.exists() and path.read_bytes() != data:
        raise DayuBridgeError("staging_conflict", "existing staging bytes differ")
    try:
        if not path.exists():
            temporary.write_bytes(data)
            os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
    return {
        "candidate_id": candidate.candidate_id, "provider": candidate.provider,
        "provider_document_id": candidate.provider_document_id, "source_url": candidate.source_url,
        "staged_path": str(path), "content_sha256": digest, "byte_size": len(data),
        "mime_type": mime, "retrieved_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "adapter_name": identity["name"], "adapter_version": identity["version"], **response_headers,
    }


async def _sec_operation(action, payload, budget, scratch, provider_state, staging, identity, checkpoint):
    user_agent = os.environ.get("SEC_USER_AGENT", "").strip()
    if not user_agent:
        raise DayuBridgeError("provider_not_configured", "configured SEC_USER_AGENT is required")
    from dayu.fins.downloaders.sec_downloader import SecDownloader
    from dayu.fins.pipelines.sec_filing_collection import collect_filings_from_table

    transport = BudgetedAsyncHTTPTransport(httpx.AsyncHTTPTransport(), budget, checkpoint=checkpoint)
    original = _OriginalResponse()
    async with httpx.AsyncClient(transport=transport, follow_redirects=True,
                                headers={"User-Agent": user_agent}, timeout=30,
                                event_hooks={"response": [original.observe_async]} if action == "fetch" else {}) as client:
        downloader = SecDownloader(workspace_root=provider_state, client=client)
        if action == "discover":
            request = SourceRequest(**{field.name: payload[field.name]
                for field in fields(SourceRequest) if field.name in payload})
            values = await discover_sec(request, downloader, collect=collect_filings_from_table)
            return {"candidates": values}
        candidate, raw = _candidate(payload, "US")
        body = await downloader.fetch_file_bytes(candidate.source_url)
        budget.ensure_open()
        verify_sec_primary(body, cik=raw["cik"], year=candidate.fiscal_year,
                           period=candidate.fiscal_period, report_date=raw["report_date"])
        return {"receipt": _stage(body, candidate, staging, identity, mime="text/html", suffix=".html", response=original)}


def _hk_operation(action, payload, budget, scratch, staging, identity, checkpoint):
    from dayu.fins.downloaders.hkexnews_downloader import HkexnewsDiscoveryClient
    from dayu.fins.pipelines.cn_download_models import CnReportCandidate, CnReportQuery

    transport = BudgetedHTTPTransport(httpx.HTTPTransport(), budget, checkpoint=checkpoint)
    original = _OriginalResponse()
    with httpx.Client(transport=transport, follow_redirects=True,
                      headers={"User-Agent": "DayuAgent/1.0 (+hk-download)"}, timeout=30,
                      event_hooks={"response": [original.observe]} if action == "fetch" else {}) as client:
        downloader = HkexnewsDiscoveryClient(client=client,
            sleep_func=lambda seconds: bounded_sleep(budget, seconds))
        if action == "discover":
            request = SourceRequest(**{field.name: payload[field.name]
                for field in fields(SourceRequest) if field.name in payload})
            return {"candidates": discover_hk(request, downloader, query_type=CnReportQuery)}
        candidate, raw = _candidate(payload, "HK")
        sdk_candidate = CnReportCandidate(**raw["sdk_report_candidate"])
        if (sdk_candidate.source_url != candidate.source_url
            or sdk_candidate.source_id != candidate.provider_document_id
            or sdk_candidate.fiscal_year != candidate.fiscal_year
            or sdk_candidate.fiscal_period != candidate.fiscal_period):
            raise DayuBridgeError("invalid_candidate", "HK SDK record differs from selected target")
        asset = downloader.download_report_pdf(sdk_candidate)
        path = asset.pdf_path.resolve(strict=True)
        # A public SDK returning an unexpected production path is not permission
        # to move or delete it. Only this parent's ephemeral allocation is owned.
        path.relative_to(scratch)
        try:
            data = path.read_bytes()
            if len(data) != asset.content_length or hashlib.sha256(data).hexdigest() != asset.sha256:
                raise DayuBridgeError("sdk_asset_mismatch", "HK downloaded asset hash/size differs")
            budget.ensure_open()
            return {"receipt": _stage(data, candidate, staging, identity, mime="application/pdf", suffix=".pdf", response=original)}
        finally:
            path.unlink(missing_ok=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--market", choices=("HK", "US"), required=True)
    parser.add_argument("--adapter-name", required=True)
    parser.add_argument("--adapter-version", required=True)
    parser.add_argument("--provider-state-root", type=Path, required=True)
    parser.add_argument("action", choices=("discover", "fetch"))
    parser.add_argument("--staging-dir", type=Path)
    args = parser.parse_args(argv)
    identity = {"name": args.adapter_name, "version": args.adapter_version}
    budget = None

    def checkpoint(usage):
        print(json.dumps({"schema_version": "1.0", "status": "progress", "adapter": identity,
                          "acquisition_usage": usage,
                          "http_wire_bytes": budget.wire_response_bytes_used if budget else 0,
                          "http_exchanges": budget.http_exchanges_used if budget else 0,
                          "http_observation": budget.last_http_observation if budget else None}, sort_keys=True), file=sys.stderr, flush=True)

    try:
        payload = json.load(sys.stdin)
        if not isinstance(payload, dict):
            raise DayuBridgeError("invalid_request", "request must be an object")
        budget = _budget(payload)
        budget.ensure_new_request()
        scratch_value = os.environ.get("CWP_ADAPTER_SCRATCH_ROOT")
        if not scratch_value:
            raise DayuBridgeError("missing_scratch", "parent-owned SDK scratch is required")
        scratch = Path(scratch_value).resolve(strict=True)
        if not scratch.is_dir() or scratch.is_symlink():
            raise DayuBridgeError("invalid_scratch", "parent-owned SDK scratch is invalid")
        temp = scratch / "tmp"
        temp.mkdir()
        tempfile.tempdir = str(temp)  # Process-local SDK temp allocation, never external originals.
        for name in ("TMP", "TEMP", "TMPDIR"):
            os.environ[name] = str(temp)
        staging = args.staging_dir
        if args.action == "fetch":
            if staging is None:
                raise DayuBridgeError("invalid_request", "fetch requires explicit staging allocation")
            staging = staging.resolve(strict=True)
        provider_state = args.provider_state_root.resolve()
        provider_state.mkdir(parents=True, exist_ok=True)
        checkpoint(usage_receipt(budget))
        # SDK logs must not corrupt the single JSON stdout or expose config values.
        with redirect_stdout(io.StringIO()):
            if args.market == "US":
                # Dayu's Windows throttle lock is not cross-process. Serialize
                # the SDK operation with CWP's shared OS lock instead.
                with os_file_mutex(provider_state / "sec-sdk.lock", timeout_seconds=budget.remaining_seconds):
                    async def run():
                        try:
                            return await asyncio.wait_for(_sec_operation(args.action, payload, budget, scratch,
                                provider_state, staging, identity, checkpoint), timeout=budget.remaining_seconds)
                        except asyncio.TimeoutError as exc:
                            raise ProviderBudgetStop("deadline_exceeded", "acquisition deadline exceeded") from exc
                    result = asyncio.run(run())
            else:
                result = _hk_operation(args.action, payload, budget, scratch, staging, identity, checkpoint)
        budget.ensure_open()
    except Exception as exc:
        code = getattr(exc, "error_code", "provider_failed")
        error = {"code": code, "type": type(exc).__name__,
                 "message": "bounded SDK operation did not complete",
                 "retryable": isinstance(exc, (httpx.HTTPError, RuntimeError)) and code == "provider_failed"}
        # Invalid requests have used zero network; final handled failure is exact.
        error["acquisition_usage"] = usage_receipt(budget) if budget else {
            "schema_version": "1.0", "response_bytes": 0, "cost_usd": "0"}
        print(json.dumps({"schema_version": "1.0", "status": "failed", "adapter": identity,
                          "error": error,
                          "http_wire_bytes": budget.wire_response_bytes_used if budget else 0,
                          "http_exchanges": budget.http_exchanges_used if budget else 0,
                          "http_observation": budget.last_http_observation if budget else None}, sort_keys=True), file=sys.stderr, flush=True)
        return 1
    print(json.dumps({"schema_version": "1.0", "status": "ok", "adapter": identity,
                      "acquisition_usage": usage_receipt(budget),
                      "http_wire_bytes": budget.wire_response_bytes_used,
                      "http_exchanges": budget.http_exchanges_used,
                      "http_observation": budget.last_http_observation, **result}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
