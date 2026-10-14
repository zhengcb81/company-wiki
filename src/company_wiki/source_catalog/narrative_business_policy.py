"""0.7.0 source-oriented business meaning, independent of file/parser format.

A role/name/topic alone never makes a candidate. Patterns require operating
objects plus concrete relationships, mechanisms, events or restrictions. The
text is classification input only; callers keep original bytes and locators.
"""
from __future__ import annotations

import re

from .n6_candidate_operating_facts import OperatingFact, detect_operating_fact
from .n6_candidate_completion import BUSINESS_CHARACTER_WINDOW

_OBJECT = re.compile(
    r"\b(?:products?|services?|platforms?|solutions?|(?:multi[- ]?)?models?|agents?|"
    r"workloads?|workflows?|systems?|tokens?|silicon|performance|components?|production|capacity|"
    r"assembly|manufacturing|equipment|deliver(?:y|ies)|shipments?|customers?|pricing|subscriptions?|distributors?|"
    r"knowledge work|coding|cyber (?:operations|defense)|infrastructure|applications?|stack)\b|"
    r"产品|服务|平台|方案|模型|产能|产线|人工|设备|部件|原材料|供应商|生产|制造|"
    r"工艺|客户|用户|渠道|订单|转化率|广告价格|研发|技术|业务|海外需求", re.IGNORECASE)
_EVENT = re.compile(r"\b(?:launch\w*|introduc\w*|deploy\w*|releas\w*|"
    r"open(?:ed)?|commission\w*|roll(?:ed)? out)\b|推出|发布|上线|投入运行", re.IGNORECASE)
_MECHANISM = re.compile(
    r"\b(?:reduc\w*|lower\w*|less|sav\w*|improv\w*|efficien\w*|"
    r"price performance|depends? on|diversif\w*|mix(?:ing)?|routing|modular assembly|standardized modules|"
    r"triag\w*|red teaming|fix\w*|continuously operating)\b|"
    r"\b(?:tasks?|workloads?)\b[^。.!?;]{0,80}\b(?:done by|served by|routed to|processed by|assigned to)\b|"
    r"\bperformance\b[^。.!?;]{0,100}\bcost\b|"
    r"\bcost\b[^。.!?;]{0,100}\bperformance\b|"
    r"\b(?:multi[- ]?model|model)\b[^。.!?;]{0,90}\b(?:critical|important)\b|"
    r"\b(?:critical|important)\b[^。.!?;]{0,90}\b(?:multi[- ]?model|model)\b|"
    r"通过.{0,50}(?:提高|减少|降低|提升|实现)|因(?:为|此)|取决于|"
    r"模块化|先组装|生产流程.{0,30}(?:按照|采用|通过|分为)|供货能力|人工.{0,25}(?:安排|调整)|"
    r"降低.{0,30}(?:成本|能耗|风险)|提升.{0,30}(?:效率|转化率|价格)", re.IGNORECASE)
_STRUCTURE = re.compile(
    r"\b(?:consist\w*|compris\w*|divided into|made up of|"
    r"direct sales|mix of the portfolio|supplied through)\b|"
    r"\b(?:through|via|using)\b[^。.!?;]{0,50}\b(?:distributors?|distribution networks?|supply channels?)\b|"
    r"\bdistributors?\b[^。.!?;]{0,60}\b(?:handle|provide|sell|supply|support|serve)\b|"
    r"\btargets?\s+(?:(?:industrial|enterprise|manufacturing|overseas|international|institutional|retail)\s+(?:customers?|users?|markets?)|manufacturers?|equipment makers)\b|"
    r"产品.{0,40}(?:用于|应用于|可覆盖)|"
    r"通过.{0,35}(?:直销|渠道|经销|外购)|模块化|"
    r"主要采用.{1,40}(?:生产模式|销售模式|工艺)|"
    r"(?:生产模式|生产流程|生产组织|销售渠道|客户群体|研发平台)"
    r".{0,35}(?:采用|按照|分为|由|包括|通过|面向)|"
    r"原材料.{0,30}(?:来源于|外购|供应渠道)", re.IGNORECASE)
