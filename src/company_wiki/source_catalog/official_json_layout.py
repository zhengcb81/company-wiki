"""Declared JSON layout adapters: envelope, pagination, records, field roles.

A layout is registered data, not executable expressions and not provider
script.  It declares where a paged collection lives, which fields carry
record/issuer/text/time/state meaning, and which provider state values mark
statements instead of answers.  No company name, ticker, page number or
record id may appear here; unknown shapes stay ``unsupported_json_layout``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
from typing import Any

from .official_json_structure import (
    JsonStructureDocument,
    JsonStructureError,
    JsonStructureNode,
)

LAYOUT_DTO_SCHEMA = "official-json-layout/1"


class OfficialJsonLayoutError(ValueError):
    """A named layout refusal; the raw page is never rewritten."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class TextFieldRule:
    """A declared business text field and its neutral role base."""

    name: str
    role_base: str  # "question" | "answer_or_statement"

    def to_dict(self) -> dict[str, str]:
        return {"field": self.name, "role_base": self.role_base}


@dataclass(frozen=True)
class JsonLayout:
    schema_version: str
    layout_id: str
    layout_version: str
    envelope_success_pointer: str | None
    envelope_code_pointer: str | None
    envelope_message_pointer: str | None
    envelope_error_fields: tuple[str, ...]
    collection_pointer: str
    pagination_pointer: str | None
    pagination_fields: dict[str, str] = field(default_factory=dict)
    record_id_field: str = "id"
    activity_issuer_fields: tuple[str, ...] = ()
    company_issuer_fields: tuple[str, ...] = ()
    stock_code_field: str | None = None
    company_name_fields: tuple[str, ...] = ()
    text_fields: tuple[TextFieldRule, ...] = ()
    precollect_question_field: str | None = None
    precollect_answer_field: str | None = None
    translation_fields: tuple[tuple[str, str], ...] = ()
    time_fields: tuple[str, ...] = ()
    state_fields: tuple[str, ...] = ()
    answered_state_field: str | None = None
    question_ref_field: str | None = None
    statement_type_field: str | None = None
    statement_type_values: tuple[int, ...] = ()
    envelope_error_string_fields: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "layout_id": self.layout_id,
            "layout_version": self.layout_version,
            "envelope": {
                "success_pointer": self.envelope_success_pointer,
                "code_pointer": self.envelope_code_pointer,
                "message_pointer": self.envelope_message_pointer,
                "error_fields": list(self.envelope_error_fields),
            },
            "collection_pointer": self.collection_pointer,
            "pagination": {
                "container_pointer": self.pagination_pointer,
                "fields": dict(self.pagination_fields),
            },
            "record_id_field": self.record_id_field,
            "issuer_fields": {
                "activity": list(self.activity_issuer_fields),
                "company": list(self.company_issuer_fields),
                "stock_code": self.stock_code_field,
                "names": list(self.company_name_fields),
            },
            "text_fields": [rule.to_dict() for rule in self.text_fields],
            "precollect": {
                "question_field": self.precollect_question_field,
                "answer_field": self.precollect_answer_field,
            },
            "translation_fields": [
                {"field": name, "of": origin} for name, origin in self.translation_fields
            ],
            "time_fields": list(self.time_fields),
            "state_fields": list(self.state_fields),
            "classification": {
                "answered_state_field": self.answered_state_field,
                "question_ref_field": self.question_ref_field,
                "statement_type_field": self.statement_type_field,
                "statement_type_values": list(self.statement_type_values),
            },
        }


