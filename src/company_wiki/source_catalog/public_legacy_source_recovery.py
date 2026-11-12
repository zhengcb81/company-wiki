"""Explicit exact-source recovery over the existing metadata-only restore gate.

Preview verifies the one pinned inactive original without restoring it. Apply
replays the same checks inside restore_document_facts' existing owner lock and
transaction. Ordinary browse/read never invokes this admin composition.
"""

from __future__ import annotations

from dataclasses import asdict
import hashlib
import json
import re
from typing import Any

from .assertion_service import restore_document_facts, source_issuer_identity
from .cn_primary_issuer import observe_cn_original, pdf_text_pages
from .local_inventory import (
    LocalPrepareLimits,
    LocalReadBudget,
    metadata_retirement,
    observe_document,
    verify_registered_original,
)
from .public_legacy_source_link import legacy_source_key
from .resolver import SourceRequest
from .source_location import relative_segments
from .source_reader import SourceReadError, SourceRef

REQUEST_SCHEMA = "company-wiki-legacy-source-recovery-request/1"
RESPONSE_SCHEMA = "company-wiki-legacy-source-recovery/1"
_FIELDS = {
    "schema_version",
    "legacy_source_id",
    "expected_source_sha256",
    "expected_retirement_observation_sha256",
    "expected_retirement_audit_ids",
    "source_request",
}
_SCOPE_FIELDS = {
    "entity",
    "document_kind",
    "as_of_date",
    "market",
    "security_id",
    "fiscal_year",
    "fiscal_period",
    "mode",
    "allow_download",
}
_SHA = re.compile(r"[0-9a-f]{64}\Z")
_KEY = re.compile(r"src_[0-9a-f]{16}\Z")
_AUDIT = re.compile(r"retire-[0-9a-f]{32}\Z")


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def validate_request(request: Any) -> SourceRequest:
    if (
        not isinstance(request, dict)
        or set(request) != _FIELDS
        or request["schema_version"] != REQUEST_SCHEMA
    ):
        raise SourceReadError("blocked", "recovery_request_invalid")
    if not isinstance(request["legacy_source_id"], str) or not _KEY.fullmatch(
        request["legacy_source_id"]
    ):
        raise SourceReadError("blocked", "recovery_legacy_source_id_invalid")
    for field in ("expected_source_sha256", "expected_retirement_observation_sha256"):
        if not isinstance(request[field], str) or not _SHA.fullmatch(request[field]):
            raise SourceReadError("blocked", "recovery_pin_invalid")
    audits = request["expected_retirement_audit_ids"]
    if (
        not isinstance(audits, list)
        or not 1 <= len(audits) <= 64
        or any(
            not isinstance(value, str) or not _AUDIT.fullmatch(value)
            for value in audits
        )
        or len(set(audits)) != len(audits)
    ):
        raise SourceReadError("blocked", "recovery_audit_pin_invalid")
    scope = request["source_request"]
    if not isinstance(scope, dict) or set(scope) != _SCOPE_FIELDS:
        raise SourceReadError("blocked", "recovery_scope_invalid")
    if (
        scope["market"] != "CN"
        or scope["mode"] != "exact"
        or scope["allow_download"] is not False
        or not isinstance(scope["entity"], str)
        or len(scope["entity"]) > 200
        or any(char in scope["entity"] for char in "/\\")
        or not isinstance(scope["security_id"], str)
        or not re.fullmatch(r"[0-9]{6}", scope["security_id"])
    ):
        raise SourceReadError("blocked", "recovery_scope_invalid")
    return SourceRequest(**scope)


def _exact_candidate(catalog, request) -> SourceRef:
    rows = catalog.reader.fetchall(
        """SELECT l.document_id,l.source_id,l.root_id,l.relative_path,l.absolute_path,
                  s.content_sha256,s.byte_size,s.mime_type
           FROM locations l JOIN sources s ON s.source_id=l.source_id
           WHERE s.content_sha256=? AND l.role='original_primary'""",
        (request["expected_source_sha256"],),
    )
    if len(rows) > 256:
        raise SourceReadError("unavailable", "recovery_location_limit")
    roots = {root.root_id: root for root in catalog.config.roots}
    matches = {}
    for row in rows:
        aliases = {str(row["absolute_path"] or "")}
        root = roots.get(str(row["root_id"]))
        segments = relative_segments(str(row["relative_path"]))
        if root is not None and segments is not None:
            aliases.add(str(root.path.joinpath(*segments)))
        if not any(
            value and legacy_source_key(value) == request["legacy_source_id"]
            for value in aliases
        ):
            continue
        ref = SourceRef(
            document_id=str(row["document_id"]),
            source_id=str(row["source_id"]),
            content_sha256=str(row["content_sha256"]),
            byte_size=int(row["byte_size"]),
            mime_type=str(row["mime_type"]),
            schema_version="2.0",
        )
        matches[(ref.document_id, ref.source_id, ref.content_sha256)] = ref
    if len(matches) != 1:
        raise SourceReadError("blocked", "recovery_exact_candidate_not_unique")
    return next(iter(matches.values()))