# Enumerating identifiable components is useful static source meaning. A list
# consisting entirely of generic categories or business activities is not.
_COMPONENT_LIST = re.compile(
    r"(?:产品|业务|服务|设备|部件|系统)(?:主要)?(?:分为|包括|由)"
    r"(?P<components>[^，。；]{1,100})")
_COMPONENT_SEPARATOR = re.compile(r"以及|与|和|及|、")
# Normalize only list grammar in classification tokens; source units and
# component names such as 等离子刻蚀设备 remain byte-for-byte unchanged.
_COMPONENT_ENUMERATION_SUFFIX = re.compile(r"(?:等等|等)(?:类型|种类|类别|产品|服务|设备|业务|方案)?$")
_GENERIC_COMPONENT = re.compile(
    r"(?:(?:高端|先进|各类|多类|各种|相关|主要|配套|核心|多种|综合|的)|"
    r"研发|研究|开发|生产|制造|销售|经营|管理|业务|产品|服务|设备|装备|"
    r"解决方案|方案)+")


def _component_structure(clause: str) -> bool:
    for match in _COMPONENT_LIST.finditer(clause):
        parts = tuple(_COMPONENT_ENUMERATION_SUFFIX.sub("", part.strip()).strip()
            for part in _COMPONENT_SEPARATOR.split(match.group("components")))
        if len(parts) > 1 and any(part and not _GENERIC_COMPONENT.fullmatch(part)
            for part in parts):
            return True
    return False


_CONSTRAINT = re.compile(
    r"\b(?:constraints?|shortages?|bottleneck|limited|restrict\w*|fails?|"
    r"goes away|resilience|remain available|qualification required|"
    r"required before|cannot|can't be|short.term|subject to)\b|"
    r"限制|约束|瓶颈|受限|中断|短期|突发|须.{0,25}(?:验证|认证)|"
    r"尚.{0,25}(?:不确定|验证|认证)|不确定性", re.IGNORECASE)
_INDUSTRY_SUBJECT = re.compile(r"\b(?:industry|sector|market demand|export licensing)\b|行业|产业|供需格局|行业政策", re.IGNORECASE)
_INDUSTRY_OPERATING_OBJECT = re.compile(
    r"\b(?:export licensing|export permits?|export approvals?|import licensing|"
    r"regulatory (?:approvals?|requirements?)|(?:market|industry) demand|"
    r"(?:market|industry) supply|industry pricing|supply-demand|supply chains?|"
    r"production standards?|market access)\b|"
    r"出口许可|出口审批|进出口政策|行业(?:政策|准入|标准|供需|竞争)|"
    r"市场需求|市场供给|供需格局|供应链", re.IGNORECASE)
_INDUSTRY_CHANGE = re.compile(r"\b(?:shift\w*|tighten\w*|loosen\w*|"
    r"restrict(?:s|ed|ing)?|rising|falling|introduced|revoked|enacted)\b|"
    r"变化|转向|收紧|放宽|调整|新增|延长|缩短|生效|取消", re.IGNORECASE)
_STRATEGY = re.compile(r"\b(?:plan|intend|aim|will)\b[^。.!?;]{0,100}"
    r"\b(?:build|develop|expand|enter|establish|commercialize)\b[^。.!?;]{0,80}"
    r"\b(?:markets?|networks?|products?|services?|manufacturing|countries|customers?)\b|"
    r"(?:拟|计划|将|致力于)[^。；]{0,45}(?:建设|拓展|进入|开发|形成)[^。；]{0,40}"
    r"(?:市场|网络|产品|服务|客户|研发平台)", re.IGNORECASE)
_CLAUSES = re.compile(r"[。！？!?;；\n]|\.(?:\s|$)")
_FINANCE = re.compile(r"^\s*(?:(?:our|the|total)\s+)?"
    r"(?:revenue|sales|earnings|profits?|income|dividends?|cash flow|EPS)\b"
    r"[^。.!?;]{0,70}\b(?:increas\w*|grew|grow\w*|rose|declin\w*)\b", re.IGNORECASE)
