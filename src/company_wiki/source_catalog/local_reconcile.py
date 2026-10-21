"""Explicit local intake: prove existing facts, then use the unchanged public reader."""

from __future__ import annotations
from dataclasses import asdict, replace
from datetime import date
from pathlib import Path
import re
import os
from typing import Any
from .assertion_service import (
    SOURCE_FACT_FIELDS,
    _evidence_payload,
    get_verified_assertion,
    restore_document_facts,
    source_issuer_identity,
    source_scope_qualification,
    _sec_original,
    SOURCE_SCOPE_METHOD as SEC_SCOPE_METHOD,
)
from .dayu_fiscal_metadata import extract_sec_scope, complete_sec_primary, FiscalMetadataError
from .local_inventory import (
    LocalPrepareLimits,
    LocalReadBudget,
    metadata_retirement,
    observe_document,
)
from .resolver import (
    SourceRequest,
    SourceResolver,
    _needs_hydration,
    _inside_configured_roots,
)
from .source_reader import SourceReadError, SourceRef, SourceVersionReader
from .source_group_scope import SourceRegistrationScope
from .lock import CatalogOperationLockedError
from .canonical_scope import HistoricalCaptureScopes, ScopeRelation, qualified_source_scope, scope_relatedness

SCHEMA = "local-source-prepare/1"


def _result(status, reason, *, ref=None, blocks=False, operations=(), diagnostics=()):
    return {
        "schema_version": SCHEMA,
        "status": status,
        "reason": reason,
        "source_ref": asdict(ref) if ref else None,
        "blocks_download": blocks,
        "operations": list(operations),
        "diagnostics": list(diagnostics),
        "download_events": 0,
    }


def _identity(catalog, request, cache_dir):
    return source_issuer_identity(catalog, request, cache_dir)


def _read_metadata(path, root, budget):
    """One storage read budget handles provider cache and registration metadata."""
    return budget.read_metadata_observation(path, root=root.path)


def _register_local_sources(catalog, *, root_id, relative_paths, budget):
    """A quarantined requested original is a gap, not an empty local lake.

    Group attachment diagnostics do not veto a healthy primary. The scanner
    continues to own hashing/registration; this observes its requested results.
    """
    catalog.register_sources(root_id=root_id, relative_paths=relative_paths, budget=budget)
    for relative in relative_paths:
        primary = relative.removesuffix(".source.json")
        row = catalog.reader.fetchone(
            "SELECT role,source_id,location_status FROM locations WHERE root_id=? AND relative_path=?",
            (root_id, primary),
        )
        if row is None or (row["role"] == "original_primary" and (
                not row["source_id"] or row["location_status"] not in {"active", "retired"})):
            raise SourceReadError("unavailable", "local_original_registration_failed")


def _sec_cache(original, primary, budget):
    """Bind provider publication facts to primary file/hash/size, CIK and accession."""
    observations = []
    for _location_id, path, root in original.locations:
        cached = _read_metadata(path.with_name("meta.json"), root, budget)
        if cached is None:
            continue
        meta, sha = cached
        accession = meta.get("accession_number") or meta.get("internal_document_id")
        if (
            meta.get("is_deleted") is not False
            or meta.get("ingest_complete") is not True
            or str(meta.get("company_id", "")).lstrip("0") != primary["cik"]
            or meta.get("primary_document") != path.name
            or meta.get("form_type") != primary["form_type"]
            or meta.get("report_date") != primary["report_date"]
            or not isinstance(accession, str)
            or not re.fullmatch(r"\d{10}-\d{2}-\d{6}", accession)
        ):
            raise SourceReadError("blocked", "provider_cache_identity_conflict")
        files = meta.get("files")
        matching = (
            [x for x in files if isinstance(x, dict) and x.get("name") == path.name]
            if isinstance(files, list)
            else []
        )
        if (
            len(matching) != 1
            or matching[0].get("sha256") != original.ref.content_sha256
            or matching[0].get("size") != original.ref.byte_size
        ):
            raise SourceReadError("blocked", "provider_cache_byte_binding_conflict")
        published = meta.get("filing_date")
        if published is not None:
            try:
                if date.fromisoformat(published).isoformat() != published:
                    raise ValueError()
            except (ValueError, TypeError):
                raise SourceReadError("blocked", "publication_date_invalid") from None
        expected = (
            "https://www.sec.gov/Archives/edgar/data/"
            + primary["cik"]
            + "/"
            + accession.replace("-", "")
            + "/"
            + path.name
        )
        url = matching[0].get("source_url")
        # Only true cached URLs or SEC accession+primary construction, never a guessed hostname.
        if url is not None and url != expected:
            raise SourceReadError("blocked", "provider_cache_url_conflict")
        observations.append(
            {
                "published_date": published,
                "source_url": url,
                "provider_document_id": accession,
                "locator": "registered-provider-cache:/meta.json",
                "metadata_sha256": sha,
            }
        )
    if not observations:
        return None
    if (
        len(
            {
                (x["published_date"], x["source_url"], x["provider_document_id"])
                for x in observations
            }
        )
        != 1
    ):
        raise SourceReadError("blocked", "provider_cache_publication_conflict")
    return observations[0]




