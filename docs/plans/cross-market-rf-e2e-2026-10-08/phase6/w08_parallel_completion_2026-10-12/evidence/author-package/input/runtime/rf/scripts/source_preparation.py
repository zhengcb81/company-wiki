"""WU-1000: the single production orchestration entry — source preparation.

From a FilingRequest, this CLI drives the REAL cross-repo chain as
subprocesses: filing-fetch (resolve/ensure, always requested in pathless
SourceRef v2 form) → company-wiki catalog (verified raw open) → RevenueSourceRecord
+ reuse receipt.  The verified open is done by company-wiki itself
(``--company-wiki-catalog-config`` is required; missing/unavailable config is a
named failure before any outbound call).  The former legacy normalized-body
reader survives only as ``_prepare_legacy_source``, an isolated helper for
historical offline fixture replay — it is not a production default and is
never called from ``prepare_source``.

The forecast calculator (revenue_forecast.py) stays pure: it consumes the
validated source record and never touches network/catalog/download.

Exit codes: 0 = source record produced; 1 = not found/not admissible;
2 = usage error; 3 = internal.
"""

from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
FILING_FETCH_CLIENT = PROJECT_ROOT / "scripts" / "filing_fetch_client.py"

import company_wiki_source  # noqa: E402
from filing_upstream_cause import failure_observation, parse_error_document, safe_failure_message, validated_source_failure_reason  # noqa: E402
from processing_demand import DemandQueue  # noqa: E402
from filing_fetch_client import select_filing  # noqa: E402
from source_period_semantics import valid_fiscal_year  # noqa: E402

# ZR-701: source preparation submits one demand per prepared source (key =
# the source record's sha-256 identity) so schedulers/consumers can claim,
# heartbeat and complete the work under the shared ProcessingDemand
# contract.  In-memory queue (persistence is a later phase).
_preparation_demands = DemandQueue()


def preparation_demands() -> DemandQueue:
    """The process-level demand queue (test-visible)."""
    return _preparation_demands


def _read_deadline(timeout_seconds: float) -> float:
    if (isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, (int, float))
            or not math.isfinite(timeout_seconds) or timeout_seconds <= 0):
        raise RuntimeError("invalid_source_preparation_timeout: expected finite positive caller budget")
    return time.monotonic() + timeout_seconds


def _remaining_timeout(deadline: float) -> float:
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise RuntimeError("source_preparation_deadline_exhausted: no time remains for the next public read")
    return remaining


def _demand_key(record: dict) -> str:
    """Stable demand key for one prepared source (keeps prepare_source
    within the frozen complexity ratchet)."""
    return str(record.get("source_id") or record.get("source_sha256") or "")


def _submit_preparation_demand(record: dict) -> None:
    """ZR-701: enqueue one deduped processing demand per prepared source."""
    source_key = _demand_key(record)
    if source_key:
        _preparation_demands.enqueue(key=source_key, kind="source_preparation", now=0.0)


def _read_request(request_file: str | None) -> dict:
    if request_file:
        return json.loads(Path(request_file).read_text(encoding="utf-8"))
    return json.load(sys.stdin)


_SOURCE_TYPE_BY_KIND = {
    "annual_report": "regulatory_filing",
    "quarterly_report": "regulatory_filing",
    "semi_annual_report": "regulatory_filing",
    "regulatory_filing": "regulatory_filing",
    "investor_presentation": "investor_presentation",
    "earnings_transcript": "earnings_transcript",
    "official_statistics": "official_statistics",
    "company_release": "company_release",
    "investor_relations": "company_release",
    "investor_call_transcript": "earnings_transcript",
    "broker_research": "specialist_research",
    "prospectus": "regulatory_filing",
    "equity_offering_prospectus": "regulatory_filing",
    "convertible_bond_prospectus": "regulatory_filing",
    "news": "reputable_news",
}
_SOURCE_LOCATION_FIELDS = {
    "path",
    "canonical_path",
    "relative_path",
    "storage_path",
    "canonical_location_id",
    "root_path",
    "filesystem_path",
}