def _paged_qa_layout() -> JsonLayout:
    return JsonLayout(
        schema_version=LAYOUT_DTO_SCHEMA,
        layout_id="official-paged-qa",
        layout_version="1.0.0",
        envelope_success_pointer="/success",
        envelope_code_pointer="/code",
        envelope_message_pointer="/message",
        envelope_error_fields=("status",),
        envelope_error_string_fields=("error",),
        collection_pointer="/datas/0/records",
        pagination_pointer="/datas/0",
        pagination_fields={"current": "current", "size": "size",
                           "pages": "pages", "total": "total"},
        record_id_field="id",
        activity_issuer_fields=("activityCompanyId", "aactivityCompanyId",
                                "qactivityCompanyId"),
        company_issuer_fields=("companyId",),
        stock_code_field="stockCode",
        company_name_fields=("companyName", "companyShortName", "shortName",
                             "guestCompanyName"),
        text_fields=(
            TextFieldRule("content", "answer_or_statement"),
            TextFieldRule("questionContent", "question"),
        ),
        precollect_question_field="question",
        precollect_answer_field="answer",
        translation_fields=(("contentEn", "content"),
                            ("questionContentEn", "questionContent")),
        time_fields=("crtTime", "updTime", "auditTime", "questionDate",
                     "questionUpdDate"),
        state_fields=("isAnswered", "questionType", "questionId", "collectType",
                      "status"),
        answered_state_field="isAnswered",
        question_ref_field="questionId",
        statement_type_field="questionType",
        statement_type_values=(3,),
    )


def _flat_list_layout() -> JsonLayout:
    """A second declared layout proving the mapping is not SSE-specific."""

    return JsonLayout(
        schema_version=LAYOUT_DTO_SCHEMA,
        layout_id="official-flat-list",
        layout_version="1.0.0",
        envelope_success_pointer="/ok",
        envelope_code_pointer=None,
        envelope_message_pointer="/error_message",
        envelope_error_fields=("error",),
        collection_pointer="/result/items",
        pagination_pointer="/result",
        pagination_fields={"current": "page", "size": "page_size",
                           "pages": "page_count", "total": "item_total"},
        record_id_field="ref",
        activity_issuer_fields=(),
        company_issuer_fields=("org_id",),
        stock_code_field=None,
        company_name_fields=("org_name",),
        text_fields=(
            TextFieldRule("q", "question"),
            TextFieldRule("a", "answer_or_statement"),
        ),
        precollect_question_field=None,
        precollect_answer_field=None,
        translation_fields=(),
        time_fields=("created_at", "updated_at"),
        state_fields=("answered",),
        answered_state_field="answered",
        question_ref_field=None,
        statement_type_field=None,
        statement_type_values=(),
    )


_REGISTRY: dict[str, JsonLayout] = {
    "official-paged-qa": _paged_qa_layout(),
    "official-flat-list": _flat_list_layout(),
}


def registered_layout(layout_id: str) -> JsonLayout:
    if not isinstance(layout_id, str) or layout_id not in _REGISTRY:
        raise OfficialJsonLayoutError("unsupported_json_layout")
    return _REGISTRY[layout_id]


def registered_layout_ids() -> tuple[str, ...]:
    return tuple(sorted(_REGISTRY))