def _sec_sidecar(original, identity, budget):
    """Observed publication declarations bound to the actual registered original.

    Body-derived issuer/scope is established separately. This is the existing
    direct/raw storage metadata, never a filename/capture-time date fallback.
    """
    observations = []
    for _location_id, path, root in original.locations:
        cached = _read_metadata(path.with_name(path.name + ".source.json"), root, budget)
        if cached is None:
            continue
        meta, sha = cached
        if (meta.get("content_sha256") != original.ref.content_sha256
                or (meta.get("market"), meta.get("security_id")) != (identity.market, identity.security_id)
                or meta.get("entity") != identity.canonical_name):
            raise SourceReadError("blocked", "provider_cache_identity_conflict")
        published = meta.get("published_date") or meta.get("filing_date")
        if published is not None:
            try:
                if date.fromisoformat(published).isoformat() != published:
                    raise ValueError()
            except (ValueError, TypeError):
                raise SourceReadError("blocked", "publication_date_invalid") from None
        observations.append({"published_date": published, "source_url": meta.get("source_url"),
                             "provider": meta.get("provider"),
                             "provider_document_id": meta.get("provider_document_id"),
                             "locator": "registered-source-sidecar:/.source.json", "metadata_sha256": sha})
    if not observations:
        return None
    if len({(x["published_date"], x["source_url"], x["provider"], x["provider_document_id"])
            for x in observations}) != 1:
        raise SourceReadError("blocked", "provider_cache_publication_conflict")
    return observations[0]


def _prior_source_facts(catalog, ref):
    prior = get_verified_assertion(catalog.reader, ref.source_id, ref.content_sha256, reader="steady")
    previous = _evidence_payload(prior["evidence_json"], prior["assertion_id"]) if prior else {}
    return previous.get("source_fact_patch") or {}, previous.get("source_fact_evidence") or {}


def _scope_matches(primary, request):
    return (all(getattr(request, key) is None or getattr(request, key) == primary[key]
                for key in ("fiscal_year", "fiscal_period", "form_type"))
            and (request.document_kind != "annual_report"
                 or primary["form_type"].removesuffix("/A") in {"10-K", "20-F"}))



