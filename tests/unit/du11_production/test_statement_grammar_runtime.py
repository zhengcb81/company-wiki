"""Packaged grammar is offline, identity-bound, and honest when unavailable."""
import os
from pathlib import Path
import subprocess
import sys

import pytest

from company_wiki.document_understanding import statement_grammar as grammar
from company_wiki.resource_budget import WorkBudget, WorkBudgetExceeded


def test_offline_inference_does_not_write_dictionary_cache(tmp_path, monkeypatch):
    # Hooks/CI can supply TMPDIR independently of Windows TEMP/TMP. A populated
    # ambient root must never be mistaken for this subprocess's owned scratch.
    ambient = tmp_path / 'ambient'
    ambient.mkdir()
    marker = ambient / 'another-test.txt'
    marker.write_text('preserve', encoding='utf-8')
    owned = tmp_path / 'runtime'
    owned.mkdir()
    monkeypatch.setenv('TMPDIR', str(ambient))
    code = '''
import os, pathlib, sys, tempfile, urllib.request
sys.path.insert(0, sys.argv[1])
assert pathlib.Path(tempfile.gettempdir()).resolve() == pathlib.Path(os.environ['NLTK_DATA']).resolve()
import nltk, jieba
from company_wiki.document_understanding.statement_grammar import observe_statement
def forbidden(*args, **kwargs): raise AssertionError('runtime download or dictionary cache')
urllib.request.urlopen = forbidden
nltk.download = forbidden
jieba.Tokenizer.initialize = forbidden
assert observe_statement('Our vessels transport gas between coastal terminals.').independent
assert observe_statement('北岭公司经营铁路运输业务。').independent
assert not list(pathlib.Path(tempfile.gettempdir()).iterdir())
'''
    environment = os.environ.copy()
    environment.update(TEMP=str(owned), TMP=str(owned), TMPDIR=str(owned),
                       NLTK_DATA=str(owned))
    # pytest's sys.path (and a hook's PYTHONPATH) is not inherited reliably by
    # subprocesses. Load this test's actual checkout explicitly, in isolation.
    source_parent = str(Path(grammar.__file__).resolve().parents[3])
    environment['PYTHONPATH'] = str(ambient / 'not-the-package')
    result = subprocess.run([sys.executable, '-I', '-B', '-X', 'utf8', '-c', code,
                             source_parent],
                            env=environment, capture_output=True, text=True,
                            encoding='utf-8', timeout=30)
    assert result.returncode == 0, result.stderr
    assert list(owned.iterdir()) == []
    assert marker.read_text(encoding='utf-8') == 'preserve'


@pytest.mark.parametrize('text', (
    'Our vessels transport liquefied gas.',
    'When order volumes recover, we reopen the coastal terminals.',
))
def test_missing_resource_never_falls_back_to_support(tmp_path, monkeypatch, text):
    grammar._english_tagger.cache_clear()
    monkeypatch.setattr(grammar, '_RESOURCES', tmp_path)
    try:
        observed = grammar.observe_statement(text)
        assert observed.status == 'unknown'
        assert observed.reason == 'statement_grammar_unavailable'
        assert not observed.independent
        from company_wiki.source_catalog.narrative_business_policy import prepare_reading_business_assessment
        passage = prepare_reading_business_assessment(
            text, {'relations': []}).passage
        assert passage.reason == 'source_grammar_unavailable'
        assert not passage.relevant
    finally:
        grammar._english_tagger.cache_clear()


@pytest.mark.parametrize('name', grammar._ASSETS)
def test_resource_identity_observes_actual_asset_bytes(name, monkeypatch):
    baseline = grammar.resource_identity()
    original = Path.read_bytes

    def changed(path):
        raw = original(path)
        return raw + b'\n' if path == grammar._RESOURCES / name else raw

    monkeypatch.setattr(Path, 'read_bytes', changed)
    assert grammar.resource_identity() != baseline


