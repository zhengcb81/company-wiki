"""Bounded source purpose, distinct from grammatical actor/action relations.

The source session invokes this once over its already bounded native material.
It neither reads documents nor changes quotations, source IDs, actors or units.
Accounting models and treasury products are not operating products merely
because they share a noun with a real customer-facing business.
"""
from __future__ import annotations

import re

from company_wiki.document_normalization.text_matching import matching_reading_text
from company_wiki.document_understanding.operating_states.assertion_roles import (
    SourceAssertionRoles, prepare_source_assertions,
    descriptive_operating_relation as descriptive_operating_relation,
)

from .narrative_business_disclosures import reporting_basis_relations
from .narrative_business_meaning import concrete_operating_event, describes_business
from .narrative_reporting_rules import reporting_rule_without_operating_event
from .narrative_revenue_guidance import revenue_guidance


NON_OPERATING_PURPOSES = frozenset({
    "accounting_policy", "audit_procedure", "treasury_policy", "template_no_event", "navigation",
    "governance_training", "reporting_definition",
})
# Extra bounded full-clause scans for rule objects and concrete descriptions.
SOURCE_PURPOSE_EXTENSION_SCAN_PASSES = 12

_ACCOUNTING = re.compile(
    r"期权定价|股份支付|股票期权|使用权资产|租赁负债|账面价值|计入损益|"
    # Definitions and recognition/presentation rules have a financial object
    # and a policy predicate. A generic control/customer/risk word is not enough.
    r"控制.{0,12}(?:是指|的判断标准).{0,160}被投资方.{0,160}可变回报|"
    r"金融资产.{0,160}交易日.{0,40}(?:确认|终止确认)|"
    r"金融工具.{0,160}信用风险.{0,160}初始确认|"
    r"终止经营.{0,12}(?:是指|认定标准|列报方法)|"
    r"终止经营损益.{0,50}利润表.{0,30}(?:列示|列报)|"
    r"收入确认政策|收入确认及计量|会计政策|会计估计|"
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
_GOVERNANCE_TRAINING = re.compile(
    r"(?=[^。！？；;.!?]{0,180}(?:training|awareness|培训|教育|意识))"
    r"(?=[^。！？；;.!?]{0,180}(?:anti[- ]?fraud|anti[- ]?bribery|compliance|internal control|"
    r"governance|ethics|董事会|反舞弊|反腐败|合规|内部控制|公司治理|道德))"
    r"[^。！？；;.!?]{1,180}", re.I)
_TEMPLATE = re.compile(r"^[\s□☑☐√✓✔×✗适用不\.、/():：（）\-]+$")
_LABELLED_NO_EVENT = re.compile(
    r"^(?:(?:[A-Za-z0-9]{1,8}|[(（][A-Za-z0-9一二三四五六七八九十]{1,8}[)）])\s*[.、)]?\s*)?"
    r"(?:[^。！？；;.!?]|(?<=\d)\.(?=\d))*?[□☐]\s*适用\s*[√✓✔☑]\s*不适用\s*$")
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
_REVENUE_RECOGNITION_RULE = re.compile(
    r"收入[\s\S]{0,32}(?:确认|計量|计量)|(?:确认|計量|计量)[\s\S]{0,32}收入|"
    r"\b(?:revenue recognition|recognition of revenue|"
    r"revenue[\s\S]{0,24}recogniz\w*|revenue[\s\S]{0,24}recognis\w*|"
    r"recogniz\w*[\s\S]{0,24}revenue|recognis\w*[\s\S]{0,24}revenue)\b", re.I)
_PERFORMANCE_OBLIGATION = re.compile(r"履约义务|履約義務|\bperformance obligations?\b", re.I)
_CUSTOMER_CONTROL_TRANSFER = re.compile(
    r"客户[\s\S]{0,60}(?:取得|获得)[\s\S]{0,40}控制权|"
    r"客户控制权[\s\S]{0,20}(?:转移|转让|移交)|"
    r"向客户转让[\s\S]{0,40}(?:商品|服务)|"
    r"(?:转让|交付|提供)[\s\S]{0,40}(?:商品|服务)[\s\S]{0,30}给客户|"
    r"\bcustomers?[\s\S]{0,40}\b(?:obtain(?:s|ed)?|gain(?:s|ed)?|receive(?:s|d))"
    r"[\s\S]{0,30}\bcontrol\b|"
    r"\btransfer(?:ring)? control to customers?\b|"
    r"\bcontrol\b.{0,30}\b(?:transfer|transfers|transferred)\b.{0,30}\bto customers?\b|"
    r"\b(?:transfer(?:ring|red)?|deliver\w*|provid\w*|sell\w*)\b.{0,40}"
    r"\b(?:goods|services)\b.{0,50}\bto customers?\b", re.I)
_RECOGNITION_TIMING = re.compile(
    r"履约义务[\s\S]{0,45}(?:在)?某一(?:时段|时间段|时点)(?:内)?履行|"
    r"某一(?:时段|时间段|时点)(?:内)?履行的?履约义务|"
    r"履约进度[\s\S]{0,80}(?:确认|計量|计量)收入|"
    r"(?:按照|根据|按)[\s\S]{0,60}履约进度[\s\S]{0,60}(?:确认|計量|计量)收入|"
    r"预收[\s\S]{0,100}(?:确认为|确认为负债|作为负债)[\s\S]{0,100}"
    r"(?:履行|履约)[\s\S]{0,60}(?:转为|轉為|确认)收入|"
    r"\bperformance obligations?\b.{0,60}\b(?:satisfied|fulfilled)\b.{0,45}"
    r"\b(?:over time|at a point in time|point in time)\b|"
    r"\b(?:contract liabilities?|deferred revenue|unearned revenue)\b"
    r".{0,100}\b(?:recognized|recognised|transferred|released)\b"
    r".{0,35}\brevenue\b.{0,80}\bperformance obligations?\b", re.I)
_AUDIT_SPEECH = re.compile(
    r"\bwe (?:evaluated|tested|assessed|obtained)\b.{0,180}"
    r"\b(?:internal controls?|impairment|management(?:['’]s)? assumptions|audit|"
    r"remaining performance obligations?)\b|我们.{0,20}(?:实施审计|执行审计)", re.I)
_AUDIT_OWNER = re.compile(
    r"^\s*(?:(?:our|the|these)\s+)?(?:audit procedures?|(?:independent|external|statutory)\s+auditor)"
    r"\b.{0,45}\b(?:test\w*|evaluat\w*|check\w*|examin\w*|includ\w*|involv\w*|performed|conducted)\b|"
    r"^\s*(?:本次|我们的|我們的)?审计(?:程序|测试|证据).{0,20}(?:包括|检查|涉及|涵盖|实施)", re.I)

# Rules use accounting/incentive objects even when they contain change, service,
# staff or plan verbs. They are not observed customer/product operations.
_VALUATION_OBJECT = re.compile(r"股权投资|权益投资|股权证券|公平值|公允价值|"
    r"\b(?:equity investments?|equity securities|fair value)\b", re.I)
_VALUATION_RULE = re.compile(r"计量|替代计量|减值|可观察价格|"
    r"\b(?:measur\w*|impairment|observable price|carrying value)\b", re.I)
_INCENTIVE_OBJECT = re.compile(r"购股权|股份奖励|股权激励|股份支付|"
    r"\b(?:share[ -]based compensation|employee share options?|share incentive|equity incentive)\b", re.I)
_INCENTIVE_RULE = re.compile(r"计划|费用|授出|归属|条件|年期|有效期|旨在|"
    r"\b(?:schemes?|plans?|expense|grant\w*|vest\w*|conditions?|valid|aims?)\b", re.I)
_RESULT_DEFINITION_OBJECT = re.compile(r"非公认会计准则|经调整.{0,12}(?:亏损|利润)|"
    r"\b(?:non[- ]GAAP|adjusted (?:operating )?(?:loss|profit|EBITDA))\b", re.I)
_RESULT_DEFINITION_RULE = re.compile(r"界定|定义|对账|调节|"
    r"\b(?:defin\w*|reconcil\w*)\b", re.I)
def _clause_purpose(value: str, *, operating_proof: bool = False) -> str:
    # The form's question/label may contain product or future-plan words.
    # Its explicit negative response is still not an observed business event.
    # Source clauses separated by real terminators are assessed independently.
    if _LABELLED_NO_EVENT.fullmatch(value):
        return "template_no_event"
    if _NAVIGATION.search(value):
        return "navigation"
    if _GOVERNANCE_TRAINING.search(value):
        return "governance_training"
    if not operating_proof and ((_VALUATION_OBJECT.search(value) and _VALUATION_RULE.search(value))
            or (_INCENTIVE_OBJECT.search(value) and _INCENTIVE_RULE.search(value))
            or (_RESULT_DEFINITION_OBJECT.search(value) and _RESULT_DEFINITION_RULE.search(value))):
        return "accounting_policy"
    if revenue_guidance(value,issuer_only=True):
        return "operating_guidance"
    basis = reporting_basis_relations(value)
    if "reporting_outlook_recast" in basis:
        return "operating_guidance"
    if "reporting_segment_scope" in basis:
        return "operating_structure_basis"
    if "future_investment_disclosure" in basis:
        return "operating_investment_disclosure"
    if basis:
        return "operating_metric_basis"
    if _AUDIT_SPEECH.search(value) or _AUDIT_OWNER.search(value):
        return "audit_procedure"
    if reporting_rule_without_operating_event(value):
        return "accounting_policy"
    if concrete_operating_event(value):
        return "operating"
    if _AUDIT.search(value):
        return "audit_procedure"
    if revenue_recognition_mechanism(value):
        return "operating"
    if _ALLOCATED_FINANCIAL.search(value):
        return "accounting_policy"
    stock = _CONTRACT_STOCK.search(value)
    if stock and _STOCK_VALUE.search(value[stock.end():]):
        return "operating_contract_stock"
    if _TREASURY.search(value):
        return "treasury_policy"
    # A typed operating relation binds the actual product and its supplied
    # use/function. Financial words within that product's name are weaker
    # evidence than this relation; actual accounting rules were checked above.
    if operating_proof:
        return "operating"
    if _ACCOUNTING.search(value):
        return "accounting_policy"
    if _TEMPLATE.fullmatch(value) and any(character in value for character in "□☑☐√✓适用"):
        return "template_no_event"
    if describes_business(value):
        return "operating"
    return "unknown"


def revenue_recognition_mechanism(text: str) -> bool:
    """Recognize customer delivery and collection mechanics in revenue policy.

    A revenue/accounting noun alone is not enough. The bounded source material
    must name a performance obligation and either its timing/contract-liability
    treatment or its customer control-transfer rule.
    """
    value = matching_reading_text(text)
    if not _PERFORMANCE_OBLIGATION.search(value):
        return False
    if _RECOGNITION_TIMING.search(value):
        return True
    return bool(_REVENUE_RECOGNITION_RULE.search(value)
                and _CUSTOMER_CONTROL_TRANSFER.search(value))


def source_purpose(text: str, *, prepared: SourceAssertionRoles | None = None) -> str:
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
    prepared = prepared if prepared is not None else prepare_source_assertions(value)
    purposes = tuple(clause.rule_purpose or _clause_purpose(clause.text,
        operating_proof=clause.operating) for clause in prepared.clauses)
    for purpose in ("operating_contract_stock", "operating", "operating_metric_basis",
                    "operating_guidance", "operating_structure_basis",
                    "operating_investment_disclosure"):
        if purpose in purposes:
            return purpose
    return next((purpose for purpose in purposes if purpose in NON_OPERATING_PURPOSES), "unknown")
