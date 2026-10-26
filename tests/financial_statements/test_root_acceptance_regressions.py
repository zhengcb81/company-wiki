"""ROOT acceptance: use public references/queries, not a reconstructed ref."""
from decimal import Decimal
import json

import pytest

from company_wiki.source_catalog.financial_statements.contracts import StatementsRequest
from company_wiki.source_catalog.financial_statements.service import handle_reuse_only_request
from company_wiki.source_catalog.source_reader import SourceRef, SourceVersionReader
from .test_service_contracts import _request_payload, _recorder, _zhongwei_lrb, _service

from . import test_service_contracts as service_fixtures

catalog = service_fixtures.catalog


def request(**changes):
    return StatementsRequest.from_payload(_request_payload(**changes))


def report(response, period="2026-06-30"):
    return next(r for r in response["statements"][0]["reports"] if r["period_end"] == period)


def value(r):
    return next(row["value_decimal"] for row in r["rows"] if row["provider_field"] == "BIZTOTINCO")


def pages_changed(*, content=False):
    pages = _zhongwei_lrb()
    body = json.loads(pages[1])
    entry = body["result"]["data"]["report_list"]["20260630"]
    entry["update_time"] = "2026-10-20 12:00:00"
    if content:
        row = next(r for r in entry["data"] if r["item_field"] == "BIZTOTINCO")
        row["item_value"] = str(Decimal(row["item_value"]) + 1)
    pages[1] = json.dumps(body, ensure_ascii=False).encode()
    return pages


def test_returned_source_ref_can_be_opened_directly(catalog):
    response = _service(catalog, _recorder(_zhongwei_lrb())).handle_request(request())
    ref = SourceRef(**report(response)["source_ref"])
    opened = SourceVersionReader(catalog).open_version(ref, purpose="preview")
    assert ref.byte_size == len(opened.data) > 0


@pytest.mark.parametrize("public_readonly", [False, True])
def test_narrow_capture_does_not_make_wide_reuse_complete(catalog, public_readonly):
    handler = _recorder(_zhongwei_lrb())
    service = _service(catalog, handler)
    service.handle_request(request(period_end_from="2024-01-01"))
    before = len(handler.requests)
    wanted = request(intent="reuse_only", acquisition_limits=None)
    response = handle_reuse_only_request(wanted, catalog.config) if public_readonly else service.handle_request(wanted)
    assert response["status"] == "partial"
    assert response["statements"][0]["reports"]
    assert len(handler.requests) == before
    assert response["usage"]["http_requests"] == 0


def test_partial_acquisition_is_still_partial_on_readonly_reuse(catalog):
    service = _service(catalog, _recorder(_zhongwei_lrb()))
    service.max_pages = 1
    assert service.handle_request(request())["status"] == "partial"
    response = handle_reuse_only_request(request(intent="reuse_only", acquisition_limits=None), catalog.config)
    assert response["status"] == "partial"


def test_timestamp_only_refresh_does_not_grow_raw_or_rebind_old_version(catalog, monkeypatch):
    from company_wiki.source_catalog.financial_statements import service as module
    monkeypatch.setattr(module, "_utc_now", lambda: "2026-10-01T00:00:00Z")
    first = _service(catalog, _recorder(_zhongwei_lrb())).handle_request(request())
    original = report(first)
    roots = catalog.config.roots[0].path
    files_before = {p.relative_to(roots): p.read_bytes() for p in roots.rglob("*.json")}
    observations_before = catalog.store.fetchone("SELECT COUNT(*) AS n FROM financial_statement_observations")["n"]
    monkeypatch.setattr(module, "_utc_now", lambda: "2026-10-20T00:00:00Z")
    refreshed = _service(catalog, _recorder(pages_changed())).handle_request(request(intent="refresh"))
    now = report(refreshed)
    assert now["statement_version_id"] == original["statement_version_id"]
    assert now["source_ref"] == original["source_ref"]
    assert now["retrieved_at"] == original["retrieved_at"]
    assert {p.relative_to(roots): p.read_bytes() for p in roots.rglob("*.json")} == files_before
    assert catalog.store.fetchone("SELECT COUNT(*) AS n FROM financial_statement_observations")["n"] == observations_before


@pytest.mark.parametrize("public_readonly", [False, True])
def test_current_and_historical_revision_are_selected_before_pagination(catalog, monkeypatch, public_readonly):
    from company_wiki.source_catalog.financial_statements import service as module
    monkeypatch.setattr(module, "_utc_now", lambda: "2026-10-01T00:00:00Z")
    first = _service(catalog, _recorder(_zhongwei_lrb())).handle_request(request())
    old = report(first)
    monkeypatch.setattr(module, "_utc_now", lambda: "2026-10-20T00:00:00Z")
    service = _service(catalog, _recorder(pages_changed(content=True)))
    service.handle_request(request(intent="refresh"))
    def read(**kw):
        wanted = request(intent="reuse_only", acquisition_limits=None, **kw)
        return handle_reuse_only_request(wanted, catalog.config) if public_readonly else service.handle_request(wanted)
    current = read()
    selected = [r for r in current["statements"][0]["reports"] if r["period_end"] == "2026-06-30"]
    assert len(selected) == 1
    assert Decimal(value(selected[0])) == Decimal(value(old)) + 1
    past = read(knowledge_mode="point_in_time", as_of_date="2026-10-10")
    historic = report(past)
    assert historic["source_ref"] == old["source_ref"]
    assert value(historic) == value(old) and historic["pit_verified"] is True
    unavailable = read(knowledge_mode="point_in_time", as_of_date="2026-09-01")
    assert unavailable["statements"][0]["reports"] == []
    assert unavailable["statements"][0]["point_in_time_quality"] == "historical_asof_unverifiable"
    assert unavailable["status"] != "complete"