def _cn_cover_scope(original, identity, budget, *, allow_other_kinds=False):
    """Observe a bounded periodic cover, never turn its filename into facts."""
    import pymupdf as fitz

    try:
        with fitz.open(stream=original.data, filetype="pdf") as pdf:
            pages = []
            for number in range(min(3, len(pdf))):
                budget.check()
                pages.append(pdf[number].get_text()[:20000])
    except SourceReadError:
        raise
    except (RuntimeError, ValueError) as exc:
        raise SourceReadError("blocked", "local_original_unreadable") from exc
    for number, text in enumerate(pages, 1):
        compact = re.sub(r"\s+", "", text)
        name = re.sub(r"\s+", "", identity.canonical_name)
        named = name in compact
        codes = set(re.findall(r"(?:股票|证券)代码[:：]?([0-9]{6})(?!\d)", compact))
        if codes and codes != {identity.security_id}:
            raise SourceReadError("blocked", "primary_issuer_conflict")
        coded = identity.security_id in codes
        if not (named or coded):
            continue
        lines = [re.sub(r"\s+", "", line) for line in text.splitlines() if line.strip()][:40]
        ir_title = next((line for line in lines[:12] if line.removeprefix(name) in {
            "投资者关系活动记录表", "投资者关系活动记录", "投资者交流活动记录表"}), None)
        if ir_title and allow_other_kinds:
            facts = {"entity": identity.canonical_name, "market": identity.market,
                     "security_id": identity.security_id, "document_kind": "investor_relations",
                     "title": ir_title, "fiscal_year": None, "fiscal_period": None}
            return facts, {key: {"value": value, "locator": f"pdf:page:{number}:document-title",
                                "content_sha256": original.ref.content_sha256,
                                "extraction_method": "cn-document-title/1"} for key, value in facts.items()}
        if any(re.search(r"投资者关系活动记录|招股说明书|募集说明书|[问答][:：]", line) for line in lines[:12]):
            raise SourceReadError("blocked", "local_document_kind_unresolved")
        match = None
        for start in range(min(12, len(lines))):
            for width in range(1, 4):
                title = "".join(lines[start:start + width])
                if title.startswith(name):
                    title = title[len(name):]
                match = re.fullmatch(r"(20\d{2})年?(半年度|年度|第一季度|第二季度|第三季度|第四季度)报告(?:[（(](?:修订|更正|更新).*?[）)])?", title)
                if match is not None:
                    break
            if match is not None:
                break
        if match is None:
            continue
        label = match[2]
        period = {"年度": "FY", "半年度": "H1", "第一季度": "Q1", "第二季度": "Q2", "第三季度": "Q3", "第四季度": "Q4"}[label]
        kind = "annual_report" if period == "FY" else ("semi_annual_report" if period == "H1" else "quarterly_report")
        facts = {"entity": identity.canonical_name, "market": identity.market,
                 "security_id": identity.security_id, "document_kind": kind,
                 "fiscal_year": int(match[1]), "fiscal_period": period,
                 "title": f"{identity.canonical_name} {match[0]}"}
        evidence = {key: {"value": value, "locator": f"pdf:page:{number}:periodic-cover",
                          "content_sha256": original.ref.content_sha256,
                          "extraction_method": "cn-periodic-cover/1"} for key, value in facts.items()}
        return facts, evidence
    raise SourceReadError("blocked", "local_metadata_incomplete")


