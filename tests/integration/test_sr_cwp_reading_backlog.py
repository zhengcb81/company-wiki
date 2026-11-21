"""SR-CWP: the paged reading-backlog derivation over registered originals."""

from __future__ import annotations

import json

from company_wiki.source_catalog.incremental_read import (
    READING_BACKLOG_REQUEST_SCHEMA,
    READING_LEVEL_LOCAL,
    ReadingBacklogRequest,
)

from support.sr_cwp_fixtures import sr_cwp_readable_catalog


def _service(state):
    from company_wiki.source_catalog.incremental_read import IncrementalReadService

    return IncrementalReadService(catalog=state.catalog)


def _request(**overrides):
    payload = {
        "schema_version": READING_BACKLOG_REQUEST_SCHEMA,
        "document_kinds": ["investor_call_transcript"],
        "reading_level": READING_LEVEL_LOCAL,
        "entity": None, "since_date": None, "as_of_date": None,
        "cursor": None, "limits": None,
    }
    payload.update(overrides)
    return ReadingBacklogRequest.from_dict(payload)


def test_backlog_lists_unregistered_reading_as_unread(sr_cwp_readable_catalog):
    """A registered but unprocessed source is an exact unread ref."""
    state = sr_cwp_readable_catalog
    response = _service(state).backlog(_request())
    assert response.to_dict()["schema_version"] == "cwp-reading-backlog/1"
    assert response.next_cursor is None
    item, = response.items
    assert item.state == "unread"
    assert item.result_ref is None
    assert item.source_ref.content_sha256 == (
        state.refs["call-transcript.txt"].content_sha256
    )
    assert item.document_kind == "investor_call_transcript"
    assert response.usage["model_requests"] == 0


def test_backlog_state_tracks_the_persisted_product(sr_cwp_readable_catalog):
    """After a local read the same listing reports read with its ref."""
    state = sr_cwp_readable_catalog
    service = _service(state)
    before, = service.backlog(_request()).items
    assert before.state == "unread"

    from company_wiki.source_catalog.incremental_read import (
        INCREMENTAL_READ_REQUEST_SCHEMA, IncrementalReadRequest,
    )

    read_request = IncrementalReadRequest.from_dict({
        "schema_version": INCREMENTAL_READ_REQUEST_SCHEMA,
        "run_id": "backlog-read-1", "reading_level": READING_LEVEL_LOCAL,
        "sources": [before.source_ref.to_dict()], "limits": None,
    })
    service.read(read_request)

    after, = service.backlog(_request()).items
    assert after.state == "read"
    assert after.result_ref is not None
    assert after.result_ref.source_ref.content_sha256 == (
        before.source_ref.content_sha256
    )


def test_backlog_kind_filter_excludes_other_documents(sr_cwp_readable_catalog):
    """Only the requested kinds are listed."""
    state = sr_cwp_readable_catalog
    response = _service(state).backlog(_request(document_kinds=["annual_report"]))
    kinds = {item.document_kind for item in response.items}
    assert kinds == {"annual_report"}


def test_backlog_entity_filter_uses_the_registered_entity(sr_cwp_readable_catalog):
    """An unknown roster name lists nothing; the registered name lists its docs."""
    state = sr_cwp_readable_catalog
    assert _service(state).backlog(_request(entity="NotRegistered")).items == ()
    response = _service(state).backlog(_request(entity="Acme"))
    assert len(response.items) == 1


def test_backlog_date_window_bounds_published_dates(sr_cwp_readable_catalog):
    """The window filters on the registered published dates, both ends."""
    state = sr_cwp_readable_catalog
    inside = _service(state).backlog(_request(
        document_kinds=["annual_report", "investor_call_transcript"],
        since_date="2026-05-01", as_of_date="2026-05-01",
    ))
    assert len(inside.items) == 2
    outside = _service(state).backlog(_request(
        document_kinds=["annual_report", "investor_call_transcript"],
        since_date="2026-06-01", as_of_date="2026-12-31",
    ))
    assert outside.items == ()


def test_backlog_paging_resumes_without_loss_or_duplicate(sr_cwp_readable_catalog):
    """Keyset paging across max_items=1 sees every item exactly once."""
    state = sr_cwp_readable_catalog
    service = _service(state)
    whole = service.backlog(_request(
        document_kinds=["annual_report", "investor_call_transcript"]))
    seen: list[str] = []
    cursor = None
    for _round in range(8):
        response = service.backlog(_request(
            document_kinds=["annual_report", "investor_call_transcript"],
            limits={"max_items": 1}, cursor=cursor,
        ))
        seen.extend(item.source_ref.document_id for item in response.items)
        if response.next_cursor is None:
            break
        cursor = response.next_cursor
    assert seen == [item.source_ref.document_id for item in whole.items]


def test_backlog_wire_roundtrip(sr_cwp_readable_catalog):
    """The request survives its wire form unchanged."""
    state = sr_cwp_readable_catalog
    payload = _request(entity="Acme").to_dict()
    assert ReadingBacklogRequest.from_dict(payload) == _request(entity="Acme")
    response = _service(state).backlog(_request(entity="Acme"))
    assert json.loads(json.dumps(response.to_dict()))["items"][0]["source_ref"][
        "content_sha256"
    ] == state.refs["call-transcript.txt"].content_sha256
