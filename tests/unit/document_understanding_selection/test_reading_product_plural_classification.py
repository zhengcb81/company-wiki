"""Shared source product heads must not depend on singular/plural spelling."""
from pathlib import Path

import pytest

from company_wiki.document_understanding import narrative_continuity as continuity
from company_wiki.document_understanding.operating_states import relations
from company_wiki.resource_budget import WorkBudget
from company_wiki.source_catalog.narrative_operating_relations import SourceOperatingSession
from unit.document_understanding_selection.test_reading_native_carriers import source_fixture


@pytest.fixture(autouse=True)
def imports_owned_checkout():
    src = Path(__file__).resolve().parents[3] / "src"
    assert Path(relations.__file__).resolve().is_relative_to(src)
    assert Path(continuity.__file__).resolve().is_relative_to(src)


def observe(text):
    observation = {"schema_version": relations.OBSERVATION_SCHEMA, "unit_id": "u", "units": {
        "u": {"text": text, "parent_id": "source", "role": "management",
              "kind": "paragraph", "locator": "native:0"}}}
    result = relations.detect_operating_relations(observation, work_budget=WorkBudget(100000))
    assert result["status"] == "complete"
    return [r for r in result["relations"] if r["activity"] == "qualification"]


def slices(text, relation, field):
    refs = relation[field]
    assert all(r["unit_id"] == "u" and 0 <= r["char_start"] < r["char_end"] <= len(text)
               for r in refs)
    return [text[r["char_start"]:r["char_end"]] for r in refs]


@pytest.mark.parametrize("subject", [
    "This product", "These products", "These PRODUCTS", "This system", "These systems",
    "These devices", "These platforms", "These modules", "These materials", "These filters",
])
def test_product_subject_singular_and_plural_remain_objects_with_original_offsets(subject):
    text = subject + " have not obtained customer qualification."
    found = observe(text)
    assert len(found) == 1
    relation = found[0]
    assert slices(text, relation, "object_refs") == [subject]
    assert slices(text, relation, "actor_refs") == []
    assert (relation["polarity"], relation["stage"], relation["modality"]) == (
        "negative", "current", "actual")
    assert relation["attribution"] == "unknown"  # Lexical heads do not prove an issuer.


@pytest.mark.parametrize("text,objects", [
    ("II) These products have not obtained customer qualification.", ["These products"]),
    ("该产品尚未完成客户认证。", ["产品", "客户"]),
    ("該產品尚未完成客戶認證。", ["產品", "客戶"]),
])
def test_native_marker_and_script_preserve_exact_product_refs(text, objects):
    found = observe(text)
    assert len(found) == 1
    assert slices(text, found[0], "object_refs") == objects
    assert slices(text, found[0], "actor_refs") == []
    assert found[0]["object_refs"] == [
        {"unit_id": "u", "char_start": text.index(subject),
         "char_end": text.index(subject) + len(subject)} for subject in objects]


@pytest.mark.parametrize("subject", [
    "Sales", "Analysis", "Business", "Customers", "Pipelines", "Acme Systems Inc", "Newlines",
])
def test_ordinary_subjects_and_embedded_head_substrings_remain_actors(subject):
    text = subject + " have not obtained customer qualification."
    found = observe(text)
    assert len(found) == 1
    assert slices(text, found[0], "actor_refs") == [subject]
    assert slices(text, found[0], "object_refs") == []


@pytest.mark.parametrize("subject", ["products", "systems", "PRODUCTS", "product"])
def test_independent_our_subject_uses_the_same_product_head(subject):
    assert relations.independent_statement_start("Our " + subject + " have not obtained qualification.")


@pytest.mark.parametrize("subject", ["sales", "analysis", "customers", "pipelines", "Newlines"])
def test_independent_our_nonproduct_subject_does_not_claim_product_boundary(subject):
    assert not relations.independent_statement_start("Our " + subject + " have not obtained qualification.")


def test_mixed_product_and_third_party_subjects_keep_both_roles():
    text = "These products and customers have not obtained customer qualification."
    found = observe(text)
    assert len(found) == 1
    assert slices(text, found[0], "object_refs") == ["These products"]
    assert slices(text, found[0], "actor_refs") == ["customers"]
    assert found[0]["attribution"] == "other"


def test_new_independent_actor_does_not_inherit_the_prior_product():
    text = ("These products have not obtained customer qualification. "
            "Customers have obtained customer qualification.")
    found = observe(text)
    assert len(found) == 2
    assert slices(text, found[0], "object_refs") == ["These products"]
    assert slices(text, found[1], "object_refs") == []
    assert slices(text, found[1], "actor_refs") == ["Customers"]
    assert (found[1]["polarity"], found[1]["stage"], found[1]["modality"],
            found[1]["attribution"]) == ("unknown", "unknown", "uncertain", "other")


@pytest.mark.parametrize("object_text,right", [
    ("ZX-17 products", "These products have not obtained customer qualification."),
    ("ZX-17 systems", "These systems have not obtained customer qualification."),
    ("ZX-17 product", "This product has not obtained customer qualification."),
])
def test_true_local_product_restriction_closes_over_existing_source_dependency(object_text, right):
    left = "The company has shipped " + object_text + "."
    parsed, pipeline = source_fixture([(left,), (right,)])
    original = [(u.raw_text, u.coordinates, u.metadata) for u in parsed.units]
    budget = WorkBudget(100000)
    result = continuity.build_native_continuity(pipeline["observation"]["units"],
        provenance={u.unit_id: {**u.metadata, "source_id": u.source_id,
                    "paragraph_index": u.coordinates.paragraph_index} for u in parsed.units},
        unit_profiles=pipeline["reading_plan"]["unit_profiles"], work_budget=budget)
    session = SourceOperatingSession({u.unit_id: u for u in parsed.units}, work_budget=budget)
    assert session.local_qualification_dependencies(result["adjacency_edges"]) == {
        parsed.units[0].unit_id: (parsed.units[1].unit_id,)}
    assert [(u.raw_text, u.coordinates, u.metadata) for u in parsed.units] == original
    assert budget.used <= 100000 and not budget.exhausted

@pytest.mark.parametrize("subject", ["These products", "This product"])
def test_unproved_positive_completion_stays_uncertain_during_role_classification(subject):
    text = subject + " have obtained customer qualification."
    found = observe(text)
    assert len(found) == 1
    assert slices(text, found[0], "object_refs") == [subject]
    assert (found[0]["polarity"], found[0]["stage"], found[0]["modality"],
            found[0]["attribution"]) == ("unknown", "unknown", "uncertain", "unknown")


@pytest.mark.parametrize("subject", ["Acme Systems", "North Materials"])
def test_ambiguous_names_do_not_create_an_issuer_or_reference_dependency(subject):
    text = subject + " have not obtained customer qualification."
    found = observe(text)
    assert len(found) == 1
    assert found[0]["attribution"] == "unknown"
    parsed, pipeline = source_fixture([("The company has shipped ZX-17 products.",), (text,)])
    budget = WorkBudget(100000)
    result = continuity.build_native_continuity(pipeline["observation"]["units"],
        provenance={u.unit_id: {**u.metadata, "source_id": u.source_id,
                    "paragraph_index": u.coordinates.paragraph_index} for u in parsed.units},
        unit_profiles=pipeline["reading_plan"]["unit_profiles"], work_budget=budget)
    session = SourceOperatingSession({u.unit_id: u for u in parsed.units}, work_budget=budget)
    assert session.local_qualification_dependencies(result["adjacency_edges"]) == {}