_GENERIC_DEFINITION = re.compile(r"是指|定义为|\bis defined as\b", re.IGNORECASE)
_COMPANY_ANCHOR = re.compile(r"公司|本企业|我们|\b(?:our|we|this company)\b", re.IGNORECASE)
_QUALIFIER = re.compile(
    r"\b(?:return calculation|investment framework|my math|our math|"
    r"return framework)\b[^。.!?;]{0,100}\b(?:changed|unchanged|remains?|same)\b|"
    r"^\s*(?:not just for cost|all of these things contribute|"
    r"you need to be able to still continue)\b|"
    r"(?:回报|计算|投资)(?:框架|口径|方法).{0,30}(?:未变|不变|没有变化)", re.IGNORECASE)
_FAMILIES = (
    ("model", re.compile(r"\b(?:models?|multimodel|tokens?|tasks?|silicon|performance|workloads?)\b|模型|算力", re.IGNORECASE)),
    ("operations", re.compile(r"\b(?:agents?|cyber|operations?|triag\w*|vulnerabilities)\b|运营|安全防御", re.IGNORECASE)),
    ("production", re.compile(r"\b(?:production|capacity|assembly|manufacturing|suppli\w*|labor|components?)\b|产能|生产|人工|原材料|供应商|组装|设备", re.IGNORECASE)),
    ("commercial", re.compile(r"\b(?:customers?|distribut\w*|sales|pricing|subscriptions?|portfolio|products?|services?)\b|客户|渠道|产品|服务|转化|广告|海外", re.IGNORECASE)),
    ("infrastructure", re.compile(r"\b(?:infrastructure|stack|application|silicon|hyperscale)\b|基础设施|工艺", re.IGNORECASE)),
)


def business_objects(text: str) -> frozenset[str]:
    """Coarse operating families for nearby context, never an issuer identity."""
    return frozenset(name for name, pattern in _FAMILIES if pattern.search(text))


def business_qualification(text: str) -> bool:
    """A qualifier may join an independent business seed; it is not a seed itself."""
    return _QUALIFIER.search(text) is not None


_EVENT_FINANCE = re.compile(r"\b(?:revenues?|dividends?|earnings|financial statements?|accounting)\b|"
    r"分红|股利|财务报表|资产负债表", re.IGNORECASE)
_PASSIVE_GAP = re.compile(r"\s*(?:(?:has|have|had|been|being|was|were|is|are|will|be|now|also)\s+)*", re.IGNORECASE)


def _business_event(clause: str) -> bool:
    """An action targets an operating object within a finite clause window."""
    for event in _EVENT.finditer(clause):
        for obj in _OBJECT.finditer(clause):
            if event.end() <= obj.start():
                gap = clause[event.end():obj.start()]
                if len(gap) <= 160 and not _EVENT_FINANCE.search(gap):
                    return True
            elif obj.end() <= event.start():
                gap = clause[obj.end():event.start()]
                if len(gap) <= 40 and not _EVENT_FINANCE.search(gap):
                    if _PASSIVE_GAP.fullmatch(gap) or re.fullmatch(r"[已将正新计划预计即及\s]{0,10}", gap):
                        return True
    return False


