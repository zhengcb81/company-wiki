"""Guarded edits for this source-layer author line, after public behavior RED."""
from pathlib import Path

TREE=Path('C:/Users/郑曾波/Projects/_harness_worktrees/w06/cwp-acquisition-scope-root')
SRC=TREE/'src/company_wiki/source_catalog'
assert TREE.resolve().name=='cwp-acquisition-scope-root'

def edit(name, before, after):
    p=SRC/name
    s=p.read_text(encoding='utf-8')
    assert s.count(before)==1, (name, before[:80], s.count(before))
    p.write_text(s.replace(before,after),encoding='utf-8')

(SRC/'canonical_scope.py').write_text('''"""Source-owned scope qualification; scan declarations never prove writer origin."""
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
        _validate_source_facts(facts, evidence)
        return SourceScope(facts, evidence, "source-facts")
    if historical is not None:
        known = historical.scope(ref, document)
        if known is not None:
            return known
    return SourceScope({}, {}, "unverified-declaration")
''', encoding='utf-8')

edit('assertion_service.py',
     'def _prepare_source_fact_write(catalog, ref, current, facts, evidence):',
     'def _prepare_source_fact_write(catalog, ref, current, facts, evidence, *, assertion_store=None, capture_evidence=None):')
edit('assertion_service.py',
     '    prior = get_verified_assertion(catalog.reader, ref.source_id, ref.content_sha256, reader="steady")\n    previous_evidence',
     '    prior = get_verified_assertion(assertion_store or catalog.reader, ref.source_id, ref.content_sha256, reader="steady")\n    previous_evidence')
edit('assertion_service.py',
     '    evidence_payload = {"source_fact_patch": patch, "source_fact_evidence": field_evidence}',
     '    evidence_payload = {**previous_evidence, "source_fact_patch": patch, "source_fact_evidence": field_evidence}\n    if capture_evidence is not None:\n        evidence_payload["canonical_commit"] = capture_evidence')

edit('registration_scope.py',
     'scope: SourceRegistrationScope, *, progress=None, budget=None) -> ScanReport:',
     'scope: SourceRegistrationScope, *, progress=None, budget=None, on_registered=None) -> ScanReport:')
edit('registration_scope.py',
     'v2_scan_shadow=bool(selected.adapter_id), progress=progress, budget=budget)',
     'v2_scan_shadow=bool(selected.adapter_id), progress=progress, budget=budget,\n                         on_registered=on_registered)')
edit('scanner.py',
     '    zero_diff_rounds: int | None = None,\n    budget=None,\n) -> ScanReport:',
     '    zero_diff_rounds: int | None = None,\n    budget=None,\n    on_registered=None,\n) -> ScanReport:')
edit('scanner.py',
     '    if relative_paths is not None:\n        if not root_ids or len(root_ids) != 1:',
     '    if on_registered is not None and (not callable(on_registered) or dry_run\n            or relative_paths is None or len(relative_paths) != 1):\n        raise ValueError("writer facts require one explicit registration group")\n    if relative_paths is not None:\n        if not root_ids or len(root_ids) != 1:')
edit('scanner.py',
     '        with store.coalesced_transactions(max_operations=250):\n            return _scan_catalog_impl(',
     '        with store.coalesced_transactions(max_operations=250):\n            report = _scan_catalog_impl(')
edit('scanner.py',
     '                budget=budget,\n            )\n    except Exception:\n        _interrupt_scan_run(store, run_id)',
     '                budget=budget,\n            )\n            if on_registered is not None:\n                on_registered(store)\n            return report\n    except Exception:\n        _interrupt_scan_run(store, run_id)')

