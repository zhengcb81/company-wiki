"""Issuer projections over shared official JSON pages.

A projection is derived, immutable metadata: which records on which parent
pages belong to one issuer, with per-field locators into the exact raw bytes.
It never copies the parent page, never rewrites it, and its hash is not the
parent ``content_sha256``.  ``open_version`` on the parent SourceRef remains
the only way to obtain the original bytes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import unicodedata
from typing import Any

from .official_json_layout import (
    FieldObservation,
    PageObservation,
    RecordObservation,
    OfficialJsonLayoutError,
    classify_record,
    describe_layout_page,
    layout_fingerprint,
    registered_layout,
)
from .official_json_structure import (
    CWP_JSON_STRUCTURE_PARSER_VERSION,
    JsonStructureDocument,
    JsonStructureError,
    parse_json_structure,
)

PROJECTION_SCHEMA_VERSION = "source-projection-ref/1"
PROJECTION_ID_PREFIX = "urn:company-wiki:source-projection:sha256:"
CWP_OFFICIAL_JSON_PARSER_ID = "cwp_official_json/1.0.0"
_PAGE_TIME_FORMATS = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S")
_ISSUER_FIELDS = frozenset({
    "market", "security_id", "provider_company_id",
    "provider_activity_company_id", "canonical_name", "entity_name",
})
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class ProjectionError(ValueError):
    """A named projection refusal; the parent page stays untouched."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False)


def _parse_page_time(value: str | None) -> str | None:
    """Normalize an observed naive provider timestamp to a UTC-agnostic date.

    Provider timezone semantics are unproven, so no timezone conversion is
    applied; the raw string is preserved in the record and only the calendar
    date is derived for as-of gating.
    """
    if not value:
        return None
    for pattern in _PAGE_TIME_FORMATS:
        try:
            return datetime.strptime(value, pattern).date().isoformat()
        except ValueError:
            continue
    return None


@dataclass(frozen=True)
class FieldBinding:
    field: str
    role: str
    locator: str
    token_range: tuple[int, int]
    encoded_body_range: tuple[int, int]
    encoded_token_sha256: str
    decoded_sha256: str
    decoded_character_count: int
    speaker_known: bool
    translation_of: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "field": self.field,
            "role": self.role,
            "locator": self.locator,
            "token_range": list(self.token_range),
            "encoded_body_range": list(self.encoded_body_range),
            "encoded_token_sha256": self.encoded_token_sha256,
            "decoded_sha256": self.decoded_sha256,
            "decoded_character_count": self.decoded_character_count,
            "speaker_known": self.speaker_known,
            "translation_of": self.translation_of,
        }


@dataclass(frozen=True)
class ProjectionRecord:
    record_pointer: str
    provider_record_id: Any
    record_token_sha256: str
    record_kind: str
    attributed: bool
    issuer_observed: dict[str, Any]
    fields: tuple[FieldBinding, ...]
    times: dict[str, str]
    state: dict[str, Any]
    selected: bool
    selection_reason: str
    answer_first_publication_known: bool
    record_created_date: str | None
    as_of_eligibility: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_pointer": self.record_pointer,
            "provider_record_id": self.provider_record_id,
            "record_token_sha256": self.record_token_sha256,
            "record_kind": self.record_kind,
            "attributed": self.attributed,
            "issuer_observed": dict(self.issuer_observed),
            "fields": [item.to_dict() for item in self.fields],
            "times": dict(self.times),
            "state": dict(self.state),
            "selected": self.selected,
            "selection_reason": self.selection_reason,
            "answer_first_publication_known": self.answer_first_publication_known,
            "record_created_date": self.record_created_date,
            "as_of_eligibility": self.as_of_eligibility,
        }


@dataclass(frozen=True)
class SourceProjection:
    schema_version: str
    projection_id: str
    projection_sha256: str
    parent_source_refs: tuple[dict[str, Any], ...]
    adapter: dict[str, Any]
    issuer: dict[str, Any]
    as_of_date: str
    records: tuple[ProjectionRecord, ...]
    coverage: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "projection_id": self.projection_id,
            "projection_sha256": self.projection_sha256,
            "parent_source_refs": [dict(item) for item in self.parent_source_refs],
            "adapter": dict(self.adapter),
            "issuer": dict(self.issuer),
            "as_of_date": self.as_of_date,
            "records": [record.to_dict() for record in self.records],
            "coverage": dict(self.coverage),
        }

    def _payload_dict(self) -> dict[str, Any]:
        payload = self.to_dict()
        del payload["projection_id"]
        del payload["projection_sha256"]
        return payload

    def canonical_json(self) -> str:
        return _canonical_json(self._payload_dict())