def _revenue_source_type(handle: dict) -> str:
    kind = handle.get("document_kind")
    if not isinstance(kind, str) or kind not in _SOURCE_TYPE_BY_KIND:
        raise RuntimeError("unsupported_revenue_document_kind")
    return _SOURCE_TYPE_BY_KIND[kind]


def _catalog_config_for_reader(catalog_config: Path | None) -> Path:
    """Resolve the required catalog config; named failure before outbound."""
    if not isinstance(catalog_config, Path):
        raise RuntimeError("SourceRef v2 requires company_wiki_catalog_config")
    try:
        resolved = catalog_config.expanduser().resolve(strict=True)
    except OSError as exc:
        raise RuntimeError("company-wiki catalog config is unavailable") from exc
    if not resolved.is_file():
        raise RuntimeError("company-wiki catalog config must be a file")
    return resolved


def _filing_fetch_command(
    python: tuple[str, ...],
    *,
    filing_fetch_root: Path | None,
    company_wiki_config: Path | None,
    allow_download: bool,
    timeout_seconds: float,
) -> tuple[str, ...]:
    command = (*python, str(FILING_FETCH_CLIENT), "--source-ref-v2", "--result-envelope")
    if filing_fetch_root is not None:
        command = (*command, "--filing-fetch-root", str(filing_fetch_root))
    if company_wiki_config is not None:
        command = (*command, "--company-wiki-config", str(company_wiki_config))
    if allow_download:
        command = (*command, "--allow-download")
    if timeout_seconds:
        command = (*command, "--timeout-seconds", str(timeout_seconds))
    return command


class FilingSourcePreparationError(RuntimeError):
    """A source failure with its safe upstream diagnostic, without inference."""

    def __init__(self, message: str, *, upstream_cause: dict | None = None,
                 acquisition_failure: dict | None = None, stage: str | None = None,
                 attempts: int | None = None, calls: int | None = None, downloads: int | None = None,
                 source_failure_reason: str | None = None,
                 acquisition_observation: dict | None = None, request_diagnostic: dict | None = None):
        super().__init__(message)
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


def _safe_preparation_failure(exc: BaseException, stage: str) -> str:
    """Keep local named deadline/refusal diagnostics without copying a body."""
    marker = str(exc).split(":", 1)[0]
    if marker in {"source_preparation_deadline_exhausted", "invalid_source_preparation_timeout"}:
        return marker
    reason = validated_source_failure_reason(getattr(exc, "source_failure_reason", None))
    if reason is not None:
        if reason in {"document_kind_mismatch", "fiscal_year_mismatch", "fiscal_period_mismatch"}:
            return "source validation refused: " + reason.replace("_mismatch", " mismatch")
        return "source reader refused: " + reason
    return f"source preparation failed at {stage}"


def _run_filing_fetch(request: dict, command: tuple[str, ...], timeout: float) -> dict:
    proc = subprocess.run(
        command,
        input=json.dumps(request, ensure_ascii=False),
        text=True,
        encoding="utf-8",
        capture_output=True,
        cwd=str(PROJECT_ROOT),
        timeout=timeout + 30,
        check=False,
    )
    if proc.returncode != 0:
        payload = parse_error_document(proc.stderr)
        raise FilingSourcePreparationError(
            safe_failure_message(payload, prefix=f"filing-fetch client exited {proc.returncode}"),
            **failure_observation(payload),
        )
    payload = json.loads(proc.stdout)
    return payload if isinstance(payload, dict) else {}


