"""Actual cache decisions follow the scoped algorithm dependency recipe."""
from hashlib import sha256
import importlib
from pathlib import Path

import pytest

from unit.document_understanding_selection.test_reading_decision_inventory import (
    _real_interim_pipeline,
)


@pytest.mark.parametrize("name", [
    "company_wiki.source_catalog.narrative_antecedent",
    "company_wiki.source_catalog.narrative_parent_composition",
    "company_wiki.document_understanding.profiles.signals",
    "company_wiki.document_understanding.strategy_binding",
    "company_wiki.document_understanding.source_discourse",
    "company_wiki.source_catalog.narrative_decision_inventory",
])
def test_algorithm_change_invalidates_actual_generation_cache(monkeypatch, name):
    from company_wiki.automation.narrative_generation import current_reading_decision_matches
    from company_wiki.document_understanding.decision_dependencies import freeze_decision_dependencies
    from company_wiki.source_catalog import narrative_decision_inventory as decision_inventory

    observed = _real_interim_pipeline()
    observed["observation"]["metadata"]["mime_type"] = "text/plain"
    frozen = freeze_decision_dependencies(decision_inventory.build_decision_trace(observed))
    assert frozen["status"] == "complete"
    manifest = {"reading_dependencies": frozen,
                "selection_generation": {"decision_digest": frozen["decision_digest"]}}
    assert current_reading_decision_matches(manifest)
    target = Path(importlib.import_module(name).__file__).resolve()
    read_bytes = Path.read_bytes

    def changed(path):
        data = read_bytes(path)
        return data + b"\n# changed algorithm\n" if path.resolve() == target else data

    monkeypatch.setattr(Path, "read_bytes", changed)
    assert not current_reading_decision_matches(manifest)


def test_decision_identity_accepts_only_replay_implementations_used_by_source_reading():
    from company_wiki.source_catalog.narrative_decision_inventory import decision_versions

    with pytest.raises(ValueError, match="unknown material matcher"):
        decision_versions(material_matcher="company_wiki.document_understanding.source_discourse")


def test_new_imported_algorithm_is_discovered_without_editing_recipe(tmp_path):
    from company_wiki.implementation_identity import algorithm_hashes

    package = tmp_path / "algorithms"
    package.mkdir()
    entry = package / "reading.py"
    helper = package / "helper.py"
    unrelated = package / "unused.py"
    entry.write_text("from . import helper\n", encoding="utf-8")
    helper.write_bytes(b"RULE = 1\n")
    unrelated.write_text("UNUSED = 1\n", encoding="utf-8")
    def locate(name):
        return package / (name.rsplit(".", 1)[-1] + ".py")
    before = algorithm_hashes(("algorithms.reading",), locate=locate,
                              includes=lambda name: name.startswith("algorithms."))
    assert set(before) == {"algorithms.reading", "algorithms.helper"}
    unrelated.write_text("UNUSED = 2\n", encoding="utf-8")
    assert algorithm_hashes(("algorithms.reading",), locate=locate,
                            includes=lambda name: name.startswith("algorithms.")) == before
    helper.write_bytes(b"RULE = 2\n")
    after = algorithm_hashes(("algorithms.reading",), locate=locate,
                             includes=lambda name: name.startswith("algorithms."))
    assert after["algorithms.helper"] == sha256(helper.read_bytes()).hexdigest()
    assert after != before


def test_owner_recipe_tracks_new_public_reexports_inside_its_layer(tmp_path, monkeypatch):
    import sys
    from types import ModuleType

    from company_wiki import document_understanding
    from company_wiki.document_understanding.reading_identity import reading_algorithm_hashes

    init = tmp_path / "__init__.py"
    init.write_bytes(Path(document_understanding.__file__).read_bytes() +
                     b"\nfrom .reading_probe import observe\nimport company_wiki.source_catalog.narrative_reading\n")
    owner_rule = tmp_path / "reading_probe.py"
    owner_rule.write_bytes(b"def observe():\n    return 1\n")
    name = "company_wiki.document_understanding.reading_probe"
    deployed = ModuleType(name)
    deployed.__file__ = str(owner_rule)
    monkeypatch.setattr(document_understanding, "__file__", str(init))
    monkeypatch.setitem(sys.modules, name, deployed)

    before = reading_algorithm_hashes(pdf_frontend=False)
    assert before[name] == sha256(owner_rule.read_bytes()).hexdigest()
    assert "company_wiki.source_catalog.narrative_reading" not in before
    owner_rule.write_bytes(b"def observe():\n    return 2\n")
    assert reading_algorithm_hashes(pdf_frontend=False)[name] != before[name]


