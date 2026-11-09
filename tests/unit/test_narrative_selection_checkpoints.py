"""An orchestration cancellation keeps its identity across the PDF read port."""

import pytest

from company_wiki.automation.heartbeat import HeartbeatFailure
from company_wiki.automation.narrative_contracts import SourceRevisionEventPayload
from company_wiki.automation.narrative_select import NarrativeSelectHandler
from unit import test_narrative_select_handler as fixture


def test_pdf_read_preserves_the_lease_exception_from_its_checkpoint():
    data = b"%PDF-"
    payload = fixture._payload(data, title="Quarterly filing", document_kind="quarterly_report",
                               language="en", mime_type="application/pdf")
    lost = HeartbeatFailure("synthetic lease loss")
    calls = 0

    def checkpoint():
        nonlocal calls
        calls += 1
        if calls == 3:  # Source identity checked, PDF parser about to start.
            raise lost

    handler = NarrativeSelectHandler(reader=fixture.FakeReader(payload, data))
    with pytest.raises(HeartbeatFailure) as error:
        handler.select_source(SourceRevisionEventPayload.from_dict(payload), checkpoint=checkpoint)
    assert error.value is lost