def _validate_v2_candidate(request: dict, handle: dict) -> int | None:
    source_ref = handle.get("source_ref")
    if _SOURCE_LOCATION_FIELDS & set(handle):
        raise RuntimeError(
            "filing-fetch SourceRef candidate contains a storage location"
        )
    if isinstance(source_ref, dict) and _SOURCE_LOCATION_FIELDS & set(source_ref):
        raise RuntimeError("filing-fetch SourceRef contains a storage location")
    if not isinstance(source_ref, dict):
        raise RuntimeError("filing-fetch SourceRef candidate is missing source_ref")
    if handle.get("document_kind") != request.get("document_kind"):
        raise FilingSourcePreparationError("filing-fetch SourceRef document_kind mismatch", source_failure_reason="document_kind_mismatch")
    fiscal_year = handle.get("fiscal_year")
    if not valid_fiscal_year(handle.get("document_kind"), fiscal_year):
        raise RuntimeError("SourceRef v2 requires a valid resolved fiscal_year")
    requested_year = request.get("fiscal_year")
    if requested_year is not None and (type(requested_year) is not int or requested_year < 1):
        raise RuntimeError("SourceRef v2 requires a valid requested fiscal_year")
    if requested_year is not None and requested_year != fiscal_year:
        raise FilingSourcePreparationError("filing-fetch SourceRef fiscal_year mismatch", source_failure_reason="fiscal_year_mismatch")
    resolved_period = handle.get("fiscal_period")
    if resolved_period is not None and (
            not isinstance(resolved_period, str) or not resolved_period.strip()
            or resolved_period.strip() != resolved_period):
        raise RuntimeError("SourceRef v2 requires a valid resolved fiscal_period")
    requested_period = request.get("fiscal_period")
    if requested_period is None:
        # FF/CWP already resolved one source. Omission is no extra period
        # constraint, never an instruction to replace its observed period.
        requested_period = resolved_period
        if request.get("document_kind") == "annual_report" and resolved_period not in (None, "FY"):
            requested_period = "FY"  # Preserve the existing annual-only rule.
    if resolved_period != requested_period:
        raise FilingSourcePreparationError("filing-fetch SourceRef fiscal_period mismatch", source_failure_reason="fiscal_period_mismatch")
    return fiscal_year


def _v2_resolution_events(handle: dict) -> tuple[str, int]:
    outcome = handle.get("resolution_outcome")
    if not isinstance(outcome, str) or outcome not in {
        "reused_existing",
        "reused_after_discovery",
        "downloaded_new",
    }:
        raise RuntimeError("filing-fetch SourceRef resolution_outcome is invalid")
    downloads = handle.get("download_events")
    if isinstance(downloads, bool) or downloads not in (0, 1):
        raise RuntimeError("filing-fetch SourceRef download_events is invalid")
    expected_downloads = int(outcome == "downloaded_new")
    if downloads != expected_downloads:
        raise RuntimeError("filing-fetch SourceRef outcome/download_events mismatch")
    return outcome, downloads


def _prepare_source_ref_v2(
    request: dict,
    handle: dict,
    catalog_config: Path,
    *,
    timeout_seconds: float, source_reader_receipt_version: str = "2.1",
    registered_read: bool = False,
) -> dict:
    """Open and record one pathless candidate using company-wiki's verifier."""
    from company_wiki_source_reader_v2 import open_source_version_v2, validate_source_reader_receipt_version
    from company_wiki_source_v2 import build_revenue_source_record_from_verified_read

    version = validate_source_reader_receipt_version(source_reader_receipt_version)
    deadline = _read_deadline(timeout_seconds)
    reader_options = {"source_reader_receipt_version": version} if version == "2.2" else {}
    fiscal_year = _validate_v2_candidate(request, handle)
    outcome, downloads = ("reused_existing", 0) if registered_read else _v2_resolution_events(handle)
    body, receipt, manifest = open_source_version_v2(
        source_ref=handle["source_ref"],
        catalog_config=catalog_config,
        as_of_date=str(request.get("as_of_date", "")),
        expected_fiscal_year=fiscal_year,
        timeout_seconds=_remaining_timeout(deadline), **reader_options,
    )
    if registered_read:
        _registered_manifest_constraints(handle, manifest)
    record = build_revenue_source_record_from_verified_read(
        source_ref=handle["source_ref"],
        read_receipt=receipt,
        source_bytes=body,
        source_manifest=manifest,
        source_candidate=handle,
        as_of_date=str(request.get("as_of_date", "")),
        source_type=_revenue_source_type(handle),
        publisher=str(handle.get("provider") or "company-wiki"),
        page_or_section="1",
        prompt_injection_status=handle.get("prompt_injection_status"),
    )
    record["reuse_receipt"] = {
        "parser_calls": None,
        "llm_calls": None,
        "download_calls": downloads,
        "outcome": outcome,
        "policy_hash": receipt["policy_sha256"],
        "source_read_policy_sha256": receipt["source_read_policy_sha256"],
        "prompt_injection_status": record["capture"]["prompt_injection_status"],
        "artifact_read": [],
        "producer_events": [],
        "artifact_read_events": [],
        "artifact_failed_events": [],
    }
    _submit_preparation_demand(record)
    return record