def test_same_lower_bound_unbounded_upper_request_reuses_without_http(catalog):
    payload = _request_payload(period_end_from="2024-01-01")
    payload.pop("period_end_to")
    wanted = StatementsRequest.from_payload(payload)
    handler = _recorder(_zhongwei_lrb())
    service = _service(catalog, handler)
    assert service.handle_request(wanted)["status"] == "complete"
    before = len(handler.requests)
    second = service.handle_request(wanted)
    assert second["status"] == "complete"
    assert len(handler.requests) == before and second["usage"]["http_requests"] == 0


@pytest.mark.parametrize("same_timestamp", [False, True])
def test_content_transitions_follow_observation_order_even_when_old_content_returns(catalog, monkeypatch, same_timestamp):
    from company_wiki.source_catalog.financial_statements import service as module
    def capture(day, pages):
        stamp = "2026-10-01T00:00:00Z" if same_timestamp else f"2026-10-{day:02d}T00:00:00Z"
        monkeypatch.setattr(module, "_utc_now", lambda: stamp)
        return _service(catalog, _recorder(pages)).handle_request(request(intent="refresh"))
    original = report(capture(1, _zhongwei_lrb()))
    revised = report(capture(10, pages_changed(content=True)))
    assert Decimal(value(revised)) == Decimal(value(original)) + 1
    returned = report(capture(20, _zhongwei_lrb()))
    assert value(returned) == value(original)
    assert returned["source_ref"] == original["source_ref"]
    past = handle_reuse_only_request(request(intent="reuse_only", acquisition_limits=None,
        knowledge_mode="point_in_time", as_of_date="2026-10-21"), catalog.config)
    assert value(report(past)) == value(original)
    if not same_timestamp:
        middle = handle_reuse_only_request(request(intent="reuse_only", acquisition_limits=None,
            knowledge_mode="point_in_time", as_of_date="2026-10-15"), catalog.config)
        assert value(report(middle)) == value(revised)


def test_pit_coverage_does_not_borrow_future_periods_or_fetch_envelope(catalog, monkeypatch):
    from company_wiki.source_catalog.financial_statements import service as module
    monkeypatch.setattr(module, "_utc_now", lambda: "2026-10-01T00:00:00Z")
    limited = _service(catalog, _recorder(_zhongwei_lrb()))
    limited.max_pages = 1
    first = limited.handle_request(request())
    old_periods = {r["period_end"] for r in first["statements"][0]["reports"]}
    monkeypatch.setattr(module, "_utc_now", lambda: "2026-10-20T00:00:00Z")
    _service(catalog, _recorder(_zhongwei_lrb())).handle_request(request(intent="refresh"))
    past = handle_reuse_only_request(request(intent="reuse_only", acquisition_limits=None,
        knowledge_mode="point_in_time", as_of_date="2026-10-10"), catalog.config)
    statement = past["statements"][0]
    assert {r["period_end"] for r in statement["reports"]} == old_periods
    assert statement["coverage"]["observed_periods"] == len(old_periods)
    assert statement["status"] == "partial"
    assert statement["coverage"]["quality"] == "historical_coverage_unverifiable"


def test_offline_replay_does_not_claim_a_new_provider_observation(catalog, monkeypatch):
    from company_wiki.source_catalog.financial_statements import service as module
    monkeypatch.setattr(module, "_utc_now", lambda: "2026-10-01T00:00:00Z")
    original = report(_service(catalog, _recorder(_zhongwei_lrb())).handle_request(request()))
    monkeypatch.setattr(module, "_utc_now", lambda: "2026-10-10T00:00:00Z")
    service = _service(catalog, _recorder(pages_changed(content=True)))
    revised = report(service.handle_request(request(intent="refresh")))
    before = [dict(row) for row in catalog.store.fetchall("SELECT * FROM financial_statement_observations")]
    monkeypatch.setattr(module, "_utc_now", lambda: "2026-10-20T00:00:00Z")
    service.replay_source(request=request(intent="reuse_only", acquisition_limits=None),
        source_id=original["source_ref"]["source_id"])
    current = report(service.handle_request(request(intent="reuse_only", acquisition_limits=None)))
    assert value(current) == value(revised)
    assert [dict(row) for row in catalog.store.fetchall("SELECT * FROM financial_statement_observations")] == before
