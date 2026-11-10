"""Build revenue source/capture records from a filing-fetch handle.

The standalone ``filing-fetch`` skill (via ``filing_fetch_client``) owns
identity, reuse-first lookup, market-routed download, canonical write, and
provenance — delegating to ``company-wiki``. This module keeps only the
revenue-specific conversion: turning one capture-ready handle into a
schema-3.6 source record with an immutable capture receipt. It verifies the
local whole-file hash but does not claim that a passage supports any revenue
parameter.

The bundled ``filing_acquisition.py`` is **deprecated** — new callers must
use ``filing_fetch_client.resolve_filing()`` or invoke the filing-fetch CLI
directly.
"""

from __future__ import annotations

from datetime import date, datetime
import hashlib
import json
from pathlib import Path
import re
from typing import Any


_SOURCE_TYPES = {
    "audited_filing",
    "exchange_filing",
    "regulatory_filing",
    "official_statistics",
    "company_release",
    "investor_presentation",
    "earnings_transcript",
    "official_operating_data",
    "contract_award",
    "customer_filing",
    "tender_document",
    "sector_regulator",
    "industry_association",
    "primary_market_dataset",
    "specialist_research",
    "reputable_news",
}
_PROMPT_INJECTION_STATUSES = {
    "not_reviewed", "not_detected", "detected_and_ignored",
}
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class CompanyWikiSourceError(RuntimeError):
    """Raised when a capture-ready source cannot be built from a handle."""