def _proven_facts(catalog, original, identity, request, budget, *, claimed_match=False, match_scope=True):
    ref = original.ref
    prior_patch, prior_proof = _prior_source_facts(catalog, ref)
    if _sec_original(ref, identity.market, request.document_kind):
        qualification = source_scope_qualification(catalog, ref,
            metadata={"market": identity.market, "document_kind": request.document_kind},
            request=request, identity=identity)
        reused_scope = not qualification.needs_original
        primary = qualification.scope(original.data, budget=budget, extractor=extract_sec_scope)
        if match_scope and not _scope_matches(primary, request):
            if claimed_match:
                raise SourceReadError("blocked", "primary_scope_conflict")
            return None, None
        if not reused_scope:
            primary = complete_sec_primary(primary)
        cache = _sec_cache(original, primary, budget)
        if cache is None and prior_patch.get("published_date") is None:
            cache = _sec_sidecar(original, identity, budget)
        # A prior verified assertion is already hash-bound, but legacy row/filename/mtime is not proof.
        published = (
            cache["published_date"] if cache else prior_patch.get("published_date")
        )
        source_url = cache["source_url"] if cache else prior_patch.get("source_url")
        facts = {
            "entity": identity.canonical_name,
            "market": identity.market,
            "security_id": identity.security_id,
            "document_kind": ("regulatory_filing" if not match_scope and request.document_kind == "annual_report"
                              and primary["form_type"].removesuffix("/A") not in {"10-K", "20-F"}
                              else request.document_kind),
            "fiscal_year": primary["fiscal_year"],
            "fiscal_period": primary["fiscal_period"],
            "period_end": primary["report_date"],
            "form_type": primary["form_type"],
            "title": primary["title"],
            "published_date": published,
            "filing_date": published,
            "source_url": source_url,
        }
        if cache:
            facts.update(
                provider=cache.get("provider", "sec"), provider_document_id=cache["provider_document_id"]
            )
        evidence = {
            key: {
                "locator": "primary-dei:/"
                + (
                    {
                        "period_end": "DocumentPeriodEndDate",
                        "fiscal_year": "DocumentFiscalYearFocus",
                        "fiscal_period": "DocumentFiscalPeriodFocus",
                        "form_type": "DocumentType",
                    }.get(key, "EntityCentralIndexKey")
                ),
                "value": value,
                "content_sha256": ref.content_sha256,
                "issuer_record_id": identity.source_record_id,
                "extraction_method": SEC_SCOPE_METHOD,
            }
            for key, value in facts.items()
        }
        for key in {"entity", "market", "security_id"}:
            evidence[key]["primary_cik"] = primary["cik"]
        evidence["title"]["locator"] = "html:/html/head/title"
        for key in {
            "published_date",
            "filing_date",
            "source_url",
            "provider",
            "provider_document_id",
        } & set(facts):
            evidence[key] = (
                {
                    "locator": cache["locator"],
                    "value": facts[key],
                    "metadata_sha256": cache["metadata_sha256"],
                    "content_sha256": ref.content_sha256,
                }
                if cache
                else prior_proof.get(key, {"locator": "source-metadata:unknown", "value": facts[key],
                                           "content_sha256": ref.content_sha256})
            )
        return facts, evidence
    # Other already-verified source fact declarations can be rechecked against their actual bytes.
    required = {"entity", "market", "security_id", "document_kind"}
    if request.fiscal_year is not None:
        required.add("fiscal_year")
    if request.fiscal_period is not None:
        required.add("fiscal_period")
    identity_conflict = any(prior_patch.get(key) not in (None, expected) for key, expected in (
        ("market", identity.market), ("security_id", identity.security_id)))
    if identity_conflict or not required <= set(prior_patch) or any(
        prior_patch.get(key) is None for key in required
    ):
        if ref.mime_type == "application/pdf" and identity.market == "CN":
            facts, proof = _cn_cover_scope(original, identity, budget, allow_other_kinds=True)
            facts["published_date"] = None if identity_conflict else prior_patch.get("published_date")
            proof["published_date"] = (None if identity_conflict else prior_proof.get("published_date")) or {
                "locator": "source-metadata:publication-unknown", "value": facts["published_date"]}
            return facts, proof
        raise SourceReadError("blocked", "local_metadata_incomplete")
    if (prior_patch["market"], prior_patch["security_id"]) != (
        identity.market,
        identity.security_id,
    ):
        raise SourceReadError("blocked", "primary_identity_unresolved")
    if match_scope and any(
        getattr(request, key) is not None
        and getattr(request, key) != prior_patch.get(key)
        for key in ("fiscal_year", "fiscal_period", "document_kind")
    ):
        return None, None
    return {
        key: value for key, value in prior_patch.items() if key in SOURCE_FACT_FIELDS
    }, prior_proof


def _facts_with_availability(catalog, original, identity, request, budget, **options):
    from .source_availability import capture_observation, verified_open_observation
    facts, evidence = _proven_facts(catalog, original, identity, request, budget, **options)
    if facts is None:
        return None, None
    facts.setdefault("published_date", None)
    if facts["published_date"] is None:
        previous = evidence.get("published_date", {})
        observation = {**previous, "value": None,
                       "locator": "source-observation:publication-unknown"}
        # Preserve the earliest owner-verified observation across retries.
        observation.setdefault("verified_open", verified_open_observation(original))
        captured = capture_observation(catalog, original.ref, budget=budget)
        if captured is not None:
            observation["availability_capture"] = captured
        evidence["published_date"] = observation
    return facts, evidence