def layout_fingerprint(layout_id: str) -> str:
    layout = registered_layout(layout_id)
    encoded = json.dumps(layout.to_dict(), ensure_ascii=False, sort_keys=True,
                         separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class FieldObservation:
    field: str
    pointer: str
    role_base: str
    locator: str
    token_range: tuple[int, int]
    encoded_body_range: tuple[int, int]
    encoded_token_sha256: str
    decoded: str
    decoded_sha256: str
    decoded_character_count: int
    translation_of: str | None = None


@dataclass(frozen=True)
class RecordObservation:
    pointer: str
    provider_record_id: Any
    token_range: tuple[int, int]
    record_token_sha256: str
    attributed: bool
    issuer_observed: dict[str, Any]
    text_fields: dict[str, FieldObservation]
    translation_fields: dict[str, FieldObservation]
    times: dict[str, str]
    state: dict[str, Any]

    @property
    def activity_company_ids(self) -> tuple[int, ...]:
        values = [value for value in self.issuer_observed.get(
            "provider_company_ids", ()) if isinstance(value, int)]
        return tuple(sorted(set(values)))


@dataclass(frozen=True)
class PageObservation:
    layout_id: str
    layout_version: str
    envelope: dict[str, Any]
    envelope_status: str
    business_evidence: bool
    pagination: dict[str, Any]
    records: tuple[RecordObservation, ...]


def _optional_node(doc: JsonStructureDocument, pointer: str | None
                   ) -> JsonStructureNode | None:
    if not pointer:
        return None
    try:
        return doc.at_pointer(pointer)
    except JsonStructureError as exc:
        if exc.code == "pointer_not_found":
            return None
        raise


def _field_observation(record_pointer: str, name: str, role_base: str,
                       node: JsonStructureNode, *,
                       translation_of: str | None = None) -> FieldObservation:
    return FieldObservation(
        field=name,
        pointer=node.pointer,
        role_base=role_base,
        locator=node.locator(),
        token_range=node.token_range,
        encoded_body_range=node.encoded_body_range,
        encoded_token_sha256=node.encoded_token_sha256,
        decoded=node.decoded or "",
        decoded_sha256=node.decoded_sha256,
        decoded_character_count=node.decoded_character_count,
        translation_of=translation_of,
    )


def describe_layout_page(layout_id: str, doc: JsonStructureDocument
                         ) -> PageObservation:
    """Project one parsed page through a declared layout, or refuse."""
    layout = registered_layout(layout_id)

    error_signal = False
    for name in layout.envelope_error_fields:
        node = _optional_node(doc, "/" + name)
        if node is None:
            continue
        if node.kind == "number" and node.value is not None:
            # Status-code style indicators: failure is a real HTTP-ish code.
            error_signal = error_signal or int(node.value) >= 400
        elif node.kind == "literal":
            error_signal = error_signal or node.value is True
    for name in layout.envelope_error_string_fields:
        node = _optional_node(doc, "/" + name)
        if node is not None and node.kind == "string" and node.decoded:
            error_signal = True
    success = _optional_node(doc, layout.envelope_success_pointer)
    code = _optional_node(doc, layout.envelope_code_pointer)
    if success is not None and success.kind == "literal":
        error_signal = error_signal or success.value is not True
    if code is not None and code.kind == "number":
        error_signal = error_signal or not 200 <= int(code.value) < 300
    envelope: dict[str, Any] = {}
    if success is not None:
        envelope["success"] = success.value
    if code is not None:
        envelope["code"] = code.value
    message = _optional_node(doc, layout.envelope_message_pointer)
    if message is not None and message.kind == "string":
        envelope["message"] = message.decoded
    if error_signal:
        return PageObservation(
            layout_id=layout.layout_id, layout_version=layout.layout_version,
            envelope=envelope, envelope_status="response_is_error",
            business_evidence=False, pagination={}, records=(),
        )
    if success is None and layout.envelope_success_pointer:
        # No declared success field and no declared error field: this page is
        # not an error response, it is a shape the layout never declared.
        raise OfficialJsonLayoutError("layout_pointer_not_found")

    collection = _optional_node(doc, layout.collection_pointer)
    if collection is None or collection.kind != "array":
        raise OfficialJsonLayoutError("layout_pointer_not_found")

    pagination: dict[str, Any] = {}
    if layout.pagination_pointer:
        container = _optional_node(doc, layout.pagination_pointer)
        if container is None or container.kind != "object":
            raise OfficialJsonLayoutError("layout_pointer_not_found")
        for role, name in layout.pagination_fields.items():
            node = container.members().get(name)
            if node is not None and node.kind == "number":
                pagination[role] = node.value

    records: list[RecordObservation] = []
    for index, node in enumerate(collection.items()):
        if node.kind != "object":
            raise OfficialJsonLayoutError("layout_record_not_object")
        records.append(_describe_record(layout, node))
    return PageObservation(
        layout_id=layout.layout_id, layout_version=layout.layout_version,
        envelope=envelope, envelope_status="ok", business_evidence=True,
        pagination=pagination, records=tuple(records),
    )


def _describe_record(layout: JsonLayout, node: JsonStructureNode
                     ) -> RecordObservation:
    members = node.members()
    provider_id: Any = None
    id_node = members.get(layout.record_id_field)
    if id_node is not None and id_node.kind in {"number", "string"}:
        provider_id = id_node.value

    issuer_observed: dict[str, Any] = {
        "provider_company_ids": [],
        "provider_company_id": None,
        "stock_code": None,
        "company_names": [],
    }
    activity_ids: list[int] = []
    primary_activity: int | None = None
    for name in layout.activity_issuer_fields:
        member = members.get(name)
        if member is not None and member.kind == "number":
            value = int(member.value)
            activity_ids.append(value)
            if name == layout.activity_issuer_fields[0] and primary_activity is None:
                primary_activity = value
    for name in layout.company_issuer_fields:
        member = members.get(name)
        if member is not None and member.kind == "number":
            issuer_observed["provider_company_id"] = int(member.value)
    if layout.stock_code_field:
        member = members.get(layout.stock_code_field)
        if member is not None and member.kind == "string" and member.decoded:
            issuer_observed["stock_code"] = member.decoded
    names: list[str] = []
    for name in layout.company_name_fields:
        member = members.get(name)
        if member is not None and member.kind == "string" and member.decoded:
            names.append(member.decoded)
    issuer_observed["provider_company_ids"] = sorted(set(activity_ids))
    issuer_observed["provider_activity_company_id"] = primary_activity
    issuer_observed["company_names"] = names
    attributed = bool(activity_ids or issuer_observed["provider_company_id"]
                      is not None)

    text_fields: dict[str, FieldObservation] = {}
    for rule in layout.text_fields:
        member = members.get(rule.name)
        if member is not None and member.kind == "string":
            text_fields[rule.name] = _field_observation(
                node.pointer, rule.name, rule.role_base, member)
    if layout.precollect_question_field:
        member = members.get(layout.precollect_question_field)
        if member is not None and member.kind == "string":
            text_fields[layout.precollect_question_field] = _field_observation(
                node.pointer, layout.precollect_question_field, "question", member)
    if layout.precollect_answer_field:
        member = members.get(layout.precollect_answer_field)
        if member is not None and member.kind == "string" and member.decoded:
            text_fields[layout.precollect_answer_field] = _field_observation(
                node.pointer, layout.precollect_answer_field,
                "answer_or_statement", member)

    translation_fields: dict[str, FieldObservation] = {}
    for name, origin in layout.translation_fields:
        member = members.get(name)
        if member is not None and member.kind == "string" and member.decoded:
            translation_fields[name] = _field_observation(
                node.pointer, name, "translation", member, translation_of=origin)

    times: dict[str, str] = {}
    for name in layout.time_fields:
        member = members.get(name)
        if member is not None and member.kind == "string" and member.decoded:
            times[name] = member.decoded
    state: dict[str, Any] = {}
    for name in layout.state_fields:
        member = members.get(name)
        if member is not None:
            state[name] = member.value

    return RecordObservation(
        pointer=node.pointer,
        provider_record_id=provider_id,
        token_range=node.token_range,
        record_token_sha256=node.encoded_token_sha256,
        attributed=attributed,
        issuer_observed=issuer_observed,
        text_fields=text_fields,
        translation_fields=translation_fields,
        times=times,
        state=state,
    )


def classify_record(layout: JsonLayout, record: RecordObservation) -> str:
    """Classify a record from declared state fields, never from text cues."""
    answered = None
    if layout.answered_state_field:
        answered = record.state.get(layout.answered_state_field)
    has_question_ref = bool(
        layout.question_ref_field
        and record.state.get(layout.question_ref_field) is not None
    )
    statement_type = None
    if layout.statement_type_field:
        value = record.state.get(layout.statement_type_field)
        if isinstance(value, int):
            statement_type = value
    answer_present = any(
        rule.role_base == "answer_or_statement" and rule.name in record.text_fields
        for rule in layout.text_fields
    ) or bool(layout.precollect_answer_field
              and layout.precollect_answer_field in record.text_fields)
    has_precollect_question = bool(
        layout.precollect_question_field
        and layout.precollect_question_field in record.text_fields)
    has_precollect_answer = bool(
        layout.precollect_answer_field
        and layout.precollect_answer_field in record.text_fields)
    question_present = has_precollect_question or any(
        rule.role_base == "question" and rule.name in record.text_fields
        for rule in layout.text_fields
    )
    text_present = question_present or answer_present

    if has_precollect_question and has_precollect_answer:
        return "precollected_question_with_answer"
    if has_precollect_question:
        return "unanswered_question"
    if has_question_ref and answered is True and answer_present:
        return "answered_qa"
    if (statement_type is not None
            and statement_type in layout.statement_type_values
            and answered is not True):
        if not record.attributed:
            return "event_remark_unattributed"
        return "closing_remark"
    if not record.attributed:
        return "event_remark_unattributed"
    if answered is False and text_present:
        return "unanswered_question"
    if answered is True and answer_present:
        return "answered_qa"
    return "other_statement"
