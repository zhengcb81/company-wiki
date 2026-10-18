"""Bounded source purpose, distinct from grammatical actor/action relations.

The source session invokes this once over its already bounded native material.
It neither reads documents nor changes quotations, source IDs, actors or units.
Accounting models and treasury products are not operating products merely
because they share a noun with a real customer-facing business.
"""
from __future__ import annotations

import re

from company_wiki.document_normalization.text_matching import matching_reading_text


NON_OPERATING_PURPOSES = frozenset({
    "accounting_policy", "audit_procedure", "treasury_policy", "template_no_event", "navigation",
})

_ACCOUNTING = re.compile(
    r"期权定价|股份支付|股票期权|使用权资产|租赁负债|账面价值|计入损益|"
    r"\b(?:employee share options?|share.based (?:payments?|compensation)|"
    r"option.pricing|right.of.use assets?|lease liabilities|carrying (?:value|amount)|"
    r"accounting estimates?|accounting polic(?:y|ies)|consolidated financial statements|"
    r"accounting and internal control systems)\b|"
    r"\bgoodwill\b.{0,100}\b(?:reporting units?|impairment|fair value|carrying)\b|"
    r"\bfair value\b.{0,100}\b(?:options?|impairment|measurement)\b|"
    r"\bvaluation model\b.{0,100}\b(?:risk.free|fair value|employee shares?)\b", re.I)
_AUDIT = re.compile(
    r"审计程序|审计测试|审计证据|注册会计师|关键审计事项|"
    r"\b(?:audit procedures?|audit evidence|key audit matters?|"
    r"independent auditor|auditors?['’]? (?:report|responsibilities))\b|"
    r"\bwe (?:evaluated|tested|assessed|obtained)\b.{0,180}"
    r"\b(?:internal controls?|impairment|management(?:['’]s)? assumptions|audit)\b", re.I)
_TREASURY = re.compile(
    r"(?:理财产品|现金管理|资金管理).{0,80}(?:审批|批准|授权|闲置资金|投资)|"
    r"(?:审批|批准|授权|闲置资金).{0,80}(?:理财产品|现金管理)|"
    r"\b(?:board|treasury)\b.{0,100}\b(?:approved|authorized|invest)\b"
    r".{0,100}\b(?:wealth management|cash management|financial products)\b", re.I)
_NAVIGATION = re.compile(
    r"^\s*(?:(?:see|refer to)\s+(?:note|item|section)\s*\d+|"
    r"(?:详见|参见|请参阅).{0,30}(?:附注|章节|第.{0,6}节))", re.I)
_TEMPLATE = re.compile(r"^[\s□☑☐√✓✔×✗适用不\.、/():：（）\-]+$")
# This stock is an operating contract measure, not a financial total inferred
# from an arbitrary currency amount. Period/conversion interpretation stays in
# the original source; this classifier never computes a dated metric.
_CONTRACT_STOCK = re.compile(
    r"\b(?:remaining performance obligations?|RPO|order backlog|order book|"
    r"contracted backlog)\b|剩余履约义务|在手订单|未履约订单", re.I)
_STOCK_VALUE = re.compile(
    r"^\s*(?:\([^)]{0,80}\))?\s*(?:were|was|are|is|total(?:ed|s)?|stood at|amounted to|"
    r"[=:：]|为|达到|合计|约为)\s*(?:(?:approximately|about|over|nearly|USD|RMB|HKD|US\$|"
    r"港币|人民币)\s*)?[$¥€]?\s*\d", re.I)
_ALLOCATED_FINANCIAL = re.compile(
    r"\b(?:revenue|income|sales)\b.{0,60}\b(?:allocated|attribut(?:ed|able)|relat(?:ed|ing))\b"
    r".{0,30}\b(?:RPO|remaining performance obligations?)\b|"
    r"收入.{0,30}(?:分摊|分配|计入).{0,30}(?:剩余履约义务|未履约订单)", re.I)
_OPERATING_OBJECT = re.compile(
    r"(?:新工厂|新产线|生产线|客户|设备|产品|晶圆|平台|软件|研发|海外|用户)|"
    r"\b(?:customers?|clients?|platforms?|production lines?|factories|reactors?|"
    r"overseas|software|engineers?)\b", re.I)
_OPERATING_EVENT = re.compile(
    r"(?:推出|投产|量产|交付|客户认证|客户验证|重复订单|收购|并购|招聘|聘用)|"
    r"租赁.{0,25}(?:新工厂|新产线)|"
    r"\b(?:launched|deployed|commissioned|delivered|repeat orders?|acquired|"
    r"hired|customer certification)\b", re.I)
_AUDIT_SPEECH = re.compile(
    r"\bwe (?:evaluated|tested|assessed|obtained)\b.{0,180}"
    r"\b(?:internal controls?|impairment|management(?:['’]s)? assumptions|audit|"
    r"remaining performance obligations?)\b|我们.{0,20}(?:实施审计|执行审计)", re.I)
_AUDIT_OWNER = re.compile(
    r"^\s*(?:(?:our|the|these)\s+)?(?:audit procedures?|(?:independent|external|statutory)\s+auditor)"
    r"\b.{0,45}\b(?:test\w*|evaluat\w*|check\w*|examin\w*|includ\w*|involv\w*|performed|conducted)\b|"
    r"^\s*(?:本次|我们的|我們的)?审计(?:程序|测试|证据).{0,20}(?:包括|检查|涉及|涵盖|实施)", re.I)


def _clause_purpose(value: str) -> str:
    if _AUDIT_SPEECH.search(value) or _AUDIT_OWNER.search(value):
        return "audit_procedure"
    if _OPERATING_OBJECT.search(value) and _OPERATING_EVENT.search(value):
        return "operating"
    if _AUDIT.search(value):
        return "audit_procedure"
    if _ALLOCATED_FINANCIAL.search(value):
        return "accounting_policy"
    stock = _CONTRACT_STOCK.search(value)
    if stock and _STOCK_VALUE.search(value[stock.end():]):
        return "operating_contract_stock"
    if _ACCOUNTING.search(value):
        return "accounting_policy"
    if _TREASURY.search(value):
        return "treasury_policy"
    if _TEMPLATE.fullmatch(value) and any(character in value for character in "□☑☐√✓适用"):
        return "template_no_event"
    if _NAVIGATION.search(value):
        return "navigation"
    return "unknown"


def source_purpose(text: str) -> str:
    """Describe the purpose of bounded material; no whole-chapter blacklist.

    A separate complete operating clause keeps mixed acquisition/factory notes
    useful. Generic model, product, improve and test words cannot override an
    accounting/audit/treasury purpose by themselves.
    """
    value = matching_reading_text(text)
    # No noun in another sentence may lend an operating object to a policy
    # verb. Conversely a genuine independent business sentence is retained
    # inside an acquisition/lease note rather than blacklisting that chapter.
    purposes = tuple(_clause_purpose(clause.strip()) for clause in
        re.split(r"[。！？；;]|(?<=[.!?])\s+", value) if clause.strip())
    for purpose in ("operating_contract_stock", "operating"):
        if purpose in purposes:
            return purpose
    return next((purpose for purpose in purposes if purpose in NON_OPERATING_PURPOSES), "unknown")