def _field_role(record_kind: str, observation: FieldObservation) -> str | None:
    base = observation.role_base
    if observation.translation_of is not None:
        return base + "_provider_translation"
    if record_kind == "answered_qa":
        if base == "question":
            return "investor_question"
        return "management_answer"
    if record_kind in {"unanswered_question", "precollected_question"}:
        if base == "question":
            return "investor_question"
        return "investor_question" if base == "answer_or_statement" else None
    if record_kind == "closing_remark":
        return "company_statement" if base == "answer_or_statement" else None
    if record_kind == "precollected_question_with_answer":
        if base == "question":
            return "investor_question"
        return "company_official_answer"
    if record_kind == "event_remark_unattributed":
        return "event_remark" if base == "answer_or_statement" else None
    if record_kind == "other_statement":
        return "statement_unclassified" if base == "answer_or_statement" else None
    return None


def _binding(record_kind: str, observation: FieldObservation) -> FieldBinding | None:
    role = _field_role(record_kind, observation)
    if role is None:
        return None
    return FieldBinding(
        field=observation.field,
        role=role,
        locator=observation.locator,
        token_range=observation.token_range,
        encoded_body_range=observation.encoded_body_range,
        encoded_token_sha256=observation.encoded_token_sha256,
        decoded_sha256=observation.decoded_sha256,
        decoded_character_count=observation.decoded_character_count,
        speaker_known=False,
        translation_of=observation.translation_of,
    )


def _record_proves_issuer(record: RecordObservation, issuer: dict[str, Any]) -> bool:
    """Every issuer identity field present on the record must agree, and at
    least one must match.  Question and answer issuers never overwrite each
    other: the check is per record, on observed fields only."""
    observed = record.issuer_observed
    matched_any = False
    requested_company = issuer.get("provider_company_id")
    requested_activity = issuer.get("provider_activity_company_id")
    requested_stock = issuer.get("security_id")
    requested_canonical = issuer.get("canonical_name")

    activity_ids = observed.get("provider_company_ids") or []
    if requested_activity is not None:
        if activity_ids:
            if requested_activity in activity_ids:
                matched_any = True
            else:
                return False
    company_id = observed.get("provider_company_id")
    if requested_company is not None:
        if company_id is not None:
            if requested_company == company_id:
                matched_any = True
            else:
                return False
    stock = observed.get("stock_code")
    if requested_stock is not None and stock is not None:
        if requested_stock == stock:
            matched_any = True
        else:
            return False
    names = observed.get("company_names") or []
    if requested_canonical and names:
        normalized = {name.casefold() for name in names}
        if requested_canonical.casefold() in normalized:
            matched_any = True
    return matched_any


def _source_ref(sha: str, size: int) -> dict[str, Any]:
    return {
        "document_id": "urn:company-wiki:document:sha256:" + sha,
        "source_id": "urn:company-wiki:source:sha256:" + sha,
        "content_sha256": sha,
        "byte_size": size,
        "mime_type": "application/json",
        "schema_version": "2.0",
    }