def _business_fact(text: str) -> OperatingFact:
    reasons: list[str] = []
    for clause in _CLAUSES.split(text):
        if not clause or len(clause) > BUSINESS_CHARACTER_WINDOW:
            continue
        if _GENERIC_DEFINITION.search(clause) and not _COMPANY_ANCHOR.search(clause):
            continue
        # An industry operating-policy/supply/demand change is source meaning
        # without requiring an invented company product or customer noun.
        if (_INDUSTRY_SUBJECT.search(clause) and _INDUSTRY_OPERATING_OBJECT.search(clause)
            and _INDUSTRY_CHANGE.search(clause)):
            reasons.append("current_industry_context")
        if not _OBJECT.search(clause):
            continue
        # Relations must occur in the same bounded clause, unlike a finance
        # growth statement followed by an unrelated operating noun far away.
        if _business_event(clause):
            reasons.append("specific_business_event")
        if _MECHANISM.search(clause):
            reasons.append("operating_mechanism")
        if _STRUCTURE.search(clause) or _component_structure(clause):
            reasons.append("business_structure")
        if _CONSTRAINT.search(clause):
            reasons.append("business_risk_or_constraint")
        if _STRATEGY.search(clause):
            reasons.append("business_strategy")
    reasons = list(dict.fromkeys(reasons))
    if not reasons:
        return OperatingFact()
    families = business_objects(text)
    topics = ["industry_dynamics"] if "current_industry_context" in reasons else ["core_business"]
    if "business_strategy" in reasons:
        topics.append("new_business")
    if "production" in families:
        topics.append("capacity_projects")
    if re.search(r"海外|境外|\b(?:overseas|international)\b", text, re.IGNORECASE):
        topics.append("overseas")
    if "model" in families or "operations" in families:
        topics.append("products_rd")
    return OperatingFact(True, tuple(topics), tuple(reasons), 3, False)


def detect_business_fact(text: str) -> OperatingFact:
    """Extend the unchanged legacy fact detector with explicit business meaning."""
    legacy = detect_operating_fact(text)
    business = _business_fact(text)
    return OperatingFact(
        eligible=legacy.eligible or business.eligible,
        topics=tuple(dict.fromkeys((*legacy.topics, *business.topics))),
        reasons=tuple(dict.fromkeys((*legacy.reasons, *business.reasons))),
        score=legacy.score + business.score,
        financial_exempt=legacy.financial_exempt,
    )


def reject_finance_only_text(text: str) -> bool:
    """Reject a financial-growth subject without concrete operating meaning."""
    return (_FINANCE.search(text) is not None and not _business_fact(text).eligible
        and not detect_operating_fact(text).eligible)


_ACTIVITY = re.compile(
    r"\b(?:expand\w*|enter\w*|qualif\w*|certif\w*|commercializ\w*|"
    r"scal\w*|convert\w*|adopt\w*|renew\w*|retain\w*|pilot\w*|ramp\w*)\b|"
    r"拓展|扩张|擴張|扩建|擴建|认证|認證|验证|驗證|试产|試產|交付|商业化|商業化|"
    r"导入|導入|投产|投產|开拓|開拓|新增|转化|轉化", re.IGNORECASE)

# Only the opt-in ReadingPlan detector consumes these relations. Explicit
# legacy selectors keep detect_business_fact and its historical predicates.
READING_BUSINESS_POLICY_VERSION = "reading-business-policy/3"
_READING_OBJECT = re.compile(
    r"\b(?:products?|services?|software|platforms?|hosting|cloud|subscriptions?|"
    r"customers?|users?|transactions?)\b|产品|產品|服务|服務|软件|軟件|平台|云|雲|客户|客戶|用户|用戶|订阅|訂閱", re.I)
_BILLING_BASIS = re.compile(
    r"\b(?:consumption[- ]based|usage[- ]based|metered|per[- ](?:seat|user)|"
    r"(?:paid|licensed|active)\s+(?:seats?|users?)|average revenue per user|"
    r"storage consumed|computation used)\b|"
    r"按(?:量|使用量|用量|席位|用户|用戶|交易).{0,8}(?:计费|計費|收费|收費)|"
    r"(?:客户|客戶|用户|用戶)(?:实际|實際)?(?:使用量|用量)|按席位|按量计费|按量計費", re.I)
_BILLING_RELATION = re.compile(
    r"\b(?:charges?|charging|billed|billing|pricing)\b[^。.!?;]{0,100}\b(?:based on|per|for|by)\b|"
    r"\brevenue\b[^。.!?;]{0,100}\b(?:affected|depends? on|from|based on|driven by)\b|"
    r"\b(?:billing|pricing|business)\s+(?:basis|model)\b|"
    r"(?:收入|收费|收費|计费|計費|定价|定價).{0,45}(?:取决于|取決於|根据|根據|采用|採用|按照|按)|"
    r"(?:采用|採用).{0,35}(?:计费|計費|收费|收費)", re.I)