def test_resource_identity_includes_inference_package_version(monkeypatch):
    baseline = grammar.resource_identity()
    original = grammar.metadata.version
    monkeypatch.setattr(grammar.metadata, 'version',
                        lambda name: 'future-version' if name == 'nltk' else original(name))
    assert grammar.resource_identity() != baseline


def test_scope_limit_is_unknown_without_clipping_or_loading_tagger(monkeypatch):
    def unexpected():
        raise AssertionError('oversized source cannot load a tagger')

    monkeypatch.setattr(grammar, '_english_tagger', unexpected)
    text = 'A' * (grammar.MAX_STATEMENT_CHARS + 1)
    observed = grammar.observe_statement(text)
    assert observed.status == 'unknown'
    assert observed.reason == 'statement_grammar_scope_limit'
    assert len(text) == grammar.MAX_STATEMENT_CHARS + 1


def test_fallback_charges_existing_budget_before_model_work(monkeypatch):
    def unexpected(_text):
        raise AssertionError('budget exhausted before model work')

    monkeypatch.setattr(grammar, '_english_statement', unexpected)
    text = 'Our vessels transport gas.'
    budget = WorkBudget(grammar.STATEMENT_GRAMMAR_WORK_PER_CHAR * len(text))
    with pytest.raises(WorkBudgetExceeded):
        grammar.observe_statement(text, work_budget=budget)
    assert budget.exhausted


@pytest.mark.parametrize('text', (
    'Our vessels transport gas between coastal terminals.',
    'When order volumes recover, our software processes customer billing records.',
))
def test_shared_source_session_turns_grammar_budget_stop_into_partial_once(monkeypatch, text):
    from company_wiki.source_catalog.narrative_operating_relations import READING_BUSINESS_SCAN_PASSES
    from unit.du11_production.test_source_information_binding import session_for, unit_id

    def unexpected(_text):
        raise AssertionError('exhausted source must not execute POS')

    monkeypatch.setattr(grammar, '_english_statement', unexpected)
    session, budget = session_for([text])
    uid = unit_id(0)
    session.relations(uid)
    budget.max_work_units = budget.used + READING_BUSINESS_SCAN_PASSES * len(session.source_text(uid))
    session.fact(uid)
    used = budget.used
    assert not session.complete
    assert session.source_passage(uid) is None
    session.fact(uid)
    assert budget.used == used


def test_statement_boundary_result_is_reused_for_the_same_scope_without_a_second_charge(monkeypatch):
    from company_wiki.document_understanding.operating_states.assertion_roles import (
        AssertionRole, SourceAssertionRoles,
    )
    from company_wiki.source_catalog import narrative_source_passage as passage_owner

    text = 'When order volumes recover, we reopen the coastal terminals.'
    roles = SourceAssertionRoles((AssertionRole(text, False),))
    budget = WorkBudget(100_000)
    scope = passage_owner.prepare_source_statement_scope(text, roles, grammar_work_budget=budget)
    used = budget.used
    assert used == grammar.STATEMENT_GRAMMAR_WORK_PER_CHAR * len(text) + 1

    def unexpected(*args, **kwargs):
        raise AssertionError('same scope must reuse the prepared grammar observation')

    monkeypatch.setattr(passage_owner, 'observe_statement', unexpected)
    passage = passage_owner.prepare_source_passage(text, roles, purpose='unknown', financial_only=False,
        accounting_text=lambda _text: False, non_operating_purposes=frozenset(),
        existing_use=('context_only', 'no_independent_business_support'), existing_relevant=False,
        statement_scope=scope, grammar_work_budget=budget)
    assert passage.use == 'support' and passage.relevant
    assert budget.used == used


def test_existing_typed_proof_never_needs_pos_fallback(monkeypatch):
    from unit.du11_production.test_source_information_binding import session_for, unit_id

    def unexpected(_text):
        raise AssertionError('existing source proof must not run POS fallback')

    monkeypatch.setattr(grammar, '_chinese_statement', unexpected)
    session, _ = session_for(['公司已交付设备至客户开展生产验证，尚未完成量产认证。'])
    fact = session.fact(unit_id(0))
    assert fact.eligible
    assert session.source_passage(unit_id(0)).use == 'support'
