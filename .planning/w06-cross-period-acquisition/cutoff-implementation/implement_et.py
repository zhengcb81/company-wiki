"""Implement the reviewed ET cutoff cause at the existing source responsibility layer."""
import hashlib
import json
from pathlib import Path

TREE = Path('C:/Users/郑曾波/Projects/_harness_worktrees/w06/et-cutoff-root')
EVIDENCE = Path(__file__).resolve().parent / 'et'
before = json.loads((EVIDENCE / 'before.json').read_text(encoding='utf-8'))
expected = next(item['sha256'] for item in before['files'] if item['path'] == 'transcript_api.py')
path = TREE / 'transcript_api.py'
if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
    raise RuntimeError('Product changed before RED implementation')
text = path.read_text(encoding='utf-8')

def replace_once(old, new):
    global text
    if text.count(old) != 1:
        raise RuntimeError(f'Expected exactly one implementation anchor: {old[:80]}')
    text = text.replace(old, new, 1)

replace_once(
    '''    if match["call_date"] > normalized["as_of"]:
        return _base_result(
            request_id,
            "not_found",
            provider="fmp",
            result_schema=result_schema,
            fiscal_period=f"{normalized['fiscal_year']}-Q{normalized['fiscal_quarter']}",
            candidate_count=0,
        )''',
    '''    if match["call_date"] > normalized["as_of"]:
        return _base_result(
            request_id,
            "not_found",
            provider="fmp",
            result_schema=result_schema,
            fiscal_period=f"{normalized['fiscal_year']}-Q{normalized['fiscal_quarter']}",
            candidate_count=0,
            error_code="call_after_as_of",
        )''',
)
replace_once(
    '''    ticker = normalized["ticker"]
    exchanges = (
        EXCHANGES if normalized["exchange"] == "auto" else (normalized["exchange"],)
    )
    session = None''',
    '''    ticker = normalized["ticker"]
    session = None''',
)
replace_once(
    '''        eligible: dict[str, dict[str, Any]] = {}
        for exchange in exchanges:
            quote_url = f"https://{ALLOWED_HOST}/quote/{exchange}/{ticker.lower()}/"
            listing, _, _ = _read_bounded(
                session, quote_url, deadline, MAX_LISTING_BYTES
            )
            for candidate in _candidate_urls(listing, ticker, quote_url):
                candidate_period = candidate["period"]
                if (
                    candidate_period
                    == (normalized["fiscal_year"], normalized["fiscal_quarter"])
                    and candidate["published_date"] <= normalized["as_of"]
                ):
                    eligible[candidate["source_url"]] = candidate''',
    '''        eligible, excluded_after_as_of = _listing_candidate_selection(
            session, ticker, normalized["exchange"], normalized["as_of"], deadline,
            fiscal_period=(normalized["fiscal_year"], normalized["fiscal_quarter"]),
        )''',
)
replace_once(
    '''        if not eligible:
            return _base_result(
                request_id,
                "not_found",
                result_schema=result_schema,
                fiscal_period=f"{normalized['fiscal_year']}-Q{normalized['fiscal_quarter']}",
                candidate_count=0,
            )''',
    '''        if not eligible:
            return _base_result(
                request_id,
                "not_found",
                result_schema=result_schema,
                fiscal_period=f"{normalized['fiscal_year']}-Q{normalized['fiscal_quarter']}",
                candidate_count=0,
                **({"error_code": "publication_after_as_of"}
                   if excluded_after_as_of else {}),
            )''',
)
replace_once(
    '''def _listing_candidates(
    session: requests.Session,
    ticker: str,
    exchange: str,
    as_of: date,
    deadline: float,
) -> dict[str, dict[str, Any]]:
    """All candidate transcript metadata visible on the quote listings.

    Shared by exact-period discovery and the in-process batch listing helper;
    never fetches a transcript body.
    """
    exchanges = EXCHANGES if exchange == "auto" else (exchange,)
    eligible: dict[str, dict[str, Any]] = {}
    for ex in exchanges:
        quote_url = f"https://{ALLOWED_HOST}/quote/{ex}/{ticker.lower()}/"
        listing, _, _ = _read_bounded(session, quote_url, deadline, MAX_LISTING_BYTES)
        for candidate in _candidate_urls(listing, ticker, quote_url):
            if candidate["published_date"] <= as_of:
                eligible[candidate["source_url"]] = candidate
    return eligible''',
    '''def _listing_candidate_selection(
    session: requests.Session,
    ticker: str,
    exchange: str,
    as_of: date,
    deadline: float,
    *,
    fiscal_period: tuple[int, int] | None = None,
) -> tuple[dict[str, dict[str, Any]], bool]:
    """Select validated metadata and retain why a target scope was excluded.

    Identity is owned by _candidate_urls. Filter the requested period before
    recording cutoff exclusion, so another quarter cannot explain this gap.
    All configured exchanges are observed before uniqueness is decided.
    """
    exchanges = EXCHANGES if exchange == "auto" else (exchange,)
    eligible: dict[str, dict[str, Any]] = {}
    excluded_after_as_of = False
    for ex in exchanges:
        quote_url = f"https://{ALLOWED_HOST}/quote/{ex}/{ticker.lower()}/"
        listing, _, _ = _read_bounded(session, quote_url, deadline, MAX_LISTING_BYTES)
        for candidate in _candidate_urls(listing, ticker, quote_url):
            if fiscal_period is not None and candidate["period"] != fiscal_period:
                continue
            if candidate["published_date"] <= as_of:
                eligible[candidate["source_url"]] = candidate
            else:
                excluded_after_as_of = True
    return eligible, excluded_after_as_of


def _listing_candidates(
    session: requests.Session,
    ticker: str,
    exchange: str,
    as_of: date,
    deadline: float,
) -> dict[str, dict[str, Any]]:
    """Preserve the in-process batch listing interface; no body fetch."""
    eligible, _ = _listing_candidate_selection(
        session, ticker, exchange, as_of, deadline,
    )
    return eligible''',
)
replace_once(
    '''        eligible = {
            url: candidate
            for url, candidate in _listing_candidates(
                session,
                normalized["ticker"],
                normalized["exchange"],
                normalized["as_of"],
                deadline,
            ).items()
            if candidate["period"]
            == (normalized["fiscal_year"], normalized["fiscal_quarter"])
        }''',
    '''        eligible, excluded_after_as_of = _listing_candidate_selection(
            session,
            normalized["ticker"],
            normalized["exchange"],
            normalized["as_of"],
            deadline,
            fiscal_period=(normalized["fiscal_year"], normalized["fiscal_quarter"]),
        )''',
)
replace_once(
    '''            candidate_count=len(candidates),
            candidates=candidates,
        )''',
    '''            candidate_count=len(candidates),
            candidates=candidates,
            **({"error_code": "publication_after_as_of"}
               if not candidates and excluded_after_as_of else {}),
        )''',
)
path.write_text(text, encoding='utf-8', newline='\n')
with (TREE / '.planning/w06-cutoff-result/progress.md').open('a', encoding='utf-8') as stream:
    stream.write('\nA正规RED：5FAIL/6PASS/42deselected，1.58s；5失败均API/CLI实际not_found缺error_code，没有缺文件/import错误。对照原空列表、边界日、错误期间/身份、多候选控制已PASS。旧RED保存在central et/red.*。\nB实现：唯一合法FMP晚call加闭合诊断；Motley exact fetch/discover共享同一次listing、身份和目标期间先筛后日期，batch dict界面保留；待集中责任节点。\n')
print(json.dumps({'product_files_written': 1, 'cutoff_wire_diagnostics': ['call_after_as_of', 'publication_after_as_of'], 'extra_requests': 0}))