def build_source_projection(
    *,
    parent_pages: list[tuple[str, int, JsonStructureDocument]],
    layout_id: str,
    issuer: dict[str, Any],
    as_of_date: str,
) -> SourceProjection:
    """Build one issuer projection over one or more exact parent pages."""
    if not parent_pages:
        raise ProjectionError("no_parent_pages")
    if not isinstance(issuer, dict) or not set(issuer) <= _ISSUER_FIELDS:
        raise ProjectionError("invalid_issuer")
    if not isinstance(as_of_date, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", as_of_date):
        raise ProjectionError("invalid_as_of_date")
    layout = registered_layout(layout_id)

    pages: list[dict[str, Any]] = []
    observations: list[tuple[str, PageObservation]] = []
    for sha, size, doc in parent_pages:
        if not isinstance(sha, str) or not _SHA256_RE.fullmatch(sha):
            raise ProjectionError("invalid_parent_sha")
        try:
            observation = describe_layout_page(layout_id, doc)
        except OfficialJsonLayoutError as exc:
            raise ProjectionError(exc.code) from exc
        observations.append((sha, observation))
        pages.append({
            "content_sha256": sha,
            "byte_size": size,
            "envelope_status": observation.envelope_status,
            "pagination": dict(observation.pagination),
            "records": len(observation.records),
        })

    proof_found = False
    for _, observation in observations:
        if observation.business_evidence:
            for record in observation.records:
                if _record_proves_issuer(record, issuer):
                    proof_found = True
                    break
        if proof_found:
            break
    if not proof_found:
        raise ProjectionError("issuer_not_on_page")

    projection_records: list[ProjectionRecord] = []
    selected_count = 0
    other_issuer = 0
    unattributed = 0
    as_of_excluded = 0
    for _, observation in observations:
        for record in observation.records:
            kind = classify_record(layout, record)
            proves = _record_proves_issuer(record, issuer)
            created = _parse_page_time(record.times.get("crtTime"))
            if created is None:
                created = _parse_page_time(
                    record.times.get("created_at"))
            if created is not None and created > as_of_date:
                eligibility = "after_as_of"
            elif created is None:
                eligibility = "unknown"
            else:
                eligibility = "eligible"
            bindings = tuple(
                binding for observation_field in (
                    list(record.text_fields.values())
                    + list(record.translation_fields.values()))
                if (binding := _binding(kind, observation_field)) is not None
            )
            if not proves:
                if record.attributed:
                    other_issuer += 1
                    reason = "other_issuer"
                else:
                    unattributed += 1
                    reason = "unattributed"
                selected = False
            elif eligibility == "after_as_of":
                as_of_excluded += 1
                selected = False
                reason = "record_after_as_of"
            elif eligibility == "unknown":
                selected = False
                reason = "record_time_unknown"
            else:
                selected = True
                selected_count += 1
                reason = "issuer_and_as_of_eligible"
            projection_records.append(ProjectionRecord(
                record_pointer=record.pointer,
                provider_record_id=record.provider_record_id,
                record_token_sha256=record.record_token_sha256,
                record_kind=kind,
                attributed=record.attributed,
                issuer_observed=dict(record.issuer_observed),
                fields=bindings,
                times=dict(record.times),
                state=dict(record.state),
                selected=selected,
                selection_reason=reason,
                answer_first_publication_known=False,
                record_created_date=created,
                as_of_eligibility=eligibility,
            ))

    pagination_complete = bool(pages) and all(
        page["envelope_status"] == "ok" and page["pagination"] for page in pages)
    if pagination_complete:
        declared = pages[0]["pagination"].get("pages")
        total = pages[0]["pagination"].get("total")
        currents = [page["pagination"].get("current") for page in pages]
        pagination_complete = (
            isinstance(declared, int) and isinstance(total, int)
            and len(pages) == declared
            and currents == list(range(1, declared + 1))
            and sum(page["records"] for page in pages) == total
        )
    coverage = {
        "pages": pages,
        "page_envelope_complete": all(
            page["envelope_status"] == "ok" for page in pages),
        "pagination_complete": pagination_complete,
        "issuer_records_selected": selected_count,
        "other_issuer_records": other_issuer,
        "unattributed_records": unattributed,
        "as_of_excluded_records": as_of_excluded,
        "total_records": len(projection_records),
    }

    adapter = {
        "parser": CWP_OFFICIAL_JSON_PARSER_ID,
        "structure_parser_version": CWP_JSON_STRUCTURE_PARSER_VERSION,
        "layout_id": layout.layout_id,
        "layout_version": layout.layout_version,
        "layout_fingerprint": layout_fingerprint(layout_id),
    }
    issuer_view = {key: issuer.get(key) for key in sorted(_ISSUER_FIELDS)}
    parent_ref_list: list[dict[str, Any]] = [
        _source_ref(sha, size) for sha, size, _ in parent_pages]
    payload = {
        "schema_version": PROJECTION_SCHEMA_VERSION,
        "parent_source_refs": parent_ref_list,
        "adapter": adapter,
        "issuer": issuer_view,
        "as_of_date": as_of_date,
        "records": [record.to_dict() for record in projection_records],
        "coverage": coverage,
    }
    projection_sha256 = hashlib.sha256(
        _canonical_json(payload).encode("utf-8")).hexdigest()
    parent_refs = tuple(parent_ref_list)
    result = SourceProjection(
        schema_version=PROJECTION_SCHEMA_VERSION,
        projection_id=PROJECTION_ID_PREFIX + projection_sha256,
        projection_sha256=projection_sha256,
        parent_source_refs=parent_refs,
        adapter=adapter,
        issuer=issuer_view,
        as_of_date=as_of_date,
        records=tuple(projection_records),
        coverage=coverage,
    )
    # Self-check: the published payload hashes to the identity we publish.
    if result.canonical_json() != _canonical_json(payload):
        raise ProjectionError("projection_payload_mismatch")
    return result


def projection_from_dict(value: Any) -> SourceProjection:
    if not isinstance(value, dict):
        raise ProjectionError("invalid_projection_payload")
    required = {"schema_version", "projection_id", "projection_sha256",
                "parent_source_refs", "adapter", "issuer", "as_of_date",
                "records", "coverage"}
    if set(value) != required:
        raise ProjectionError("invalid_projection_payload")
    if value["schema_version"] != PROJECTION_SCHEMA_VERSION:
        raise ProjectionError("unsupported_projection_version")
    records = []
    for item in value["records"]:
        bindings = tuple(
            FieldBinding(
                field=binding["field"], role=binding["role"],
                locator=binding["locator"],
                token_range=tuple(binding["token_range"]),
                encoded_body_range=tuple(binding["encoded_body_range"]),
                encoded_token_sha256=binding["encoded_token_sha256"],
                decoded_sha256=binding["decoded_sha256"],
                decoded_character_count=binding["decoded_character_count"],
                speaker_known=binding["speaker_known"],
                translation_of=binding["translation_of"],
            )
            for binding in item["fields"])
        records.append(ProjectionRecord(
            record_pointer=item["record_pointer"],
            provider_record_id=item["provider_record_id"],
            record_token_sha256=item["record_token_sha256"],
            record_kind=item["record_kind"],
            attributed=item["attributed"],
            issuer_observed=item["issuer_observed"],
            fields=bindings,
            times=item["times"],
            state=item["state"],
            selected=item["selected"],
            selection_reason=item["selection_reason"],
            answer_first_publication_known=item["answer_first_publication_known"],
            record_created_date=item["record_created_date"],
            as_of_eligibility=item["as_of_eligibility"],
        ))
    projection = SourceProjection(
        schema_version=value["schema_version"],
        projection_id=value["projection_id"],
        projection_sha256=value["projection_sha256"],
        parent_source_refs=tuple(value["parent_source_refs"]),
        adapter=dict(value["adapter"]),
        issuer=dict(value["issuer"]),
        as_of_date=value["as_of_date"],
        records=tuple(records),
        coverage=dict(value["coverage"]),
    )
    if hashlib.sha256(projection.canonical_json().encode("utf-8")).hexdigest() != (
            projection.projection_sha256):
        raise ProjectionError("projection_hash_mismatch")
    if projection.projection_id != PROJECTION_ID_PREFIX + projection.projection_sha256:
        raise ProjectionError("projection_id_mismatch")
    return projection


# --- catalog integration -----------------------------------------------------


def _reader(catalog):
    from .source_reader import SourceVersionReader
    return SourceVersionReader(catalog)


def _ref_from_dict(value: Any):
    from .source_reader import SourceRef
    if not isinstance(value, dict):
        raise ProjectionError("invalid_parent_source_ref")
    try:
        return SourceRef(**value)
    except TypeError:
        raise ProjectionError("invalid_parent_source_ref") from None


def build_projection_from_refs(
    catalog, *, refs, layout_id: str, issuer: dict[str, Any], as_of_date: str,
) -> SourceProjection:
    """Open exact parent versions, parse them, and build one issuer projection."""
    pages: list[tuple[str, int, Any]] = []
    for ref_value in refs:
        ref = (_ref_from_dict(ref_value) if isinstance(ref_value, dict)
               else ref_value)
        content = _reader(catalog).open_version(ref, purpose="source_export")
        if content.content_sha256 != ref.content_sha256:
            raise ProjectionError("parent_version_mismatch")
        from .official_json_structure import parse_json_structure
        doc = parse_json_structure(content.data, limits=None)
        pages.append((ref.content_sha256, ref.byte_size, doc))
    return build_source_projection(
        parent_pages=pages, layout_id=layout_id, issuer=issuer,
        as_of_date=as_of_date)


_PROJECTIONS_DIRNAME = "projections"


def _projections_root(catalog) -> Path:
    from pathlib import Path
    root = Path(catalog.config.catalog_dir) / _PROJECTIONS_DIRNAME
    root.mkdir(parents=True, exist_ok=True)
    return root


def persist_projection(catalog, projection: SourceProjection) -> str:
    """Idempotent projection store under the store-owned catalog directory."""
    if projection.projection_id != PROJECTION_ID_PREFIX + projection.projection_sha256:
        raise ProjectionError("projection_id_mismatch")
    path = _projections_root(catalog) / (projection.projection_sha256 + ".json")
    encoded = projection.canonical_json().encode("utf-8")
    if path.exists():
        if path.read_bytes() != encoded + b"\n":
            raise ProjectionError("projection_store_conflict")
        return projection.projection_id
    temporary = path.with_name(path.name + f".{os.getpid()}.tmp")
    try:
        with temporary.open("xb") as stream:
            stream.write(encoded + b"\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()
    return projection.projection_id


def load_projection(catalog, projection_id: str) -> SourceProjection:
    if not isinstance(projection_id, str) or not projection_id.startswith(
            PROJECTION_ID_PREFIX):
        raise ProjectionError("invalid_projection_id")
    sha = projection_id[len(PROJECTION_ID_PREFIX):]
    if not _SHA256_RE.fullmatch(sha):
        raise ProjectionError("invalid_projection_id")
    path = _projections_root(catalog) / (sha + ".json")
    if not path.is_file():
        raise ProjectionError("projection_not_found")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise ProjectionError("invalid_projection_payload") from None
    return projection_from_dict(payload)


def replay_projection(catalog, projection: SourceProjection,
                      *, record_pointer: str | None = None) -> dict[str, Any]:
    """Verify parents, pointers, byte slices, hashes and roles before display.

    This is the public replay contract: a displayed fragment must re-verify
    against the exact original bytes through the normal reader, its recorded
    parser identity, and the recorded role and issuer attribution.
    """
    if projection.adapter.get("structure_parser_version") != (
            CWP_JSON_STRUCTURE_PARSER_VERSION):
        raise ProjectionError("unsupported_parser_version")
    reader = _reader(catalog)
    docs: dict[str, Any] = {}
    for ref_value in projection.parent_source_refs:
        ref = _ref_from_dict(ref_value)
        content = reader.open_version(ref, purpose="source_export")
        docs[ref.content_sha256] = parse_json_structure(content.data)
    verified: list[dict[str, Any]] = []
    for record in projection.records:
        if record_pointer is not None and record.record_pointer != record_pointer:
            continue
        node = None
        doc = None
        for sha, candidate_doc in docs.items():
            try:
                candidate = candidate_doc.at_pointer(record.record_pointer)
            except JsonStructureError:
                continue
            if candidate.encoded_token_sha256 == record.record_token_sha256:
                node, doc = candidate, candidate_doc
                break
        if node is None or doc is None:
            raise ProjectionError("pointer_replay_failed")
        fields: list[dict[str, Any]] = []
        for binding in record.fields:
            try:
                field_node = doc.at_pointer(
                    record.record_pointer + "/" + binding.field)
            except JsonStructureError as exc:
                raise ProjectionError("pointer_replay_failed") from exc
            if (field_node.token_range != tuple(binding.token_range)
                    or field_node.encoded_body_range != tuple(binding.encoded_body_range)
                    or field_node.encoded_token_sha256 != binding.encoded_token_sha256
                    or field_node.decoded_sha256 != binding.decoded_sha256
                    or field_node.decoded_character_count != binding.decoded_character_count):
                raise ProjectionError("field_locator_mismatch")
            if field_node.locator() != binding.locator:
                raise ProjectionError("field_locator_mismatch")
            fields.append({
                "field": binding.field,
                "role": binding.role,
                "locator": binding.locator,
                "text": field_node.decoded,
                "token_range": list(binding.token_range),
                "encoded_body_range": list(binding.encoded_body_range),
                "encoded_token_sha256": binding.encoded_token_sha256,
                "decoded_sha256": binding.decoded_sha256,
                "speaker_known": binding.speaker_known,
                "translation_of": binding.translation_of,
            })
        verified.append({
            "record_pointer": record.record_pointer,
            "provider_record_id": record.provider_record_id,
            "record_kind": record.record_kind,
            "selected": record.selected,
            "selection_reason": record.selection_reason,
            "answer_first_publication_known": record.answer_first_publication_known,
            "record_created_date": record.record_created_date,
            "times": dict(record.times),
            "fields": fields,
        })
    return {
        "schema_version": "official-json-replay-result/1",
        "projection_id": projection.projection_id,
        "projection_sha256": projection.projection_sha256,
        "verified_records": len([r for r in verified if r["selected"]]),
        "records": verified,
    }


def evidence_span_for_field(projection: SourceProjection, record: ProjectionRecord,
                            binding: FieldBinding, *, paragraph_index: int,
                            decoded_text: str):
    """Bind one selected field to an EvidenceSpan v1 over the parent page.

    ``paragraph_index`` is the field's stable lexical ordinal on the page; it
    is never reordered by issuer filtering.  The JSON locator lives in
    ``structured_value.source_locator``; coordinates stay loc:v1.  The span's
    ``raw_text`` is the NFC-normalized display form of the exact decoded
    value, whose identity stays pinned by ``decoded_sha256``.
    """
    from company_wiki.source_contract.evidence_span import (
        EvidenceCoordinates,
        EvidenceSpan,
        ParseStatus,
    )
    parent = projection.parent_source_refs[0]
    structured = {
        "source_locator": binding.locator,
        "pointer": record.record_pointer + "/" + binding.field,
        "record_pointer": record.record_pointer,
        "provider_record_id": record.provider_record_id,
        "record_kind": record.record_kind,
        "role": binding.role,
        "token_range": list(binding.token_range),
        "encoded_body_range": list(binding.encoded_body_range),
        "encoded_token_sha256": binding.encoded_token_sha256,
        "decoded_sha256": binding.decoded_sha256,
        "answer_first_publication_known": record.answer_first_publication_known,
        "projection_id": projection.projection_id,
    }
    return EvidenceSpan.create(
        source_id=parent["source_id"],
        coordinates=EvidenceCoordinates(paragraph_index=paragraph_index),
        raw_text=unicodedata.normalize("NFC", decoded_text),
        structured_value=structured,
        parser_name="cwp_official_json",
        parser_version="1.0.0",
        parse_status=ParseStatus.PARSED,
        quality_flags=[],
    )


SOURCE_PROJECTION_EXPORT_SCHEMA = "source-projection-export/1"
SOURCE_PROJECTION_EXPORT_ID_PREFIX = "urn:company-wiki:source-projection-export:sha256:"


def build_projection_export(catalog, projection: SourceProjection) -> dict[str, Any]:
    """Versioned projection export: refs, projection and evidence spans."""
    reader = _reader(catalog)
    parents: dict[str, bytes] = {}
    for ref_value in projection.parent_source_refs:
        ref = _ref_from_dict(ref_value)
        content = reader.open_version(ref, purpose="source_export")
        parents[ref.content_sha256] = content.data
    texts: dict[str, str] = {}
    for ref_value in projection.parent_source_refs:
        doc = parse_json_structure(parents[ref_value["content_sha256"]])
        for node in _iter_string_nodes(doc.root):
            if node.decoded is not None:
                texts[node.decoded_sha256] = node.decoded
    spans: list[dict[str, Any]] = []
    paragraph = 0
    for record in projection.records:
        if not record.selected:
            continue
        for binding in record.fields:
            paragraph += 1
            span = evidence_span_for_field(
                projection, record, binding, paragraph_index=paragraph,
                decoded_text=texts.get(binding.decoded_sha256, ""))
            spans.append(span.to_dict())
    payload = {
        "schema_version": SOURCE_PROJECTION_EXPORT_SCHEMA,
        "source_refs": [dict(item) for item in projection.parent_source_refs],
        "projection": projection.to_dict(),
        "evidence_spans": spans,
        "counts": {
            "source_refs": len(projection.parent_source_refs),
            "evidence_spans": len(spans),
            "selected_records": len([r for r in projection.records if r.selected]),
        },
    }
    digest = hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()
    return {
        **payload,
        "bundle_sha256": digest,
        "export_id": SOURCE_PROJECTION_EXPORT_ID_PREFIX + digest,
    }


def _iter_string_nodes(node):
    if node.kind == "string":
        yield node
    elif node.kind == "object":
        for child in node.members().values():
            yield from _iter_string_nodes(child)
    elif node.kind == "array":
        for child in node.items():
            yield from _iter_string_nodes(child)
