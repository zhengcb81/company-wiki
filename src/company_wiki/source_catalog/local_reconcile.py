"""Explicit local intake: prove existing facts, then use the unchanged public reader."""

from __future__ import annotations
from dataclasses import asdict
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
)
from .dayu_fiscal_metadata import extract_sec_scope, complete_sec_primary, FiscalMetadataError
from .local_inventory import (
    LocalPrepareLimits,
    LocalReadBudget,
    metadata_retirement,
    observe_document,
    verify_registered_original,
)
from .resolver import (
    SourceRequest,
    SourceResolver,
    _needs_hydration,
    _inside_configured_roots,
)
from .security_identity import (
    SecurityIdentityResolver,
    SecurityMasterStore,
    IdentityStatus,
)
from .source_reader import SourceReadError, SourceRef, SourceVersionReader
from .source_group_scope import SourceRegistrationScope
from .lock import CatalogOperationLockedError

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
    master = SecurityMasterStore(
        cache_dir or catalog.config.catalog_dir / "security_master"
    ).load(markets=(request.market,) if request.market else None)
    result = SecurityIdentityResolver(master).identify(
        request.security_id or request.entity, market=request.market
    )
    identity = result.resolved
    if (
        result.status is not IdentityStatus.RESOLVED
        or identity is None
        or not identity.verified
        or not identity.active
    ):
        raise SourceReadError("blocked", "verified_issuer_unavailable")
    # A ticker supplied alongside another issuer name must not silently win.
    entity_result = SecurityIdentityResolver(master).identify(
        request.entity, market=request.market
    )
    if entity_result.resolved is None or (
        entity_result.resolved.market,
        entity_result.resolved.security_id,
    ) != (identity.market, identity.security_id):
        raise SourceReadError("blocked", "requested_issuer_conflict")
    return identity


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


def _proven_facts(catalog, original, identity, request, budget):
    ref = original.ref
    prior = get_verified_assertion(
        catalog.reader, ref.source_id, ref.content_sha256, reader="steady"
    )
    previous = (
        _evidence_payload(prior["evidence_json"], prior["assertion_id"])
        if prior
        else {}
    )
    prior_patch = previous.get("source_fact_patch") or {}
    prior_proof = previous.get("source_fact_evidence") or {}
    if (
        identity.market == "US"
        and ref.mime_type in {"text/html", "application/xhtml+xml"}
        and request.document_kind in {"regulatory_filing", "annual_report"}
    ):
        primary = extract_sec_scope(original.data)
        cik = identity.identifiers.get("cik")
        if not cik or not cik.isdigit() or str(int(cik)) != primary["cik"]:
            raise SourceReadError("blocked", "primary_issuer_conflict")
        if (
            (
                request.fiscal_year is not None
                and request.fiscal_year != primary["fiscal_year"]
            )
            or (
                request.fiscal_period is not None
                and request.fiscal_period != primary["fiscal_period"]
            )
            or (
                request.form_type is not None
                and request.form_type != primary["form_type"]
            )
        ):
            return None, None
        primary = complete_sec_primary(primary)
        cache = _sec_cache(original, primary, budget)
        # A prior verified assertion is already hash-bound, but legacy row/filename/mtime is not proof.
        published = (
            cache["published_date"] if cache else prior_patch.get("published_date")
        )
        if published is None:
            raise SourceReadError("blocked", "publication_date_unknown")
        source_url = cache["source_url"] if cache else prior_patch.get("source_url")
        facts = {
            "entity": identity.canonical_name,
            "market": identity.market,
            "security_id": identity.security_id,
            "document_kind": request.document_kind,
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
                provider="sec", provider_document_id=cache["provider_document_id"]
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
            }
            for key, value in facts.items()
        }
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
                else prior_proof[key]
            )
        return facts, evidence
    # Other already-verified source fact declarations can be rechecked against their actual bytes.
    required = {"entity", "market", "security_id", "document_kind", "published_date"}
    if request.fiscal_year is not None:
        required.add("fiscal_year")
    if request.fiscal_period is not None:
        required.add("fiscal_period")
    if not required <= set(prior_patch) or any(
        prior_patch.get(key) is None for key in required
    ):
        if ref.mime_type == "application/pdf" and identity.market == "CN":
            import fitz

            with fitz.open(stream=original.data, filetype="pdf") as pdf:
                budget.check()
                cover = pdf[0].get_text()[:20000] if len(pdf) else ""
            # Cover can establish an issuer/year gap, never a publication day.
            normalized = re.sub(r"\s+", "", cover)
            if identity.canonical_name.replace(" ", "") in normalized:
                raise SourceReadError("blocked", "publication_date_unknown")
        raise SourceReadError("blocked", "local_metadata_incomplete")
    if (prior_patch["market"], prior_patch["security_id"]) != (
        identity.market,
        identity.security_id,
    ):
        raise SourceReadError("blocked", "primary_identity_unresolved")
    if any(
        getattr(request, key) is not None
        and getattr(request, key) != prior_patch.get(key)
        for key in ("fiscal_year", "fiscal_period", "document_kind")
    ):
        return None, None
    return {
        key: value for key, value in prior_patch.items() if key in SOURCE_FACT_FIELDS
    }, prior_proof


