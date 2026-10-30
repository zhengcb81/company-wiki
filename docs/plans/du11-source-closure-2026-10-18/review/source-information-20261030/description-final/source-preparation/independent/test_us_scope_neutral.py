"""Independent local synthetic SEC checks. All writable state stays in basetemp."""
from hashlib import sha256
from pathlib import Path
import sys
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'tests'))

from integration.test_legacy_local_reconcile import lake, DATA
from company_wiki.source_catalog.local_reconcile import prepare_local_source
from company_wiki.source_catalog.local_inventory import LocalPrepareLimits
from company_wiki.source_catalog.resolver import SourceRequest
from company_wiki.source_catalog.source_reader import SourceVersionReader


def request(kind='regulatory_filing', year=2026, period='Q2'):
    return SourceRequest(entity='Acme', market='US', security_id='ACME',
                         document_kind=kind, fiscal_year=year, fiscal_period=period,
                         as_of_date='2026-10-30')


def test_old_annual_scope_does_not_become_request_specific_kind(lake):
    _ = lake.store
    raw = lake.config.roots[0].path / 'Acme' / 'old.htm'
    raw.parent.mkdir()
    data = DATA.replace(b'>2026</', b'>2001</').replace(b'>Q2</', b'>FY</').replace(b'>10-Q</', b'>10-K</')
    raw.write_bytes(data)
    result = prepare_local_source(lake, request(), limits=LocalPrepareLimits(max_candidates=4))
    assert result['status'] == 'not_found', result
    rows = lake.query(text=sha256(data).hexdigest(), limit=2)
    assert len(rows) == 1
    row = rows[0]
    reader = SourceVersionReader(lake)
    ref = reader.query_ref(row['document_id'], row['source_id'], sha256(data).hexdigest())
    facts = reader.describe_version(ref)
    assert (facts['fiscal_year'], facts['fiscal_period'], facts['form_type']) == (2001, 'FY', '10-K')
    again = prepare_local_source(lake, request('annual_report', 2001, 'FY'))
    # Unknown publication can block historical reuse; actual kind cannot become not_found.
    assert again['status'] != 'not_found', (facts, again)


@pytest.mark.parametrize(('data', 'expected'), [
    (DATA.replace(b'>2026</', b'>2001</').replace(b'>12345</', b'>98765</'), 'blocked'),
    (DATA.replace(b'>2026</', b'>2001</').replace(b'<ix:nonNumeric name="dei:DocumentPeriodEndDate">2025-12-31</ix:nonNumeric>', b''), 'not_found'),
    (DATA.replace(b'<ix:nonNumeric name="dei:DocumentPeriodEndDate">2025-12-31</ix:nonNumeric>', b''), 'blocked'),
])
def test_identity_and_target_dates_remain_required_but_known_old_year_can_exclude(lake, data, expected):
    _ = lake.store
    raw = lake.config.roots[0].path / 'Acme' / 'old.htm'
    raw.parent.mkdir()
    raw.write_bytes(data)
    result = prepare_local_source(lake, request())
    assert result['status'] == expected, result
    assert result['download_events'] == 0
    if expected == 'blocked':
        assert result['blocks_download']
    assert raw.read_bytes() == data


def test_retry_reuses_persisted_scope_without_reextracting(lake, monkeypatch):
    import company_wiki.source_catalog.local_reconcile as module
    _ = lake.store
    raw = lake.config.roots[0].path / 'Acme' / 'old.htm'
    raw.parent.mkdir()
    raw.write_bytes(DATA.replace(b'>2026</', b'>2001</'))
    original = module.extract_sec_scope
    calls = []
    def observed(*args, **kwargs):
        calls.append(True)
        return original(*args, **kwargs)
    monkeypatch.setattr(module, 'extract_sec_scope', observed)
    first = prepare_local_source(lake, request())
    first_count = len(calls)
    assert first['status'] == 'not_found' and first_count > 0, first
    second = prepare_local_source(lake, request())
    assert second['status'] == 'not_found' and len(calls) == first_count, second


def test_partial_old_scope_never_becomes_positive_after_request_switch(lake):
    _ = lake.store
    raw = lake.config.roots[0].path / 'Acme' / 'old.htm'
    raw.parent.mkdir()
    raw.write_bytes(DATA.replace(b'>2026</', b'>2001</').replace(
        b'<ix:nonNumeric name="dei:DocumentPeriodEndDate">2025-12-31</ix:nonNumeric>', b''))
    first = prepare_local_source(lake, request())
    assert first['status'] == 'not_found', first
    second = prepare_local_source(lake, request(year=2001))
    assert second['status'] == 'blocked' and second['blocks_download'], second
