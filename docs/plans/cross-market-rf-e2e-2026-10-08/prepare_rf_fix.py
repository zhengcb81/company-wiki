"""Stage narrow source-boundary repairs after recorded RED regressions."""
from pathlib import Path
import os

root = Path(os.environ['USERPROFILE']) / 'Projects/revenue-forecast/scripts'
stage = Path(__file__).parent / 'rf_fix_stage'


def replace(name, old, new):
    source = (root / name).read_text(encoding='utf-8')
    if source.count(old) != 1:
        raise RuntimeError(f'{name}: expected one source anchor')
    (stage / name).write_text(source.replace(old, new), encoding='utf-8')


replace('filing_fetch_client.py', '''    status = response.get("status")
    if status != "capture_ready":''', '''    status = response.get("status")
    if response.get("schema_version") == "2.0":
        filing = response.get("filing")
        if (status == "source_candidate" and isinstance(filing, dict)
                and filing.get("status") == "source_candidate"
                and isinstance(filing.get("source_ref"), dict)):
            return filing
        reason = filing.get("reason") if isinstance(filing, dict) else None
        raise _ClientError(
            f"filing-fetch returned status={status}: {reason or 'invalid v2 filing result'}",
            status=status, error_code=status,
            retryable=filing.get("retryable", False) if isinstance(filing, dict) else False,
        )
    if status != "capture_ready":''')

replace('source_preparation.py', '''    if handle.get("fiscal_period") != request.get("fiscal_period"):
        raise RuntimeError("filing-fetch SourceRef fiscal_period mismatch")''', '''    requested_period = request.get("fiscal_period")
    if requested_period is None and request.get("document_kind") == "annual_report":
        # FY is the only annual period; do not infer a quarterly/half-year period.
        requested_period = handle.get("fiscal_period") if handle.get("fiscal_period") in (None, "FY") else "FY"
    if handle.get("fiscal_period") != requested_period:
        raise RuntimeError("filing-fetch SourceRef fiscal_period mismatch")''')

replace('company_wiki_source_reader_v2.py', '''    retrieved = _datetime(manifest["retrieved_at"], "source manifest retrieved_at")
    period_end = manifest["period_end"]
    if period_end is not None and _date(period_end, "source manifest period_end") > published:
        raise SourceVersionTransportError("source manifest period ends after publication")
    if not (published <= retrieved.date() <= as_of):
        raise SourceVersionTransportError("source manifest is outside as_of_date")''', '''    retrieved_value = manifest["retrieved_at"]
    period_end = manifest["period_end"]
    if period_end is not None and _date(period_end, "source manifest period_end") > published:
        raise SourceVersionTransportError("source manifest period ends after publication")
    if published > as_of:
        raise SourceVersionTransportError("source manifest is outside as_of_date")
    if retrieved_value is not None:
        retrieved = _datetime(retrieved_value, "source manifest retrieved_at")
        if not (published <= retrieved.date() <= as_of):
            raise SourceVersionTransportError("source manifest is outside as_of_date")''')

source = (root / 'company_wiki_source_v2.py').read_text(encoding='utf-8')
old = '''    retrieved = _aware_datetime(manifest.get("retrieved_at"), "source manifest retrieved_at")
    if not published <= retrieved.date() <= as_of:
        raise CompanyWikiSourceError("source manifest is outside as_of_date")'''
new = '''    if published > as_of:
        raise CompanyWikiSourceError("source manifest is outside as_of_date")
    if manifest.get("retrieved_at") is not None:
        retrieved = _aware_datetime(manifest["retrieved_at"], "source manifest retrieved_at")
        if not published <= retrieved.date() <= as_of:
            raise CompanyWikiSourceError("source manifest is outside as_of_date")'''
assert source.count(old) == 1
source = source.replace(old, new)
old = '''    pairs = {
        "document_id": "document_id", "source_id": "source_id",'''
new = '''    if candidate.get("status") == "source_candidate":
        expected_fields = {"status", "source_ref", "byte_verification", "document_kind",
                           "fiscal_year", "fiscal_period", "resolution_outcome", "download_events"}
        if set(candidate) != expected_fields:
            raise CompanyWikiSourceError("v2 source candidate fields are invalid")
        _same(candidate["byte_verification"], "pending_verified_open", "byte verification")
        for field in ("document_kind", "fiscal_year", "fiscal_period"):
            _same(candidate[field], manifest[field], f"source candidate {field}")
        outcome = candidate["resolution_outcome"]
        if not isinstance(outcome, str) or outcome not in _OUTCOMES:
            raise CompanyWikiSourceError("source candidate outcome invalid")
        _same(candidate["download_events"], int(outcome == "downloaded_new"), "download events")
        return candidate
    pairs = {
        "document_id": "document_id", "source_id": "source_id",'''
assert source.count(old) == 1
source = source.replace(old, new)
old = '''    retrieved = _aware_datetime(manifest["retrieved_at"], "source manifest retrieved_at")
    captured_date = retrieved.date().isoformat()
    read_at = receipt["read_at"]'''
new = '''    read_at = receipt["read_at"]
    # Unknown historical collection time stays unknown. The new local capture
    # uses the actual verified-read event, never an invented collection time.
    captured_at = manifest["retrieved_at"] if manifest["retrieved_at"] is not None else read_at
    retrieved = _aware_datetime(captured_at, "source capture timestamp")
    if not published <= retrieved.date() <= as_of:
        raise CompanyWikiSourceError("source capture is outside as_of_date")
    captured_date = retrieved.date().isoformat()'''
assert source.count(old) == 1
(stage / 'company_wiki_source_v2.py').write_text(source.replace(old, new), encoding='utf-8')
print('four runtime files staged')
