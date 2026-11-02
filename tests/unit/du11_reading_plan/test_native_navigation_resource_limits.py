"""Navigation uses the existing work account and explicit request limits."""
import pytest

from company_wiki.document_understanding.geometry_intent import reading
from company_wiki.document_understanding.geometry_intent.contracts import DiagnosticSink
from company_wiki.resource_budget import WorkBudget
from unit.du11_reading_plan.test_reading import prepare, routed as routed


def test_public_explicit_request_limits_are_not_silently_clamped(routed):
    result = prepare([[1, 'Business', 1]], limits={'max_pages': 1000, 'max_requests': 900})
    assert result['plan']['limits'] == {'max_pages': 1000, 'max_requests': 900}


@pytest.mark.parametrize('variant', ['large', 'deep', 'long-title'])
def test_valid_native_outline_has_no_additional_size_or_depth_permission(variant):
    if variant == 'large':
        outline = [[1, f'Heading {index}', index + 1] for index in range(4100)]
    elif variant == 'deep':
        outline = [[index + 1, f'Heading {index}', index + 1] for index in range(40)]
    else:
        outline = [[1, 'Heading' * 1000, 1]]
    budget = WorkBudget(100_000)
    rows, complete = reading._native_rows(outline, 5000, budget, DiagnosticSink())
    assert complete and len(rows) == len(outline)
    assert budget.used >= len(rows) and not budget.exhausted


def test_work_exhaustion_keeps_completed_window_prefix_without_renewing_budget(routed, monkeypatch):
    budget = WorkBudget(100_000)
    actual = reading.canonical_digest
    completed = []

    def observe(value):
        digest = actual(value)
        if isinstance(value, dict) and {'navigation_status', 'heading_path', 'basis'} <= value.keys():
            completed.append(dict(value))
            if len(completed) == 1:
                # Tighten this same real account at an actual completed window,
                # not a fixed guessed operation count or a second budget.
                budget.max_work_units = budget.used
        return digest

    monkeypatch.setattr(reading, 'canonical_digest', observe)
    result = prepare([[1, 'Business', 1], [1, 'Projects', 10]], budget=budget)
    assert completed and budget.exhausted and result['partial']
    assert len(result['windows']) == 1
    assert result['windows'][0]['physical_start'] == 1
    assert result['windows'][0]['physical_end'] == 9
    assert result['plan']['summary']['partial']
    assert budget.used <= budget.max_work_units


def test_page_admission_uses_actual_plan_keys_not_a_second_64_key_permission():
    from company_wiki.document_understanding.geometry_intent import (
        admit_geometry_request, new_admission_state, plan_geometry_requests,
    )
    from unit.du9_geometry_planner.test_root_policy_interop import compiled_offering, rule, window

    policy = compiled_offering()
    windows = [window(f'w{index}', rule(policy, 'business'), index + 1, index + 1) for index in range(65)]
    budget = WorkBudget(500_000)
    plan = plan_geometry_requests(policy, windows, page_count=100,
        limits={'max_pages': 100, 'max_requests': 100}, work_budget=budget)
    keys = [row['window_key'] for row in plan['allocations']]
    assert len(keys) == 65
    decision, state = admit_geometry_request(plan, new_admission_state(plan), page=1,
        window_keys=keys, tabular_evidence='observed_candidate', remaining=100)
    assert decision['decision'] == 'admitted'
    assert len(decision['window_keys']) == len(keys)
    assert state['spent'] == {'pages': 1, 'requests': 1}


def test_budget_stop_during_merge_preserves_completed_canonical_windows(routed, monkeypatch):
    budget = WorkBudget(100_000)
    actual = reading.canonical_digest
    stopped = []

    def observe(value):
        digest = actual(value)
        if (isinstance(value, dict) and {'window_key', 'navigation_status', 'heading_path'} <= value.keys()
                and not stopped):
            stopped.append(True)
            budget.max_work_units = budget.used
        return digest

    monkeypatch.setattr(reading, 'canonical_digest', observe)
    result = prepare([[1, 'Business', 1], [1, 'Projects', 10]], budget=budget)
    assert stopped and budget.exhausted and result['partial']
    assert len(result['windows']) == 2
    for row in result['windows']:
        assert row['window_key'] == actual({key: value for key, value in row.items() if key != 'window_key'})


def test_actual_geometry_session_passes_the_same_work_account_to_admission(monkeypatch):
    from types import SimpleNamespace
    from company_wiki.source_catalog import narrative_pdf_intent as runtime
    from company_wiki.document_understanding.geometry_intent import plan_geometry_requests
    from unit.du9_geometry_planner.test_root_policy_interop import compiled_offering, rule, window

    policy = compiled_offering()
    budget = WorkBudget(200_000, used=41)
    plan = plan_geometry_requests(policy, [window('one', rule(policy, 'business'), 1, 10)],
        page_count=100, limits={'max_pages': 10, 'max_requests': 10}, work_budget=budget)
    monkeypatch.setattr(runtime, 'prepare_geometry_reading', lambda *args, **kwargs:
        {'plan': plan, 'partial': False, 'route': {'family': 'annual'}})
    monkeypatch.setattr(runtime, 'observe_pdf_candidate', lambda *args, **kwargs:
        {'continuation': None, 'candidate': True, 'partial': False})
    real = runtime.admit_geometry_request
    calls = []

    def admit(*args, **kwargs):
        calls.append(kwargs['work_budget'])
        return real(*args, **kwargs)

    monkeypatch.setattr(runtime, 'admit_geometry_request', admit)
    session = runtime.SourceGeometrySession([], context=None,
        state=SimpleNamespace(source_id='source', source_sha256='a' * 64, page_count=100, parser_version='2.0.0'),
        outline=[[1, 'Business', 1]], budget=budget,
        collector=SimpleNamespace(limits={'max_pages': 10}, exhausted=False))
    used = budget.used
    assert session.request(1, object()) == (True, True)
    assert calls == [budget] and budget.used > used
    assert session.state['spent'] == {'pages': 1, 'requests': 1}


def test_admission_cannot_validate_or_copy_plan_after_work_is_exhausted(monkeypatch):
    from company_wiki.document_understanding.geometry_intent import planner
    from company_wiki.resource_budget import WorkBudgetExceeded

    calls = []
    monkeypatch.setattr(planner, '_require_plan', lambda value: calls.append(value))
    with pytest.raises(WorkBudgetExceeded):
        planner.admit_geometry_request({}, {}, page=1, window_keys=['one'],
            tabular_evidence='observed_candidate', remaining=1, work_budget=WorkBudget(0))
    assert calls == []
