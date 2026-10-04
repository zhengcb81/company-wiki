"""Path-independent, exact-version reads from the local source catalog.

This is the first v2 read slice.  The public reference contains identity only;
each open checks the current catalog, root policy and actual bytes again.
Filing reuse requires a declared publication and reporting period; sparse
capture descriptions remain diagnostics rather than access prerequisites.
"""

from __future__ import annotations

import os
import re
import sqlite3
from collections.abc import Iterator
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any

from .policy_2x import export_policy_2x
from .prompt_injection import (
    PromptInjectionReviewError,
    read_prompt_injection_review,
)
from .source_read_policy import source_read_policy_sha256
from .reader import CatalogReaderUnavailable
from .runtime_policy import RuntimePolicyError, load_runtime_policy
from .scanner import R4_PROVENANCE_KEY
from .resolver import (
    _ReadBudget,
    _fiscal_year,
    _inside_configured_roots,
    _provider_identity,
    _read_verified_bytes,
    _source_metadata,
    SourceRequest,
    SourceResolver,
)
from .service import SourceCatalog
from .store import metadata_state


SOURCE_REF_SCHEMA_VERSION = "2.0"
SOURCE_READ_RECEIPT_SCHEMA_VERSION = "2.1"
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_ERROR_STATUSES = frozenset(
    {"not_found", "not_indexed", "unavailable", "blocked", "ambiguous"}
)
_SUPPORTED_READ_PURPOSES = frozenset(
    {"preview", "filing_reuse", "source_export", "narrative_derivation"}
)


class SourceReadError(RuntimeError):
    """A named refusal with no bytes or physical path in its public detail."""

    def __init__(self, status: str, reason: str, detail: str = ""):
        if status not in _ERROR_STATUSES:
            raise ValueError(f"unknown read status: {status}")
        self.status = status
        self.reason = reason
        self.detail = detail
        super().__init__(f"{status}: {reason}" + (f" ({detail})" if detail else ""))


@dataclass(frozen=True)
class SourceRef:
    document_id: str
    source_id: str
    content_sha256: str
    byte_size: int
    mime_type: str
    schema_version: str = SOURCE_REF_SCHEMA_VERSION


@dataclass(frozen=True)
class ReviewSnapshot:
    """Review state observed after the exact source bytes were verified."""

    status: str
    source_sha256: str | None
    evidence_sha256: str | None
    policy_hash: str | None
    reviewed_at: str | None


@dataclass(frozen=True)
class VerifiedContent:
    document_id: str
    source_id: str
    content_sha256: str
    data: bytes
    byte_size: int
    read_at: str
    policy_sha256: str
    source_read_policy_sha256: str
    review: ReviewSnapshot | None = None
    schema_version: str = SOURCE_REF_SCHEMA_VERSION


@dataclass(frozen=True)
class VerifiedVersionReceipt:
    """Verified source identity without source bytes or a physical location."""

    document_id: str
    source_id: str
    content_sha256: str
    byte_size: int
    read_at: str
    policy_sha256: str
    source_read_policy_sha256: str
    review: ReviewSnapshot | None = None
    schema_version: str = SOURCE_REF_SCHEMA_VERSION


@dataclass(frozen=True)
class SourceQueryResult:
    status: str
    matches: tuple[SourceRef, ...]
    reason: str
    schema_version: str = SOURCE_REF_SCHEMA_VERSION


def _relative_segments(relative_path: str) -> tuple[str, ...] | None:
    """Reject absolute, parent and drive paths before joining a configured root."""
    normalized = relative_path.replace("\\", "/")
    if (
        not normalized
        or any(ord(character) < 32 for character in normalized)
        or PurePosixPath(normalized).is_absolute()
    ):
        return None
    if PureWindowsPath(relative_path).drive:
        return None
    segments = tuple(normalized.split("/"))
    if any(segment in {"", ".", ".."} for segment in segments):
        return None
    return segments