def test_unused_pdf_frontend_does_not_invalidate_text_decision(monkeypatch):
    from company_wiki.source_catalog import narrative_decision_inventory as decision_inventory
    from company_wiki.source_catalog import narrative_pdf_intent

    target = Path(narrative_pdf_intent.__file__).resolve()
    read_bytes = Path.read_bytes
    before = decision_inventory.decision_versions(mime_type="text/plain")

    def changed(path):
        data = read_bytes(path)
        return data + b"\n# changed PDF-only algorithm\n" if path.resolve() == target else data

    monkeypatch.setattr(Path, "read_bytes", changed)
    assert decision_inventory.decision_versions(mime_type="text/plain") == before


def test_pdf_projection_helper_follows_actual_carrier(monkeypatch):
    from company_wiki.source_catalog import narrative_decision_inventory as decision_inventory
    from company_wiki.document_normalization.layout_snapshots import identity

    target = Path(identity.__file__).resolve()
    read_bytes = Path.read_bytes
    before_pdf = decision_inventory.decision_versions(pdf_frontend=True, mime_type="application/pdf")
    before_text = decision_inventory.decision_versions(mime_type="text/plain")

    def changed(path):
        data = read_bytes(path)
        return data + b"\n# changed projection helper\n" if path.resolve() == target else data

    monkeypatch.setattr(Path, "read_bytes", changed)
    assert decision_inventory.decision_versions(pdf_frontend=True, mime_type="application/pdf") != before_pdf
    assert decision_inventory.decision_versions(mime_type="text/plain") == before_text


def test_pdf_table_observation_change_invalidates_real_pdf_cache_only(monkeypatch):
    from company_wiki.source_catalog import narrative_decision_inventory as inventory
    from company_wiki.automation.narrative_generation import current_reading_decision_matches
    from company_wiki.document_understanding.decision_dependencies import freeze_decision_dependencies
    from company_wiki.document_understanding import pdf_table_observations
    from company_wiki.source_catalog.narrative_pdf_layout import PDF_READING_LAYOUT_FEATURE_VERSION

    pipeline = _real_interim_pipeline()
    pipeline['observation']['metadata'].update(
        mime_type='application/pdf', native_layout_frontend_version=PDF_READING_LAYOUT_FEATURE_VERSION)
    frozen = freeze_decision_dependencies(inventory.build_decision_trace(pipeline))
    manifest = {'reading_dependencies': frozen,
                'selection_generation': {'decision_digest': frozen['decision_digest']}}
    assert frozen['status'] == 'complete'
    assert current_reading_decision_matches(manifest)
    before_text = inventory.decision_versions(mime_type='text/plain')
    target = Path(pdf_table_observations.__file__).resolve()
    original = Path.read_bytes
    monkeypatch.setattr(Path, 'read_bytes', lambda path: original(path) + b'\n# next table algorithm\n'
                        if path.resolve() == target else original(path))
    assert not current_reading_decision_matches(manifest)
    assert inventory.decision_versions(mime_type='text/plain') == before_text


@pytest.mark.parametrize('changed_component', ('resource', 'package'))
def test_linguistic_data_and_runtime_version_invalidate_actual_cache(monkeypatch, changed_component):
    from company_wiki.document_understanding import statement_grammar as grammar
    from company_wiki.source_catalog import narrative_decision_inventory as inventory
    from company_wiki.document_understanding.decision_dependencies import freeze_decision_dependencies
    from company_wiki.automation.narrative_generation import current_reading_decision_matches
    pipeline = _real_interim_pipeline()
    pipeline['observation']['metadata']['mime_type'] = 'text/plain'
    frozen = freeze_decision_dependencies(inventory.build_decision_trace(pipeline))
    manifest = {'reading_dependencies': frozen,
                'selection_generation': {'decision_digest': frozen['decision_digest']}}
    assert frozen['status'] == 'complete' and current_reading_decision_matches(manifest)
    if changed_component == 'resource':
        target = grammar._RESOURCES / 'jieba.dict.txt'
        original = Path.read_bytes
        monkeypatch.setattr(Path, 'read_bytes', lambda path: original(path) + b'\n'
                            if path == target else original(path))
    else:
        original_version = grammar.metadata.version
        monkeypatch.setattr(grammar.metadata, 'version', lambda name: 'next-grammar-runtime'
                            if name == 'nltk' else original_version(name))
    assert not current_reading_decision_matches(manifest)
