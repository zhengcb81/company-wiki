"""Recognize background-only clauses for the automatic business quote view."""

import re

from company_wiki.document_model.text_matching import matching_reading_text


_BOUNDARY = re.compile(r"(?<!\d)[,.，]|[,.，](?!\d)|[。；;！？!?]")
_OUTLINE = re.compile(r"^\s*(?:\d+[、)]\s*|(?:答[:：]\s*)?(?:您?好|各位好)[，,:：\s]*)")
_AMOUNT = r"\d+(?:,\d{3})*(?:\.\d+)?"
_CURRENCY = rf"(?:人民币|港币|港元|美元|\$)?\s*{_AMOUNT}\s*(?:百万元|亿元|万元|元|百?万港元|百?万美元)?"
_ISSUER = r"(?:本公司|公司|本企业|本集团|董事会)"
_EN_DIVIDEND = r"(?:(?:interim|annual|quarterly|final|special) )?(?:cash )?dividends?"
_PER_SHARE = rf"(?:(?:HK|US|A|C|S)?\$|£|€)?{_AMOUNT} per (?:common |ordinary )?share"
_DIVIDEND_EVENT = r"(?:declared|paid|distributed)"
_PAY = re.compile(
    rf"(?:(?:{_ISSUER})?(?:拟|决定|计划|将)?(?:向(?:全体)?股东)?(?:每\s*\d+\s*股)\s*"
    rf"(?:派发|分派|分配|发放)(?:现金)?(?:红利|股息|股利)\s*{_CURRENCY}(?:\s*[（(]含税[）)])?|"
    rf"{_EN_DIVIDEND} of {_PER_SHARE} (?:was|were|will be) {_DIVIDEND_EVENT}|"
    r"(?:we|the (?:company|board|group)) (?:has |have )?"
    rf"(?:{_DIVIDEND_EVENT}|(?:has )?resolved to declare|will (?:declare|pay)) (?:an? )?"
    rf"{_EN_DIVIDEND} of {_PER_SHARE})", re.I,
)
_DIVIDEND_BASIS = re.compile(
    rf"(?:(?:目前)?(?:{_ISSUER})?(?:[A-Z]股)?回购专用证券\s*账户上(?:已)?回购股份为\s*{_AMOUNT}\s*股|"
    rf"(?:[A-Z]股)?库存股为\s*{_AMOUNT}\s*股|"
    rf"(?:前述合计\s*{_AMOUNT}\s*股|(?:已回购股份和)?库存股)不参与分红|"
    rf"(?:{_ISSUER})?以(?:目前)?(?:公司总股本\s*{_AMOUNT}\s*股)?扣除"
    rf"(?:公司[A-Z]股回购专用证券账户上已回购股份和)?(?:[A-Z]股)?(?:库存股|回购股份)后的"
    rf"(?:总)?股本(?:\s*{_AMOUNT}\s*股)?为基数(?:测算|计算)?|"
    rf"(?:共计|合计)(?:派发|分派|发放)(?:现金)?(?:红利|股利|股息)\s*{_CURRENCY}(?:\s*[（(]含税[）)])?|"
    r"(?:repurchased|treasury) shares? (?:(?:is|are) excluded from the (?:dividend )?calculation|"
    r"(?:do|does) not participate in (?:the|any) (?:dividend )?distribution)|"
    r"payable(?: to (?:shareholders|stockholders))? on (?:\d{1,2} [a-z]+|[a-z]+ \d{1,2})(?: \d{4})?)", re.I,
)
_REFERENCE = r"(?:本报告)?第[一二三四五六七八九十\d]+节(?:、[一二三四五六七八九十、（()）]+)?(?:[“\"]可能面对的风险[”\"](?:部分的相关内容)?)?"
_RATIO_VALUE = re.compile(
    rf"(?:{_ISSUER})?\s*(?:去?年|本年|本期|报告期|\d{{4}}\s*年(?:度)?)?"
    rf"(?:加权平均)?净资产收益率(?:为|是|达到)\s*{_AMOUNT}%"
)
_METRIC_AMOUNT = rf"{_CURRENCY}(?:[（(]{_CURRENCY}[）)])?"
_CONTEXT = re.compile(
    rf"(?:(?:{_ISSUER})?(?:将)?(?:严格按照相关规定|依法)?履行(?:必要的)?关联(?:方|股东|董事)回避表决(?:等)?义务|"
    r"履行(?:批准)?关联交易的法定程序(?:和信息披露义务)?|"
    rf"(?:本?报告期(?:内)?\s*)?(?:不存在|没有)(?:对{_ISSUER}生产经营产生(?:实质性|重大)影响的)?"
    r"(?:特别)?重大风险|"
    rf"(?:{_ISSUER})?已在(?:本|该)报告中(?:详细)?(?:阐述|说明|列示)(?:在生产经营过程中)?"
    r"(?:可能)?(?:面临的)?相关风险|"
    rf"(?:具体)?(?:内容|情况|详情)?(?:详见|请参阅|参见){_REFERENCE}|"
    rf"(?:{_ISSUER})?(?:始终|一贯)恪守(?:最高)?(?:国际)?(?:质量)?监管标准|"
    r"自成立以来|(?:凭借|依托)(?:优异|优良|优秀|良好|卓越)的(?:服务(?:记录|纪录|质量)|质量管理)"
    r"(?:以及|及|和)(?:完善|健全|严密)的(?:知识产权保护|合规管理|质量管理)体系|"
    r"在(?:[\u3400-\u9fff]+行业(?:中|内)?|行业内|业内|业界)赢得了?(?:公认的)?(?:优秀|良好)声誉|"
    rf"(?:{_ISSUER})?(?:所形成的)?服务品质在(?:业内|业界)具备(?:极高|很高|良好)认可度和公信力|"
    rf"(?:{_ISSUER})?经营层(?:一贯)?尽职尽责(?:保障{_ISSUER}持续稳定发展)?(?:并对(?:{_ISSUER})?持续发展充满信心)?|"
    rf"(?:{_ISSUER})?(?:经营层|管理层)?(?:并)?对(?:{_ISSUER})?(?:可)?持续发展充满信心|报告期内|"
    rf"(?:而)?(?:上年同期|[二零〇一三四五六七八九]{{4}}年同期)的?(?:经营|营业)(?:亏损|利润)(?:则)?为\s*{_METRIC_AMOUNT}|"
    rf"(?:经营|营业)(?:亏损|利润)为\s*{_METRIC_AMOUNT}|"
    r"(?:for (?:more|further) details,? )?(?:see|refer to) (?:item|note|section) \d+[a-z]?|"
    r"(?:our )?(?:management|leadership) (?:is|remains) confident in (?:our|the company's) "
    r"(?:long-term (?:success|growth|prospects)|future growth))", re.I,
)
_PERIOD_CHANGE = re.compile(rf"较(?:上年|上年度|上年同期|去年同期)(?:实现)?(?:增长|上升|下降)(?:\s*{_AMOUNT}%)?")


def business_summary_context_only(source: str) -> bool:
    """Omit a scope only when each clause is recognizable as background.

    Share counts alone do not prove a dividend calculation. An unclassified
    clause keeps the complete source scope, including incidental background.
    This policy is local to the automatic view, outside source admission.
    """
    clauses = tuple(part for raw in _BOUNDARY.split(matching_reading_text(source))
                    if (part := _OUTLINE.sub("", raw).strip()))
    payout = any(_PAY.fullmatch(part) for part in clauses)
    has_ratio = any(_RATIO_VALUE.fullmatch(part) for part in clauses)
    return bool(clauses) and all(
        _CONTEXT.fullmatch(part) or _RATIO_VALUE.fullmatch(part)
        or (has_ratio and _PERIOD_CHANGE.fullmatch(part))
        or (payout and (_PAY.fullmatch(part) or _DIVIDEND_BASIS.fullmatch(part)))
        for part in clauses
    )


__all__ = ["business_summary_context_only"]
