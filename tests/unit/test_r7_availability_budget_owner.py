"""Availability metadata shares the existing read budget, not size permits."""
from dataclasses import asdict
import hashlib
import json

import pytest

from company_wiki.source_catalog import source_availability as owner
from company_wiki.source_catalog.local_inventory import LocalPrepareLimits, LocalReadBudget
from company_wiki.source_catalog.source_reader import SourceReadError
from contract.test_source_availability import REF, capture_payload, fixture_catalog


def large_capture():
    return {**capture_payload(), 'optional_trace': {'text': '来源🙂' * 20000, 'complete': False}}


@pytest.mark.parametrize('supplied', [True, False])
def test_large_sidecar_availability_uses_same_actual_metadata_read_budget(tmp_path, monkeypatch, supplied):
    catalog = fixture_catalog(tmp_path, large_capture())
    path = catalog.config.roots[0].path / 'original.txt.source.json'
    size = path.stat().st_size
    budget = LocalReadBudget(LocalPrepareLimits(max_bytes=1024**2))
    if supplied:
        proof = owner.verified_availability_evidence(catalog, REF, budget=budget)
    else:
        import company_wiki.source_catalog.local_inventory as inventory
        monkeypatch.setattr(inventory, 'LocalReadBudget', lambda _limits: budget)
        proof = owner.verified_availability_evidence(catalog, REF)
    assert size > 128 * 1024
    assert proof['available_by'] == '2026-10-07'
    assert proof['evidence_ref'].endswith(hashlib.sha256(path.read_bytes()).hexdigest())
    assert budget.bytes_read == budget.observed_charge_bytes == size


def test_capture_reconciliation_keeps_full_optional_trace_and_charges_once(tmp_path):
    payload = large_capture()
    catalog = fixture_catalog(tmp_path, payload, cap=65)
    size = (catalog.config.roots[0].path / 'original.txt.source.json').stat().st_size
    budget = LocalReadBudget(LocalPrepareLimits(max_bytes=1024**2))
    assert owner.capture_observation(catalog, REF, budget=budget) == payload
    assert budget.bytes_read == size  # Same path aliases do not reread one sidecar.
    assert budget.discovery_entries == 65


def test_work_limit_keeps_already_verified_capture_without_claiming_all_locations(tmp_path):
    catalog = fixture_catalog(tmp_path, capture_payload(), cap=65)
    budget = LocalReadBudget(LocalPrepareLimits(max_discovery_entries=1))
    proof = owner.verified_availability_evidence(catalog, REF, budget=budget)
    assert proof['available_by'] == '2026-10-07'
    assert budget.triggered_bound == 'max_discovery_entries'
    assert budget.bytes_read > 0


@pytest.mark.parametrize('stop', ['cancelled', 'deadline'])
@pytest.mark.parametrize('cap', [1, 2])
@pytest.mark.parametrize('entry', ['verified_availability_evidence', 'capture_observation'])
def test_capture_does_not_override_explicit_cancellation_or_deadline(tmp_path, monkeypatch, stop, cap, entry):
    catalog = fixture_catalog(tmp_path, capture_payload(), cap=cap)
    budget = LocalReadBudget(LocalPrepareLimits())
    original = budget.read_metadata_observation
    def observe(*args, **kwargs):
        value = original(*args, **kwargs)
        if stop == 'cancelled':
            budget.cancel()
        else:
            budget.deadline = 0
        return value
    monkeypatch.setattr(budget, 'read_metadata_observation', observe)
    with pytest.raises(SourceReadError) as raised:
        getattr(owner, entry)(catalog, REF, budget=budget)
    assert raised.value.reason == ('cancelled' if stop == 'cancelled' else 'local_prepare_deadline')


@pytest.mark.parametrize('condition', ['bytes', 'deadline'])
def test_true_metadata_resource_limit_stops_before_reading(tmp_path, condition):
    catalog = fixture_catalog(tmp_path, large_capture())
    budget = LocalReadBudget(LocalPrepareLimits(max_bytes=128 if condition == 'bytes' else 1024**2))
    if condition == 'deadline':
        budget.deadline = 0
    with pytest.raises(SourceReadError) as raised:
        owner.verified_availability_evidence(catalog, REF, budget=budget)
    assert raised.value.reason == ('budget_exceeded' if condition == 'bytes' else 'local_prepare_deadline')
    assert budget.bytes_read == 0


