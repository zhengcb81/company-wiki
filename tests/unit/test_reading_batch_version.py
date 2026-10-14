"""The public finite request selects an engine version without mutating globals."""

import pytest

from company_wiki.automation.narrative_batch_request import NarrativeBatchRequest
from unit.test_narrative_batch_request import _request


def test_explicit_supported_reading_version_is_frozen_and_roundtrips():
    old = NarrativeBatchRequest.from_dict(_request())
    upgraded = NarrativeBatchRequest.from_dict({**_request(), "selector_version": "0.9.0"})
    assert upgraded.execution_versions["selector"] == "0.9.0"
    assert old.execution_versions["selector"] == "0.8.0"
    assert upgraded.input_hash != old.input_hash
    assert upgraded.request_sha256 != old.request_sha256
    assert upgraded.to_dict()["selector_version"] == "0.9.0"
    assert NarrativeBatchRequest.from_dict(upgraded.to_dict()) == upgraded
    assert "selector_version" not in old.to_dict()


@pytest.mark.parametrize("version", [None, "unknown", " 0.9.0", 9, True])
def test_invalid_explicit_version_is_rejected_before_execution(version):
    with pytest.raises(ValueError):
        NarrativeBatchRequest.from_dict({**_request(), "selector_version": version})
