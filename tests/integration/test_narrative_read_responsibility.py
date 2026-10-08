"""An immutable read uses one source observation and one actual byte open."""

import json

import pytest

from company_wiki.automation.narrative_transport import NarrativeTransportReader
from company_wiki.automation.narrative_transport_contracts import NarrativeReadRequest, NarrativeTransportError
from support.narrative_transport_fixture import published_fixture
from contract.test_source_metadata_responsibility import dispute


def test_narrative_read_does_not_self_check_policy_or_repeat_metadata(tmp_path, monkeypatch):
    with published_fixture(tmp_path) as fixture:
        transport = NarrativeTransportReader(fixture.artifacts, fixture.reader)
        reference = transport.reference(fixture.source_ref)
        counters = {'open': 0, 'describe': 0, 'policy': 0}
        for method, name in [('open_version', 'open'), ('describe_version', 'describe'),
                             ('read_policy_sha256', 'policy')]:
            original = getattr(fixture.reader, method)
            def counted(*args, _original=original, _name=name, **kwargs):
                counters[_name] += 1
                return _original(*args, **kwargs)
            monkeypatch.setattr(fixture.reader, method, counted)
        result = transport.read(NarrativeReadRequest.from_dict(fixture.read_request(reference)))
        assert result.data == fixture.payload
        assert counters == {'open': 0, 'describe': 0, 'policy': 0}  # one combined read API owns all three
        assert result.receipt['replay_status'] == 'verified'


def test_current_narrative_survives_auxiliary_conflict_but_historical_unknown_is_not_claimed(tmp_path):
    with published_fixture(tmp_path) as fixture:
        ref = fixture.reader.query_ref(fixture.source_ref.document_id, fixture.source_ref.source_id,
                                      fixture.source_ref.content_sha256)
        dispute(fixture.catalog, ref, 'acquisition.source_url', 'published_date')
        transport = NarrativeTransportReader(fixture.artifacts, fixture.reader)
        reference = transport.reference(fixture.source_ref)
        wire = fixture.read_request(reference)
        wire['as_of_date'] = None
        result = transport.read(NarrativeReadRequest.from_dict(wire))
        assert result.data == fixture.payload
        assert result.receipt['manifest']['published_date'] is None
        assert 'path' not in json.dumps(result.receipt)
        wire['as_of_date'] = '2026-09-01'
        with pytest.raises(NarrativeTransportError, match='source_publication_unknown'):
            transport.read(NarrativeReadRequest.from_dict(wire))