hook='''    def _record_validated_capture(self, request, candidate, receipt, store):
        """Internal writer event, never reconstructed from a scanner-side declaration."""
        if not isinstance(request, SourceRequest) or not isinstance(candidate, DownloadCandidate):
            # Official JSON/shared source intake has its own source-fact owner.
            return
        from .assertion_service import (
            _evidence_payload, _prepare_source_fact_write, _validate_source_facts,
            _write_source_fact_projection, get_verified_assertion,
        )
        from .source_reader import SourceRef

        source_id = source_id_for_sha256(receipt.content_sha256)
        document_id = source_id.replace("urn:company-wiki:source:", "urn:company-wiki:document:")
        row = store.fetchone("SELECT * FROM sources WHERE source_id=?", (source_id,))
        if row is None or (row["content_sha256"], row["byte_size"], row["mime_type"]) != (
                receipt.content_sha256, receipt.byte_size, receipt.mime_type):
            raise CanonicalImportError("canonical_registered_version_conflict")
        ref = SourceRef(document_id, source_id, receipt.content_sha256, receipt.byte_size, receipt.mime_type)
        facts = {"entity": request.entity, "market": candidate.market,
            "security_id": request.security_id, "document_kind": candidate.document_kind,
            "fiscal_year": candidate.fiscal_year, "fiscal_period": candidate.fiscal_period,
            "form_type": candidate.form_type, "published_date": candidate.filing_date,
            "filing_date": candidate.filing_date, "provider": candidate.provider,
            "provider_document_id": candidate.provider_document_id, "source_url": candidate.source_url,
            "language": candidate.language, "title": candidate.title}
        claim = {"owner": "CanonicalSourceWriter", "schema_version": "1.0",
            "request": request.identity_dict(),
            "candidate": {key:getattr(candidate,key) for key in (
                "candidate_id", "provider", "provider_document_id", "market", "entity",
                "title", "source_url", "document_kind", "filing_date", "fiscal_year",
                "fiscal_period", "form_type", "language")},
            "receipt": {key:getattr(receipt,key) for key in (
                "candidate_id", "provider", "provider_document_id", "source_url",
                "content_sha256", "byte_size", "mime_type", "adapter_name", "adapter_version")}}
        claim_sha = hashlib.sha256(canonical_json(claim).encode("utf-8")).hexdigest()
        evidence = {key:{"locator":"canonical-commit:/" + (
                "request/security_id" if key=="security_id" else "candidate/" + key),
                "value":value, "content_sha256":ref.content_sha256,
                "commit_sha256":claim_sha, "extraction_method":"provider-metadata-import/1"}
            for key,value in facts.items()}
        prior = get_verified_assertion(store, ref.source_id, ref.content_sha256, reader="steady")
        if prior:
            old = _evidence_payload(prior["evidence_json"],prior["assertion_id"])
            previous = old.get("source_fact_patch") or {}
            for key,value in previous.items():
                if key in {"entity","market","security_id","document_kind","fiscal_year","fiscal_period","form_type"} and key in facts and value is not None and facts[key] is not None:
                    left, right = str(value).casefold(), str(facts[key]).casefold()
                    if left != right:
                        raise CanonicalImportError("canonical_scope_conflict:" + key)
            # An explicit correction/unknown is stronger than another provider declaration.
            facts = {key:value for key,value in facts.items() if key not in previous}
            evidence = {key:value for key,value in evidence.items() if key in facts}
        if not facts:
            return
        _validate_source_facts(facts,evidence)
        assertion, projection, _ = _prepare_source_fact_write(
            self.catalog,ref,{"display_name":request.entity},facts,evidence,
            assertion_store=store,capture_evidence={**claim,"sha256":claim_sha})
        if assertion is not None:
            with store.transaction() as connection:
                _write_source_fact_projection(connection,ref,assertion,projection)

'''
edit('canonical_writer.py', '    def source_ref_for_import(\n', hook+'    def source_ref_for_import(\n')
edit('canonical_writer.py',
     '            if existing is not None:\n                source_ref = self.source_ref_for_import(request, candidate, receipt.content_sha256)',
     '            if existing is not None:\n                with self.catalog.store.transaction():\n                    self._record_validated_capture(request,candidate,receipt,self.catalog.store)\n                source_ref = self.source_ref_for_import(request, candidate, receipt.content_sha256)')
# The dedup transaction must use the same connection for prior facts; coalescing supplies that port.
edit('canonical_writer.py', '                with self.catalog.store.transaction():\n                    self._record_validated_capture',
     '                with self.catalog.store.coalesced_transactions():\n                    self._record_validated_capture')
edit('canonical_writer.py',
     '                    frozenset({destination.relative_to(self.company_root.path).as_posix()})),\n            )',
     '                    frozenset({destination.relative_to(self.company_root.path).as_posix()})),\n                on_registered=lambda store: self._record_validated_capture(request,candidate,receipt,store),\n            )')

# Prefilter trustworthy non-target sources, preserving the existing SEC primary owner path.
edit('local_reconcile.py', 'from .lock import CatalogOperationLockedError',
     'from .lock import CatalogOperationLockedError\nfrom .canonical_scope import HistoricalCaptureScopes, ScopeRelation, qualified_source_scope, scope_relatedness')
edit('local_reconcile.py',
     '    diagnostics = []\n    operations = []\n    qualified_documents = set()\n    targeted = False\n    try:\n        identity = identity or _identity(catalog, request, identity_cache_dir)',
     '''    diagnostics = []
    operations = []
    qualified_documents = set()
    targeted = False
    historical = HistoricalCaptureScopes(catalog,budget)
    eligible = []
    known_identity = None
    for candidate in candidates:
        budget.check()
        row = catalog.reader.exact_source_version(candidate["document_id"])
        ref = SourceRef(row["document_id"],row["source_id"],row["content_sha256"],row["byte_size"],row["mime_type"])
        scope = qualified_source_scope(catalog,ref,candidate,historical=historical)
        relation = scope_relatedness(scope,request)
        if relation is ScopeRelation.NOT_RELEVANT:
            known_identity = known_identity or scope.identity()
            diagnostics.append({"document_id":ref.document_id,"reason":"trusted_scope_not_relevant"})
            continue
        eligible.append(candidate)
        if relation is ScopeRelation.MATCH and scope.authority == "source-facts":
            known_identity = known_identity or scope.identity()
    candidates = eligible
    if not candidates:
        if not _discovery_done and known_identity and _discover_source_groups(catalog,known_identity,budget):
            return _prepare_local_source(catalog,request,identity_cache_dir=identity_cache_dir,
                limits=limits,_discovery_done=True,_budget=budget)
        return _result("not_found","no_matching_local_period",diagnostics=diagnostics)
    try:
        identity = identity or known_identity or _identity(catalog, request, identity_cache_dir)''')