_SEGMENT_OBJECT = re.compile(r"\b(?:reportable|reporting|operating|business)?\s*segments?\b|分部|业务板块|業務板塊", re.I)
_SEGMENT_SCOPE = re.compile(
    r"\b(?:reportable|reporting|operating|business)\s+segments?\b|"
    r"\bour\s+segments?\b|\b(?:our|the|company)\s+business\b|"
    r"报告分部|報告分部|经营分部|經營分部|分部口径|分部口徑|业务板块|業務板塊", re.I)
_SEGMENT_RELATION = re.compile(
    r"\b(?:operate|manage|report)\b[^。.!?;]{0,100}\b(?:using|through|segments?)\b|"
    r"\bsegments?\b[^。.!?;]{0,70}\b(?:consist|comprise|include|composition|changes?|changed|recast)\b|"
    r"\b(?:composition|changes?|changed|recast|reclassif\w*)\b[^。.!?;]{0,100}\bsegments?\b|"
    r"(?:分部|业务板块|業務板塊).{0,55}(?:由|分为|分為|组成|組成|调整|調整|重述|变更|變更)|"
    r"(?:调整|調整|重述|变更|變更).{0,35}(?:分部|业务板块|業務板塊)", re.I)
_PRODUCT_SUBJECT = re.compile(
    r"\b(?:products?|services?|software|platforms?|hosting|cloud|segments?)\b|"
    r"产品|產品|服务|服務|软件|軟件|平台|业务|業務|分部", re.I)
_REVENUE_GROWTH = re.compile(
    r"\b(?:revenue|sales)\b[^。.!?;]{0,45}\b(?:increas\w*|grew|growth|declin\w*|decreas\w*)\b|"
    r"(?:收入|销售|銷售).{0,20}(?:增长|增長|下降|减少|減少)", re.I)
_DRIVER_LINK = re.compile(r"\b(?:driven by|due to|reflecting)\b|主要由|受.{0,12}带动|受.{0,12}帶動|得益于|得益於", re.I)
_OPERATING_MEASURE = re.compile(
    r"\b(?:consumption|usage|subscribers?|seats?|customers?|users?|units?|volumes?|pricing)\b|"
    r"使用量|用量|订阅|訂閱|席位|用户|用戶|客户|客戶|销量|銷量|价格|價格", re.I)
_MEASURE_CHANGE = re.compile(
    r"\b(?:higher|lower|growing|rising|falling|increas\w*|decreas\w*|grew|growth|"
    r"declin\w*|expansion|adoption|mix)\b|增长|增長|上升|下降|提升|减少|減少|增加|扩张|擴張", re.I)
_MEASURE_COUNT = re.compile(r"^\s*(?:(?:of|was|were|reached|at|to)\s+)?\d|"
                            r"\d[\d,.]*\s+(?:(?:million|billion|thousand|paid|active|licensed)\s+)*$", re.I)
_CONTRACT_OBJECT = re.compile(
    r"\b(?:remaining (?:performance )?obligations?|contract(?:ed)? backlog|order backlog|"
    r"unfulfilled customer contracts?)\b|剩余履约义务|剩餘履約義務|合同负债|合同負債|在手订单|在手訂單|未履行客户合同|未履行客戶合同", re.I)
_CONTRACT_CONVERSION = re.compile(
    r"\b(?:recogniz\w*|recognis\w*|invoic\w*|ship\w*|deliver\w*|convert\w*)\b|"
    r"确认|確認|开票|開票|交付|转化|轉化", re.I)
_FORWARD_PERIOD = re.compile(
    r"\b(?:future periods?|thereafter|over the next|within the next|next\s+\d+\s+(?:months?|quarters?|years?))\b|"
    r"未来|未來|之后期间|之後期間|以后期间|以後期間", re.I)

