"""Source-owned scope qualification; scan declarations never prove writer origin."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json
from types import SimpleNamespace
from typing import Any

from .assertion_service import (
    _evidence_payload, _sec_original, _validate_source_facts, get_verified_assertion,
)
from .resolver import SourceRequest
from .store import canonical_json


class ScopeRelation(str, Enum):
    MATCH = "match"
    NOT_RELEVANT = "not_relevant"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class SourceScope:
    facts: dict[str, Any]
    evidence: dict[str, Any]
    authority: str

    def identity(self):
        if not all(self.facts.get(key) for key in ("entity", "market", "security_id")):
            return None
        return SimpleNamespace(canonical_name=self.facts["entity"], market=self.facts["market"],
            security_id=self.facts["security_id"], ticker=self.facts["security_id"])


def _same(left, right):
    return " ".join(str(left).split()).casefold() == " ".join(str(right).split()).casefold()


def scope_relatedness(scope: SourceScope, request: SourceRequest) -> ScopeRelation:
    """A known different period is irrelevant; an unproven identity is not an empty lake."""
    if scope.authority not in {"source-facts", "historical-canonical-request"}:
        return ScopeRelation.UNKNOWN
    facts = scope.facts
    for key in ("entity", "market", "security_id"):
        expected = getattr(request, key)
        actual = facts.get(key)
        if expected is not None and (actual is None or not _same(expected, actual)):
            return ScopeRelation.UNKNOWN
    if not facts.get("document_kind"):
        return ScopeRelation.UNKNOWN
    for key in ("document_kind", "fiscal_year", "fiscal_period", "form_type",
                "provider", "provider_document_id", "language"):
        expected = getattr(request, key)
        actual = facts.get(key)
        if expected is not None and actual is not None and not _same(expected, actual):
            return ScopeRelation.NOT_RELEVANT
    if any(getattr(request, key) is not None and facts.get(key) is None
           for key in ("fiscal_year", "fiscal_period", "form_type", "provider",
                       "provider_document_id", "language")):
        return ScopeRelation.UNKNOWN
    return ScopeRelation.MATCH


class HistoricalCaptureScopes:
    """One bounded journal observation per local operation, no persistent second store."""
    def __init__(self, catalog, budget):
        self.catalog, self.budget = catalog, budget
        self._attempts = None

    def _read(self):
        if self._attempts is not None:
            return self._attempts
        from .source_reader import SourceReadError
        path = self.catalog.config.catalog_dir / "acquisition_attempts.jsonl"
        self._attempts = {}
        self.budget.check()
        try:
            size = path.stat().st_size
        except FileNotFoundError:
            return self._attempts
        if size > min(4194304, self.budget.max_bytes - self.budget.bytes_read):
            raise SourceReadError("unavailable", "local_journal_byte_limit")
        with path.open("rb") as stream:
            data = stream.read(size + 1)
        stop = self.budget.charge(len(data))
        if stop:
            raise SourceReadError("unavailable", stop)
        if len(data) != size:
            raise SourceReadError("unavailable", "local_journal_changed")
        try:
            for raw in data.splitlines():
                self.budget.check()
                item = json.loads(raw)
                if not isinstance(item, dict):
                    continue
                values = {k:v for k,v in item.items() if k not in {"schema_version","attempt_id","recorded_at"}}
                digest = hashlib.sha256(canonical_json(values).encode()).hexdigest()
                if (item.get("schema_version") == "1.0"
                    and item.get("outcome") in {"downloaded_new", "deduplicated_after_download"}
                    and item.get("attempt_id") == "urn:company-wiki:acquisition-attempt:sha256:" + digest):
                    self._attempts.setdefault(item.get("content_sha256"), []).append(item)
        except (ValueError, TypeError, RecursionError):
            raise SourceReadError("blocked", "local_journal_unreadable") from None
        return self._attempts

    def scope(self, ref, document):
        metadata = document.get("metadata") or {}
        capture = metadata.get("acquisition") if isinstance(metadata, dict) else None
        if not isinstance(capture, dict) or not isinstance(capture.get("request"), dict):
            return None
        try:
            request = SourceRequest(**capture["request"])
        except (TypeError, ValueError):
            return None
        candidate = capture.get("candidate")
        receipt = capture.get("receipt")
        if not isinstance(candidate, dict) or not isinstance(receipt, dict):
            return None
        if (capture.get("request_id") != request.request_id
            or capture.get("content_sha256") != ref.content_sha256
            or receipt.get("content_sha256") != ref.content_sha256
            or receipt.get("byte_size") != ref.byte_size
            or receipt.get("mime_type") != ref.mime_type):
            return None
        for item in self._read().get(ref.content_sha256, ()):
            if item.get("request_id") != request.request_id:
                continue
            keys = ("candidate_id", "provider", "provider_document_id", "source_url")
            if not all(item.get(k) and item[k] == candidate.get(k) == receipt.get(k) for k in keys):
                continue
            facts = {key:value for key,value in request.identity_dict().items()
                     if key in {"entity","market","security_id","document_kind","form_type",
                                "fiscal_year","fiscal_period","provider","provider_document_id","language"}
                     and value is not None}
            return SourceScope(facts, {}, "historical-canonical-request")
        return None


def qualified_source_scope(catalog, ref, document, *, historical=None) -> SourceScope:
    """Only a source-layer verified row or genuine historical commit may qualify scope."""
    metadata = document.get("metadata") or {}
    capture = metadata.get("acquisition") if isinstance(metadata, dict) else {}
    market = capture.get("market") if isinstance(capture, dict) else None
    if _sec_original(ref, market, document.get("document_kind")):
        # SEC HTML's owner uses actual primary DEI, including its existing native proof cache.
        return SourceScope({}, {}, "primary-original-required")
    prior = get_verified_assertion(catalog.reader, ref.source_id, ref.content_sha256, reader="steady")
    if prior and prior["document_id"] == ref.document_id and prior["evidence_basis"] == "source-facts":
        payload = _evidence_payload(prior["evidence_json"], prior["assertion_id"])
        facts, evidence = payload.get("source_fact_patch"), payload.get("source_fact_evidence")
        if not isinstance(facts, dict) or not isinstance(evidence, dict):
            raise ValueError("source facts must be a nonempty object of known fields")
        _validate_source_facts(facts, evidence)
        commit = payload.get("canonical_commit")
        if commit is not None:
            from .source_reader import SourceReadError
            valid = isinstance(commit,dict)
            if valid:
                digest = hashlib.sha256(canonical_json(
                    {k:v for k,v in commit.items() if k != "sha256"}).encode()).hexdigest()
                receipt = commit.get("receipt") or {}
                valid = (commit.get("owner") == "CanonicalSourceWriter"
                    and commit.get("schema_version") == "1.0" and commit.get("sha256") == digest
                    and isinstance(receipt,dict)
                    and (receipt.get("content_sha256"),receipt.get("byte_size"),receipt.get("mime_type"))
                        == (ref.content_sha256,ref.byte_size,ref.mime_type)
                    and all(proof.get("commit_sha256") == digest for proof in evidence.values()
                            if proof.get("extraction_method") == "provider-metadata-import/1"))
            if not valid:
                raise SourceReadError("blocked","canonical_capture_binding_conflict")
        return SourceScope(facts, evidence, "source-facts")
    if historical is not None:
        known = historical.scope(ref, document)
        if known is not None:
            return known
    return SourceScope({}, {}, "unverified-declaration")