def recover_legacy_source(
    catalog, request: dict[str, Any], *, operation: str
) -> dict[str, Any]:
    scope = validate_request(request)
    if operation not in {"preview", "apply"}:
        raise SourceReadError("blocked", "recovery_operation_invalid")
    ref = _exact_candidate(catalog, request)
    observation = observe_document(catalog, ref.document_id)
    digest = hashlib.sha256(_canonical(observation)).hexdigest()
    if (
        digest != request["expected_retirement_observation_sha256"]
        or [item["audit_id"] for item in observation["retire_audit"]]
        != request["expected_retirement_audit_ids"]
    ):
        raise SourceReadError("unavailable", "recovery_retirement_observation_changed")
    if observation["version"]["source_status"] != "retired" or not metadata_retirement(
        observation
    ):
        raise SourceReadError("blocked", "retirement_not_metadata_only")
    if ref.mime_type != "application/pdf" or ref.byte_size > 16_000_000:
        raise SourceReadError("blocked", "recovery_native_cn_pdf_required")
    identity = source_issuer_identity(
        catalog, scope, catalog.config.catalog_dir / "security_master"
    )
    budget = LocalReadBudget(
        LocalPrepareLimits(max_candidates=8, max_bytes=64_000_000, timeout_seconds=30)
    )
    observed_facts = []
    original_proofs = []

    def qualify(original):
        # Recheck native period and security even if old assertions happen to
        # contain complete-looking fields. No other candidate is inspected.
        pages = pdf_text_pages(original.data)
        proof = observe_cn_original(
            catalog,
            ref,
            pages=pages,
            metadata={
                "market": "CN",
                "document_kind": scope.document_kind,
                "security_id": scope.security_id,
            },
        )
        legal_name = proof["legal_name"].replace("（", "(").replace("）", ")")
        covers: dict[tuple[int, str], tuple[int, str]] = {}
        headings = []
        for page_number, raw in enumerate(pages[:50], start=1):
            lines = [
                "".join(line.split()).replace("（", "(").replace("）", ")")
                for line in raw.splitlines()
                if line.strip()
            ]
            heading = "".join(lines[:6])
            if legal_name in heading:
                headings.append((page_number, heading))
        if not headings:
            raise SourceReadError("blocked", "recovery_primary_header_issuer_missing")
        for page_number, heading in headings:
            for match in re.finditer(
                r"(20[0-9]{2})年?(半年度|年度|第一季度|第二季度|第三季度|第四季度)报告",
                heading,
            ):
                covers.setdefault((int(match[1]), match[2]), (page_number, match[0]))
        if len(covers) != 1:
            raise SourceReadError("blocked", "recovery_primary_cover_ambiguous")
        (year, label), (page_number, title) = next(iter(covers.items()))
        period = {
            "年度": "FY",
            "半年度": "H1",
            "第一季度": "Q1",
            "第二季度": "Q2",
            "第三季度": "Q3",
            "第四季度": "Q4",
        }[label]
        kind = (
            "annual_report"
            if period == "FY"
            else "semi_annual_report"
            if period == "H1"
            else "quarterly_report"
        )
        cover = {
            "entity": identity.canonical_name,
            "market": "CN",
            "security_id": proof["security"]["security_id"],
            "document_kind": kind,
            "fiscal_year": year,
            "fiscal_period": period,
            "title": proof["legal_name"] + " " + title,
        }
        for field in (
            "market",
            "security_id",
            "document_kind",
            "fiscal_year",
            "fiscal_period",
        ):
            if cover.get(field) != getattr(scope, field):
                raise SourceReadError("blocked", "recovery_native_scope_conflict")
        facts = {**cover, "published_date": None, "source_url": None}
        evidence = {
            field: {
                "value": value,
                "locator": f"pdf:page:{page_number}:primary-periodic-header",
                "content_sha256": ref.content_sha256,
                "extraction_method": "cn-primary-header-with-uscc/1",
                "primary_uscc": proof["key"]["value"],
            }
            for field, value in cover.items()
        }
        from .source_availability import capture_observation, verified_open_observation

        evidence["published_date"] = {
            "value": None,
            "locator": "source-observation:publication-unknown",
            "verified_open": verified_open_observation(original),
        }
        captured = capture_observation(catalog, ref, budget=budget)
        if captured is not None:
            evidence["published_date"]["availability_capture"] = captured
        evidence["source_url"] = {
            "value": None,
            "locator": "source-observation:url-unknown",
        }
        observed_facts.append((facts, evidence))
        original_proofs.append(proof)
        return facts, evidence

    if operation == "preview":
        original = verify_registered_original(catalog, ref, budget=budget)
        qualify(original)
        if observe_document(catalog, ref.document_id) != observation:
            raise SourceReadError(
                "unavailable", "recovery_retirement_observation_changed"
            )
        result = {
            "status": "ready_to_restore",
            "assertion_id": None,
            "restore_audit_id": None,
        }
    else:
        result = restore_document_facts(
            catalog,
            ref=ref,
            retirement_observation=observation,
            budget=budget,
            fact_replay=qualify,
        )
    facts, evidence = observed_facts[0]
    value = {
        "schema_version": RESPONSE_SCHEMA,
        "operation": operation,
        "status": result["status"],
        "legacy_source_id": request["legacy_source_id"],
        "source_ref": asdict(ref),
        "retirement_observation_sha256": digest,
        "retirement_audit_ids": request["expected_retirement_audit_ids"],
        "native_scope": {
            field: facts.get(field)
            for field in (
                "entity",
                "market",
                "security_id",
                "document_kind",
                "fiscal_year",
                "fiscal_period",
                "published_date",
            )
        },
        "native_original_issuer_proof": original_proofs[0],
        "facts_sha256": hashlib.sha256(_canonical(facts)).hexdigest(),
        "evidence_sha256": hashlib.sha256(_canonical(evidence)).hexdigest(),
        "assertion_id": result.get("assertion_id"),
        "restore_audit_id": result.get("restore_audit_id"),
        "download_events": 0,
        "model_calls": 0,
    }
    value["receipt_sha256"] = hashlib.sha256(_canonical(value)).hexdigest()
    return value
