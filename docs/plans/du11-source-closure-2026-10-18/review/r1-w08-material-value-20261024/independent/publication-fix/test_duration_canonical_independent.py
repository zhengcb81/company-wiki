"""Request identity is invariant under valid numeric representation, not intent."""
from dataclasses import replace
import json
import pytest
from unit.test_narrative_batch import _request
from company_wiki.automation.narrative_batch_request import NarrativeBatchRequest

@pytest.mark.parametrize("seconds", (17,17.0,17.125))
def test_finite_duration_json_replay_keeps_request_and_execution_identity(seconds):
    request=replace(_request(),max_seconds=seconds)
    wire=json.loads(json.dumps(request.to_dict()))
    resumed=NarrativeBatchRequest.from_dict(wire)
    assert request.request_sha256==resumed.request_sha256
    assert request.input_hash==resumed.input_hash
    assert resumed.max_seconds==seconds
    assert type(wire["max_seconds"]) is float


def test_distinct_fraction_and_duration_do_not_collapse_into_same_identity():
    first=replace(_request(),max_seconds=17)
    equivalent=replace(first,max_seconds=17.0)
    different=replace(first,max_seconds=18)
    fractional=replace(first,max_seconds=17.125)
    assert first.request_sha256==equivalent.request_sha256
    assert first.input_hash==equivalent.input_hash
    assert len({first.request_sha256,different.request_sha256,fractional.request_sha256})==3
    assert len({first.input_hash,different.input_hash,fractional.input_hash})==3


def test_existing_normalized_float_serialization_is_unchanged():
    from company_wiki.automation.models import canonical_json_hash
    request=_request()
    before=request.to_dict()
    assert type(request.max_seconds) is float
    assert before["max_seconds"]==30.0
    assert request.request_sha256==canonical_json_hash(before)
    assert request.to_dict()==before
