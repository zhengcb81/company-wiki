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
    assert session.reference(ids[1]) is result
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
