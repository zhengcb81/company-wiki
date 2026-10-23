"""Bounded source purpose, distinct from grammatical actor/action relations.

The source session invokes this once over its already bounded native material.
It neither reads documents nor changes quotations, source IDs, actors or units.
Accounting models and treasury products are not operating products merely
because they share a noun with a real customer-facing business.
"""
from __future__ import annotations

import re

from company_wiki.document_normalization.text_matching import matching_reading_text

from .narrative_business_meaning import concrete_operating_event, describes_business


NON_OPERATING_PURPOSES = frozenset({
    "accounting_policy", "audit_procedure", "treasury_policy", "template_no_event", "navigation",
})

_ACCOUNTING = re.compile(
    r"期权定价|股份支付|股票期权|使用权资产|租赁负债|账面价值|计入损益|"
    # Definitions and recognition/presentation rules have a financial object
    # and a policy predicate. A generic control/customer/risk word is not enough.
    r"控制.{0,12}(?:是指|的判断标准).{0,160}被投资方.{0,160}可变回报|"
    r"金融资产.{0,160}交易日.{0,40}(?:确认|终止确认)|"
    r"金融工具.{0,160}信用风险.{0,160}初始确认|"
    r"终止经营.{0,12}(?:是指|认定标准|列报方法)|"
    r"终止经营损益.{0,50}利润表.{0,30}(?:列示|列报)|"
    r"\bcontrols?\b.{0,100}\binvest(?:or|ee)\b.{0,160}\bvariable returns\b|"
    r"\b(?:financial assets?|regular.way (?:purchases?|sales?))\b.{0,160}\btrade date\b|"
    r"(?=[^。;!?]{0,240}(?:信用风险|\bcredit risk\b))"
    r"(?=[^。;!?]{0,240}(?:金融工具|\bfinancial instruments?\b))"
    r"(?=[^。;!?]{0,240}(?:初始确认|\binitial recognition\b))[^。;!?]{1,240}|"
    r"\bdiscontinued operations?\b.{0,35}\b(?:is a component|are components|represents? a component)\b|"
    r"\b(?:profit or loss|income or loss)\b.{0,60}\bdiscontinued operations?\b"
    r".{0,80}\bpresented separately\b.{0,60}\bincome statement\b|"
    r"\bincome statement\b.{0,160}\bdiscontinued operations?\b.{0,80}\bpresented separately\b|"
    r"利润表.{0,80}(?:列示|列报).{0,100}终止经营损益|"
    r"金融负债.{0,120}终止确认|终止确认.{0,120}金融负债|"
    r"\bfinancial liabilit(?:y|ies)\b.{0,160}\bderecogni[sz]\w*\b|"
    r"\bderecogni[sz]\w*\b.{0,160}\bfinancial liabilit(?:y|ies)\b|"
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
    r"^\s*(?:(?:for (?:further |more )?details[,:]?\s+)?(?:see|refer to)\s+"
    r"(?:the\s+)?(?:note|item|section)(?:\s*\d+|\s+on\b)|"
    r"(?:具体)?(?:详见|参见|请参阅).{0,30}(?:附注|章节|第.{0,6}节)|"
    r"^[^。！？；;.!?]{1,80}?(?:情况|详情|说明|信息)(?:请)?(?:详见|参见|参阅).{0,30}第.{0,6}节)", re.I)
_TEMPLATE = re.compile(r"^[\s□☑☐√✓✔×✗适用不\.、/():：（）\-]+$")
_LABELLED_NO_EVENT = re.compile(
    r"^(?:(?:[A-Za-z0-9]{1,8}|[(（][A-Za-z0-9一二三四五六七八九十]{1,8}[)）])\s*[.、)]?\s*)?"
    r"(?:[^。！？；;.!?]|(?<=\d)\.(?=\d))*?[□☐]\s*适用\s*[√✓✔☑]\s*不适用\s*$")
# A new explicit actor starts an independent assertion even after a comma.
# Subordinate audit test descriptions do not manufacture a company event.
_ASSERTION_ACTOR = re.compile(
    r"[,，]\s*(?:(?:and|but)\s+)?(?=(?:公司|本公司|集团|本集团|我们|"
    r"the company\b|the group\b|our company\b|we\b))", re.I)

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
_AUDIT_SPEECH = re.compile(
    r"\bwe (?:evaluated|tested|assessed|obtained)\b.{0,180}"
    r"\b(?:internal controls?|impairment|management(?:['’]s)? assumptions|audit|"
    r"remaining performance obligations?)\b|我们.{0,20}(?:实施审计|执行审计)", re.I)
_AUDIT_OWNER = re.compile(
    r"^\s*(?:(?:our|the|these)\s+)?(?:audit procedures?|(?:independent|external|statutory)\s+auditor)"
    r"\b.{0,45}\b(?:test\w*|evaluat\w*|check\w*|examin\w*|includ\w*|involv\w*|performed|conducted)\b|"
    r"^\s*(?:本次|我们的|我們的)?审计(?:程序|测试|证据).{0,20}(?:包括|检查|涉及|涵盖|实施)", re.I)


def _clause_purpose(value: str) -> str:
    # The form's question/label may contain product or future-plan words.
    # Its explicit negative response is still not an observed business event.
    # Source clauses separated by real terminators are assessed independently.
    if _LABELLED_NO_EVENT.fullmatch(value):
        return "template_no_event"
    if _NAVIGATION.search(value):
        return "navigation"
    if _AUDIT_SPEECH.search(value) or _AUDIT_OWNER.search(value):
        return "audit_procedure"
    if concrete_operating_event(value):
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
    if describes_business(value):
        return "operating"
    return "unknown"


def source_purpose(text: str) -> str:
    """Describe the purpose of bounded material; no whole-chapter blacklist.

    A separate complete operating clause keeps mixed acquisition/factory notes
    useful. Generic model, product, improve and test words cannot override an
    accounting/audit/treasury purpose by themselves.
    """
    value = matching_reading_text(text)
    if _LABELLED_NO_EVENT.fullmatch(value):
        return "template_no_event"
    # No noun in another sentence may lend an operating object to a policy
    # verb. Conversely a genuine independent business sentence is retained
    # inside an acquisition/lease note rather than blacklisting that chapter.
    sentences = re.split(r"[。！？；;]|(?<=[.!?])\s+", value)
    clauses = (part for sentence in sentences for part in _ASSERTION_ACTOR.split(sentence))
    purposes = tuple(_clause_purpose(clause.strip()) for clause in clauses if clause.strip())
    for purpose in ("operating_contract_stock", "operating"):
        if purpose in purposes:
            return purpose
    return next((purpose for purpose in purposes if purpose in NON_OPERATING_PURPOSES), "unknown")
