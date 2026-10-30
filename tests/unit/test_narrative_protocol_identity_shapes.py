"""JSON protocol identifiers must reject shape errors through named boundaries."""
import pytest

from company_wiki.automation import narrative_summary_protocols as protocols
from company_wiki.automation import narrative_model_runtime as runtime
from company_wiki.automation.narrative_model import ModelResponseError


@pytest.mark.parametrize('value', [[], {}, ['reading-model-input/7'], False, 7, 1.5])
def test_protocol_lookup_does_not_hash_non_string_json(value):
    assert protocols.scoped_protocol_for_projection(value) is None
    assert protocols.scoped_protocol_for_request(value) is None
    with pytest.raises(ValueError, match='unknown scoped summary prompt'):
        protocols.scoped_protocol_for_prompt(value)
    with pytest.raises(ValueError, match='unknown scoped summary prompt'):
        protocols.summary_bundle_format(value)
    with pytest.raises(ModelResponseError, match='PROJECTION'):
        runtime.resolve_model_boundary(value)


def test_absent_and_known_protocol_identities_retain_existing_semantics():
    assert protocols.scoped_protocol_for_projection(None) is None
    assert protocols.summary_bundle_format(None) == protocols.LEGACY_BUNDLE
    for item in protocols.SCOPED_PROTOCOLS:
        assert protocols.scoped_protocol_for_projection(item.projection) is item
        assert protocols.scoped_protocol_for_request(item.request_schema) is item
        assert protocols.scoped_protocol_for_prompt(item.prompt) is item
