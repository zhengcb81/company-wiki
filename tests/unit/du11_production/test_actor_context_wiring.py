"""Source session preserves actor context in original IDs before selection."""
from company_wiki.resource_budget import WorkBudget
from company_wiki.source_catalog.narrative_operating_relations import SourceOperatingSession
from unit.du11_source_closure.test_antecedent_wiring import text_case
from dataclasses import replace
import pytest


def test_session_keeps_adjacent_business_without_promoting_identity_and_reuses_preparation():
    parsed, _, ids = text_case(['At Oriole, orders are rising.', 'Beyond this, our new policies rose by 12%.'])
    budget = WorkBudget(100_000)
    session = SourceOperatingSession({u.unit_id: u for u in parsed.units}, work_budget=budget,
                                    antecedents={ids[1]: ((ids[0],), True)})
    result = session.reference(ids[1])
    assert result['required_original_unit_ids'] == (ids[0],)
    assert result['attribution'] == 'unknown'
    assert result['reference_kind'] == 'actor_context'
    used = budget.used
    assert session.reference(ids[1]) == result
    assert budget.used == used


def test_composed_material_reference_offsets_return_to_original_units():
    parsed, _, ids = text_case(['Oriole serves this market.', 'Beyond this, we have not', 'started shipments.'])
    session = SourceOperatingSession({u.unit_id: u for u in parsed.units}, work_budget=WorkBudget(100_000),
                                    groups={'joined': tuple(ids[1:])},
                                    antecedents={ids[1]: ((ids[0],), True)})
    result = session.reference(ids[1])
    assert result['required_original_unit_ids'] == (ids[0],)
    assert result['reference_refs']
    assert all(ref['unit_id'] in ids[1:] for ref in result['reference_refs'])
    assert all(ref['unit_id'] != 'joined' for ref in result['reference_refs'])


@pytest.mark.parametrize('nested', [False, True])
def test_actual_metadata_turn_boundary_prevents_borrowing_previous_business(nested):
    parsed, _, ids = text_case(['Oriole serves this market.', 'Beyond this, we plan production next year.'])
    units = {}
    for i, unit in enumerate(parsed.units):
        turn = {'speaker': 'same-person', 'turn_id': f'turn-{i}', 'timestamp': f'00:0{i}'}
        metadata = {'native_speaker_turn': turn} if nested else turn
        units[unit.unit_id] = replace(unit, metadata=metadata)
    session = SourceOperatingSession(units, work_budget=WorkBudget(100_000),
                                    antecedents={ids[1]: ((ids[0],), True)})
    result = session.reference(ids[1])
    assert not result['required_original_unit_ids']
    assert result['attribution'] == 'unknown'


def test_source_session_owns_frozen_context_and_one_work_account():
    parsed, _, ids = text_case(['Oriole supplies control systems.', 'We delivered 30 units.'])
    units = {unit.unit_id: unit for unit in parsed.units}
    contexts = {ids[1]: (ids[0],)}
    budget = WorkBudget(100_000)
    session = SourceOperatingSession(units, work_budget=budget, contexts=contexts)
    contexts.clear()
    assert session.context_for(ids[1]) == (ids[0],)
    with pytest.raises(AttributeError):
        session.work_budget = WorkBudget(100_000)
    with pytest.raises(TypeError):
        session.units[ids[1]] = parsed.units[0]
    assert not hasattr(session, "engine") and not hasattr(session, "groups")


def test_preparation_reuses_the_exact_scope_and_keeps_other_meaning_context_separate():
    parsed, _, ids = text_case(['Oriole supplies control systems.', 'We delivered 30 units.'])
    session = SourceOperatingSession({unit.unit_id: unit for unit in parsed.units},
                                    work_budget=WorkBudget(100_000))
    base = session.fact(ids[1])
    citation = session.citation_owner((ids[1],))
    assert citation == ids[1] and session.fact(citation) is base
    contextual = session.support_owner((ids[1],), meaning_context=(ids[0],))
    assert contextual != citation
    assert session.context_for(contextual) == (ids[0],)
    assert session.context_for(citation) == ()


