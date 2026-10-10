"""Shared internal identity for raw and projected narrative work.

A binding is a detached identity snapshot, not proof of current source truth.
The source port verifies current bytes and semantics at its own boundaries.
No records, storage locations or automation dependencies are stored here.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date
import json
import re
from typing import Any, Protocol, cast

from .source_contract import source_id_for_sha256

_SHA = re.compile(r"[0-9a-f]{64}\Z")
_PROJECTION_PREFIX = "urn:company-wiki:source-projection:sha256:"
_BASE_KEYS = {"kind", "item_key", "subject_sha256", "parent_source_refs"}
_PROJECTION_KEYS = _BASE_KEYS | {"issuer", "as_of_date", "adapter", "coverage"}
_REF_KEYS = {"schema_version", "document_id", "source_id", "content_sha256", "byte_size", "mime_type"}


class SubjectBindingError(ValueError):
    """An internal identity snapshot cannot be interpreted consistently."""


class ProjectionSnapshot(Protocol):
    def to_dict(self) -> dict[str, Any]: ...


def _plain(value: Any) -> Any:
    if isinstance(value, Mapping):
        if any(not isinstance(key, str) for key in value):
            raise SubjectBindingError("subject JSON keys must be strings")
        return {key: _plain(child) for key, child in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return [_plain(child) for child in value]
    return value


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value) and value.strip() == value


def _hash(value: Any) -> bool:
    return isinstance(value, str) and _SHA.fullmatch(value) is not None


def _validate_ref(ref: Any) -> None:
    if not isinstance(ref, dict) or set(ref) != _REF_KEYS or ref["schema_version"] != "2.0":
        raise SubjectBindingError("invalid parent SourceRef 2.0")
    if (not _hash(ref["content_sha256"])
            or ref["source_id"] != source_id_for_sha256(ref["content_sha256"])
            or not _text(ref["document_id"]) or not _text(ref["mime_type"])
            or type(ref["byte_size"]) is not int or ref["byte_size"] <= 0):
        raise SubjectBindingError("inconsistent parent source identity")


def _validate(value: Any) -> None:
    if not isinstance(value, dict):
        raise SubjectBindingError("subject binding must be an object")
    kind = value.get("kind")
    keys = _BASE_KEYS if kind == "raw" else _PROJECTION_KEYS if kind == "official_json" else None
    if keys is None or set(value) != keys or not _hash(value["subject_sha256"]):
        raise SubjectBindingError("invalid subject binding fields")
    parents = value["parent_source_refs"]
    if not isinstance(parents, list) or not parents:
        raise SubjectBindingError("subject requires its real parent references")
    for ref in parents:
        _validate_ref(ref)
    if kind == "raw":
        if (len(parents) != 1 or value["item_key"] != parents[0]["document_id"]
                or value["subject_sha256"] != parents[0]["content_sha256"]):
            raise SubjectBindingError("raw subject differs from its source reference")
        return
    if value["item_key"] != _PROJECTION_PREFIX + value["subject_sha256"]:
        raise SubjectBindingError("projection ID differs from projection hash")
    if (not isinstance(value["issuer"], dict) or not isinstance(value["adapter"], dict)
            or not isinstance(value["coverage"], dict)):
        raise SubjectBindingError("projection binding requires source context")
    try:
        cutoff = date.fromisoformat(value["as_of_date"])
        if cutoff.isoformat() != value["as_of_date"]:
            raise ValueError("noncanonical date")
    except (TypeError, ValueError):
        raise SubjectBindingError("invalid projection as-of date") from None


@dataclass(frozen=True)
class NarrativeSubject:
    _binding_json: str
    _kind: str = field(init=False, repr=False)
    _item_key: str = field(init=False, repr=False)
    _subject_sha256: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        try:
            value = json.loads(self._binding_json)
            _validate(value)
            json.dumps(value, allow_nan=False)
            object.__setattr__(self, "_kind", value["kind"])
            object.__setattr__(self, "_item_key", value["item_key"])
            object.__setattr__(self, "_subject_sha256", value["subject_sha256"])
        except (TypeError, ValueError) as exc:
            raise SubjectBindingError("invalid serialized subject") from exc

    @classmethod
    def from_dict(cls, value: object) -> NarrativeSubject:
        plain = _plain(value)
        try:
            encoded = json.dumps(plain, ensure_ascii=False, sort_keys=True,
                                 separators=(",", ":"), allow_nan=False)
        except (TypeError, ValueError) as exc:
            raise SubjectBindingError("subject binding is not finite JSON") from exc
        return cls(encoded)

    @classmethod
    def from_raw(cls, source_ref: Mapping[str, Any]) -> NarrativeSubject:
        ref = _plain(source_ref)
        _validate_ref(ref)
        return cls.from_dict({"kind": "raw", "item_key": ref["document_id"],
            "subject_sha256": ref["content_sha256"], "parent_source_refs": [ref]})

    @classmethod
    def from_projection(cls, projection: ProjectionSnapshot) -> NarrativeSubject:
        value = projection.to_dict()
        return cls.from_dict({"kind": "official_json", "item_key": value["projection_id"],
            "subject_sha256": value["projection_sha256"],
            "parent_source_refs": value["parent_source_refs"], "issuer": value["issuer"],
            "as_of_date": value["as_of_date"], "adapter": value["adapter"],
            "coverage": value["coverage"]})

    def to_dict(self) -> dict[str, Any]:
        return cast(dict[str, Any], json.loads(self._binding_json))

    @property
    def kind(self) -> str:
        return self._kind

    @property
    def item_key(self) -> str:
        return self._item_key

    @property
    def subject_sha256(self) -> str:
        return self._subject_sha256

    @property
    def parent_source_refs(self) -> tuple[dict[str, Any], ...]:
        return tuple(self.to_dict()["parent_source_refs"])

    @property
    def anchor_ref(self) -> dict[str, Any]:
        """Real parent FK association, never a substitute for subject identity."""
        return self.parent_source_refs[0]

    @property
    def issuer(self) -> dict[str, Any] | None:
        return cast(dict[str, Any] | None, self.to_dict().get("issuer"))

    @property
    def as_of_date(self) -> str | None:
        return cast(str | None, self.to_dict().get("as_of_date"))


def publication_target(subject: NarrativeSubject, generation_sha256: str | None = None) -> str:
    if subject.kind == "raw":
        return "urn:company-wiki:narrative-bundle:" + subject.item_key + ":" + subject.subject_sha256
    if not _hash(generation_sha256):
        raise SubjectBindingError("projection publication requires its exact generation hash")
    return ("urn:company-wiki:narrative-projection-bundle:" + subject.subject_sha256
            + ":" + str(generation_sha256))