def _discover_source_groups(catalog, identity, budget, request):
    """Finite issuer-layout metadata enumeration, separate from raw verification."""
    from .adapter_dispatch import discover_issuer_paths
    from .policy import _effective_reusable

    changed = False
    unresolved = []
    names = {identity.canonical_name, identity.ticker, identity.security_id}

    def local_path(path, root, *, directory):
        budget.check()
        try:
            status = path.lstat()
        except FileNotFoundError:
            return False
        if _needs_hydration(status):
            raise SourceReadError("unavailable", "placeholder_not_hydrated")
        if path.is_symlink() or getattr(status, "st_file_attributes", 0) & 0x400:
            return False
        return (path.is_dir() if directory else path.is_file()) and _inside_configured_roots(
            Path(os.path.realpath(path)), (root,))

    for root in catalog.config.roots:
        if not _effective_reusable(root, catalog.config):
            continue
        selected = discover_issuer_paths(
            root, names=tuple(names), security_ids=(identity.ticker, identity.security_id),
            is_local=lambda path, *, directory: local_path(path, root, directory=directory),
            metadata_reader=budget.metadata_reader(root.path),
            observe_group=budget.observe_group, observe_entry=budget.observe_entry,
        )
        def priority(relative):
            # Hints order work only. Qualification below observes actual bytes.
            name = Path(relative).name.casefold()
            year_hit = request.fiscal_year is not None and str(request.fiscal_year) in name
            period_tokens = {"FY": ("annual", "年报", "年度"), "H1": ("h1", "半年", "中期"),
                             "Q1": ("q1", "一季"), "Q2": ("q2", "二季"),
                             "Q3": ("q3", "三季"), "Q4": ("q4", "四季")}
            period_hit = any(token in name for token in period_tokens.get(request.fiscal_period, ()))
            return (not year_hit, not period_hit, relative)

        for relative in sorted(selected, key=priority):
            location = catalog.reader.fetchone("SELECT document_id FROM locations WHERE root_id=? AND relative_path=? AND role='original_primary'", (root.root_id, relative))
            if location is None:
                # Each completed registration/proof survives a later bound.
                if budget.candidates >= budget.max_candidates:
                    raise SourceReadError("unavailable", "local_candidate_limit")
                _register_local_sources(catalog, root_id=root.root_id, relative_paths={relative}, budget=budget)
                changed = True
                location = catalog.reader.fetchone(
                    "SELECT document_id FROM locations WHERE root_id=? AND relative_path=? AND role='original_primary'",
                    (root.root_id, relative))
            row = catalog.reader.exact_source_version(location["document_id"]) if location else None
            if row is None:
                raise SourceReadError("unavailable", "local_original_registration_failed")
            ref = SourceRef(row["document_id"], row["source_id"], row["content_sha256"], row["byte_size"], row["mime_type"])
            scope = qualified_source_scope(catalog, ref, {"document_kind": row["document_kind"]})
            relation = scope_relatedness(scope, request)
            if relation is ScopeRelation.NOT_RELEVANT:
                continue
            from .document_kinds import PERIODIC_DOCUMENT_KINDS
            from .source_availability import stored_availability_evidence
            period_known = scope.facts.get("document_kind") not in PERIODIC_DOCUMENT_KINDS or (
                type(scope.facts.get("fiscal_year")) is int and bool(scope.facts.get("fiscal_period")))
            date_observed = bool(scope.facts.get("published_date")) or stored_availability_evidence(catalog, ref) is not None
            if relation is ScopeRelation.MATCH and scope.authority == "source-facts" and period_known and date_observed:
                # Discovery consumes stored scope proof. The final selected
                # version is opened once below; do not re-open every old PDF.
                continue
            if getattr(identity, "_discovery_only", False):
                # Requested names may locate files; only their actual source
                # owner can establish facts. No lookup is needed for an empty
                # issuer directory, and an unknown original is not absence.
                identity = scope.identity() or _identity(catalog, request, getattr(identity, "_identity_cache_dir", None))
            broad = replace(request, fiscal_year=None, fiscal_period=None, form_type=None)
            def prove(original):
                return _facts_with_availability(catalog, original, identity, broad, budget, match_scope=False)
            try:
                restore_document_facts(catalog, ref=ref, retirement_observation=observe_document(catalog, ref.document_id),
                                       budget=budget, fact_replay=prove)
                changed = True
            except SourceReadError as exc:
                if exc.reason in {"budget_exceeded", "cancelled", "local_prepare_deadline"}:
                    raise
                if exc.reason != "local_original_missing":
                    unresolved.append((exc.status, exc.reason))
            if request.mode != "latest_as_of" and SourceVersionReader(catalog).query_local(request).status == "found":
                return True
    if unresolved:
        # Includes registered generic-kind originals. The next retry sees
        # them again until a source owner can prove scope; no lost sentinel.
        status, reason = unresolved[0]
        raise SourceReadError(status, reason)
    return changed