def _discover_source_groups(catalog, identity, budget):
    """Finite issuer-layout metadata enumeration, separate from raw verification."""
    from .source_reader import _relative_segments
    from .policy import _effective_reusable
    from .models import DOCUMENT_EXTENSIONS

    targets = []
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
        selected = set()
        seen_bases = set()
        if root.kind == "dayu_portfolio":
            for ticker in sorted({identity.ticker, identity.security_id}):
                if _relative_segments(ticker) != (ticker,):
                    continue
                base = root.path / ticker / "filings"
                if not local_path(base, root, directory=True):
                    continue
                with os.scandir(base) as entries:
                    for entry in entries:
                        budget.observe_entry()
                        group = Path(entry.path)
                        if not local_path(group, root, directory=True):
                            continue
                        budget.observe_group()
                        cached = _read_metadata(group / "meta.json", root, budget)
                        if cached is None:
                            continue
                        primary = cached[0].get("primary_document")
                        if (not isinstance(primary, str) or _relative_segments(primary) != (primary,)
                                or Path(primary).suffix.lower() not in DOCUMENT_EXTENSIONS):
                            continue
                        path = group / primary
                        if local_path(path, root, directory=False):
                            selected.add(path.relative_to(root.path).as_posix())
        elif root.kind == "company_raw":
            for name in sorted(names):
                if _relative_segments(name) != (name,):
                    continue
                base = root.path / name
                if not local_path(base, root, directory=True):
                    continue
                base_key = os.path.normcase(os.path.realpath(base))
                if base_key in seen_bases:
                    continue
                seen_bases.add(base_key)
                stack = [base]
                while stack:
                    directory = stack.pop()
                    budget.observe_group()
                    with os.scandir(directory) as entries:
                        for entry in entries:
                            budget.observe_entry()
                            path = Path(entry.path)
                            if entry.is_dir(follow_symlinks=False):
                                # Direct company content plus only the legacy raw tree.
                                if (directory != base or entry.name == "raw") and entry.name != ".rejections" and local_path(path, root, directory=True):
                                    stack.append(path)
                            elif (path.suffix.lower() in DOCUMENT_EXTENSIONS
                                    and not entry.name.endswith(".source.json") and entry.name != "meta.json"
                                    and local_path(path, root, directory=False)):
                                selected.add(path.relative_to(root.path).as_posix())
        for relative in sorted(selected):
            if catalog.reader.fetchone("SELECT 1 FROM locations WHERE root_id=? AND relative_path=?", (root.root_id, relative)) is None:
                targets.append((root.root_id, relative))
                if len(targets) > budget.max_candidates:
                    raise SourceReadError("unavailable", "local_candidate_limit")
    scopes = {}
    for root_id, relative in targets:
        scopes.setdefault(root_id, set()).add(relative)
    for root_id, paths in scopes.items():
        budget.check()
        _register_local_sources(catalog, root_id=root_id, relative_paths=paths, budget=budget)
    return bool(scopes)


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
    reader = SourceVersionReader(catalog)
    query = reader.query_local(request)
    if query.status == "found" and not _discovery_done:
        ref = query.matches[0]
        reader.verify_version(ref, purpose="filing_reuse", budget=budget)
        return _result("ready", "existing_active_source", ref=ref)
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
            if _discover_source_groups(catalog, identity, budget):
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
    targeted = False
    try:
        identity = _identity(catalog, request, identity_cache_dir)
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
            original = verify_registered_original(catalog, ref, budget=budget)
            facts, evidence = _proven_facts(
                catalog, original, identity, request, budget
            )
            if facts is None:
                continue
            targeted = True
            operation = restore_document_facts(
                catalog,
                ref=ref,
                facts=facts,
                evidence=evidence,
                retirement_observation=observed,
                budget=budget,
                fact_replay=lambda checked: _proven_facts(
                    catalog,
                    checked,
                    _identity(catalog, request, identity_cache_dir),
                    request,
                    budget,
                ),
            )
            operations.append(
                {
                    key: value
                    for key, value in operation.items()
                    if key not in {"source_ref", "verified_locations"}
                }
            )
            if facts["published_date"] > request.as_of_date:
                diagnostics.append(
                    {
                        "document_id": ref.document_id,
                        "reason": "publication_after_as_of",
                    }
                )
        except (
            SourceReadError,
            FiscalMetadataError,
            ValueError,
            OSError,
            CatalogOperationLockedError,
        ) as exc:
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
    if query.status == "found":
        ref = query.matches[0]
        reader.verify_version(ref, purpose="filing_reuse", budget=budget)
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
    if not _discovery_done and _discover_source_groups(catalog, identity, budget):
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