def _prepare_legacy_source(request: dict, handle: dict) -> dict:
    """ISOLATED historical offline-fixture path (P5-RF): builds a record from
    the legacy resolution_envelope plus derived normalized/summary/sections
    artifact bodies.  NOT a production default and never invoked by
    ``prepare_source``; retained only so legacy offline contract fixtures
    (e.g. tests/test_fc904, tests/test_message_contract_pins) keep replaying
    their real assertions.  New code must not call this.
    """
    # Download evidence comes from the resolution envelope, never from the
    # existence of a returned handle; absent evidence is fail-closed.
    envelope = handle.get("resolution_envelope")
    if not isinstance(envelope, dict):
        raise RuntimeError(
            "company-wiki resolution envelope missing — download evidence "
            "cannot be derived; fail closed instead of fabricating counts"
        )
    download_events = envelope.get("download_events")
    if isinstance(download_events, bool) or download_events not in (0, 1):
        raise RuntimeError(
            f"invalid download_events in resolution envelope: {download_events!r}"
        )
    artifact_read, producer_events = company_wiki_source.select_artifact_roles(handle)
    io_evidence = company_wiki_source.verify_artifact_reads(handle, artifact_read)
    artifact_read_events = io_evidence["verified_read_events"]
    artifact_failed_events = io_evidence["failed_read_events"]
    prompt_injection_status = envelope.get("prompt_injection_status")
    if prompt_injection_status is None:
        prompt_injection_status = "not_reviewed"
    parser_calls = envelope.get("parser_calls")
    llm_calls = envelope.get("llm_calls")
    if parser_calls is None or llm_calls is None:
        raise RuntimeError(
            "parser/llm counts absent from the resolution envelope — fail "
            "closed instead of fabricating 0"
        )
    record = company_wiki_source.build_revenue_source_record(
        handle,
        as_of_date=str(request.get("as_of_date", "")),
        source_type=_revenue_source_type({**request, **handle}),
        publisher=str(handle.get("provider") or "unknown"),
        page_or_section="1",
        prompt_injection_status=prompt_injection_status,
    )
    record["reuse_receipt"] = {
        "parser_calls": parser_calls,
        "llm_calls": llm_calls,
        "download_calls": download_events,
        "outcome": envelope.get("outcome"),
        "policy_hash": envelope.get("policy_hash"),
        "activation_epoch": envelope.get("activation_epoch"),
        "bundle_status": envelope.get("bundle_status"),
        "prompt_injection_status": prompt_injection_status,
        "artifact_read": artifact_read,
        "producer_events": producer_events,
        "artifact_read_events": artifact_read_events,
        "artifact_failed_events": artifact_failed_events,
    }
    _submit_preparation_demand(record)
    return record



def _registered_manifest_constraints(candidate: dict, manifest: dict) -> None:
    """Bind supplied period/issuer facts to the same public verified-open manifest."""
    fields = ("document_kind", "fiscal_year", "fiscal_period", "market", "security_id", "canonical_entity_id")
    for key in fields:
        if key in candidate:
            expected, actual = candidate[key], manifest[key]
            if type(expected) is not type(actual) or expected != actual:
                raise RuntimeError("registered_source_manifest_mismatch:" + key)