def _prepare_local_source(
    catalog,
    request: SourceRequest,
    *,
    identity_cache_dir: Path | None = None,
    limits: LocalPrepareLimits | None = None,
    registrations: tuple[SourceRegistrationScope, ...] = (),
    _discovery_done=False,
    _budget=None,
) -> dict[str, Any]:
    """Explicit bounded writer composition; source-query stays read only."""
    if not isinstance(request, SourceRequest):
        raise TypeError("request must be SourceRequest")
    budget = _budget or LocalReadBudget(limits or LocalPrepareLimits())
    if not catalog.config.database_path.exists():
        # Explicit prepare owns a finite writer operation; pure query/open
        # keeps its read-only missing-catalog refusal.
        _ = catalog.store
    reader = SourceVersionReader(catalog)
    query = reader.query_local(request)
    identity = None
    if request.mode == "latest_as_of" and not _discovery_done:
        if query.matches:
            ref = query.matches[0]
            identity = qualified_source_scope(catalog, ref, {"document_kind": request.document_kind}).identity()
        if identity is None:
            try:
                identity = _identity(catalog, request, identity_cache_dir)
            except (ValueError, SourceReadError):
                from types import SimpleNamespace
                identity = SimpleNamespace(canonical_name=request.entity, market=request.market,
                    security_id=request.security_id, ticker=request.security_id, _discovery_only=True,
                    _identity_cache_dir=identity_cache_dir)
        _discover_source_groups(catalog, identity, budget, request)
        return _prepare_local_source(catalog, request, identity_cache_dir=identity_cache_dir,
            limits=limits, _discovery_done=True, _budget=budget)
    if query.status == "found" and _discovery_done:
        ref = query.matches[0]
        reader.verify_version(ref, purpose="filing_reuse", budget=budget)
        return _result("ready", "local_source_reconciled", ref=ref)
    claimed_matches = {ref.document_id for ref in query.matches} if query.status == "found" else set()
    if query.status == "found" and not _discovery_done:
        ref = query.matches[0]
        market = request.market or reader.describe_version(ref).get("market")
        if not _sec_original(ref, market, request.document_kind):
            reader.verify_version(ref, purpose="filing_reuse", budget=budget)
            return _result("ready", "existing_active_source", ref=ref)
        try:
            qualification = source_scope_qualification(catalog, ref,
                metadata=reader.describe_version(ref), request=request, identity_cache_dir=identity_cache_dir)
        except (ValueError, SourceReadError) as exc:
            return _result(getattr(exc, "status", "blocked"),
                           getattr(exc, "reason", "local_fact_validation_failed"), blocks=True)
        primary = qualification.primary
        if primary is not None:
            reader._verified_version(ref, purpose="filing_reuse",
                expected_read_policy_sha256=None, retain_bytes=False, budget=budget,
                scope_qualification=qualification)
            return _result("ready", "existing_active_source", ref=ref)
        # The same registered identity observation can drive the existing writer
        # when proof is missing; it must not resolve another master for this hit.
        identity = qualification.identity
    if query.status == "ambiguous":
        return _result("ambiguous", query.reason, blocks=True)
    if (
        len(registrations) > 16
        or sum(len(x.relative_paths) for x in registrations) > budget.max_candidates
    ):
        raise ValueError("registration scope exceeds local limit")
    for scope in registrations:
        budget.check()
        _register_local_sources(catalog,
            root_id=scope.root_id, relative_paths=set(scope.relative_paths), budget=budget
        )
    try:
        candidates = catalog.query_filing_candidates(
            document_kind=request.document_kind,
            source_statuses=("active", "retired"),
            limit=1000,
        )
    except Exception:
        raise
    resolver = SourceResolver(catalog)
    candidates = [x for x in candidates if resolver._entity_matches(request.entity, x)]
    if not candidates:
        if not _discovery_done:
            try:
                identity = _identity(catalog, request, identity_cache_dir)
            except (ValueError, SourceReadError):
                return _result("not_found", "no_registered_local_source")
            if _discover_source_groups(catalog, identity, budget, request):
                return _prepare_local_source(
                    catalog,
                    request,
                    identity_cache_dir=identity_cache_dir,
                    limits=limits,
                    _discovery_done=True,
                    _budget=budget,
                )
        return _result("not_found", "no_registered_local_source")
    diagnostics = []
    operations = []
    qualified_documents = set()
    targeted = False
    historical = HistoricalCaptureScopes(catalog,budget)
    eligible = []
    known_identity = None
    for candidate in candidates:
        budget.check()
        from .resolver import _source_metadata
        metadata = _source_metadata(candidate, store=catalog.reader, reader="steady")
        row = catalog.reader.exact_source_version(candidate["document_id"])
        ref = SourceRef(row["document_id"],row["source_id"],row["content_sha256"],row["byte_size"],row["mime_type"])
        body_owner = (_sec_original(ref, request.market, request.document_kind)
                      or request.market == "CN" and ref.mime_type == "application/pdf")
        if resolver._identity_matches(request, metadata) == "conflict" and not body_owner:
            diagnostics.append({"document_id": candidate["document_id"], "reason": "registered_identity_conflict"})
            continue
        qualified = qualified_source_scope(catalog,ref,candidate,historical=historical)
        relation = scope_relatedness(qualified,request)
        if relation is ScopeRelation.NOT_RELEVANT:
            known_identity = known_identity or qualified.identity()
            diagnostics.append({"document_id":ref.document_id,"reason":"trusted_scope_not_relevant"})
            continue
        eligible.append(candidate)
        if relation is ScopeRelation.MATCH and qualified.authority == "source-facts":
            known_identity = known_identity or qualified.identity()
    candidates = eligible
    if not candidates:
        if not _discovery_done and known_identity and _discover_source_groups(catalog,known_identity,budget,request):
            return _prepare_local_source(catalog,request,identity_cache_dir=identity_cache_dir,
                limits=limits,_discovery_done=True,_budget=budget)
        return _result("not_found","no_matching_local_period",diagnostics=diagnostics)
    try:
        identity = identity or known_identity or _identity(catalog, request, identity_cache_dir)
    except (ValueError, SourceReadError) as exc:
        return _result(
            "blocked",
            getattr(exc, "reason", "verified_issuer_unavailable"),
            blocks=True,
        )
    if len(candidates) > budget.max_candidates:
        return _result("unavailable", "local_candidate_limit", blocks=True)
    for candidate in candidates:
        budget.check()
        row = catalog.reader.exact_source_version(candidate["document_id"])
        ref = SourceRef(
            row["document_id"],
            row["source_id"],
            row["content_sha256"],
            row["byte_size"],
            row["mime_type"],
        )
        try:
            observed = observe_document(catalog, ref.document_id)
            if row["source_status"] == "retired" and not metadata_retirement(observed):
                raise SourceReadError("blocked", "retirement_not_metadata_only")
            observed_facts = []

            def qualify(checked):
                facts, evidence = _facts_with_availability(
                    catalog, checked, identity, request, budget,
                    claimed_match=ref.document_id in claimed_matches,
                )
                observed_facts.append(facts)
                return facts, evidence

            operation = restore_document_facts(
                catalog,
                ref=ref,
                retirement_observation=observed,
                budget=budget,
                fact_replay=qualify,
            )
            if operation["status"] == "not_relevant":
                continue
            facts = observed_facts[0]
            targeted = True
            qualified_documents.add(ref.document_id)
            operations.append(
                {
                    key: value
                    for key, value in operation.items()
                    if key not in {"source_ref", "verified_locations"}
                }
            )
            if facts["published_date"] is not None and facts["published_date"] > request.as_of_date:
                diagnostics.append(
                    {
                        "document_id": ref.document_id,
                        "reason": "publication_after_as_of",
                    }
                )
            elif facts["published_date"] is None:
                from .qualification import qualify_source
                from .source_availability import stored_availability_evidence
                date_quality = qualify_source(None, as_of_date=request.as_of_date,
                    availability_evidence=stored_availability_evidence(catalog, ref), source_sha256=ref.content_sha256)
                if not date_quality.historical_date_eligible:
                    diagnostics.append({"document_id": ref.document_id, "reason": "publication_date_unknown"})
        except (
            SourceReadError,
            FiscalMetadataError,
            ValueError,
            OSError,
            CatalogOperationLockedError,
        ) as exc:
            if isinstance(exc, SourceReadError) and exc.reason == "local_original_missing":
                diagnostics.append({"document_id": ref.document_id, "reason": exc.reason})
                continue
            if isinstance(exc, SourceReadError) and exc.reason in {
                "budget_exceeded", "cancelled", "local_prepare_deadline",
                "local_source_group_limit", "local_discovery_entry_limit",
            }:
                raise
            targeted = True
            diagnostics.append(
                {
                    "document_id": ref.document_id,
                    "reason": getattr(
                        exc,
                        "reason",
                        (
                            "local_reconcile_busy"
                            if isinstance(exc, CatalogOperationLockedError)
                            else getattr(
                                exc, "error_code", "local_fact_validation_failed"
                            )
                        ),
                    ),
                    "status": getattr(
                        exc,
                        "status",
                        "unavailable"
                        if isinstance(exc, CatalogOperationLockedError)
                        else "blocked",
                    ),
                }
            )
    query = reader.query_local(request)
    if query.status == "found" and query.matches[0].document_id in qualified_documents:
        ref = query.matches[0]
        budget.check()
        return _result(
            "ready",
            "local_source_reconciled",
            ref=ref,
            operations=operations,
            diagnostics=diagnostics,
        )
    if query.status == "ambiguous":
        return _result(
            "ambiguous",
            query.reason,
            blocks=True,
            operations=operations,
            diagnostics=diagnostics,
        )
    if targeted:
        statuses = {x.get("status") for x in diagnostics}
        return _result(
            "unavailable" if "unavailable" in statuses else "blocked",
            "local_metadata_gap",
            blocks=True,
            operations=operations,
            diagnostics=diagnostics,
        )
    if not _discovery_done and _discover_source_groups(catalog, identity, budget, request):
        return _prepare_local_source(
            catalog,
            request,
            identity_cache_dir=identity_cache_dir,
            limits=limits,
            _discovery_done=True,
            _budget=budget,
        )
    return _result(
        "not_found",
        "no_matching_local_period",
        operations=operations,
        diagnostics=diagnostics,
    )


def prepare_local_source(
    catalog,
    request: SourceRequest,
    *,
    identity_cache_dir: Path | None = None,
    limits: LocalPrepareLimits | None = None,
    registrations: tuple[SourceRegistrationScope, ...] = (),
) -> dict[str, Any]:
    """Return named local outcomes; a failed proof never means permission to fetch."""
    try:
        return _prepare_local_source(
            catalog,
            request,
            identity_cache_dir=identity_cache_dir,
            limits=limits,
            registrations=registrations,
        )
    except SourceReadError as exc:
        return _result(exc.status, exc.reason, blocks=True)
    except CatalogOperationLockedError:
        return _result("unavailable", "local_reconcile_busy", blocks=True)
