"""Path-independent, exact-version reads from the local source catalog.

This is the first v2 read slice.  The public reference contains identity only;
each open checks the current catalog, root policy and actual bytes again.
Period and historical availability belong to selection. Capture descriptions
and old read fingerprints are observations, never byte access prerequisites.
"""

from __future__ import annotations

import re
import sqlite3
from collections.abc import Iterator, Mapping
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from types import MappingProxyType
from typing import Any

from .document_kinds import PERIODIC_DOCUMENT_KINDS
from .policy import _effective_reusable
from .policy_2x import export_policy_2x
from .qualification import qualify_source, latest_source_index
from .prompt_injection import (
    PromptInjectionReviewError,
    read_prompt_injection_review,
)
from .source_read_policy import exact_source_read_policy_sha256, source_read_policy_sha256
from .reader import CatalogReaderUnavailable
from .runtime_policy import validate_snapshot
from .metadata_observation import observe_metadata
from .resolver import (
    _ReadBudget,
    _fiscal_year,
    _provider_identity,
    _read_verified_bytes,
    _source_metadata,
    SourceRequest,
    SourceResolver,
)
from .service import SourceCatalog
from .store import metadata_state
from .security_code import canonical_security_code
from .source_location import (
    SourceLocationError,
    relative_segments as _relative_segments,
    resolve_source_location,
)


from company_wiki.source_contract.source_version import (
    SOURCE_REF_SCHEMA_VERSION, SourceReadError, SourceRef, ReviewSnapshot,
    VerifiedContent, VerifiedVersionReceipt,
)
SOURCE_READ_RECEIPT_SCHEMA_VERSION = "2.1"
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_SUPPORTED_READ_PURPOSES = frozenset(
    {"preview", "filing_reuse", "source_export", "narrative_derivation"}
)
_EXACT_SOURCE_FACT_FIELDS = (
    "document_kind", "canonical_entity_id", "market", "security_id",
    "fiscal_year", "fiscal_period", "period_end", "published_date", "form_type",
    "title", "language",
)
_SCOPE_UNOBSERVED = object()












@dataclass(frozen=True)
class SourceQueryResult:
    status: str
    matches: tuple[SourceRef, ...]
    reason: str
    schema_version: str = SOURCE_REF_SCHEMA_VERSION
    excluded_candidates: tuple[dict[str, object], ...] = ()


@dataclass(frozen=True, init=False)
class FilingReuseObservation:
    """The exact filing verified for one local acquisition decision."""

    source_ref: SourceRef
    receipt: VerifiedVersionReceipt
    admitted_copy: Mapping[str, Any]
    request_id: str

    def __init__(self) -> None:
        raise TypeError("observe filing reuse through SourceVersionReader")

    @property
    def location_id(self) -> str:
        return str(self.admitted_copy["location_id"])


