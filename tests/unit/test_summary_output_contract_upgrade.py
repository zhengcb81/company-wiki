"""A retired compression schema cannot waive current request identity."""
from dataclasses import asdict, replace

import pytest

from company_wiki.automation.narrative_model_runtime import build_model_request
from support.narrative_model_request_fixture import selection
from support.summary_output_contract_upgrade import (
    archived_compression_projection, assert_archived_request_upgrade,
)


def test_archived_compatibility_rejects_forged_current_input_hash():
    source = selection()
    actual = build_model_request(source)
    with archived_compression_projection():
        archived = build_model_request(source)
    with pytest.raises(AssertionError):
        assert_archived_request_upgrade(replace(actual, input_sha256='f' * 64), asdict(archived), selected=source)


def test_request_binding_checks_selection_context_absent_from_displayed_wire():
    source = selection()
    actual = build_model_request(source)
    with archived_compression_projection():
        archived = build_model_request(source)
    changed = replace(source, selection=replace(source.selection, source_units=source.selection.source_units + 1))
    rebuilt = build_model_request(changed)
    assert rebuilt.data_json == actual.data_json
    assert rebuilt.input_sha256 != actual.input_sha256
    with pytest.raises(AssertionError):
        assert_archived_request_upgrade(actual, asdict(archived), selected=changed)


@pytest.mark.parametrize('version', [None, 'reading-model-input/1', 'reading-model-input/2', 'reading-model-input/3'])
@pytest.mark.parametrize('output_budget', [None, 8192])
def test_real_bound_request_passes_and_bad_hash_fails_in_each_legacy_capture(version, output_budget):
    from unit.test_narrative_reading_transport import with_reading
    source = with_reading()
    actual = build_model_request(source, reading_projection_version=version)
    if output_budget is not None:
        actual = actual.with_output_budget(output_budget)
    with archived_compression_projection():
        archived = build_model_request(source, reading_projection_version=version)
        if output_budget is not None:
            archived = archived.with_output_budget(output_budget)
    assert_archived_request_upgrade(actual, asdict(archived), selected=source, reading_projection_version=version)
    with pytest.raises(AssertionError):
        assert_archived_request_upgrade(replace(actual, input_sha256='f' * 64), asdict(archived),
                                        selected=source, reading_projection_version=version)


@pytest.mark.parametrize('version', ['reading-model-input/4', 'reading-model-input/6'])
def test_current_scoped_input_identity_is_not_waived_by_archived_presentation(version):
    import json
    from pathlib import Path
    from company_wiki.automation.narrative_contracts import NarrativeSelectResult
    value = json.loads((Path(__file__).parents[1] / 'fixtures/atomic_recipe_legacy_requests.json').read_text(encoding='utf-8'))
    source = NarrativeSelectResult.from_dict(value['selection'])
    actual = build_model_request(source, reading_projection_version=version)
    archived = value['requests'][version]
    assert_archived_request_upgrade(actual, archived, selected=source, reading_projection_version=version)
    with pytest.raises(AssertionError):
        assert_archived_request_upgrade(replace(actual, input_sha256='f' * 64), archived,
                                        selected=source, reading_projection_version=version)