def prepare_registered_source_result(
    candidate: dict, *, as_of_date: str, company_wiki_catalog_config: Path,
    timeout_seconds: float = 30.0, source_reader_receipt_version: str = "2.1",
) -> dict:
    """Read a registered pathless official source through the same exact verifier.

    Acquisition/discovery remain upstream. This entry opens the already registered
    candidate once and produces a real SourceCapture, without asking FF to resolve
    a nonfinancial document or inventing a financial year.
    """
    request = {field: candidate.get(field) for field in
               ("document_kind", "fiscal_year", "fiscal_period")}
    request["as_of_date"] = as_of_date
    source = _prepare_source_ref_v2(request, candidate,
        _catalog_config_for_reader(company_wiki_catalog_config), timeout_seconds=timeout_seconds,
        source_reader_receipt_version=source_reader_receipt_version, registered_read=True)
    return {"schema_version": "source-preparation-result/1", "source": source,
            "filing_fetch": None, "narrative": None}


def prepare_source_result(
    request: dict,
    *,
    allow_download: bool = False,
    timeout_seconds: float = 900.0,
    python: tuple[str, ...] = (sys.executable,),
    company_wiki_config: Path | None = None,
    filing_fetch_root: Path | None = None,
    source_reader_v2: bool = True,
    company_wiki_catalog_config: Path | None = None,
    narrative_request: dict | None = None,
    source_reader_receipt_version: str = "2.1",
) -> dict:
    """Orchestrate the real chain and return the RevenueSourceRecord.

    The only default route is SourceRef v2: the FF candidate is requested in
    pathless SourceRef form and verified by company-wiki's reader with the
    REQUIRED ``company_wiki_catalog_config`` (missing/unavailable config is a
    named failure before any outbound call).  ``source_reader_v2`` remains
    accepted only for call-site compatibility — it is a no-op, there is no
    legacy fallback.
    """
    from company_wiki_source_reader_v2 import validate_source_reader_receipt_version
    version = validate_source_reader_receipt_version(source_reader_receipt_version)
    deadline = _read_deadline(timeout_seconds)
    reader_options = {"source_reader_receipt_version": version} if version == "2.2" else {}
    catalog_config = _catalog_config_for_reader(company_wiki_catalog_config)
    command = _filing_fetch_command(
        python,
        filing_fetch_root=filing_fetch_root,
        company_wiki_config=company_wiki_config,
        allow_download=allow_download,
        timeout_seconds=timeout_seconds,
    )
    filing_fetch = _run_filing_fetch(request, command, _remaining_timeout(deadline))
    stage = "source_reader"
    try:
        record = _prepare_source_ref_v2(
            request,
            select_filing(filing_fetch),
            catalog_config,
            timeout_seconds=_remaining_timeout(deadline), **reader_options,
        )
        narrative = None
        if narrative_request is not None:
            stage = "narrative_reader"
            from company_wiki_narrative_reader import read_narrative_context
            from source_narrative_context import narrative_read_receipt
            context = read_narrative_context(narrative_request, catalog_config=catalog_config,
                                             timeout_seconds=_remaining_timeout(deadline))
            value = context.to_dict()
            refs = value["parent_source_refs"] if value.get("schema_version") == "revenue-narrative-context/3" else [value["source_ref"]]
            if select_filing(filing_fetch)["source_ref"] not in refs:
                raise RuntimeError("narrative SourceRef does not match the prepared source")
            narrative = narrative_read_receipt(context)
    except (RuntimeError, ValueError, OSError) as exc:
        observed = failure_observation(filing_fetch)
        observed["stage"] = stage
        reason = validated_source_failure_reason(getattr(exc, "source_failure_reason", None))
        if reason is not None:
            observed["source_failure_reason"] = reason
        raise FilingSourcePreparationError(_safe_preparation_failure(exc, stage), **observed) from exc
    return {"schema_version": "source-preparation-result/1", "source": record,
            "filing_fetch": filing_fetch, "narrative": narrative}