class SourceVersionReader:
    """Read an exact catalog version without accepting or returning a raw path."""

    def __init__(self, catalog: SourceCatalog, *, runtime_policy: dict[str, Any] | None = None):
        if not isinstance(catalog, SourceCatalog):
            raise TypeError("catalog must be SourceCatalog")
        self.catalog = catalog
        if runtime_policy is not None and validate_snapshot(runtime_policy):
            raise ValueError("invalid explicit compatibility snapshot")
        self._runtime_policy = runtime_policy

    def _read_context(self) -> tuple[SourceResolver, dict[str, Any] | None, str]:
        """Use current steady facts, or a caller's explicit compatibility view.

        An automatically discovered rollout file cannot grant or deny reads.
        """
        policy = self._runtime_policy
        read_policy_sha256 = source_read_policy_sha256(self.catalog.config, policy)
        resolver = SourceResolver(self.catalog, runtime_policy=policy)
        return resolver, policy, read_policy_sha256

    def _resolver_and_read_policy(
        self, expected_read_policy_sha256: str | None = None, *, ref: SourceRef | None = None,
    ) -> tuple[SourceResolver, str]:
        """Report the current fingerprint; stored fingerprints are lineage."""
        resolver, policy, read_policy_sha256 = self._read_context()
        self._validate_read_policy_pin(expected_read_policy_sha256)
        if expected_read_policy_sha256 is not None:
            if expected_read_policy_sha256 != read_policy_sha256 and ref is not None:
                read_policy_sha256 = self._exact_read_policy(ref, resolver, policy)
        return resolver, read_policy_sha256

    @staticmethod
    def _validate_read_policy_pin(value: str | None) -> None:
        if value is not None and (not isinstance(value, str) or not _SHA256.fullmatch(value)):
            raise SourceReadError("blocked", "invalid_read_policy_pin")

    def _resolver_for_request(self) -> SourceResolver:
        return self._resolver_and_read_policy()[0]

    def read_policy_sha256(self, ref: SourceRef | None = None) -> str:
        """Return scoped schema-3 identity, or global schema-2 selection identity.

        No-argument calls retain their existing selection/legacy semantics.
        Physical location is resolved and actual bytes checked again on open.
        """
        resolver, policy, global_pin = self._read_context()
        if ref is None:
            return global_pin
        return self._exact_read_policy(ref, resolver, policy)

    def _exact_read_policy(
        self, ref: SourceRef, resolver: SourceResolver, runtime_policy: dict[str, Any] | None,
        *, metadata: dict[str, str | int | None] | None = None,
    ) -> str:
        if metadata is None:
            metadata = self._describe_version(ref, resolver)
        try:
            locations = self.catalog.reader.exact_source_locations(ref.document_id, ref.source_id)
        except (CatalogReaderUnavailable, sqlite3.Error):
            raise SourceReadError("unavailable", "catalog_unavailable") from None
        return exact_source_read_policy_sha256(
            self.catalog.config, runtime_policy, source_ref=asdict(ref),
            source_facts={field: metadata.get(field) for field in _EXACT_SOURCE_FACT_FIELDS},
            registered_root_ids=(location["root_id"] for location in locations),
        )

    def _candidate_pages(
        self, request: SourceRequest, *, include_unknown_publication: bool = False,
        identity_tokens: tuple[str, ...] | None = None,
    ) -> Iterator[dict[str, Any]]:
        from .identity_candidates import iter_identity_filing_candidates
        from .security_identity import _normalize_text

        tokens = identity_tokens if identity_tokens is not None else (_normalize_text(request.entity),)
        candidates = iter_identity_filing_candidates(
            self.catalog, document_kind=request.document_kind, identity_tokens=tokens,
            published_on_or_before=None if include_unknown_publication else request.as_of_date,
        )
        try:
            for number, document in enumerate(candidates, start=1):
                if number > 20_000:
                    raise SourceReadError("unavailable", "candidate_budget_exceeded")
                yield document
        except (CatalogReaderUnavailable, sqlite3.Error):
            raise SourceReadError("unavailable", "catalog_unavailable") from None

    def query_ref(self, document_id: str, source_id: str, expected_sha256: str) -> SourceRef:
        from .source_references import query_source_reference
        return query_source_reference(lambda: self.catalog.reader, document_id, source_id, expected_sha256)

    def query_local(self, request: SourceRequest) -> SourceQueryResult:
        """Find indexed versions by business identity without opening source bytes.

        This lookup never scans, downloads, or grants permission to reuse a
        filing.  The selected action is checked again by open_version.
        """
        return self._query_local(request, include_unknown_publication=False)

    def lookup_transcript_import(self, request: SourceRequest) -> SourceQueryResult:
        """Find an exact stored transcript for duplicate suppression.

        A missing publication date is reported explicitly and never changes
        the normal as-of query contract. This lookup is for import idempotency,
        not historical evidence selection.
        """
        if not isinstance(request, SourceRequest):
            raise TypeError("request must be SourceRequest")
        if (
            request.document_kind != "investor_call_transcript"
            or request.market is None
            or request.security_id is None
            or request.fiscal_year is None
            or request.fiscal_period is None
            or request.provider is None
            or request.mode not in {None, "exact"}
        ):
            raise ValueError("transcript import lookup requires exact company and period")
        return self._query_local(request, include_unknown_publication=True)

    def _query_local(
        self, request: SourceRequest, *, include_unknown_publication: bool
    ) -> SourceQueryResult:
        if not isinstance(request, SourceRequest):
            raise TypeError("request must be SourceRequest")
        resolver = self._resolver_for_request()
        found: list[tuple[str, str, SourceRef]] = []
        found_scopes: list[dict] = []
        excluded: list[dict[str, object]] = []

        def make_query_result(status: str, matches: tuple[SourceRef, ...], reason: str) -> SourceQueryResult:
            return SourceQueryResult(status, matches, reason,
                                     excluded_candidates=tuple(excluded))

        candidate_tokens = resolver.issuer_identity_tokens(
            request.entity, market=request.market, security_id=request.security_id,
            issuer_link_id=request.issuer_link_id,
        )
        for document in self._candidate_pages(
            request, include_unknown_publication=True, identity_tokens=candidate_tokens,
        ):
            document = observe_metadata(document.get("metadata")).project_document(document)
            metadata = _source_metadata(
                document, store=self.catalog.reader,
                reader=resolver.reader,
                current_epoch=resolver.current_epoch,
                active_cohorts=resolver.active_cohorts,
                legacy_bridge_allowed=resolver.legacy_bridge_allowed,
            )
            if not resolver._entity_matches(request.entity, document, metadata=metadata,
                                            identity_tokens=candidate_tokens):
                continue
            if "published_date" in metadata:
                document["published_date"] = metadata["published_date"]
            if resolver.match_source_identity(
                market=request.market,
                security_id=request.security_id,
                issuer_link_id=request.issuer_link_id,
                metadata=metadata,
            ) != "match":
                continue
            if request.fiscal_year is not None and (
                _fiscal_year(document, metadata) != request.fiscal_year
            ):
                continue
            if request.form_type and metadata.get("form_type") != request.form_type:
                continue
            if request.fiscal_period and (
                metadata.get("fiscal_period") != request.fiscal_period
            ):
                continue
            if request.language and metadata.get("language") != request.language:
                continue
            provider, provider_document_id, identities = _provider_identity(metadata)
            if request.provider and (
                provider != request.provider
                if include_unknown_publication
                else provider is not None and provider != request.provider
            ):
                continue
            if request.provider_document_id and (
                request.provider_document_id not in identities
                or (request.provider and provider != request.provider)
            ):
                continue
            source_id = str(document["source_id"] or "")
            digest = str(document["content_sha256"] or "")
            if not source_id or not _SHA256.fullmatch(digest):
                continue
            try:
                ref = self.query_ref(document["document_id"], source_id, digest)
            except SourceReadError:
                continue
            from .source_availability import stored_availability_evidence
            availability = stored_availability_evidence(self.catalog, ref) if not document["published_date"] else None
            qualification = qualify_source(document["published_date"], as_of_date=request.as_of_date,
                                           availability_evidence=availability, source_sha256=ref.content_sha256)
            if not qualification.historical_date_eligible and not (
                include_unknown_publication and qualification.publication_status == "unknown"
            ):
                excluded.append({"source_ref": asdict(ref), "qualification": qualification.to_dict()})
                continue
            published = str(document["published_date"] or "")
            found.append((published, provider_document_id or "", ref))
            from .canonical_scope import qualified_source_scope
            scope = qualified_source_scope(self.catalog, ref, document)
            found_scopes.append({**scope.facts, "scope_verified": scope.authority == "source-facts",
                                 "published_date": published, "provider_document_id": provider_document_id,
                                 "source_id": source_id})
        if not found:
            return make_query_result("not_found", (), "no_local_match")
        if request.mode == "latest_as_of":
            selected = latest_source_index(found_scopes)
            if selected is None:
                return make_query_result("ambiguous", tuple(item[2] for item in found), "latest_period_or_revision_unknown")
            return make_query_result("found", (found[selected][2],), "latest_as_of")
        if len(found) > 1:
            return make_query_result(
                "ambiguous", tuple(item[2] for item in found),
                "multiple_local_matches",
            )
        if not found[0][0] and include_unknown_publication:
            return make_query_result(
                "unknown_publication", (found[0][2],), "publication_date_unknown"
            )
        return make_query_result("found", (found[0][2],), "one_local_match")

    def describe_version(self, ref: SourceRef) -> dict[str, str | int | None]:
        """Project catalog-owned display and capture facts for an exact version.

        Only explicit capture fields are exported.  A scanner title derived
        from a filename is deliberately not promoted into a source title.
        """
        return self._describe_version(ref, self._resolver_for_request())

    def _describe_version(
        self, ref: SourceRef, resolver: SourceResolver,
    ) -> dict[str, str | int | None]:
        """Project facts under the same validated visibility as the scoped pin."""
        if not isinstance(ref, SourceRef):
            raise TypeError("ref must be SourceRef")
        if self.query_ref(ref.document_id, ref.source_id, ref.content_sha256) != ref:
            raise SourceReadError("unavailable", "source_ref_changed")
        try:
            version_row = self.catalog.reader.exact_source_version(ref.document_id)
        except (CatalogReaderUnavailable, sqlite3.Error):
            raise SourceReadError("unavailable", "catalog_unavailable") from None
        if version_row is None:
            raise SourceReadError("not_indexed", "document_not_indexed")
        observation = observe_metadata(version_row["metadata_json"])
        shared = observation.metadata
        row: dict[str, Any] = observation.project_document(dict(version_row))
        visible = _source_metadata(
            {"source_id": ref.source_id, "metadata": shared},
            store=self.catalog.reader,
            reader=resolver.reader,
            current_epoch=resolver.current_epoch,
            active_cohorts=resolver.active_cohorts,
            legacy_bridge_allowed=resolver.legacy_bridge_allowed,
        )
        def claim(key: str) -> str | None:
            value = visible.get(key)
            return str(value).strip() or None if value is not None else None

        source_url = claim("source_url") or claim("https_url")
        if source_url and not source_url.startswith(("https://", "http://")):
            source_url = None
        fiscal_year_text = claim("fiscal_year")
        fiscal_year = (
            int(fiscal_year_text)
            if fiscal_year_text and re.fullmatch(r"\d{4}", fiscal_year_text)
            else None
        )
        return {
            "document_id": ref.document_id,
            "source_id": ref.source_id,
            "content_sha256": ref.content_sha256,
            "byte_size": ref.byte_size,
            "mime_type": ref.mime_type,
            "title": claim("source_title"),
            "document_kind": str(row["document_kind"] or "") or None,
            "published_date": visible.get("published_date", str(row["published_date"] or "") or None),
            "source_url": source_url,
            "retrieved_at": claim("retrieved_at"),
            "collector_name": claim("collector_name"),
            "collector_version": claim("collector_version"),
            "canonical_entity_id": claim("canonical_entity_id"),
            "display_name": claim("display_name"),
            "market": claim("market"),
            "security_id": claim("security_id"),
            "fiscal_year": fiscal_year,
            "fiscal_period": claim("fiscal_period"),
            "period_end": claim("period_end"),
            "form_type": claim("form_type"),
            "provider": claim("provider"),
            "provider_document_id": claim("provider_document_id"),
            "language": claim("language"),
        }

    def metadata_diagnostics(self, ref: SourceRef) -> dict[str, object]:
        """Read-only field quality for an exact source, outside the v2 manifest."""
        self.query_ref(ref.document_id, ref.source_id, ref.content_sha256)
        row = self.catalog.reader.exact_source_version(ref.document_id)
        if row is None:
            raise SourceReadError("not_indexed", "document_not_indexed")
        return observe_metadata(row["metadata_json"]).to_dict()

    def availability_evidence(self, ref: SourceRef) -> dict[str, str] | None:
        """Read recorded historical availability for the exact source reference."""
        from .source_availability import verified_availability_evidence

        return verified_availability_evidence(self.catalog, ref)

    def open_described_version(
        self, ref: SourceRef, *, purpose: str = "source_export",
        expected_read_policy_sha256: str | None = None,
        identity_cache_dir: Path | None = None,
    ) -> tuple[VerifiedContent, dict[str, str | int | None]]:
        """Observe facts once and verify the actual buffer under one read context."""
        self._validate_read_policy_pin(expected_read_policy_sha256)
        resolver, policy, global_pin = self._read_context()
        manifest = self._describe_version(ref, resolver)
        pin = (global_pin if expected_read_policy_sha256 == global_pin else
               self._exact_read_policy(ref, resolver, policy, metadata=manifest))
        qualification = None
        if purpose == "filing_reuse":
            from .assertion_service import source_scope_qualification
            qualification = source_scope_qualification(
                self.catalog, ref, metadata=manifest,
                identity_cache_dir=identity_cache_dir,
            )
        opened = self._verified_version(ref, purpose=purpose, expected_read_policy_sha256=None,
                                        retain_bytes=True, current_read_policy_sha256=pin,
                                        scope_qualification=qualification)
        assert isinstance(opened, VerifiedContent)
        return opened, manifest

    def describe_candidate(self, ref: SourceRef) -> dict[str, object]:
        """DB-only, pathless prequalification for a filing consumer.

        Capture fields are observations from an indexed location, not source
        version identity. Security code is the source identity's canonical
        market representation; describe_version retains the observed value.
        The final open must still verify the current bytes.
        """
        manifest = self.describe_version(ref)
        try:
            version = self.catalog.reader.exact_source_version(ref.document_id)
            indexed = self.catalog.reader.exact_source_locations(
                ref.document_id, ref.source_id
            )
        except (CatalogReaderUnavailable, sqlite3.Error):
            raise SourceReadError("unavailable", "catalog_unavailable") from None
        if version is None:
            raise SourceReadError("not_indexed", "document_not_indexed")
        roots = {root.root_id: root for root in self.catalog.config.roots}
        locations = []
        for row in indexed:
            location = dict(row)
            root = roots.get(location["root_id"])
            if root is None:
                continue
            location["root_priority"] = root.priority
            locations.append(location)
        capture: dict[str, object] | None = None
        for location in sorted(
            self.catalog._annotate_locations(ref.document_id, locations),
            key=lambda item: (item["root_priority"], item["root_id"],
                              item["relative_path"], item["location_id"]),
        ):
            root = roots[location["root_id"]]
            if location["candidate_rank"] <= 0 or _relative_segments(
                str(location["relative_path"])
            ) is None:
                continue
            if root.allowed_document_kinds and version["document_kind"] not in (
                root.allowed_document_kinds
            ):
                continue
            if root.allowed_statuses and version["source_status"] not in (
                root.allowed_statuses
            ):
                continue
            if root.max_file_size is not None and ref.byte_size > root.max_file_size:
                continue
            observed, problem = metadata_state(location["manifest_json"])
            if problem is not None:
                continue
            if observed.get("content_sha256") not in (None, "", ref.content_sha256):
                continue
            # Prefer a complete observation, but retain a sparse one without
            # discarding its known fields or combining different locations.
            if capture is None:
                capture = observed
            if all(
                isinstance(observed.get(key), str) and observed[key].strip()
                for key in ("retrieved_at", "collector_name", "collector_version")
            ):
                capture = observed
                break

        review_status = self._current_review(ref).status
        url = manifest["source_url"]
        https_url = url if isinstance(url, str) and url.startswith("https://") else None
        period_known = bool(
            manifest["fiscal_year"] is not None
            or manifest["fiscal_period"]
            or manifest["period_end"]
        )
        capture_complete = all(
            isinstance(value, str) and value.strip()
            for value in (
                (capture or {}).get(key)
                for key in ("retrieved_at", "collector_name", "collector_version")
            )
        )
        candidate: dict[str, object] = {
            "source_ref": asdict(ref),
            "document_id": ref.document_id,
            "source_id": ref.source_id,
            "title": manifest["title"],
            "document_kind": manifest["document_kind"],
            "fiscal_year": manifest["fiscal_year"],
            "fiscal_period": manifest["fiscal_period"],
            "period_end": manifest["period_end"],
            "form_type": manifest["form_type"],
            "published_date": manifest["published_date"],
            "https_url": https_url,
            "snapshot_sha256": ref.content_sha256,
            "byte_size": ref.byte_size,
            "mime_type": ref.mime_type,
            "retrieved_at": capture.get("retrieved_at") if capture else None,
            "collector_name": capture.get("collector_name") if capture else None,
            "collector_version": capture.get("collector_version") if capture else None,
            "provider": manifest["provider"],
            "provider_document_id": manifest["provider_document_id"],
            "canonical_entity_id": manifest["canonical_entity_id"],
            "display_name": manifest["display_name"],
            "market": manifest["market"],
            "security_id": canonical_security_code(
                str(manifest["security_id"]) if manifest["security_id"] is not None else None,
                str(manifest["market"]) if manifest["market"] is not None else None,
            ),
            "language": manifest["language"],
            "capture_ready": bool(
                capture_complete and https_url and manifest["published_date"]
                and (period_known or manifest["document_kind"] not in PERIODIC_DOCUMENT_KINDS)
            ),
            "prompt_injection_status": review_status,
            "capture_provenance": "indexed_location_manifest" if capture else None,
        }
        market = candidate.get("market")
        security_id = candidate.get("security_id")
        if isinstance(market, str) and isinstance(security_id, str) and security_id:
            try:
                from .security_identity import (
                    SecurityIdentityError,
                    SecurityMasterStore,
                    SecurityMasterUnavailableError,
                )

                store = SecurityMasterStore(
                    Path(self.catalog.config.catalog_dir) / "security_master"
                )
                issuer_link_id = store.issuer_link_id_for_security(market, security_id)
            except (OSError, SecurityIdentityError, SecurityMasterUnavailableError):
                issuer_link_id = None
            if issuer_link_id is not None:
                candidate["issuer_link_id"] = issuer_link_id
        return candidate

    def _current_review(self, ref: SourceRef) -> ReviewSnapshot:
        """Return an optional review diagnostic, never a read prerequisite."""
        try:
            review = read_prompt_injection_review(
                self.catalog.reader, ref.document_id
            )
        except (PromptInjectionReviewError, sqlite3.Error):
            return ReviewSnapshot("not_reviewed", None, None, None, None)
        if (
            review is None
            or review.get("source_sha256") != ref.content_sha256
            or not _SHA256.fullmatch(str(review.get("evidence_sha256") or ""))
            or not _SHA256.fullmatch(str(review.get("policy_hash") or ""))
        ):
            return ReviewSnapshot("not_reviewed", None, None, None, None)
        return ReviewSnapshot(
            str(review["status"]), ref.content_sha256,
            str(review["evidence_sha256"]), str(review["policy_hash"]),
            str(review.get("reviewed_at") or "") or None,
        )

    def _review_for_result(
        self, ref: SourceRef, *, purpose: str, retain_bytes: bool
    ) -> ReviewSnapshot | None:
        if purpose == "narrative_derivation":
            return self._current_review(ref)
        if retain_bytes and purpose == "filing_reuse":
            return self._current_review(ref)
        return None

    def open_version(
        self, ref: SourceRef, *, purpose: str = "filing_reuse",
        expected_read_policy_sha256: str | None = None,
    ) -> VerifiedContent:
        """Return only fully verified bytes of the pinned version, or refuse."""
        result = self._verified_version(
            ref, purpose=purpose,
            expected_read_policy_sha256=expected_read_policy_sha256,
            retain_bytes=True,
        )
        assert isinstance(result, VerifiedContent)
        return result

    def verify_version(
        self, ref: SourceRef, *, purpose: str = "source_export",
        expected_read_policy_sha256: str | None = None,
        budget: _ReadBudget | None = None,
    ) -> VerifiedVersionReceipt:
        """Stream-verify the version with open_version's exact read rules."""
        result = self._verified_version(
            ref, purpose=purpose,
            expected_read_policy_sha256=expected_read_policy_sha256,
            retain_bytes=False, budget=budget,
        )
        assert isinstance(result, VerifiedVersionReceipt)
        return result

    def verify_reusable_version(
        self, ref: SourceRef, *, request: SourceRequest, metadata: dict[str, Any],
        budget: _ReadBudget,
    ) -> FilingReuseObservation:
        """Verify the selected version under filing-root and SEC scope rules."""
        from .assertion_service import source_scope_qualification

        scope = source_scope_qualification(self.catalog, ref, metadata=metadata, request=request)
        receipt, admitted_copy = self._verified_location(
            ref, purpose="filing_reuse", expected_read_policy_sha256=None,
            retain_bytes=False, budget=budget, scope_qualification=scope,
            reusable_only=True,
        )
        assert isinstance(receipt, VerifiedVersionReceipt) and admitted_copy is not None
        observation = object.__new__(FilingReuseObservation)
        object.__setattr__(observation, "source_ref", ref)
        object.__setattr__(observation, "receipt", receipt)
        object.__setattr__(observation, "admitted_copy", admitted_copy)
        object.__setattr__(observation, "request_id", request.request_id)
        return observation

    def _admitted_candidates(
        self, ref: SourceRef, version_row: sqlite3.Row, *, roots: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """The readable locations for one ref, after the catalog annotator
        and root policy.

        This is the single admission gate shared by every byte path, so the
        whole-buffer reader and any transport elect the same candidate by
        construction.  The existing catalog annotator owns role/status/
        rejections filtering and the stable preference order.  Policy decides
        action eligibility.
        """
        locations = []
        try:
            indexed_locations = self.catalog.reader.exact_source_locations(
                ref.document_id, ref.source_id
            )
        except (CatalogReaderUnavailable, sqlite3.Error):
            raise SourceReadError("unavailable", "catalog_unavailable") from None
        for row in indexed_locations:
            location = dict(row)
            root = roots.get(location["root_id"])
            if root is None:
                continue
            location["root_priority"] = root.priority
            locations.append(location)
        if not locations:
            raise SourceReadError("unavailable", "no_indexed_location")
        annotated = self.catalog._annotate_locations(ref.document_id, locations)
        admitted = []
        for location in annotated:
            root = roots[location["root_id"]]
            if location["candidate_rank"] <= 0:
                continue
            kinds = root.allowed_document_kinds
            if kinds and version_row["document_kind"] not in kinds:
                continue
            limit = root.max_file_size
            if limit is not None and ref.byte_size > limit:
                continue
            statuses = root.allowed_statuses
            if statuses and version_row["source_status"] not in statuses:
                continue
            admitted.append(location)
        if not admitted:
            raise SourceReadError("blocked", "root_admission_denied")
        return admitted

    def _verified_version(
        self, ref: SourceRef, *, purpose: str,
        expected_read_policy_sha256: str | None,
        retain_bytes: bool, current_read_policy_sha256: str | None = None,
        budget: _ReadBudget | None = None, scope_qualification=_SCOPE_UNOBSERVED,
    ) -> VerifiedContent | VerifiedVersionReceipt:
        verified, _ = self._verified_location(
            ref, purpose=purpose, expected_read_policy_sha256=expected_read_policy_sha256,
            retain_bytes=retain_bytes, current_read_policy_sha256=current_read_policy_sha256,
            budget=budget, scope_qualification=scope_qualification,
        )
        return verified

    def _verified_location(
        self, ref: SourceRef, *, purpose: str,
        expected_read_policy_sha256: str | None,
        retain_bytes: bool, current_read_policy_sha256: str | None = None,
        budget: _ReadBudget | None = None, scope_qualification=_SCOPE_UNOBSERVED,
        reusable_only: bool = False,
    ) -> tuple[VerifiedContent | VerifiedVersionReceipt, Mapping[str, Any] | None]:
        """Verify through the current policy and same-SHA location fallback.

        The current catalog, root policy and registered relative locations are
        re-evaluated on every call.  Stored absolute_path is never trusted.
        """
        if not isinstance(ref, SourceRef):
            raise TypeError("ref must be SourceRef")
        if ref.schema_version != SOURCE_REF_SCHEMA_VERSION:
            raise SourceReadError("unavailable", "unsupported_version")
        if purpose not in _SUPPORTED_READ_PURPOSES:
            raise SourceReadError("blocked", "unsupported_purpose")
        current = self.query_ref(ref.document_id, ref.source_id, ref.content_sha256)
        if current != ref:
            raise SourceReadError("unavailable", "source_ref_changed")
        if current_read_policy_sha256 is None:
            _, read_policy_sha256 = self._resolver_and_read_policy(
                expected_read_policy_sha256, ref=ref,
            )
        else:
            read_policy_sha256 = current_read_policy_sha256
        try:
            version_row = self.catalog.reader.exact_source_version(ref.document_id)
        except (CatalogReaderUnavailable, sqlite3.Error):
            raise SourceReadError("unavailable", "catalog_unavailable") from None
        if version_row is None:
            raise SourceReadError("not_indexed", "document_not_indexed")

        if purpose == "filing_reuse":
            if scope_qualification is _SCOPE_UNOBSERVED:
                from .assertion_service import source_scope_qualification
                scope_qualification = source_scope_qualification(
                    self.catalog, ref, metadata=self.describe_version(ref))
            elif scope_qualification is not None and scope_qualification.ref != ref:
                raise SourceReadError("unavailable", "source_scope_ref_changed")
        elif scope_qualification is _SCOPE_UNOBSERVED:
            scope_qualification = None
        config = self.catalog.config
        roots = {root.root_id: root for root in config.roots
                 if not reusable_only or _effective_reusable(root, config)}
        candidates = self._admitted_candidates(ref, version_row, roots=roots)

        supplied_budget = budget is not None
        if budget is None:
            budget = _ReadBudget()
            budget.begin_request()
        elif not isinstance(budget, _ReadBudget):
            raise TypeError("budget must be a read budget")
        failures: list[str] = []
        all_missing = True
        policy_sha256, _ = export_policy_2x(config)
        for location in sorted(candidates, key=lambda item: item["candidate_rank"]):
            root = roots[location["root_id"]]
            try:
                resolved = resolve_source_location(root, str(location["relative_path"]))
            except SourceLocationError as exc:
                failures.append(exc.reason)
                all_missing = False
                continue
            observation, status, reason, detail = _read_verified_bytes(
                resolved, expected_sha256=ref.content_sha256, budget=budget,
                expected_byte_size=ref.byte_size,
                retain_bytes=retain_bytes or bool(scope_qualification and scope_qualification.needs_original),
            )
            if not status:
                assert observation is not None
                if scope_qualification is not None:
                    scope_qualification.verify(observation.data, budget=budget)
                review = self._review_for_result(
                    ref, purpose=purpose, retain_bytes=retain_bytes
                )
                read_at = datetime.now(UTC).isoformat()
                if retain_bytes:
                    content = VerifiedContent.from_observation(
                        ref, observation, read_at=read_at, policy_sha256=policy_sha256,
                        source_read_policy_sha256=read_policy_sha256, review=review,
                    )
                    return content, None
                receipt = VerifiedVersionReceipt(
                    document_id=ref.document_id, source_id=ref.source_id,
                    content_sha256=ref.content_sha256, byte_size=observation.byte_size,
                    read_at=read_at, policy_sha256=policy_sha256,
                    source_read_policy_sha256=read_policy_sha256, review=review,
                )
                # Only the catalog's legacy handle projection needs physical
                # coordinates. Use this exact admitted copy, even if the
                # same location ID was rebound after candidate lookup.
                admitted_copy = MappingProxyType({
                    **location, "absolute_path": str(resolved),
                    "verified_sha256": observation.content_sha256,
                }) if reusable_only else None
                return receipt, admitted_copy
            failures.append(reason or status or detail or "read_failed")
            all_missing = all_missing and reason == "read_failed" and detail == "FileNotFoundError"
            if reason in {"cancelled", "budget_exceeded"}:
                if supplied_budget:
                    raise SourceReadError("unavailable", reason)
                break
        if reusable_only and all_missing:
            raise SourceReadError("not_found", "local_original_missing")
        raise SourceReadError(
            "unavailable", "no_verified_location", ",".join(sorted(set(failures)))
        )

__all__ = [
    'SourceReadError',
    'SourceRef',
    'SourceVersionReader',
    'VerifiedContent',
]