# Only the opt-in reader interprets these retail/network relations. A count is
# a source stock statement, not an inferred opening/net-addition calculation.
_STORE_OBJECT = re.compile(r"\b(?:stores?|outlets?|shops?|branches?|retail locations?)\b|"
    r"门店|門店|店铺|店鋪|店舖|网点|網點|零售网络|零售網絡", re.I)
_STORE_STOCK = re.compile(
    r"\b(?:network\s+of|total\s+of|(?:operate[ds]?|had|have|has)\s+|"
    r"compris\w*\s+|consist\w*\s+of)\s*"
    r"(?:(?:a\s+)?total\s+of\s+)?(?:(?:over|nearly|about|approximately|more than)\s+)?"
    r"\d[\d,.]*\s+(?:[a-z][a-z0-9-]*\s+){0,5}(?:stores?|outlets?|shops?|branches?)\b|"
    r"(?:共有|共计|共計|总计|總計|合计|合計|拥有|擁有|设有|設有|营运|營運|运营|運營|经营|經營)"
    r".{0,12}\d[\d,.]*.{0,20}(?:门店|門店|店铺|店鋪|店舖|网点|網點)", re.I)
_STORE_MODE = re.compile(r"\b(?:directly operated|direct[- ]operations?|company[- ]owned|"
    r"retail[- ]partners?|distributors?|franchisees?|franchis\w*)\b|"
    r"直营|直營|合伙人|合夥人|加盟|代理|經銷|经销", re.I)
_STORE_MODE_RELATION = re.compile(r"\b(?:through|via|under|by|using)\b|"
    r"通过|通過|采用|採用|按照|由|以.{0,12}模式", re.I)
_STORE_OPERATION = re.compile(r"\b(?:operat(?:e|es|ed|ing)|serv(?:e|es|ed|ing)|manage[ds]?|"
    r"sell|sells|sold|own[eds]*|models?)\b|运营|運營|营运|營運|经营|經營|服務|服务|模式", re.I)
_STORE_ACTIVITY = re.compile(r"\b(?:expand(?:s|ed|ing)?|open(?:s|ed|ing)?|clos(?:e|es|ed|ing)|"
    r"contract(?:ed|ing)|relocat(?:e|es|ed|ing)|enter(?:s|ed|ing)?|extend(?:s|ed|ing)?|shut(?:s|ting)?)\b|"
    r"拓展|扩展|擴展|扩张|擴張|开设|開設|新开|新開|"
    r"关闭|關閉|收缩|收縮|迁移|遷移", re.I)
_STORE_FINANCIAL_GAP = re.compile(r"\b(?:cash|accounts?|leases?|liabilit\w*|income|revenues?|"
    r"profits?|assets?|balances?|tax(?:es)?|expenses?|rent|payments?|reimbursements?)\b|"
    r"收入|利润|利潤|资产|資產|现金|現金|负债|負債|税款|稅款|租金", re.I)


def _store_activity(clause: str) -> bool:
    """The opening/closure/expansion acts on a network, not a nearby account."""
    for activity in _STORE_ACTIVITY.finditer(clause):
        for obj in _STORE_OBJECT.finditer(clause):
            if activity.end() <= obj.start():
                gap = clause[activity.end():obj.start()]
                bound = 160
            elif obj.end() <= activity.start():
                gap = clause[obj.end():activity.start()]
                bound = 60
            else:
                continue
            if len(gap) <= bound and not _STORE_FINANCIAL_GAP.search(gap):
                return True
    return False


def _reading_text(text: str) -> str:
    """Interpret native wrapping only; original wording/coordinates stay intact."""
    compact = re.sub(r"(?<=[\u3400-\u9fff])\s+(?=[\u3400-\u9fff])", "", text)
    return compact.replace("\r\n", " ").replace("\n", " ").replace("\r", " ")


def _measured_driver(explanation: str) -> bool:
    """A metric has a measure or observed change, not merely a customer noun."""
    for metric in _OPERATING_MEASURE.finditer(explanation):
        before = explanation[max(0, metric.start() - 32):metric.start()]
        after = explanation[metric.end():metric.end() + 60]
        if (_MEASURE_CHANGE.search(before) or _MEASURE_CHANGE.search(after)
                or _MEASURE_COUNT.search(before) or _MEASURE_COUNT.search(after)):
            return True
    return False