edit('acquisition.py',
     '    acquisition_failure: dict[str, Any] | None = None\n\n    def to_dict',
     '    acquisition_failure: dict[str, Any] | None = None\n    local_preparation: dict[str, Any] | None = None\n\n    def to_dict')
edit('acquisition.py',
     '        if self.acquisition_failure is not None:\n            result["acquisition_failure"] = self.acquisition_failure\n        return result',
     '        if self.acquisition_failure is not None:\n            result["acquisition_failure"] = self.acquisition_failure\n        if self.local_preparation is not None:\n            result["local_preparation"] = self.local_preparation\n        return result')
edit('acquisition.py',
     '                resolution=resolution, reason=local["reason"])',
     '''                resolution=resolution, reason=local["reason"], local_preparation={
                    "status":local["status"],"reason":local["reason"],"blocks_download":True,
                    "causes":sorted({item["reason"] for item in local.get("diagnostics",())})})''')
edit('operation_contract.py',
     '    gap_plan: dict[str, Any] | None\n',
     '    gap_plan: dict[str, Any] | None\n    local_preparation: dict[str, Any] | None = None\n')
helper='''def _local_preparation(value):
    if value is None:
        return None
    diagnostic = _object(value,"local_preparation")
    if (set(diagnostic) != {"status","reason","blocks_download","causes"}
        or diagnostic["status"] not in {"blocked","unavailable","ambiguous"}
        or diagnostic["blocks_download"] is not True
        or not isinstance(diagnostic["causes"],list)):
        raise SourceOperationProjectionError("invalid local preparation diagnostic")
    reasons = [diagnostic["reason"],*diagnostic["causes"]]
    if not all(isinstance(reason,str) and re.fullmatch(r"[a-z][a-z0-9_]{0,79}",reason)
               for reason in reasons):
        raise SourceOperationProjectionError("local preparation reason must be a named code")
    return {"status":diagnostic["status"],"reason":diagnostic["reason"],
            "blocks_download":True,"causes":list(diagnostic["causes"])}


'''
edit('operation_contract.py', 'def parse_operation_payload(\n',helper+'def parse_operation_payload(\n')
edit('operation_contract.py',
     '    gap = acquisition_resolution = None\n    if typed_operation == "ensure":\n        _, gap, acquisition_resolution = _ensure_parts(result)',
     '    gap = acquisition_resolution = None\n    acquisition = {}\n    if typed_operation == "ensure":\n        acquisition, gap, acquisition_resolution = _ensure_parts(result)')
edit('operation_contract.py',
     '        gap_plan=gap,\n    )',
     '        gap_plan=gap,\n        local_preparation=_local_preparation(acquisition.get("local_preparation")),\n    )')
edit('operation_projection.py',
     '    if operation_input.producer_status == "gap":',
     '    if operation_input.local_preparation is not None:\n        return operation_input.local_preparation["status"], None, None\n    if operation_input.producer_status == "gap":')
edit('operation_projection.py',
     '    if _contains_physical_field(result):',
     '    if operation_input.local_preparation is not None:\n        result["local_preparation"] = operation_input.local_preparation\n    if _contains_physical_field(result):')

plan=TREE/'.planning/w06-cross-period-acquisition'
with (plan/'progress.md').open('a',encoding='utf-8') as f:
    f.write('''\n### A 正式行为 RED\npublic-behavior-red：6 FAIL / 1 PASS，3.697s；三市场跨年度及 HK 跨季度/半年期公共 writer 暖库→新期缺失全部实际 missing（旧期导入/零下载复用先通过）；pathless local blocker 实际误报 not_found。scan同形伪造未升为事实正控 PASS。此前3次测试接线错误（keyword-only构造器、bounded adapter、writer staging）留证，不当产品缺陷。全合成 scratch 恢复，无网络/费用。\n### B 实现\n已按上方细则写共用 scope、正常 writer 自动事实通道、有限注册同事务 hook、local 非目标预筛及 pathless named诊断；下一步范围测试及历史/冲突控制，不把代码已写当通过。\n''')
print('Common source-scope implementation written; no commit/install/config/raw changes')
