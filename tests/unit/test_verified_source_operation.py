"""The source port owns actual bytes; consumers bind the returned identity."""
from dataclasses import replace
import hashlib

import pytest

from company_wiki.automation import narrative_source_guard as owner
from company_wiki.automation.narrative_contracts import SourceRevisionEventPayload
from company_wiki.automation.models import HandlerOutcome
from unit.test_narrative_select_handler import FakeReader, _pdf_bytes, _payload, _run


def fixture():
    data = _pdf_bytes('Company launched a new product.')
    payload = _payload(data, title='Annual report', document_kind='annual_report',
                       language='en', mime_type='application/pdf')
    return data, payload, FakeReader(payload, data)


def test_actual_handler_prefers_the_single_combined_source_observation():
    data, payload, base = fixture()
    calls = []

    class CombinedReader:
        def open_described_version(self, ref, **kwargs):
            calls.append((ref, kwargs))
            return base.opened, base.metadata

        def open_version(self, *args, **kwargs):
            pytest.fail('do not reopen a combined source observation')

        def describe_version(self, *args, **kwargs):
            pytest.fail('do not independently re-query metadata')

    result, _ = _run(payload, data, reader=CombinedReader())
    assert result.outcome is HandlerOutcome.SUCCEEDED and len(calls) == 1


def test_verified_buffer_is_not_hashed_again_by_the_upper_identity_guard(monkeypatch):
    _, payload, reader = fixture()
    event = SourceRevisionEventPayload.from_dict(payload)
    actual = hashlib.sha256
    calls = []

    def counted(value):
        calls.append(len(value))
        return actual(value)

    monkeypatch.setattr(hashlib, 'sha256', counted)
    owner.validate_opened_identity(event, reader.opened)
    assert calls == []


@pytest.mark.parametrize('field,value', [('source_id', 'different'), ('content_sha256', '0' * 64),
                                        ('document_id', 'wrong-document'), ('byte_size', 999)])
def test_returned_wrong_identity_is_still_rejected(field, value):
    _, payload, reader = fixture()
    opened = replace(reader.opened, **{field: value})
    with pytest.raises(owner.NarrativeSourceGuardError):
        owner.validate_opened_identity(SourceRevisionEventPayload.from_dict(payload), opened)