def test_large_stored_availability_is_not_lost_to_inline_representation_size(monkeypatch):
    import company_wiki.source_catalog.assertion_service as assertions
    from types import SimpleNamespace
    observed = {'schema_version': 'source-verified-open/1', 'source_ref': asdict(REF),
                'verified_at': '2026-10-07T00:00:00Z'}
    raw = json.dumps({'source_fact_evidence': {'published_date': {'verified_open': observed}},
                      'optional_trace': 'x' * 170000})
    row = {'document_id': REF.document_id, 'evidence_basis': 'source-facts', 'evidence_json': raw}
    monkeypatch.setattr(assertions, 'get_verified_assertion', lambda *_args, **_kw: row)
    budget = LocalReadBudget(LocalPrepareLimits(max_bytes=1024**2))
    proof = owner.stored_availability_evidence(SimpleNamespace(reader=object()), REF, budget=budget)
    assert proof['available_by'] == '2026-10-07'
    assert proof['source_sha256'] == REF.content_sha256
    assert budget.bytes_read == len(raw.encode('utf-8'))


def test_large_source_fact_evidence_validates_json_and_retains_same_scope():
    from company_wiki.source_catalog.assertion_service import validate_source_facts
    facts = {'published_date': None}
    evidence = {'published_date': {'value': None, 'locator': '/source-availability',
                                  'availability_capture': large_capture()}}
    validate_source_facts(facts, evidence)
    with pytest.raises(ValueError):
        validate_source_facts(facts, {'published_date': {**evidence['published_date'], 'value': 'wrong'}})
    with pytest.raises(ValueError):
        validate_source_facts(facts, {'published_date': {**evidence['published_date'], 'nonfinite': float('nan')}})


@pytest.mark.parametrize('stop', ['cancelled', 'deadline'])
def test_stored_proof_obeys_stop_after_metadata_validation(monkeypatch, stop):
    import company_wiki.source_catalog.assertion_service as assertions
    from types import SimpleNamespace
    observation = {'schema_version': 'source-verified-open/1', 'source_ref': asdict(REF),
                   'verified_at': '2026-10-07T00:00:00Z'}
    row = {'document_id': REF.document_id, 'evidence_basis': 'source-facts',
           'evidence_json': json.dumps({'source_fact_evidence': {
               'published_date': {'verified_open': observation}}})}
    monkeypatch.setattr(assertions, 'get_verified_assertion', lambda *_args, **_kw: row)
    budget = LocalReadBudget(LocalPrepareLimits())
    original = owner.open_source_evidence
    def checked(*args):
        result = original(*args)
        if stop == 'cancelled':
            budget.cancel()
        else:
            budget.deadline = 0
        return result
    monkeypatch.setattr(owner, 'open_source_evidence', checked)
    with pytest.raises(SourceReadError) as raised:
        owner.stored_availability_evidence(SimpleNamespace(reader=object()), REF, budget=budget)
    assert raised.value.reason == ('cancelled' if stop == 'cancelled' else 'local_prepare_deadline')


@pytest.mark.parametrize('scenario', ['no_proof', 'stored', 'cancelled'])
def test_stored_proof_uses_default_resolver_parent_account(monkeypatch, scenario):
    import company_wiki.source_catalog.assertion_service as assertions
    from company_wiki.source_catalog.read_budget import ReadBudget
    from types import SimpleNamespace
    observation = {'schema_version': 'source-verified-open/1', 'source_ref': asdict(REF),
                   'verified_at': '2026-10-07T00:00:00Z'}
    raw = json.dumps({'source_fact_evidence': {'published_date': {'verified_open': observation}}})
    row = {'document_id': REF.document_id, 'evidence_basis': 'source-facts', 'evidence_json': raw}
    monkeypatch.setattr(assertions, 'get_verified_assertion',
                        lambda *_args, **_kw: None if scenario == 'no_proof' else row)
    budget = ReadBudget(max_bytes=1024**2)
    assert budget.charge(30) == ''
    if scenario == 'cancelled':
        budget.cancel()
        with pytest.raises(SourceReadError) as raised:
            owner.stored_availability_evidence(SimpleNamespace(reader=object()), REF, budget=budget)
        assert raised.value.reason == 'cancelled'
        assert budget.bytes_read == 30
    else:
        proof = owner.stored_availability_evidence(SimpleNamespace(reader=object()), REF, budget=budget)
        assert (proof is None) == (scenario == 'no_proof')
        assert budget.bytes_read == 30 + (len(raw.encode()) if scenario == 'stored' else 0)