def _reading_relations(clauses: tuple[str, ...]) -> tuple[str, ...]:
    """Specific source relationships, not a bag of nouns across sentences."""
    reasons = []
    for clause in clauses:
        if _GENERIC_DEFINITION.search(clause) and not _COMPANY_ANCHOR.search(clause):
            continue
        if (_READING_OBJECT.search(clause) and _BILLING_BASIS.search(clause)
                and _BILLING_RELATION.search(clause)):
            reasons.append("business_billing_basis")
        if (_SEGMENT_OBJECT.search(clause) and _SEGMENT_SCOPE.search(clause)
                and _SEGMENT_RELATION.search(clause)):
            reasons.append("business_reporting_scope")
        growth = _REVENUE_GROWTH.search(clause)
        link = _DRIVER_LINK.search(clause)
        if growth and link:
            # The operating object belongs to the subject, and its explanation
            # must give an actual operating measure or nested growth relation.
            subject = clause[:growth.start()]
            explanation = clause[link.end():]
            if (_PRODUCT_SUBJECT.search(subject) and (
                _measured_driver(explanation)
                or (_PRODUCT_SUBJECT.search(explanation) and _REVENUE_GROWTH.search(explanation))
            )):
                reasons.append("product_operating_driver")
        if (_CONTRACT_OBJECT.search(clause) and _CONTRACT_CONVERSION.search(clause)
                and _FORWARD_PERIOD.search(clause)):
            reasons.append("contract_revenue_conversion")
        if _STORE_OBJECT.search(clause):
            if any(not _STORE_FINANCIAL_GAP.search(match.group()) for match in _STORE_STOCK.finditer(clause)):
                reasons.append("store_network_stock")
            if (_STORE_MODE.search(clause) and _STORE_MODE_RELATION.search(clause)
                    and _STORE_OPERATION.search(clause)):
                reasons.append("store_operating_model")
            if _store_activity(clause):
                reasons.append("store_network_progress")
    return tuple(dict.fromkeys(reasons))


def detect_reading_business_fact(text: str) -> OperatingFact:
    """Operating activity and bounded business relationships, independent of issuer.

    Legacy replay keeps its historical recognizer. The reading policy admits
    general operating activity in the same bounded clause; a noun or a financial
    growth sentence alone is insufficient. Numeric amounts are never required.
    """
    fact = detect_business_fact(text)
    clauses = tuple(clause for clause in _CLAUSES.split(_reading_text(text))
                    if clause and len(clause) <= BUSINESS_CHARACTER_WINDOW)
    activity = any(_OBJECT.search(clause) and _ACTIVITY.search(clause) for clause in clauses)
    relations = _reading_relations(clauses)
    if not relations and not activity and not _business_fact(text).eligible:
        # The historical English event recognizer can treat a product-labelled
        # financial growth clause as an event. Preserve legacy replay, but the
        # new path needs operating meaning rather than "revenue grew" plus an
        # unrelated happy-customer/product-philosophy noun. Other sentences can
        # still carry independently proven source facts; raw spans are untouched.
        source_clauses = tuple(clause for clause in clauses if not _REVENUE_GROWTH.search(clause))
        if len(source_clauses) != len(clauses):
            fact = detect_business_fact(". ".join(source_clauses))
    if not activity and not relations:
        return fact
    families = business_objects(text)
    topics = tuple(dict.fromkeys((*fact.topics, *relations,
        *(("business_progress",) if activity else ()),
        *(("capacity_projects",) if activity and "production" in families else ()))))
    return OperatingFact(True, topics, tuple(dict.fromkeys((*fact.reasons, *relations,
                         *(("operating_activity",) if activity else ())))),
                         max(fact.score, 3), fact.financial_exempt or bool(relations))


__all__ = ["business_objects", "business_qualification", "detect_business_fact",
           "detect_reading_business_fact", "reject_finance_only_text", "READING_BUSINESS_POLICY_VERSION"]