def prepare_source(
    request: dict, *, allow_download: bool = False, timeout_seconds: float = 900.0,
    python: tuple[str, ...] = (sys.executable,), company_wiki_config: Path | None = None,
    filing_fetch_root: Path | None = None, source_reader_v2: bool = True,
    company_wiki_catalog_config: Path | None = None, narrative_request: dict | None = None,
    source_reader_receipt_version: str = "2.1",
) -> dict:
    """Compatibility source-only entry; the full result is an explicit sidecar."""
    return prepare_source_result(
        request, allow_download=allow_download, timeout_seconds=timeout_seconds, python=python,
        company_wiki_config=company_wiki_config, filing_fetch_root=filing_fetch_root,
        source_reader_v2=source_reader_v2, company_wiki_catalog_config=company_wiki_catalog_config,
        narrative_request=narrative_request, source_reader_receipt_version=source_reader_receipt_version,
    )["source"]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Revenue source preparation — the single production entry."
    )
    parser.add_argument("--request-file", help="request JSON file (else stdin)")
    parser.add_argument("--allow-download", action="store_true")
    parser.add_argument("--result-envelope", action="store_true",
                        help="retain filing-fetch result and explicit narrative read receipt")
    parser.add_argument("--narrative-request-file", type=Path,
                        help="explicit existing narrative-read-request/1 or projected /3; never starts a model")
    parser.add_argument(
        "--source-reader-v2",
        action="store_true",
        help="compatibility no-op: SourceRef v2 is the only default; "
        "the legacy normalized-body reader is no longer reachable",
    )
    parser.add_argument("--company-wiki-catalog-config", type=Path, default=None)
    parser.add_argument("--source-reader-receipt-version", choices=("2.1", "2.2"), default="2.1",
                        help="declared producer receipt capability; 2.2 explicitly requests availability evidence")
    parser.add_argument("--timeout-seconds", type=float, default=900.0)
    parser.add_argument(
        "--company-wiki-config",
        type=Path,
        default=None,
        help="override company-wiki config for the chain (E2E)",
    )
    parser.add_argument(
        "--filing-fetch-root",
        type=Path,
        default=None,
        help="override the filing-fetch skill root for the chain (E2E)",
    )
    args = parser.parse_args(argv)

    for stream in (sys.stdin, sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")

    try:
        request = _read_request(args.request_file)
        prepare = prepare_source_result if args.result_envelope else prepare_source
        narrative_request = (json.loads(args.narrative_request_file.read_text(encoding="utf-8"))
                             if args.narrative_request_file else None)
        record = prepare(
            request,
            allow_download=args.allow_download,
            timeout_seconds=args.timeout_seconds,
            company_wiki_config=args.company_wiki_config,
            filing_fetch_root=args.filing_fetch_root,
            source_reader_v2=args.source_reader_v2,
            company_wiki_catalog_config=args.company_wiki_catalog_config,
            narrative_request=narrative_request,
            source_reader_receipt_version=args.source_reader_receipt_version,
        )
    except (json.JSONDecodeError, ValueError) as exc:
        sys.stderr.write(json.dumps({"error_code": "bad_request", "error": str(exc)}))
        sys.stderr.write("\n")
        return 2
    except RuntimeError as exc:
        failure = {"error_code": "upstream", "error": str(exc)}
        failure.update(failure_observation({key: getattr(exc, key, None) for key in
                       ("upstream_cause", "acquisition_failure", "stage", "attempts", "calls", "downloads",
                        "source_failure_reason", "acquisition_observation", "request_diagnostic")}))
        sys.stderr.write(json.dumps(failure))
        sys.stderr.write("\n")
        return 3
    sys.stdout.write(json.dumps(record, ensure_ascii=False, indent=2))
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