class SourceVersionReader:
    """Read an exact catalog version without accepting or returning a raw path."""

    def __init__(self, catalog: SourceCatalog):
        if not isinstance(catalog, SourceCatalog):
            raise TypeError("catalog must be SourceCatalog")
        self.catalog = catalog

    def _resolver_and_read_policy(
        self, expected_read_policy_sha256: str | None = None
    ) -> tuple[SourceResolver, str]:
        """Pin activation and all root admission fields for one operation."""
        policy_path = self.catalog.config.catalog_dir / "runtime_policy.json"
        policy = None
        if policy_path.exists():
            try:
                policy = load_runtime_policy(policy_path)
            except RuntimePolicyError:
                raise SourceReadError("blocked", "runtime_policy_invalid") from None
            current_policy_hash, _ = export_policy_2x(self.catalog.config)
            if policy.get("policy_hash") != current_policy_hash:
                raise SourceReadError("blocked", "runtime_policy_mismatch")
        read_policy_sha256 = source_read_policy_sha256(self.catalog.config, policy)
        if expected_read_policy_sha256 is not None:
            if not isinstance(expected_read_policy_sha256, str) or not _SHA256.fullmatch(
                expected_read_policy_sha256
            ):
                raise SourceReadError("blocked", "invalid_read_policy_pin")
            if expected_read_policy_sha256 != read_policy_sha256:
                raise SourceReadError("blocked", "read_policy_mismatch")
        return SourceResolver(self.catalog, runtime_policy=policy), read_policy_sha256

    def _resolver_for_request(self) -> SourceResolver:
        return self._resolver_and_read_policy()[0]

    def read_policy_sha256(self) -> str:
        """Return a pathless pin for a subsequent exact-version open."""
        return self._resolver_and_read_policy()[1]

    def _candidate_pages(
        self, request: SourceRequest, *, include_unknown_publication: bool = False
    ) -> Iterator[dict[str, Any]]:
        page_size = 1000
        max_candidates = 20_000
        for offset in range(0, max_candidates, page_size):
            try:
                documents = self.catalog.query_filing_candidates(
                    document_kind=request.document_kind,
                    source_statuses=("active",),
                    published_on_or_before=(
                        None if include_unknown_publication else request.as_of_date
                    ),
                    limit=page_size,
                    offset=offset,
                )
            except (CatalogReaderUnavailable, sqlite3.Error):
                raise SourceReadError("unavailable", "catalog_unavailable") from None
            yield from documents
            if len(documents) < page_size:
                return
        raise SourceReadError("unavailable", "candidate_budget_exceeded")

    def query_ref(
        self, document_id: str, source_id: str, expected_sha256: str
    ) -> SourceRef:
        """Pure catalog SELECT; availability and current action policy are open gates."""
        if not isinstance(document_id, str) or not document_id.strip():
            raise ValueError("document_id must be non-empty text")
        if not isinstance(source_id, str) or not source_id.strip():
            raise ValueError("source_id must be non-empty text")
        if not isinstance(expected_sha256, str) or not _SHA256.fullmatch(
            expected_sha256
        ):
            raise ValueError("expected_sha256 must be lowercase SHA-256")
        try:
            row = self.catalog.reader.exact_source_version(document_id)
        except (CatalogReaderUnavailable, sqlite3.Error):
            raise SourceReadError("unavailable", "catalog_unavailable") from None
        if row is None:
            raise SourceReadError("not_indexed", "document_not_indexed")
        if row["source_status"] != "active":
            raise SourceReadError("blocked", "source_not_active")
        if row["source_id"] != source_id:
            raise SourceReadError("not_found", "document_source_mismatch")
        if not row["content_sha256"]:
            raise SourceReadError("not_indexed", "source_version_not_indexed")
        if row["content_sha256"] != expected_sha256:
            raise SourceReadError("unavailable", "expected_version_mismatch")
        return SourceRef(
            document_id=document_id,
            source_id=source_id,
            content_sha256=expected_sha256,
            byte_size=int(row["byte_size"]),
            mime_type=str(row["mime_type"]),
        )

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
        for document in self._candidate_pages(
            request, include_unknown_publication=include_unknown_publication
        ):
            if document["metadata_status"] != "ok":
                continue
            if not resolver._entity_matches(request.entity, document):
                continue
            metadata = _source_metadata(
                document, store=self.catalog.reader,
                reader=resolver.reader,
                current_epoch=resolver.current_epoch,
                active_cohorts=resolver.active_cohorts,
                legacy_bridge_allowed=resolver.legacy_bridge_allowed,
            )
            if resolver._identity_matches(request, metadata) != "match":
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
            published = str(document["published_date"] or "")
            if not published and not include_unknown_publication:
                continue
            if published and published > request.as_of_date:
                continue
            source_id = str(document["source_id"] or "")
            digest = str(document["content_sha256"] or "")
            if not source_id or not _SHA256.fullmatch(digest):
                continue
            try:
                ref = self.query_ref(document["document_id"], source_id, digest)
            except SourceReadError:
                continue
            found.append((published, provider_document_id or "", ref))
        if not found:
            return SourceQueryResult("not_found", (), "no_local_match")
        if request.mode == "latest_as_of":
            selected = max(
                found,
                key=lambda item: (item[0], item[1], item[2].source_id),
            )
            return SourceQueryResult("found", (selected[2],), "latest_as_of")
        if len(found) > 1:
            return SourceQueryResult(
                "ambiguous", tuple(item[2] for item in found),
                "multiple_local_matches",
            )
        if not found[0][0]:
            return SourceQueryResult(
                "unknown_publication", (found[0][2],), "publication_date_unknown"
            )
        return SourceQueryResult("found", (found[0][2],), "one_local_match")

    def describe_version(self, ref: SourceRef) -> dict[str, str | int | None]:
        """Project catalog-owned display and capture facts for an exact version.

        Only explicit capture fields are exported.  A scanner title derived
        from a filename is deliberately not promoted into a source title.
        """
        if not isinstance(ref, SourceRef):
            raise TypeError("ref must be SourceRef")
        if self.query_ref(ref.document_id, ref.source_id, ref.content_sha256) != ref:
            raise SourceReadError("unavailable", "source_ref_changed")
        try:
            row = self.catalog.reader.exact_source_version(ref.document_id)
        except (CatalogReaderUnavailable, sqlite3.Error):
            raise SourceReadError("unavailable", "catalog_unavailable") from None
        if row is None:
            raise SourceReadError("not_indexed", "document_not_indexed")
        shared, problem = metadata_state(row["metadata_json"])
        if problem is not None:
            raise SourceReadError("blocked", "metadata_unreadable")
        resolver = self._resolver_for_request()
        provenance = shared.get(R4_PROVENANCE_KEY)
        if provenance is not None:
            if not isinstance(provenance, dict) or not isinstance(
                provenance.get("fields"), dict
            ):
                raise SourceReadError("blocked", "metadata_unreadable")
            if any(
                isinstance(record, dict) and record.get("conflicts")
                for record in provenance["fields"].values()
            ):
                raise SourceReadError("blocked", "metadata_conflict")
        visible = _source_metadata(
            {"source_id": ref.source_id, "metadata": shared},
            store=self.catalog.reader,
            reader=resolver.reader,
            current_epoch=resolver.current_epoch,
            active_cohorts=resolver.active_cohorts,
            legacy_bridge_allowed=resolver.legacy_bridge_allowed,
        )
        if not visible and resolver.reader == "v2":
            raise SourceReadError("blocked", "metadata_not_visible")
        captures = [visible] if visible else []

        def claim(key: str) -> str | None:
            values = {
                str(capture[key]).strip()
                for capture in captures
                if capture.get(key) not in (None, "")
            }
            if len(values) > 1:
                raise SourceReadError("blocked", "metadata_conflict")
            return next(iter(values), None)

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
            "published_date": str(row["published_date"] or "") or None,
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

    def describe_candidate(self, ref: SourceRef) -> dict[str, object]:
        """DB-only, pathless prequalification for a filing consumer.

        Capture fields are observations from an indexed location, not source
        version identity.  The final open must still verify the current bytes.
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
        return {
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
            "security_id": manifest["security_id"],
            "language": manifest["language"],
            "capture_ready": bool(
                capture_complete and https_url and manifest["published_date"]
                and period_known
            ),
            "prompt_injection_status": review_status,
            "capture_provenance": "indexed_location_manifest" if capture else None,
        }

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
    ) -> VerifiedVersionReceipt:
        """Stream-verify the version with open_version's exact read rules."""
        result = self._verified_version(
            ref, purpose=purpose,
            expected_read_policy_sha256=expected_read_policy_sha256,
            retain_bytes=False,
        )
        assert isinstance(result, VerifiedVersionReceipt)
        return result

    def _verified_version(
        self, ref: SourceRef, *, purpose: str,
        expected_read_policy_sha256: str | None,
        retain_bytes: bool,
    ) -> VerifiedContent | VerifiedVersionReceipt:
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
        resolver, read_policy_sha256 = self._resolver_and_read_policy(
            expected_read_policy_sha256
        )
        try:
            version_row = self.catalog.reader.exact_source_version(ref.document_id)
        except (CatalogReaderUnavailable, sqlite3.Error):
            raise SourceReadError("unavailable", "catalog_unavailable") from None
        if version_row is None:
            raise SourceReadError("not_indexed", "document_not_indexed")

        config = self.catalog.config
        roots = {root.root_id: root for root in config.roots}
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

        # The existing catalog annotator owns role/status/rejections filtering
        # and the stable preference order.  Policy decides action eligibility.
        annotated = self.catalog._annotate_locations(ref.document_id, locations)
        admitted = [
            location
            for location in annotated
            if location["candidate_rank"] > 0
            and (
                not roots[location["root_id"]].allowed_document_kinds
                or version_row["document_kind"]
                in roots[location["root_id"]].allowed_document_kinds
            )
            and (
                roots[location["root_id"]].max_file_size is None
                or ref.byte_size <= roots[location["root_id"]].max_file_size
            )
            and (
                not roots[location["root_id"]].allowed_statuses
                or version_row["source_status"]
                in roots[location["root_id"]].allowed_statuses
            )
        ]
        if not admitted:
            raise SourceReadError("blocked", "root_admission_denied")
        candidates = admitted

        # Reuse needs source/period facts, while a URL or collector description
        # is optional provenance. Every admitted location still gets the same
        # exact byte verification below; sparse captures stay honestly sparse.
        if purpose == "filing_reuse":
            if not version_row["published_date"]:
                raise SourceReadError("blocked", "capture_incomplete")
            shared_metadata, metadata_problem = metadata_state(
                version_row["metadata_json"]
            )
            if metadata_problem is not None:
                raise SourceReadError("blocked", "capture_incomplete")
            provenance = shared_metadata.get(R4_PROVENANCE_KEY)
            if provenance is not None:
                if not isinstance(provenance, dict) or not isinstance(
                    provenance.get("fields"), dict
                ):
                    raise SourceReadError("blocked", "capture_incomplete")
                if any(
                    isinstance(record, dict) and record.get("conflicts")
                    for record in provenance["fields"].values()
                ):
                    raise SourceReadError("blocked", "metadata_conflict")
            identity = _source_metadata(
                {"source_id": ref.source_id, "metadata": shared_metadata},
                store=self.catalog.reader,
                reader=resolver.reader,
                current_epoch=resolver.current_epoch,
                active_cohorts=resolver.active_cohorts,
                legacy_bridge_allowed=resolver.legacy_bridge_allowed,
            )
            fiscal_year = identity.get("fiscal_year")
            if not (
                (isinstance(fiscal_year, int) and not isinstance(fiscal_year, bool))
                or str(identity.get("fiscal_period") or "").strip()
                or re.fullmatch(
                    r"\d{4}-\d{2}-\d{2}",
                    str(identity.get("period_end") or ""),
                )
            ):
                raise SourceReadError("blocked", "period_unknown")
        budget = _ReadBudget()
        budget.begin_request()
        failures: list[str] = []
        policy_sha256, _ = export_policy_2x(config)
        for location in sorted(candidates, key=lambda item: item["candidate_rank"]):
            root = roots[location["root_id"]]
            segments = _relative_segments(str(location["relative_path"]))
            if segments is None:
                failures.append("invalid_relative_path")
                continue
            candidate = root.path.joinpath(*segments)
            # Read the resolved in-root path, so replacing a symlink after this
            # check cannot redirect the actual open outside the approved root.
            resolved = Path(os.path.realpath(candidate))
            if not _inside_configured_roots(resolved, (root,)):
                failures.append("artifact_path_outside_allowed_root")
                continue
            data, status, reason, detail = _read_verified_bytes(
                resolved, expected_sha256=ref.content_sha256, budget=budget,
                expected_byte_size=ref.byte_size, retain_bytes=retain_bytes,
            )
            if not status:
                review = self._review_for_result(
                    ref, purpose=purpose, retain_bytes=retain_bytes
                )
                receipt_fields = dict(
                    document_id=ref.document_id,
                    source_id=ref.source_id,
                    content_sha256=ref.content_sha256,
                    read_at=datetime.now(UTC).isoformat(),
                    policy_sha256=policy_sha256,
                    source_read_policy_sha256=read_policy_sha256,
                )
                if retain_bytes:
                    if data is None:
                        raise SourceReadError("unavailable", "verification_invariant_broken")
                    return VerifiedContent(
                        data=data, byte_size=len(data),
                        review=review,
                        **receipt_fields,
                    )
                return VerifiedVersionReceipt(
                    byte_size=ref.byte_size, review=review, **receipt_fields
                )
            failures.append(reason or status or detail or "read_failed")
            if reason in {"cancelled", "budget_exceeded"}:
                break
        raise SourceReadError(
            "unavailable", "no_verified_location", ",".join(sorted(set(failures)))
        )
