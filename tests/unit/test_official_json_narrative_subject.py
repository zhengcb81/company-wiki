"""Subject identity contracts; real source parser, no catalog or external services."""
import hashlib
import json

import pytest

from company_wiki.narrative_subject import NarrativeSubject, SubjectBindingError, publication_target
from company_wiki.source_catalog.official_json_projection import build_source_projection
from company_wiki.source_catalog.official_json_structure import parse_json_structure


def projection(issuer=1):
    pages = []
    for page in (1, 2):
        rows = [{"ref": page * 10 + who, "org_id": who, "org_name": "Company " + str(who),
                 "q": "New business delivery?", "a": "Q4 delivery", "answered": True,
                 "created_at": "2026-09-01 10:00:00", "updated_at": "2026-09-01 10:00:00"}
                for who in (1, 2)]
        raw = json.dumps({"ok": True, "result": {"page": page, "page_size": 2,
            "page_count": 2, "item_total": 4, "items": rows}}).encode()
        pages.append((hashlib.sha256(raw).hexdigest(), len(raw), parse_json_structure(raw)))
    return build_source_projection(parent_pages=pages, layout_id="official-flat-list",
        issuer={"provider_company_id": issuer}, as_of_date="2026-10-08")


def test_raw_identity_and_legacy_target_are_unchanged():
    ref = projection().to_dict()["parent_source_refs"][0]
    subject = NarrativeSubject.from_raw(ref)
    assert subject.kind == "raw"
    assert subject.item_key == ref["document_id"]
    assert subject.subject_sha256 == ref["content_sha256"]
    assert subject.anchor_ref == ref
    assert publication_target(subject) == (
        "urn:company-wiki:narrative-bundle:" + ref["document_id"] + ":" + ref["content_sha256"])


def test_same_parent_two_issuers_are_distinct_compact_subjects():
    one, two = projection(1), projection(2)
    a, b = NarrativeSubject.from_projection(one), NarrativeSubject.from_projection(two)
    assert a.kind == b.kind == "official_json"
    assert a.item_key == one.projection_id
    assert b.item_key == two.projection_id
    assert a.item_key != b.item_key
    assert a.parent_source_refs == b.parent_source_refs
    assert len(a.parent_source_refs) == 2
    assert "records" not in a.to_dict()
    assert len(json.dumps(a.to_dict())) < len(json.dumps(one.to_dict()))
    assert a.issuer == one.to_dict()["issuer"]
    assert a.issuer["provider_company_id"] == 1
    assert a.as_of_date == "2026-10-08"


def test_projection_subject_deeply_isolates_input_and_output():
    source = projection()
    subject = NarrativeSubject.from_projection(source)
    original = subject.to_dict()
    input_wire = subject.to_dict()
    reconstructed = NarrativeSubject.from_dict(input_wire)
    input_wire["issuer"]["provider_company_id"] = 999
    assert reconstructed.to_dict() == original
    wire = subject.to_dict()
    wire["issuer"]["provider_company_id"] = 888
    wire["coverage"]["pages"][0]["content_sha256"] = "f" * 64
    parents = subject.parent_source_refs
    parents[0]["document_id"] = "different"
    assert subject.to_dict() == original
    assert NarrativeSubject.from_dict(original).to_dict() == original


@pytest.mark.parametrize("field,value", [("item_key", "urn:bad"),
    ("subject_sha256", "no-hash"), ("kind", "transcript"), ("parent_source_refs", []),
    ("as_of_date", "2026-99-99")])
def test_malformed_projection_binding_is_rejected(field, value):
    wire = NarrativeSubject.from_projection(projection()).to_dict()
    wire[field] = value
    with pytest.raises(SubjectBindingError):
        NarrativeSubject.from_dict(wire)


def test_wrong_parent_source_hash_binding_is_rejected():
    wire = NarrativeSubject.from_projection(projection()).to_dict()
    wire["parent_source_refs"][1]["content_sha256"] = "f" * 64
    with pytest.raises(SubjectBindingError):
        NarrativeSubject.from_dict(wire)


def test_duplicate_parent_observation_is_preserved_as_source_diagnostic():
    wire = NarrativeSubject.from_projection(projection()).to_dict()
    wire["parent_source_refs"].append(wire["parent_source_refs"][0])
    assert NarrativeSubject.from_dict(wire).to_dict() == wire


def test_projection_target_requires_generation_and_never_uses_raw_anchor():
    a, b = NarrativeSubject.from_projection(projection(1)), NarrativeSubject.from_projection(projection(2))
    with pytest.raises(SubjectBindingError):
        publication_target(a)
    assert publication_target(a, "a" * 64) != publication_target(b, "a" * 64)
    assert publication_target(a, "a" * 64) != publication_target(a, "b" * 64)
    assert publication_target(a, "a" * 64) != publication_target(NarrativeSubject.from_raw(a.anchor_ref))


def test_full_source_projection_schema_is_not_relabelled_as_compact_binding():
    with pytest.raises(SubjectBindingError):
        NarrativeSubject.from_dict(projection().to_dict())


def test_properties_do_not_redecode_binding_for_identity(monkeypatch):
    subject = NarrativeSubject.from_projection(projection())
    def forbidden(*args, **kwargs):
        raise AssertionError("scalar identity must not repeatedly parse the full binding")
    monkeypatch.setattr("company_wiki.narrative_subject.json.loads", forbidden)
    assert subject.kind == "official_json"
    assert subject.item_key.endswith(subject.subject_sha256)


def test_nonfinite_stored_binding_is_rejected():
    wire = NarrativeSubject.from_projection(projection()).to_dict()
    wire["coverage"]["unexpected"] = float("nan")
    with pytest.raises(SubjectBindingError):
        NarrativeSubject.from_dict(wire)
    with pytest.raises(SubjectBindingError):
        NarrativeSubject(json.dumps(wire))
