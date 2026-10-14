"""One pure semantic qualification for an already scoped, actually read table.

Discovery only suggests where to extract. Layout only establishes table members.
Neither is a business assertion. This service interprets the table's own fields
and data; callers bind their original IDs and keep every required qualifier.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
import re
from typing import Literal

from company_wiki.document_normalization.text_matching import matching_reading_text

from ..profiles.registry import configured_table_signal

FEATURE_VERSION = "operating-table-purpose/3"
MAX_PURPOSE_CHARS = 2_000_000

# These are account identities, not financial-section locations. Operating
# tables within financial notes remain eligible; a bare retention signal does
# not turn retained earnings or OCI into a customer-retention measure.
_ACCOUNT_PURPOSE = re.compile(
    r"cash and cash equivalents|accounts? (?:receivable|payable)|total assets|total liabilities|"
    r"lease liabilities|right[ -]of[ -]use assets|retained earnings|comprehensive income|"
    r"(?:shareholders?|stockholders?|owners?)['’]?\s+equity|capital surplus|paid[- ]in capital|"
    r"stock[- ]based compensation|share[- ]based payments?|fair value|risk[- ]free rate|"
    r"dividend yield|(?:selling|administrative|income tax) expenses?|"
    r"货币资金|貨幣資金|应收[账帳]款|應收[賬帳]款|应付[账帳]款|應付[賬帳]款|"
    r"资产总计|資產總計|负债合计|負債合計|租赁负债|租賃負債|使用权资产|使用權資產|"
    r"留存收益|留存盈利|留存盈餘|综合收益|綜合收益|资本公积|資本公積|盈余公积|盈餘公積|"
    r"所有者权益|所有者權益|股东权益|股東權益|未分配利润|未分配利潤|"
    r"股份支付|股权激励|股權激勵|公允价值|公允價值|期权定价|期權定價|"
    r"无风险利率|無風險利率|预期股息率|預期股息率|销售费用|銷售費用|管理费用|管理費用",
    re.IGNORECASE,
)
_OPERATING_FIELD = re.compile(
    r"产能|產能|产量|產量|销量|銷量|门店|門店|客户|客戶|订单|訂單|交付|用户|用戶|"
    r"留存率|留存比例|每店|利用率|存货周转(?:日数|天数)|"
    r"inventory turnover days|days inventory outstanding|"
    r"capacity|stores|outlets|customers|users|orders|subscribers|retention|utilization|"
    r"average revenue per|remaining (?:performance )?obligations?|contract(?:ed)? backlog|"
    r"order backlog|剩余履约义务|剩餘履約義務|未履行客户合同|未履行客戶合同",
    re.IGNORECASE,
)
_COMMENT = re.compile(r"^\s*(?:注\s*[:：]|Notes?\s*(?:\d+\s*)?[:：])", re.IGNORECASE)
_PROJECT_MONEY_SCOPE = re.compile(
    r"项目名称|項目名稱|项目总投资|項目總投資|募集资金|募集資金|在建工程|"
    r"funds? allocation|capital raised|construction in progress|book values?|carrying (?:amounts?|values?)",
    re.IGNORECASE,
)
_PROJECT_BUSINESS_FIELD = re.compile(
    r"建设周期|建設周期|建設週期|建设地点|建設地點|主要产品|主要產品|预计投产|預計投產|"
    r"建设进度|建設進度|施工进度|施工進度|投产阶段|投產階段|"
    r"construction (?:period|timeline|location|progress)|production stage|expected commissioning",
    re.IGNORECASE,
)
_OPERATING_MEASURE_FIELD = re.compile(
    r"产能|產能|产量|產量|销量|銷量|利用率|门店(?:数量|数目|网络)|門店(?:數量|數目|網絡)|"
    r"用户(?:数量|数目)|用戶(?:數量|數目)|订单(?:数量|数目)|訂單(?:數量|數目)|"
    r"capacity|utilization|shipments|actual output|(?:number|count) of (?:stores|users|orders)|"
    r"(?:store|user|order) counts?|store network|order backlog|在手订单|在手訂單|"
    r"remaining (?:performance )?obligations?|剩余履约义务|剩餘履約義務|"
    r"客户集中度|客戶集中度|customer concentration|average revenue per|留存率|留存比例|"
    r"(?:customer|user|revenue) retention(?: rate)?|"
    r"存货周转(?:日数|天数)|inventory turnover days|days inventory outstanding",
    re.IGNORECASE,
)
_FIELD_DEFINITION = re.compile(r"是指|定义为|\bis defined as\b|\bmeans? the\b", re.IGNORECASE)
_FINANCIAL_TOTAL_ROW = re.compile(
    r"^\s*(?:营业收入|收入|净利润|经营溢利|股东应占溢利|毛利率|毛利|"
    r"(?:total\s+|net\s+)?(?:revenues?|sales|income|profits?)\b|"
    r"gross (?:profit|margin)|operating (?:income|profit))", re.IGNORECASE)


def _text(value: str) -> str:
    # Interpret native wrapping in classification only. Source text and IDs are
    # untouched. This is not a new text parser or a source-range join.
    return " ".join(matching_reading_text(value).split())


def operating_header(text: str) -> bool:
    """Observe operating fields; account labels alone confer no purpose."""
    folded = _text(text)
    return (
        not _COMMENT.search(folded) and not _FIELD_DEFINITION.search(folded)
        and bool(
            _PROJECT_BUSINESS_FIELD.search(folded)
            or _OPERATING_MEASURE_FIELD.search(folded)
            or (not _ACCOUNT_PURPOSE.search(folded)
                and (_OPERATING_FIELD.search(folded) or configured_table_signal(folded)))
        )
    )


@dataclass(frozen=True)
class TablePurpose:
    status: Literal["eligible", "not_business", "incomplete"]
    reason: str
    eligible_row_indices: tuple[int, ...] = ()

    @property
    def eligible(self) -> bool:
        return self.status == "eligible"


def qualify_table(
    header_texts: Sequence[str],
    row_texts: Sequence[str],
    *,
    caption_texts: Sequence[str] = (),
    max_chars: int = MAX_PURPOSE_CHARS,
) -> TablePurpose:
    """Interpret one table's actual fields and rows without IO or model calls.

    Only caller-owned table members belong here. A neighbouring section heading
    and a footnote cannot certify the purpose of otherwise financial rows.
    Missing/empty body or a resource stop is explicit unknown, never no-business.
    """
    if type(max_chars) is not int or max_chars < 0:
        raise ValueError("max_chars must be a nonnegative integer")
    used = 0
    header_operating = False
    header_measure = False
    header_account = False
    header_money = False
    account_seen = False
    money_seen = False
    body_read = False
    eligible: list[int] = []
    for is_body, values in ((False, header_texts), (False, caption_texts), (True, row_texts)):
        if isinstance(values, str):
            raise TypeError("table purpose input must be a sequence of strings")
        for index, value in enumerate(values):
            if not isinstance(value, str):
                raise TypeError("table purpose input must contain strings")
            # The per-entry unit also bounds arbitrarily many empty values.
            used += 1 + len(value)
            if used > max_chars:
                return TablePurpose("incomplete", "TABLE_PURPOSE_RESOURCE_LIMIT")
            actual = _text(value)
            if _COMMENT.search(actual) or _FIELD_DEFINITION.search(actual):
                # A scoped explanatory note remains a required original. Its
                # business words cannot confer purpose, nor can an account
                # reference in that note erase a real operating table.
                continue
            has_account = bool(_ACCOUNT_PURPOSE.search(actual))
            has_money = bool(_PROJECT_MONEY_SCOPE.search(actual))
            measure = bool(
                _PROJECT_BUSINESS_FIELD.search(actual)
                or _OPERATING_MEASURE_FIELD.search(actual)
            )
            operating = operating_header(actual)
            account_seen = account_seen or has_account
            money_seen = money_seen or has_money
            if not is_body:
                header_operating = header_operating or operating
                header_measure = header_measure or measure
                header_account = header_account or has_account
                header_money = header_money or has_money
                continue
            if not any(character.isalnum() for character in actual):
                continue
            body_read = True
            # A real operating field can coexist with an associated balance in
            # the same native row. An independent balance row cannot borrow
            # that field from another row or become free context.
            row_operating = bool(_OPERATING_FIELD.search(actual))
            if _FINANCIAL_TOTAL_ROW.search(actual) and not measure:
                continue
            if has_account and not (measure or header_measure and row_operating):
                continue
            if has_money and not measure:
                continue
            if (header_account or header_money) and not (header_measure or measure):
                continue
            if operating or header_operating:
                eligible.append(index)
    if not body_read:
        return TablePurpose("incomplete", "TABLE_BODY_NOT_READ")
    if eligible:
        return TablePurpose("eligible", "OBSERVED_OPERATING_TABLE_FIELDS_AND_ROWS", tuple(eligible))
    if account_seen:
        return TablePurpose("not_business", "ACCOUNTING_TABLE_PURPOSE")
    if money_seen:
        return TablePurpose(
            "not_business", "PROJECT_AMOUNTS_WITHOUT_OPERATING_RELATION"
        )
    return TablePurpose("not_business", "NO_OPERATING_TABLE_PURPOSE")


__all__ = ["FEATURE_VERSION", "TablePurpose", "operating_header", "qualify_table"]