def test_observed_antecedents_are_part_of_reference_cache_identity():
    parsed, _, ids = text_case(['Oriole serves this market.', 'Beyond this, we gained customers.'])
    session = SourceOperatingSession({unit.unit_id: unit for unit in parsed.units},
                                    work_budget=WorkBudget(100_000))
    owner = session.support_owner((ids[1],))
    unresolved = session.reference(owner)
    with_predecessor = session.reference(owner, window=((ids[0],), True))
    assert ids[0] in with_predecessor['required_original_unit_ids']
    assert not unresolved['required_original_unit_ids']
    assert session.reference(owner, window=((ids[0],), True)) == with_predecessor
    assert session.reference(owner) == unresolved


def test_mutating_a_serializable_observation_cannot_rewrite_source_proof():
    parsed, _, ids = text_case(['公司已经交付控制系统。'])
    session = SourceOperatingSession({unit.unit_id: unit for unit in parsed.units},
                                    work_budget=WorkBudget(100_000))
    expected = session.relations(ids[0])
    assert expected["relations"]
    observed = session.relations(ids[0])
    used = session.work_budget.used
    observed["relations"][0]["assertion_refs"].clear()
    observed["status"] = "partial"
    assert session.relations(ids[0])["relations"][0]["assertion_refs"]
    assert session.relations(ids[0])["status"] == "complete"
    assert session.work_budget.used == used


def test_reference_cannot_use_a_product_declaration_from_the_future():
    from unit.du11_source_closure.test_reference_closure import CN_DECLARATION, CN_TARGET

    parsed, _, ids = text_case([CN_TARGET, CN_DECLARATION])
    session = SourceOperatingSession({unit.unit_id: unit for unit in parsed.units},
                                    work_budget=WorkBudget(100_000))
    observed = session.reference(ids[0], window=((ids[1],), True))
    assert observed["status"] == "partial"
    assert not observed["declaration_refs"] and not observed["required_original_unit_ids"]


@pytest.mark.parametrize("overlaps_target", [False, True])
def test_reference_checks_the_full_original_range_of_a_declaration_carrier(overlaps_target):
    from unit.du11_source_closure.test_reference_closure import CN_DECLARATION, CN_TARGET

    parsed, _, ids = text_case([CN_DECLARATION, CN_TARGET, '后续生产情况另行披露。'])
    declaration, target, future = parsed.units
    carrier_id = declaration.unit_id[:-8] + "123abc35"
    carrier = replace(declaration, unit_id=carrier_id, metadata={
        "native_range": {
            "schema_version": "native-pdf-range/1",
            "members": [{"unit_id": uid} for uid in ((ids[0], ids[2]) if overlaps_target else (ids[0],))],
        },
    })
    session = SourceOperatingSession(
        {unit.unit_id: unit for unit in (carrier, target, future)}, work_budget=WorkBudget(100_000),
        originals={unit.unit_id: unit for unit in parsed.units},
    )
    observed = session.reference(target.unit_id, window=((carrier_id,), True))
    if overlaps_target:
        assert observed["status"] == "partial" and not observed["declaration_refs"]
    else:
        assert observed["status"] == "collective"
        assert observed["required_original_unit_ids"] == (carrier_id,)


def test_citation_does_not_choose_between_competing_meaning_contexts():
    parsed, _, ids = text_case(["Earlier condition A.", "Earlier condition B.", "Company ships control systems."])
    session = SourceOperatingSession(
        {unit.unit_id: unit for unit in parsed.units}, work_budget=WorkBudget(100_000),
        groups={"scope-a": (ids[2],), "scope-b": (ids[2],)},
        contexts={"scope-a": (ids[0],), "scope-b": (ids[1],)},
    )
    session.prepare_citations()
    implicit = session.citation_owner((ids[2],))
    assert session.context_for(implicit) == ()
    for owner, prerequisite in zip(("scope-a", "scope-b"), ids):
        assert session.citation_owner((ids[2],), prepared_owner=owner) == owner
        assert session.context_for(owner) == (prerequisite,)
    reference = session.reference(ids[0])
    used = session.work_budget.used
    reference["required_original_unit_ids"] = ("foreign",)
    assert "foreign" not in session.reference(ids[0])["required_original_unit_ids"]
    assert session.work_budget.used == used