def _canonical_sha256(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _required_text(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise CompanyWikiSourceError(f"{field_name} must be non-empty trimmed text")
    return value


def _iso_date(value: Any, field_name: str) -> date:
    text = _required_text(value, field_name)
    try:
        parsed = date.fromisoformat(text)
    except ValueError as exc:
        raise CompanyWikiSourceError(f"{field_name} must use YYYY-MM-DD") from exc
    if parsed.isoformat() != text:
        raise CompanyWikiSourceError(f"{field_name} must be canonical YYYY-MM-DD")
    return parsed


def _bundle_from_handle(handle: dict[str, Any]) -> dict[str, Any] | None:
    """FC-902/FC-904: the SourceBundle rides the resolution envelope (the
    FC-704-era handle-level ``source_bundle`` field is gone).  None when the
    envelope has no bundle (bundle_status=unavailable or N-1 upstream)."""
    if not isinstance(handle, dict):
        raise CompanyWikiSourceError("handle must be a dict")
    envelope = handle.get("resolution_envelope")
    if not isinstance(envelope, dict):
        return None
    return envelope.get("bundle")


def _artifact_reusable(bundle: dict[str, Any], role: str) -> bool:
    valid = bundle.get("valid_handles")
    if not isinstance(valid, dict):
        raise CompanyWikiSourceError(
            "bundle.valid_handles must be an object (fail closed)")
    artifact = valid.get(role)
    return isinstance(artifact, dict) and artifact.get("reusable") is True


def _dag_ancestors(role: str) -> list[str]:
    """Transitive inputs of ``role`` (roles it derives from) over the same
    imported ROLE_DEPENDENCIES: ROLE_DEPENDENCIES[role] IS the direct parent
    list, walked transitively.  A role is read ONLY when every ancestor is
    also reusable (AR-03: a changed normalized invalidates its dependents)."""
    from company_wiki.source_catalog.artifact_dag import ROLE_DEPENDENCIES

    result: list[str] = []
    seen: set[str] = set()
    frontier = list(ROLE_DEPENDENCIES.get(role, ()))
    while frontier:
        current = frontier.pop()
        if current in seen:
            continue
        seen.add(current)
        result.append(current)
        frontier.extend(ROLE_DEPENDENCIES.get(current, ()))
    return result


def _production_scope(
    roles: tuple[str, ...],
    reusable: set[str],
    artifact_read: list[str],
) -> list[str]:
    """The roles that must be (re)produced for THIS request: every requested
    role that is not readable, plus every non-reusable ancestor those roles
    need.  Never the downstream closure of the requested roles — an
    unrequested dependent is not produced (I-05-C step 2: 不盲补所有下游).

    Shared by BOTH ``select_artifact_roles`` branches: the bundle-present path
    passes the roles the bundle proved reusable, the ``bundle=None`` path
    passes an empty set (nothing can be proven reusable without a bundle), so
    the two branches cannot drift into different "what must be produced"
    rules again (REM-11)."""
    needs: set[str] = set()
    for role in roles:
        if role in artifact_read:
            continue
        needs.add(role)
        for ancestor in _dag_ancestors(role):
            if ancestor not in reusable:
                needs.add(ancestor)
    return sorted(needs)


def select_artifact_roles(
    handle: dict[str, Any],
    roles: tuple[str, ...] = ("normalized", "markdown", "summary",
                              "sections", "consumer_analysis"),
    *,
    expected_provenance: dict[str, Any] | None = None,
) -> tuple[list[str], list[str]]:
    """FC-904: DAG-minimal artifact selection from the envelope bundle.

    Returns ``(artifact_read, producer_events)``:

    - ``artifact_read`` — roles that may be READ: the role has a verified
      artifact in the envelope bundle's ``valid_handles`` AND every transitive
      ancestor is also reusable (AR-03: a dependent derived from an invalidated
      input is not trusted).  ``consumer_analysis`` additionally requires a
      full provenance match when ``expected_provenance`` is given.  Role
      reusability is evaluated over the REQUEST closure (the requested roles
      plus their transitive ancestors), so a valid ancestor is still reported
      when its dependent is missing from the bundle.  Read roles' producers do
      NOT run (parser/LLM=0).
    - ``producer_events`` — roles that must be (re)produced for THIS request:
      each requested role that is not readable, plus every ancestor of those
      roles that is not reusable.  It is NOT the downstream closure of the
      requested roles — an unrequested dependent is never produced
      (AR-02/AR-03, I-05-C step 2).

    ``bundle=None`` (bundle_status=unavailable) → ``artifact_read=[]`` (nothing
    can be proven reusable, never faked) and ``producer_events`` follows the
    SAME request-scoped rule with an empty reusable set: the requested roles
    plus all their transitive ancestors.  So a ``normalized``-only request
    produces only ``normalized``, while a request naming all roles still
    produces all of them.  A malformed bundle raises (fail closed), never
    silently trusted.
    """
    bundle = _bundle_from_handle(handle)
    if bundle is None:
        # REM-11: request-scoped, exactly like the bundle-present branch below.
        # The old downstream closure of `roles` meant a normalized-only request
        # scheduled every role, contradicting the "ONLY requested" contract.
        return [], _production_scope(roles, set(), [])
    if not isinstance(bundle, dict):
        raise CompanyWikiSourceError("bundle must be an object (fail closed)")
    reusable: set[str] = set()
    # W05-C fix: check ALL roles in the request closure (requested roles AND
    # their transitive ancestors), not just the directly requested roles.
    # Without this, a valid ancestor (normalized) is never evaluated when its
    # dependent (sections) is missing from the bundle — causing artifact_read
    # to be empty even though the ancestor is perfectly reusable.
    all_roles_to_check = sorted({
        r for role in roles for r in ([role] + _dag_ancestors(role))
    })
    for role in all_roles_to_check:
        if not _artifact_reusable(bundle, role):
            continue
        if role == "consumer_analysis" and expected_provenance is not None:
            artifact = bundle["valid_handles"][role]
            if not _analysis_provenance_matches(artifact, expected_provenance):
                continue
        reusable.add(role)
    # DAG gate (AR-03): a role is READ only when its whole ancestor chain is
    # reusable — a dependent derived from an invalidated input is not trusted.
    # W05-C: include valid ancestors in artifact_read too — the caller needs
    # to know they're available for consumption, even if not explicitly requested.
    artifact_read = sorted(
        role for role in all_roles_to_check
        if role in reusable
        and all(ancestor in reusable for ancestor in _dag_ancestors(role))
    )
    # producer_events must contain ONLY what's needed to produce the REQUESTED
    # missing roles — the missing role itself plus any ancestors that are not
    # reusable.  NOT the full downstream closure of unrequested dependents
    # (which was the old bug).  Same helper the bundle=None branch uses, so the
    # two paths cannot diverge (REM-11).
    producer_events = _production_scope(roles, reusable, artifact_read)
    return artifact_read, producer_events


def verify_artifact_reads(
    handle: dict[str, Any],
    selected_roles: list[str],
) -> dict[str, Any]:
    """W05-B: verified artifact read — actual IO with hash proof.

    ``selected_roles`` is the PLAN from ``select_artifact_roles``; this
    function performs the ACTUAL file read and returns evidence.

    Returns ``{"verified_read_events": [...], "failed_read_events": [...]}``:

    - ``verified_read_events``: each event has role, artifact_path,
      content_sha256_actual, content_sha256_declared, bytes_read,
      source_sha256, read_status="verified", read_at.
    - ``failed_read_events``: events for roles whose read failed, with
      reason and detail.

    The plan (``selected_roles``) proves intent; these events prove IO.
    Without verified events, the card fails validation.
    """
    bundle = _bundle_from_handle(handle)
    if bundle is None:
        return {"verified_read_events": [], "failed_read_events": []}
    valid_handles = bundle.get("valid_handles")
    if not isinstance(valid_handles, dict):
        return {"verified_read_events": [], "failed_read_events": []}
    source = bundle.get("source", {})
    source_sha256 = str(source.get("source_sha256") or "")
    verified: list[dict[str, Any]] = []
    failed: list[dict[str, Any]] = []
    from datetime import datetime, UTC
    read_at = datetime.now(UTC).isoformat()
    for role in selected_roles:
        artifact = valid_handles.get(role)
        if not isinstance(artifact, dict):
            failed.append({
                "role": role,
                "artifact_path": None,
                "read_status": "failed",
                "reason": "artifact_not_in_bundle",
                "detail": f"role {role!r} not in valid_handles",
                "read_at": read_at,
            })
            continue
        declared_sha = str(artifact.get("content_sha256") or "")
        artifact_path = str(artifact.get("path") or "")
        if not artifact_path:
            failed.append({
                "role": role,
                "artifact_path": None,
                "read_status": "failed",
                "reason": "artifact_path_missing",
                "detail": "artifact has no path",
                "read_at": read_at,
            })
            continue
        path = Path(artifact_path)
        if not path.is_file():
            failed.append({
                "role": role,
                "artifact_path": artifact_path,
                "read_status": "failed",
                "reason": "artifact_file_missing",
                "detail": f"file not found: {artifact_path}",
                "read_at": read_at,
            })
            continue
        try:
            actual_bytes = path.read_bytes()
        except OSError as exc:
            failed.append({
                "role": role,
                "artifact_path": artifact_path,
                "read_status": "failed",
                "reason": "read_failed",
                "detail": str(exc),
                "read_at": read_at,
            })
            continue
        actual_sha = hashlib.sha256(actual_bytes).hexdigest()
        if declared_sha and actual_sha != declared_sha:
            failed.append({
                "role": role,
                "artifact_path": artifact_path,
                "read_status": "failed",
                "reason": "content_sha256_mismatch",
                "detail": f"declared={declared_sha[:12]} actual={actual_sha[:12]}",
                "bytes_read": len(actual_bytes),
                "content_sha256_actual": actual_sha,
                "content_sha256_declared": declared_sha,
                "read_at": read_at,
            })
            continue
        verified.append({
            "role": role,
            "artifact_path": artifact_path,
            "read_status": "verified",
            "content_sha256_actual": actual_sha,
            "content_sha256_declared": declared_sha,
            "bytes_read": len(actual_bytes),
            "source_sha256": source_sha256,
            "read_at": read_at,
        })
    return {"verified_read_events": verified, "failed_read_events": failed}


def select_reusable_artifacts(
    handle: dict[str, Any],
    roles: tuple[str, ...],
    *,
    expected_provenance: dict[str, Any] | None = None,
) -> dict[str, dict[str, Any]]:
    """WU-5.4: pick verified artifacts from the envelope bundle.

    For each requested role, returns the VALID artifact
    (path/content_sha256/generator) so the revenue consumer can skip
    re-parsing / re-summarizing when a verified normalized/summary/sections
    artifact exists. Fail-closed: a missing or invalid artifact is simply
    not returned (consumer falls back to the original); a malformed bundle
    raises instead of being silently trusted.

    ``expected_provenance`` (WU-6.2 E2E-D06): when given, a consumer_analysis
    artifact is reusable ONLY if its engine/model/prompt/input_bundle_hash
    all match the expected values — ANY change → not reused.
    """
    bundle = _bundle_from_handle(handle)
    if bundle is None:
        return {}
    if not isinstance(bundle, dict):
        raise CompanyWikiSourceError("bundle must be an object")
    selected: dict[str, dict[str, Any]] = {}
    for role in roles:
        if not _artifact_reusable(bundle, role):
            continue
        if role == "consumer_analysis" and expected_provenance is not None:
            if not _analysis_provenance_matches(
                    bundle["valid_handles"][role], expected_provenance):
                continue
        selected[role] = bundle["valid_handles"][role]
    return selected


_ANALYSIS_PROVENANCE_KEYS = (
    "engine",
    "model",
    "prompt",
    "input_bundle_hash",
)


def _analysis_provenance_matches(
    artifact: dict[str, Any], expected: dict[str, Any]
) -> bool:
    """E2E-D06: consumer analysis reuse requires FULL provenance match —
    engine/model/prompt/input_bundle_hash all equal the expected values."""
    for key in _ANALYSIS_PROVENANCE_KEYS:
        if artifact.get(key) != expected.get(key):
            return False
    return True


def build_revenue_source_record(
    handle: dict[str, Any],
    *,
    as_of_date: str,
    source_type: str,
    publisher: str,
    page_or_section: str,
    prompt_injection_status: str,
) -> dict[str, Any]:
    """Build a strict revenue source/capture record from one verified handle.

    ``handle`` is returned by ``filing_fetch_client.resolve_filing`` or the
    filing-fetch CLI.
    ``source_type``, ``publisher``, and evidence locator remain explicit caller
    judgments. Prompt-injection status is a diagnostic from the upstream
    envelope. This function verifies the whole local file hash but does not
    claim that a passage supports any revenue parameter.
    """

    if not isinstance(handle, dict):
        raise TypeError("handle must be a dict")
    as_of = _iso_date(as_of_date, "as_of_date")
    if source_type not in _SOURCE_TYPES:
        raise CompanyWikiSourceError(f"unsupported revenue source_type: {source_type}")
    publisher = _required_text(publisher, "publisher")
    locator = _required_text(page_or_section, "page_or_section")
    if prompt_injection_status not in _PROMPT_INJECTION_STATUSES:
        raise CompanyWikiSourceError(
            "invalid prompt_injection_status"
        )
    if handle.get("capture_ready") is not True:
        raise CompanyWikiSourceError("company-wiki handle is not capture_ready")
    published = _iso_date(handle.get("published_date"), "published_date")
    retrieved_at = _required_text(handle.get("retrieved_at"), "retrieved_at")
    try:
        captured = datetime.strptime(retrieved_at, "%Y-%m-%dT%H:%M:%SZ").date()
    except ValueError as exc:
        raise CompanyWikiSourceError(
            "retrieved_at must be UTC YYYY-MM-DDTHH:MM:SSZ"
        ) from exc
    from contracts.source_clock import SourceClockError, qualify_source_information, validate_source_events
    try:
        information = qualify_source_information(source_sha256=handle.get("snapshot_sha256"),
            published_date=published.isoformat(), as_of=as_of)
        validate_source_events(eligibility=information, original_retrieved_at=retrieved_at,
                               capture_date=captured.isoformat())
    except SourceClockError as exc:
        raise CompanyWikiSourceError(str(exc)) from exc
    snapshot_sha256 = _required_text(handle.get("snapshot_sha256"), "snapshot_sha256")
    if not _SHA256_RE.fullmatch(snapshot_sha256):
        raise CompanyWikiSourceError("snapshot_sha256 must be lowercase SHA-256")
    canonical_path = Path(
        _required_text(handle.get("canonical_path"), "canonical_path")
    )
    if not canonical_path.is_file():
        raise CompanyWikiSourceError(
            "canonical_path does not identify a local source file"
        )
    if _file_sha256(canonical_path) != snapshot_sha256:
        raise CompanyWikiSourceError(
            "canonical source bytes do not match snapshot_sha256"
        )
    url = _required_text(handle.get("https_url"), "https_url")
    if not url.startswith("https://"):
        raise CompanyWikiSourceError("https_url must use HTTPS")
    request_id = _required_text(handle.get("request_id"), "request_id")
    location_id = _required_text(
        handle.get("canonical_location_id"), "canonical_location_id"
    )
    capture = {
        "capture_schema_version": "1.0",
        "capture_method": "local_document",
        "tool_name": "revenue-forecast-filing-acquisition",
        "tool_call_id": f"{request_id}|{location_id}",
        "captured_date": captured.isoformat(),
        "snapshot_sha256": snapshot_sha256,
        "content_treatment": "untrusted_data_only",
        "prompt_injection_status": prompt_injection_status,
    }
    capture["host_receipt"] = {
        "host_receipt_schema_version": "1.0",
        "issuer": "filing-fetch-company-wiki",
        "environment": "host-runtime",
        "tool_name": capture["tool_name"],
        "action": "canonical_capture",
        "event_sha256": snapshot_sha256,
        "timestamp": captured.isoformat(),
    }
    capture["host_receipt"]["receipt_sha256"] = _canonical_sha256(
        capture["host_receipt"]
    )
    capture["receipt_sha256"] = _canonical_sha256(capture)
    return {
        "source_id": _required_text(handle.get("source_id"), "source_id"),
        "source_type": source_type,
        "title": _required_text(handle.get("title"), "title"),
        "publisher": publisher,
        "url": url,
        "published_date": published.isoformat(),
        "accessed_date": captured.isoformat(),
        "page_or_section": locator,
        "capture": capture,
        "company_wiki_trace": {
            "document_id": handle.get("document_id"),
            "source_id": handle.get("source_id"),
            "canonical_location_id": location_id,
            "canonical_path": str(canonical_path.resolve()),
            "provider": handle.get("provider"),
            "provider_document_id": handle.get("provider_document_id"),
            "collector_name": handle.get("collector_name"),
            "collector_version": handle.get("collector_version"),
        },
    }


__all__ = [
    "CompanyWikiSourceError",
    "build_revenue_source_record",
    "select_artifact_roles",
    "select_reusable_artifacts",
    "verify_artifact_reads",
]
