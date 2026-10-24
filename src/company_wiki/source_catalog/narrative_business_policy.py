"""0.7.0 source-oriented business meaning, independent of file/parser format.

A role/name/topic alone never makes a candidate. Patterns require operating
objects plus concrete relationships, mechanisms, events or restrictions. The
text is classification input only; callers keep original bytes and locators.
"""
from __future__ import annotations

import re

from company_wiki.document_normalization.text_matching import matching_reading_text, matching_script_text

from .n6_candidate_operating_facts import OperatingFact
from .n6_candidate_completion import BUSINESS_CHARACTER_WINDOW
from .narrative_source_purpose import (
    NON_OPERATING_PURPOSES,
    revenue_recognition_mechanism,
    source_purpose,
)
from .narrative_revenue_guidance import revenue_guidance
from .narrative_predicate_state import observe_metric_predicate, predicate_scope

from .narrative_business_meaning import (
    _CLAUSES,
    _COMPANY_ANCHOR,
    _FINANCE,
    _GENERIC_DEFINITION,
    _OBJECT,
    _business_fact,
    business_objects,
    business_qualification,
    concrete_operating_event,
    detect_business_fact,
    reject_finance_only_text,
)

_ACTIVITY = re.compile(
    r"\b(?:expand\w*|enter\w*|qualif\w*|certif\w*|commercializ\w*|"
    r"scal\w*|convert\w*|adopt\w*|renew\w*|retain\w*|pilot\w*|ramp\w*)\b|"
    r"拓展|扩张|擴張|扩建|擴建|认证|認證|验证|驗證|试产|試產|交付|商业化|商業化|"
    r"导入|導入|投产|投產|开拓|開拓|新增|转化|轉化", re.IGNORECASE)

# Only the opt-in ReadingPlan detector consumes these relations. Explicit
# legacy selectors keep detect_business_fact and its historical predicates.
READING_BUSINESS_POLICY_VERSION = "reading-business-policy/17"
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
_OWNED_SEGMENT_SCOPE_TEXT = (
    r"\b(?:our|(?:the|this)\s+company['’]s)\s+"
    r"(?:(?:[a-z0-9][a-z0-9&()/\-]*|&)\s+){0,9}segments?\b|"
    r"(?:本公司|公司|本集团|本集團|本企业|本企業|我们|我們)"
    r"[^。！？!?;；,，]{0,35}?(?:分部|业务板块|業務板塊)"
)
_OWNED_SEGMENT_SCOPE = re.compile(_OWNED_SEGMENT_SCOPE_TEXT, re.I)
_SEGMENT_SCOPE_BREAK = re.compile(
    r"\b(?:says?|said|defines?|defined|describes?|described|mentions?|mentioned|"
    r"explains?|explained|discuss(?:es|ed)?)\s+"
    r"(?:a|an|the|that|business|reportable|reporting|operating)\b|"
    r"说明|說明|介紹|介绍|描述|提及|泛指", re.I)
_SEGMENT_SCOPE = re.compile(
    r"\b(?:reportable|reporting|operating|business)\s+segments?\b|"
    r"\bour\s+segments?\b|\b(?:our|the|company)\s+business\b|"
    r"报告分部|報告分部|经营分部|經營分部|分部口径|分部口徑|业务板块|業務板塊|"
    + _OWNED_SEGMENT_SCOPE_TEXT, re.I)
_SEGMENT_RELATION = re.compile(
    r"\b(?:operat(?:e|es|ed|ing)|manag(?:e|es|ed|ing)|report(?:s|ed|ing)?)\b"
    r"[^。.!?;]{0,100}\b(?:using|through|segments?)\b|"
    r"\bsegments?\b[^。.!?;]{0,70}\b(?:consist(?:s|ed|ing)?|compris(?:e|es|ed|ing)|"
    r"includ(?:e|es|ed|ing)|composition|changes?|changed|recast)\b|"
    r"\b(?:composition|changes?|changed|recast|reclassif\w*)\b[^。.!?;]{0,100}\bsegments?\b|"
    r"(?:分部|业务板块|業務板塊).{0,55}(?:由|包括|包含|分为|分為|组成|組成|调整|調整|重述|变更|變更)|"
    r"(?:调整|調整|重述|变更|變更).{0,35}(?:分部|业务板块|業務板塊)", re.I)
_SEGMENT_SELF_REPORTING = re.compile(
    r"\b(?:we|our\s+company|(?:the|this)\s+company)\s+"
    r"(?:(?:have|had|will|now|currently|also)\s+)*"
    r"(?:operat(?:e|es|ed|ing)|manag(?:e|es|ed|ing)|report(?:s|ed|ing)?)\b", re.I)
_SEGMENT_COMPOSITION = re.compile(r"\b(?:consist(?:s|ed|ing)?|compris(?:e|es|ed|ing)|"
    r"includ(?:e|es|ed|ing))\b|由|包括|包含|分为|分為|组成|組成", re.I)
_SEGMENT_FINANCIAL_WORD = re.compile(
    r"\b(?:revenues?|profits?|income|earnings|cash\s+flow|tax(?:es)?|accruals?|"
    r"assets?|liabilit\w*|expenses?|financing\s+cash|investing\s+cash)\b|"
    r"营业收入|營業收入|收入|营收|營收|利润|利潤|税项|稅項|税款|稅款|资产|資產|负债|負債|现金流|現金流", re.I)
_SEGMENT_FINANCIAL_PAYLOAD = re.compile(
    r"^\s*(?:(?:of|the|a|domestic|foreign|overseas|national)\s+|國內|国内|海外|境外)*"
    r"(?:[$€£¥]\s*)?(?:\d[\d,.]*\s*(?:billion|million|thousand|亿元|億元|万元|萬元|"
    r"亿|億|万|萬|元|USD|CNY|HKD|%)?\s*(?:of\s+)?)?"
    r"(?:revenues?|profits?|income|earnings|cash\s+flow|tax(?:es)?|accruals?|"
    r"assets?|liabilit\w*|expenses?|financing\s+cash|investing\s+cash|"
    r"营业收入|營業收入|收入|营收|營收|净利润|淨利潤|利润|利潤|税项|稅項|税款|稅款|资产|資產|负债|負債|现金流|現金流)", re.I)
_PRODUCT_SUBJECT = re.compile(
    r"\b(?:products?|services?|software|platforms?|hosting|cloud|segments?)\b|"
    r"产品|產品|服务|服務|软件|軟件|平台|业务|業務|分部", re.I)
_REVENUE_GROWTH = re.compile(
    r"\b(?:revenue|sales)\b[^。.!?;]{0,45}\b(?:increas\w*|grew|growth|declin\w*|decreas\w*)\b|"
    r"(?:收入|销售|銷售).{0,20}(?:增长|增長|下降|减少|減少)", re.I)
_DRIVER_LINK = re.compile(r"\b(?:driven by|due to|reflecting)\b|主要由|由于|因为|受.{0,12}带动|得益于", re.I)
_OPERATING_MEASURE = re.compile(
    r"\b(?:consumption|usage|subscribers?|seats?|customers?|users?|units?|volumes?|pricing)\b|"
    r"capacity utilization|product mix|\b(?:projects?|orders?|capacity|output|total volume)\b|"
    r"使用量|用量|订阅|訂閱|席位|用户|用戶|客户|客戶|销量|銷量|价格|價格|"
    r"订单|訂單|产能利用率|产品组合|项目|項目|产能|產能|产量|產量|容积|容積|体积|體積", re.I)
_REVENUE_VALUE = re.compile(
    r"(?:营业收入|營業收入|收入|\b(?:revenues?|net sales)\b(?:\s+(?:share|proportion))?)\s*"
    r"(?:(?:(?:has|have|had)\s+)?(?:(?:further|now|already|currently)\s+)*"
    r"(?:was|were|is|are|of|totaled|totalled|reached|amounted to|exceed(?:s|ed)?|"
    r"represented|represents|accounted for|accounts for|"
    r"(?:increased|decreased|grew|declined|rose|fell)\s+(?:(?:further|steadily|significantly)\s+)*to)\s+|"
    r"(?:占比|佔比)?(?:(?:进一步|進一步|已|已经|已經|继续|繼續|同比|环比|環比|持续|持續)\s*)*"
    r"(?:提升至|增至|减至|減至|为|為|达到|達到|达|達|超过|超過|超|逾))?\s*"
    r"(?:(?:over|more than|nearly|approximately|about)\s+|超过|超過|超|逾|约|約)?\s*"
    r"(?:(?:人民币|人民幣|港币|港幣|美元|USD|RMB|CNY|HKD)\s*)?[$¥€£]?\s*\d[\d,.]*", re.I)
_CONTRACT_OBJECT = re.compile(
    r"\b(?:remaining (?:performance )?obligations?|contract(?:ed)? backlog|order backlog|"
    r"unfulfilled customer contracts?)\b|剩余履约义务|剩餘履約義務|合同负债|合同負債|在手订单|在手訂單|未履行客户合同|未履行客戶合同", re.I)
_CONTRACT_CONVERSION = re.compile(
    r"\b(?:recogniz\w*|recognis\w*|invoic\w*|ship\w*|deliver\w*|convert\w*)\b|"
    r"确认|確認|开票|開票|交付|转化|轉化", re.I)
_FORWARD_PERIOD = re.compile(
    r"\b(?:future periods?|thereafter|over the next|within the next|next\s+"
    r"(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|eighteen|twenty(?:[- ]four)?|thirty(?:[- ]six)?)"
    r"\s+(?:months?|quarters?|years?))\b|"
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
    return matching_reading_text(text)


_BRAND_LIST = re.compile(
    r"(?:品牌(?:组合)?|brand portfolio|brands?)"
    r"\s*[,，]?\s*(?:包括|包含|涵盖|compris\w*|includ\w*|consists? of)\s*(?P<members>[^。;!?]{1,160})", re.I)
_PORTFOLIO_DEFINITION_CONTEXT = re.compile(
    r"术语表|词汇表|概念定义|例句|\b(?:glossary|example sentence)\b|"
    r"(?:^|[\s:：])(?:定义|definition)\s*[:：]", re.I)
_MEMBER_SEPARATOR = re.compile(r"[,、]|以及|及|与|和|\b(?:and|or)\b", re.I)
_GENERIC_BRAND_MEMBER = re.compile(
    r"^(?:products?|services?|solutions?|brands?|产品|服务|方案|品牌|各类品牌|相关品牌)$", re.I)
_OWNERSHIP = re.compile(
    r"(?P<owner>[^，,。;!?]{1,80}?)(?:是|为|系)\s*(?P<target>[^，。;!?]{1,100})的"
    r"(?:最大|控股|主要)股东|"
    r"(?P<en_owner>[^。;!?]{1,80}?)\bis\s+(?:the\s+)?(?:largest|majority|controlling)\s+"
    r"shareholder\s+of\s+(?P<en_target>[^。;!?]{2,100})", re.I)
_HYPOTHETICAL_OWNER = re.compile(r"假如|假设|可能|拟|尚未|不是|并非|\b(?:if|may|might|could|would|not)\b", re.I)
_SALES_COMPONENT_CHANGE = re.compile(
    r"\b(?:higher|lower|increasing|decreasing|increased|decreased)\s+(?:net\s+)?sales\s+of\s+"
    r"(?P<component>[^,。;.!?]{1,80})", re.I)
_FINANCIAL_COMPONENT = re.compile(
    r"^(?:financial assets?|shares?|bonds?|securities|equity|interest income|taxes?|"
    r"外汇|证券|股票|债券|利息|税项)\b", re.I)
_READING_ABBREVIATION = re.compile(r"\b(?:Inc|Ltd|Co|Corp)\.(?=\s)", re.I)


def _reading_clauses(text: str) -> tuple[str, ...]:
    # Company suffix punctuation is not a sentence boundary. Only this predicate
    # view elides it; the source string and locator remain untouched.
    interpreted = _READING_ABBREVIATION.sub(lambda match: match.group()[:-1], text)
    return tuple(clause for clause in _CLAUSES.split(interpreted)
                 if clause and len(clause) <= BUSINESS_CHARACTER_WINDOW)


def _brand_portfolio(clause: str) -> tuple[bool, bool]:
    """Observe concrete disclosed membership; do not infer the actor is issuer.

    Source identity/context already belongs to the source owner. A bounded
    filing sentence need not repeat an issuer pronoun, and may describe another
    actor. Its actual wording and qualifiers stay in the evidence unchanged.
    """
    if '品牌' not in clause and 'brand' not in clause.casefold():
        return False, False
    for relation in _BRAND_LIST.finditer(clause):
        context = clause[:relation.start('members')]
        if (_HYPOTHETICAL_OWNER.search(context)
                or _PORTFOLIO_DEFINITION_CONTEXT.search(context)):
            return True, False
        members = [part.strip(' .，') for part in _MEMBER_SEPARATOR.split(relation.group('members'))]
        concrete = [part for part in members if part and not _GENERIC_BRAND_MEMBER.fullmatch(part)]
        return True, len(concrete) >= 2
    return False, False


def _ownership_scope(clause: str) -> bool:
    if '股东' not in clause and 'shareholder' not in clause.casefold():
        return False
    for relation in _OWNERSHIP.finditer(clause):
        owner = relation.group('owner') or relation.group('en_owner') or ''
        target = relation.group('target') or relation.group('en_target') or ''
        if not _HYPOTHETICAL_OWNER.search(owner) and any(c.isalpha() for c in target):
            return True
    return False


def _operating_causal_relation(clause: str) -> bool:
    for link in _DRIVER_LINK.finditer(clause):
        if _measured_driver(clause, after=link.end()):
            return True
    return False


def _measured_driver(clause: str, *, after: int = 0) -> bool:
    """Consume source relations without discarding their modality/scope.

    The causal link restricts where the evidence must occur. It does not
    create a fresh source sentence from a substring after that link.
    """
    return any(kind in {"quantity", "direction"} and start >= after
               for kind, start, _end in _source_measure_relations(clause))


_SOURCE_PRE_QUANTITY = re.compile(
    r"(?:^\s*|\b(?:with|of|to|had|have|has|served|serves|serving|includes?|including|"
    r"over|nearly|about|approximately)\s+)\d[\d,]*(?:\.\d+)?\s+"
    r"(?:(?:million|billion|thousand|paid|active|licensed|new)\s+)*$|"
    r"(?<![第\d])\d[\d,]*(?:\.\d+)?(?:万|萬|亿|億)?(?:个|個|家|项|項|名|台|套)\s*$", re.I)
_SOURCE_QUANTITY = re.compile(
    r"^\s*(?P<label>(?:(?:total\s+)?(?:counts?|numbers?|quantit(?:y|ies))\b|"
    r"(?:总|總)?(?:数量|數量|数|數|总量|總量))?)\s*"
    r"(?P<relation>(?:(?:(?:has|have|had)\s+)?(?:of|was|were|is|are|reached|at|to|stood\s+at|stands\s+at|"
    r"numbered|totals?|totaled|totalled|totaling|totalling)\s+|"
    r"(?:(?:has|have|had)\s+)?(?:increased|decreased|expanded|grew|grown|rose|fallen|fell)\s+to\s+|"
    r"(?:(?:已|已经|已經|进一步|進一步|继续|繼續|持续|持續)\s*)*"
    r"(?:提升至|提高至|增加至|上升至|减少至|減少至|下降至|降至|为|為|达到|達到|达|達|增至|约为|約為|超过|超過)))?\s*"
    r"(?:(?:about|over|nearly|approximately|more\s+than)\s+|约|約|逾|超(?:过|過)?)?"
    r"(?P<value>\d[\d,]*(?:\.\d+)?)", re.I)
_QUANTITY_SCALE = r"(?:(?:万|萬|亿|億|thousand|million|billion)\s*)?"
_SOURCE_QUANTITY_UNIT = re.compile(
    r"^\s*" + _QUANTITY_SCALE +
    r"(?:个|個|家|项|項|名|人|台|套|件|条|條|吨|噸|立方米|立方公尺|公升|升|米|"
    r"m[³3](?=$|[\s,，。.;；])|cubic\s+met(?:er|re)s?\b|kL\b|mL\b|L\b|"
    r"units?\b|customers?\b|projects?\b|subscribers?\b|lit(?:er|re)s?\b|tonnes?\b)", re.I)
_SOURCE_NON_QUANTITY = re.compile(
    r"^\s*" + _QUANTITY_SCALE +
    r"(?:元|美元|港元|人民币|人民幣|USD\b|RMB\b|CNY\b|HKD\b|dollars?\b|"
    r"年|年度|号|號|years?\b|quarters?\b|accounts?\b|is\b|was\b|在|为|為)", re.I)


_MEASURE_FINANCIAL_SUBJECT = re.compile(
    r"^\s*(?:['’]s\s*)?(?:accounts?\b|loans?\b|balances?\b|receivables?\b|"
    r"payables?\b|assets?\b|liabilities\b|amorti[sz]ation\b|"
    r"账户|帳戶|账面|帳面|贷款|貸款|余额|餘額|资产|資產|负债|負債|摊销|攤銷)", re.I)
_DIRECTION_NOMINAL = (
    r"(?:(?:counts?|numbers?|bases?|adoption|retention|engagement|utili[sz]ation|"
    r"conversion|volumes?)\b|数量|數量|数|數|总数|總數|总量|總量|利用率|转化率|轉化率)")
_DIRECTION_WORD = (
    r"(?:higher|lower|grows?|growing|rising|falling|increas\w*|decreas\w*|grew|growth|"
    r"declin\w*|expansion|adoption|improv\w*|changed|shift\w*|rose|fell|up|down)\b|"
    r"(?:增长|增長|上升|下降|提升|减少|減少|增加|扩张|擴張|提高|变动|变動|变化|變化)")
_MEASURE_CHANGE_MODIFIER = (
    r"(?:(?:rapidly|quickly|steadily|further|significantly|substantially|"
    r"year[- ]over[- ]year|year on year)\s+|"
    r"(?:同比|环比|環比|快速|迅速|持续|持續|继续|繼續|进一步|進一步|显著|顯著|稳步|穩步))")
_MEASURE_DIRECTION_AFTER = re.compile(
    r"^\s*(?:" + _DIRECTION_NOMINAL + r"\s*)?"
    r"(?:(?:has|have|had|was|were|is|are|been)\s+)*"
    r"(?:" + _MEASURE_CHANGE_MODIFIER + r"\s*)*"
    r"(?:(?:continued|continues?)\s+to\s+)?(?:" + _DIRECTION_WORD + r")", re.I)
_MEASURE_DIRECTION_BEFORE = re.compile(
    r"(?:" + _DIRECTION_WORD + r")\s*(?:(?:in|of)\s+|的)?"
    r"(?:(?:the|our|total|active|paid|licensed|new|average|annual|monthly|daily)\s+)*$", re.I)
_MEASURE_NOMINAL_END = re.compile(
    r"^\s*(?:" + _DIRECTION_NOMINAL + r"\s*)?"
    r"(?=$|[,，:]|\b(?:during|at|in|from|for|on|across|within|throughout)\b|带动|帶動)", re.I)


def _source_metric_relations(clause: str) -> tuple[tuple[str, int, int], ...]:
    """Observe metric spans with a bound quantity or change predicate.

    Both count and causal consumers use these exact relations. A rejected
    identifier/financial subject cannot borrow a nearby growth word through a
    second detector. Spans are local classification offsets, not new locators.
    """
    if _GENERIC_DEFINITION.search(clause) or _PORTFOLIO_DEFINITION_CONTEXT.search(clause):
        return ()
    relations: list[tuple[str, int, int]] = []
    for metric in _OPERATING_MEASURE.finditer(clause):
        before, after = clause[:metric.start()], clause[metric.end():]
        state = observe_metric_predicate(clause, metric.start(), metric.end())
        if not state.observed and not state.forward_outlook:
            continue
        # The same source-bound quantity relation can be an actual observation
        # or an explicit target. Preserve target recall without letting count,
        # causal or actual-metric consumers turn it into an achieved result.
        projection = "" if state.observed else "planned_"
        if _MEASURE_FINANCIAL_SUBJECT.match(after):
            continue
        quantity = _SOURCE_QUANTITY.match(after)
        after_quantity = False
        if quantity is not None:
            tail = after[quantity.end():]
            after_quantity = bool(not _SOURCE_NON_QUANTITY.match(tail) and (
                quantity.group("label") or quantity.group("relation") or _SOURCE_QUANTITY_UNIT.match(tail)))
            if not after_quantity:
                # An immediate number without a valid measurement relation is
                # an identifier/date/other value, even beside directional text.
                continue
        if after_quantity or _SOURCE_PRE_QUANTITY.search(before):
            relations.append((projection + "quantity", metric.start(), metric.end()))
        direction_after = after
        if state.forward_outlook:
            # Interpret an infinitive only under the existing forward owner.
            # Reuse the same optional nominal and direction vocabulary; bare
            # "orders to grow" cannot become an observed current metric.
            nominal = re.match(r"^\s*(?:" + _DIRECTION_NOMINAL + r"\s*)?", after, re.I)
            if nominal is not None:
                direction_after = after[:nominal.end()] + re.sub(
                    r"^to\s+", "", after[nominal.end():], count=1, flags=re.I)
        if (_MEASURE_DIRECTION_AFTER.match(direction_after) or (
                _MEASURE_DIRECTION_BEFORE.search(before) and _MEASURE_NOMINAL_END.match(after))):
            relations.append((projection + "direction", metric.start(), metric.end()))
    # Component sales changes are source relations too. Causal consumers do
    # not get a separate noun/direction fallback when this owner rejects them.
    for change in _SALES_COMPONENT_CHANGE.finditer(clause):
        component = re.sub(r"^(?:(?:the|our|their|its|a|an)\s+)+", "",
                           change.group("component").strip(), flags=re.I)
        if (_observed_measure_scope(clause, change.start(), change.end())
                and not _FINANCIAL_COMPONENT.search(component)
                and any(character.isalpha() for character in component)):
            relations.append(("direction", change.start(), change.end()))
    relations.extend(_revenue_measure_relations(clause))
    return tuple(relations)


def _source_measure_relations(clause: str) -> tuple[tuple[str, int, int], ...]:
    """Compatibility observed-only view of the same source metric relations."""
    return tuple(relation for relation in _source_metric_relations(clause)
                 if not relation[0].startswith("planned_"))


def _source_quantity_relation(clause: str) -> bool:
    """The quantity projection of the single source metric relation owner."""
    return any(kind == "quantity" for kind, _start, _end in _source_measure_relations(clause))


_REVENUE_PERIOD = (
    r"(?:\d{4}\s*年(?:度)?|本期|报告期内|報告期內|本年度|年度|本年|期内|期內|"
    r"in\s+(?:fiscal\s+)?\d{4}|(?:during|for)\s+the\s+(?:year|period)|this\s+year)")
_REVENUE_SUBJECT_GAP = re.compile(
    r"\s*(?:(?:['’]s|business|segment|licensing|subscriptions?|maintenance|support|sales)\s*)*|"
    r"\s*(?:(?:的|实现|實現|产生|產生|所|业务|業務|销售|銷售|营业|營業|"
    + _REVENUE_PERIOD + r")\s*)*", re.I)
_REVENUE_CONTINUATION_PREFIX = re.compile(
    r"\s*(?:(?:and\s+)?(?:its|their)\s+|(?:" + _REVENUE_PERIOD + r")\s*)", re.I)
_BUSINESS_CONTINUATION_PREDICATE = re.compile(
    r"\s*(?:(?:持续|持續|继续|繼續|保持|维持|維持|稳步|穩步|强劲|強勁)\s*)*"
    r"(?:发力|發力|贡献增长|貢獻增長|增长|增長|发展|發展|扩张|擴張)|"
    r"\s*(?:(?:continued|continues?)\s+to\s+)?"
    r"(?:grow|expand|contribute\s+to\s+growth|gained\s+traction)", re.I)
def _source_measure_scope(clause: str, start: int, end: int) -> tuple[int, int]:
    return predicate_scope(clause, start, end)


def _observed_measure_scope(clause: str, start: int, end: int) -> bool:
    """Actual quantities and forward outlooks share predicate/time ownership."""
    return observe_metric_predicate(clause, start, end).observed


_REVENUE_MEASURE_UNIT = re.compile(
    r"^\s*(?:[%％]|percent\b|亿元|億元|万元|萬元|亿|億|万|萬|元|"
    r"USD\b|RMB\b|CNY\b|HKD\b|dollars?\b|billion\b|million\b|thousand\b)", re.I)
_REVENUE_CURRENCY = re.compile(
    r"[$¥€£]|人民币|人民幣|港币|港幣|美元|\b(?:USD|RMB|CNY|HKD)\b", re.I)


_REVENUE_COMPARISON = re.compile(
    r"同比|环比|環比|按年|按季|较上年|較上年|較去年|较去年|"
    r"\b(?:yoy|qoq|mom|year[- ]over[- ]year|year[- ]on[- ]year|"
    r"quarter[- ]over[- ]quarter|month[- ]over[- ]month)\b|"
    r"\b(?:compared|relative)\s+(?:with|to)\s+(?:the\s+)?"
    r"(?:prior|previous|preceding)\s+(?:year|quarter|month|period)\b", re.I)


_REVENUE_COMPARISON_SUFFIX = re.compile(
    r"^\s*(?:[（(]\s*)?(?:" + _REVENUE_COMPARISON.pattern + ")", re.I)
_REVENUE_RATE_CHANGE = re.compile(
    r"(?:收入|\brevenues?\b)\s*"
    r"(?:(?:from|of)\s+(?P<owner>[^,，。;!?]{1,90}?)\s+)?"
    r"(?:(?:has|have|had)\s+)?"
    r"(?:(?:按(?:固定|不变|不變)(?:汇率|匯率)|on\s+a\s+constant[- ]currency\s+basis)\s*)?"
    r"(?:" + _MEASURE_CHANGE_MODIFIER + r"\s*)*"
    r"(?:增长|增長|下降|减少|減少|增加|上升|increased|decreased|grew|declined|rose|fell)"
    r"\s*(?:了|by\s+)?\s*\d[\d,]*(?:\.\d+)?\s*(?:[%％]|percent\b)", re.I)


def _owned_revenue_subject(clause: str, start: int) -> bool:
    """One local business-owner proof shared by revenue levels and changes."""
    parts = re.split(r"[,，]", clause[max(0, start - 120):start])
    local = parts[-1]
    if any(_REVENUE_SUBJECT_GAP.fullmatch(local[owner.end():])
           for owner in _PRODUCT_SUBJECT.finditer(local)):
        return True
    if len(parts) > 1 and _REVENUE_CONTINUATION_PREFIX.fullmatch(local):
        previous = parts[-2]
        return any(_BUSINESS_CONTINUATION_PREDICATE.fullmatch(previous[owner.end():])
                   for owner in _PRODUCT_SUBJECT.finditer(previous))
    return False


def _revenue_change_has_comparison(clause: str, change: re.Match[str]) -> bool:
    """Bind comparison to this change, not another metric in the same clause."""
    if _REVENUE_COMPARISON.search(change.group()):
        return True
    following = clause[change.end():]
    if _REVENUE_COMPARISON_SUFFIX.match(following):
        return True
    left, _right = _source_measure_scope(clause, change.start(), change.end())
    # A bare source-authored frame may precede the issuer statement. A complete
    # other predicate cannot donate its comparison basis across the comma.
    return bool(left and _REVENUE_COMPARISON.fullmatch(clause[:left].rstrip(",， ")))


def _revenue_measure_relations(clause: str) -> tuple[tuple[str, int, int], ...]:
    """Bind observed revenue levels/shares or rate changes to a local business.

    The same source-state gate and owner proof govern every projection. A
    percentage change is direction, not an amount/share; its original wording
    and basis remain in source evidence and are never numerically converted.
    """
    if _GENERIC_DEFINITION.search(clause) or _PORTFOLIO_DEFINITION_CONTEXT.search(clause):
        return ()
    relations = []
    for value in _REVENUE_VALUE.finditer(clause):
        if not _observed_measure_scope(clause, value.start(), value.end()):
            continue
        # Bare years, numbered fields and unidentified values are not amounts.
        if not (_REVENUE_MEASURE_UNIT.match(clause[value.end():])
                or _REVENUE_CURRENCY.search(value.group())):
            continue
        if _owned_revenue_subject(clause, value.start()):
            relations.append(("revenue", value.start(), value.end()))
    for change in _REVENUE_RATE_CHANGE.finditer(clause):
        if not _observed_measure_scope(clause, change.start(), change.end()):
            continue
        if not _revenue_change_has_comparison(clause, change):
            # A percentage without its disclosed comparison basis is not a
            # source-complete growth observation; never infer a prior period.
            continue
        explicit_owner = change.group("owner")
        owned = _owned_revenue_subject(clause, change.start())
        if explicit_owner:
            financial_owner = re.sub(r"^(?:(?:the|our|their|its|a|an)\s+)+", "",
                                     explicit_owner.strip(), flags=re.I)
            owned = (not _FINANCIAL_COMPONENT.search(financial_owner)
                     and any(_REVENUE_SUBJECT_GAP.fullmatch(explicit_owner[owner.end():])
                             for owner in _PRODUCT_SUBJECT.finditer(explicit_owner)))
        if owned:
            relations.append(("direction", change.start(), change.end()))
    return tuple(relations)


def _business_revenue_measure(clause: str) -> bool:
    """Revenue projection of the shared source-owned measurement relation."""
    return any(kind == "revenue" for kind, _start, _end in _source_measure_relations(clause))


def _segment_reporting_relation(clause: str) -> bool:
    """Bind an issuer's actual segment to its composition/reporting relation.

    A generic named category or a financial total is not reporting scope.
    The existing clause/character bound applies before this helper; matching
    the relation's target prevents borrowing another segment's predicate.
    """
    if not _SEGMENT_SCOPE.search(clause):
        return False
    owned = tuple(scope for scope in _OWNED_SEGMENT_SCOPE.finditer(clause)
                  if not _SEGMENT_SCOPE_BREAK.search(scope.group()))
    issuer_actions = tuple(_SEGMENT_SELF_REPORTING.finditer(clause))
    for relation in _SEGMENT_RELATION.finditer(clause):
        targets = tuple(_SEGMENT_OBJECT.finditer(relation.group()))
        if not targets:
            continue
        target = targets[0]
        start, end = relation.start() + target.start(), relation.start() + target.end()
        ownership = next((scope for scope in owned if scope.end() == end), None)
        reporting = any(action.start() <= relation.start() < action.end() for action in issuer_actions)
        if ownership is None and not reporting:
            continue
        after = clause[end:]
        composition = _SEGMENT_COMPOSITION.search(after[:70])
        if composition is not None:
            gap, payload = after[:composition.start()], after[composition.end():]
            if _SEGMENT_OBJECT.search(gap) or _SEGMENT_FINANCIAL_WORD.search(gap):
                continue
            if _SEGMENT_FINANCIAL_PAYLOAD.search(payload):
                continue
        elif ownership is not None and _SEGMENT_FINANCIAL_WORD.search(clause[ownership.start():start]):
            continue
        return True
    return False


_COVERAGE_PREDICATE = re.compile(r"覆盖|覆蓋|\bcover(?:s|ed|ing|age)?\b", re.I)
_COVERAGE_OBJECT = re.compile(
    r"产品|產品|设备|設備|软件|軟件|服务|服務|工艺|工藝|功能|业务|業務|"
    r"\b(?:products?|equipment|devices?|software|services?|processes?|functions?|business)\b", re.I)
_COVERAGE_SCOPE = re.compile(
    r"产品|產品|设备|設備|工艺|工藝|功能|应用|應用|市场|市場|地区|地區|国家|國家|"
    r"\b(?:products?|equipment|devices?|process(?:es|ing)?|functions?|applications?|"
    r"markets?|regions?|countries)\b", re.I)
_COVERAGE_RATIO = re.compile(r"\d+(?:\.\d+)?\s*(?:[%％]|percent\b)", re.I)
_COVERAGE_COUNT = re.compile(
    r"\d+\s*(?:个|個|类|類|项|項)?(?:海外|国内|國內|目标|目標)?"
    r"(?:市场|市場|地区|地區|国家|國家|功能|工艺|工藝)|"
    r"\b(?:\d+|zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|"
    r"twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty)"
    r"\s+(?:(?:regional|overseas|local|target)\s+)?"
    r"(?:markets?|regions?|countries|functions?|processes?)\b", re.I)
_COVERAGE_QUANTITY_PREFIX = re.compile(
    r"^\s*(?:(?:了|率|度|为|為|达到|達到|至|约|約|超|逾|近|至少|超过|超過|"
    r"大于|大於|将|將|已|已经|已經|可)\s*|"
    r"(?:of|is|was|reached|currently|approximately|over|nearly|about|"
    r"at least|more than|up to)\s+)*$", re.I)
_COVERAGE_LOCAL_BREAK = re.compile(
    r"[,，]|\b(?:and|but|while|whereas|whose|with|caus\w*|leading)\b|"
    r"但是|然而|同时|以及|导致", re.I)
_COVERAGE_SCOPE_END = re.compile(
    r"(?:" + _COVERAGE_SCOPE.pattern + r")\s*(?:的|为|為|is|was|at|reached)?\s*$", re.I)
_COVERAGE_FINANCIAL = re.compile(
    r"拨备|撥備|抵押|准备金|準備金|保额|保額|赔付|賠付|偿付|償付|"
    r"贷款|貸款|应收|應收|应付|應付|资产余额|資產餘額|"
    r"\b(?:provisions?|collateral|reserves?|debt|liabilities|insured\s+values?|"
    r"insured\s+amounts?|claims?|loans?|receivables?|payables?|"
    r"asset\s+balances?)\b|insurance\s+coverage", re.I)
# The same ordinary financial-results family as legacy _FINANCE, scoped only
# to the coverage denominator. A sales service/network can still have genuine
# geographic coverage; its noun is not itself a financial balance or ratio.
_COVERAGE_FINANCIAL_RESULT = re.compile(
    r"\b(?:revenues?|sales|earnings|profits?|incomes?|dividends?|cash\s+flows?|EPS)\b|"
    r"收入|营收|營收|营业额|營業額|销售额|銷售額|利润|利潤|盈利|股利|股息|现金流|現金流", re.I)


def _business_coverage_relation(clause: str) -> bool:
    """A measured coverage predicate and explicit operating scope in one clause.

    This is descriptive source meaning, not an issuer/state assignment: actual,
    planned, conditional and third-party wording remains in the unchanged
    source. In particular, coverage is never projected as a completed milestone
    or converted into market share, revenue share or an achievement forecast.
    """
    for predicate in _COVERAGE_PREDICATE.finditer(clause):
        before = clause[max(0, predicate.start() - 100):predicate.start()]
        after = re.split(r"[,，]", clause[predicate.end():predicate.end() + 120], maxsplit=1)[0]
        subject = _COVERAGE_LOCAL_BREAK.split(before)[-1]
        relation_tail = _COVERAGE_LOCAL_BREAK.split(after, maxsplit=1)[0]
        if (_COVERAGE_FINANCIAL.search(subject + relation_tail)
                or _COVERAGE_FINANCIAL_RESULT.search(relation_tail)):
            continue
        if not (_COVERAGE_OBJECT.search(before) or _COMPANY_ANCHOR.search(before)):
            continue
        for measure in _COVERAGE_RATIO.finditer(after):
            prefix = after[:measure.start()]
            if _COVERAGE_QUANTITY_PREFIX.fullmatch(prefix):
                # The denominator belongs to this quantity, not a new actor or
                # a second unrelated ratio later in the same source clause.
                denominator = _COVERAGE_LOCAL_BREAK.split(after[measure.end():], maxsplit=1)[0]
                if _COVERAGE_SCOPE.search(denominator):
                    return True
            elif (not _COVERAGE_LOCAL_BREAK.search(prefix)
                  and _COVERAGE_SCOPE_END.search(prefix)):
                return True
        for measure in _COVERAGE_COUNT.finditer(after):
            if _COVERAGE_QUANTITY_PREFIX.fullmatch(after[:measure.start()]):
                return True
    return False


def _reading_relations(clauses: tuple[str, ...]) -> tuple[str, ...]:
    """Specific source relationships, not a bag of nouns across sentences."""
    reasons = []
    for clause in clauses:
        if _GENERIC_DEFINITION.search(clause) and not _COMPANY_ANCHOR.search(clause):
            continue
        if _brand_portfolio(clause)[1]:
            reasons.append("brand_portfolio_structure")
        if _ownership_scope(clause):
            reasons.append("business_ownership_scope")
        if _operating_causal_relation(clause):
            reasons.append("operating_causal_driver")
        if (_READING_OBJECT.search(clause) and _BILLING_BASIS.search(clause)
                and _BILLING_RELATION.search(clause)):
            reasons.append("business_billing_basis")
        if _segment_reporting_relation(clause):
            reasons.append("business_reporting_scope")
        if _business_coverage_relation(clause):
            reasons.append("business_coverage_relation")
        if revenue_guidance(clause):
            reasons.append("source_revenue_guidance")
        if revenue_recognition_mechanism(clause):
            reasons.append("business_revenue_recognition")
        measures = _source_metric_relations(clause)
        if any(kind == "quantity" for kind, _start, _end in measures):
            reasons.append("operating_quantity")
        if any(kind == "direction" for kind, _start, _end in measures):
            reasons.append("operating_metric_change")
        if any(kind == "revenue" for kind, _start, _end in measures):
            reasons.append("business_revenue_measure")
        if any(kind in {"planned_quantity", "planned_direction"} for kind, _start, _end in measures):
            reasons.append("operating_plan")
        growth = _REVENUE_GROWTH.search(clause)
        link = _DRIVER_LINK.search(clause)
        if growth and link:
            # An operating subject needs the same source-owned measurement
            # as the generic causal consumer; unrelated product/revenue nouns
            # cannot create a nested-growth fallback.
            subject = clause[:growth.start()]
            if _PRODUCT_SUBJECT.search(subject) and _measured_driver(clause, after=link.end()):
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


def _detect_reading_business_fact(text: str, recognize) -> OperatingFact:
    """Operating activity and bounded business relationships, independent of issuer.

    Legacy replay keeps its historical recognizer. The reading policy admits
    general operating activity in the same bounded clause; a noun or a financial
    growth sentence alone is insufficient. Numeric amounts are never required.
    """
    interpreted = _reading_text(text)
    clauses = _reading_clauses(interpreted)
    # A generic brand list must not borrow the legacy broad "comprises products"
    # mechanism. Only the opt-in reader filters that clause; legacy stays exact.
    source_clauses = tuple(clause for clause in clauses
        if not (_brand_portfolio(clause)[0] and not _brand_portfolio(clause)[1]))
    # Preserve the old bounded per-native-line recognizer for all unfiltered
    # material. A long wrapped tail must not erase an already observed fact.
    fact = recognize('. '.join(source_clauses) if len(source_clauses) != len(clauses)
                     else matching_script_text(text))
    activity = any(concrete_operating_event(clause) or
                   (_OBJECT.search(clause) and _ACTIVITY.search(clause)) for clause in clauses)
    relations = _reading_relations(clauses)
    if not relations and not activity and not _business_fact(interpreted).eligible:
        # The historical English event recognizer can treat a product-labelled
        # financial growth clause as an event. Preserve legacy replay, but the
        # new path needs operating meaning rather than "revenue grew" plus an
        # unrelated happy-customer/product-philosophy noun. Other sentences can
        # still carry independently proven source facts; raw spans are untouched.
        source_clauses = tuple(clause for clause in clauses if not _REVENUE_GROWTH.search(clause))
        if len(source_clauses) != len(clauses):
            fact = recognize(". ".join(source_clauses))
    if not activity and not relations:
        return fact
    families = business_objects(interpreted)
    topics = tuple(dict.fromkeys((*fact.topics, *relations,
        *(("business_progress",) if activity else ()),
        *(("capacity_projects",) if activity and "production" in families else ()))))
    return OperatingFact(True, topics, tuple(dict.fromkeys((*fact.reasons, *relations,
                         *(("operating_activity",) if activity else ())))),
                         max(fact.score, 3), fact.financial_exempt or
                         any(reason != "business_revenue_measure" for reason in relations))


def detect_reading_business_fact(text: str) -> OperatingFact:
    """Compatibility text recognizer; production supplies source relationships."""
    return _purpose_fact(_detect_reading_business_fact(text, detect_business_fact), source_purpose(text))


def _purpose_fact(fact: OperatingFact, purpose: str) -> OperatingFact:
    """Keep source purpose separate from syntactic actor/action recognition."""
    if purpose == "accounting_policy" and "contract_revenue_conversion" in fact.reasons:
        # Existing clause-bound contract/recognition/future-period observation
        # distinguishes a conversion disclosure from a bare allocated total.
        purpose = "operating_contract_stock"
    if purpose in NON_OPERATING_PURPOSES:
        return OperatingFact(False, (), (), 0, False, purpose)
    if purpose == "unknown" and {"operating_quantity", "operating_metric_change", "business_revenue_measure"} & set(fact.reasons):
        purpose = "operating_metric"
    if "operating_plan" in fact.reasons and purpose == "unknown":
        purpose = "operating"
    if "source_revenue_guidance" in fact.reasons and purpose in {"unknown", "operating"}:
        purpose = "operating_guidance"
    if purpose == "operating_contract_stock":
        return OperatingFact(True, tuple(dict.fromkeys((*fact.topics, "operating_metrics"))),
            tuple(dict.fromkeys((*fact.reasons, "operating_contract_stock"))),
            max(4, fact.score), True, purpose)
    return OperatingFact(fact.eligible, fact.topics, fact.reasons, fact.score,
                         fact.financial_exempt, purpose)


_READING_ACCOUNTING = re.compile(r"营业收入|营业成本|净利润|资产负债|每股收益|现金流量|货币资金|应收账款|"
    r"\b(?:revenue|net income|earnings per share|cash flow|balance sheet)\b", re.IGNORECASE)


def reading_financial_only(text: str, fact: OperatingFact, *, recognize=None) -> bool:
    """The existing finance predicate, optionally sharing raw legacy facts.

    detect_business_fact.eligible is exactly the OR of the two legacy
    recognizers used by reject_finance_only_text; no new finance rule is added.
    """
    if fact.financial_exempt:
        return False
    rejected = (reject_finance_only_text(text) if recognize is None else
                bool(_FINANCE.search(text) and not recognize(text).eligible))
    return rejected or bool(_READING_ACCOUNTING.search(text) and not fact.eligible)


def assess_reading_business_fact(text: str, source_relations: dict, *, ref_text=None):
    """One call-local description/finance assessment for one source owner."""
    legacy_facts: dict[str, OperatingFact] = {}
    def recognize(value):
        if value not in legacy_facts:
            legacy_facts[value] = detect_business_fact(value)
        return legacy_facts[value]
    description = _purpose_fact(_detect_reading_business_fact(text, recognize), source_purpose(text))
    fact = project_reading_business_fact(text, source_relations, description=description, ref_text=ref_text)
    return fact, reading_financial_only(text, fact, recognize=recognize)


def project_reading_business_fact(text: str, source_relations: dict, *,
                                  include_description: bool = True, ref_text=None,
                                  description: OperatingFact | None = None) -> OperatingFact:
    """Combine independent descriptions with source-owned operating states.

    The text-only compatibility recognizer cannot assert progress in production.
    Relations already own scope, attribution and modifiers; this projection
    never reparses predicates, changes refs or borrows an actor from a noun.
    Legacy 0.8 recognition remains unchanged.
    """
    fact = (description if description is not None else detect_reading_business_fact(text)) if include_description else OperatingFact()
    if fact.purpose in NON_OPERATING_PURPOSES:
        return fact
    dynamic_reasons = {"operating_activity", "specific_business_event",
                       "applied_operating_milestone", "customer_adoption_milestone"}
    independent = tuple(reason for reason in fact.reasons if reason not in dynamic_reasons)
    topics = [topic for topic in fact.topics if topic != "business_progress"] if independent else []
    reasons = list(independent)
    if not source_relations.get("relations") and set(fact.reasons) & dynamic_reasons:
        # Uncovered event grammar is useful source description, not proof of a
        # milestone. Preserve recall without a text-only completed-state label.
        reasons.append("operating_description_unknown")
        topics.append("core_business")
    for relation in source_relations.get("relations", ()):
        polarity, stage = relation["polarity"], relation["stage"]
        attribution, modality = relation["attribution"], relation["modality"]
        topics.append("core_business")
        if attribution in {"other", "quoted_related_party"}:
            reasons.append("operating_other_party_state")
        elif modality in {"planned", "conditional", "aspirational"}:
            topics.append("new_business")
            reasons.append("operating_plan")
        elif polarity == "negative" or stage in {"not_yet", "suspended", "discontinued"}:
            reasons.append("operating_restriction")
        elif (attribution == "issuer" and polarity == "positive" and modality == "actual"
              and stage in {"current", "contact_established"}):
            # Current state is retained as state. A bound aspect marker or a
            # concrete signed/contact relationship proves an observed milestone.
            qualifiers = [ref_text(ref) if ref_text is not None else text[ref["char_start"]:ref["char_end"]]
                          for ref in relation["qualifier_refs"]]
            milestone = (stage == "contact_established" or
                (relation["activity"] == "business_relationship" and relation["predicate_refs"]) or
                any(re.search(r"已|完成|开始|正在|\b(?:already|has|have|began|started|currently)\b", q, re.I)
                    for q in qualifiers))
            reasons.append("operating_milestone" if milestone else "operating_current_state")
            if milestone:
                topics.append("business_progress")
        else:
            reasons.append("operating_state_unknown")
        if relation["activity"] == "production" and attribution == "issuer":
            topics.append("capacity_projects")
    return OperatingFact(bool(reasons), tuple(dict.fromkeys(topics)), tuple(dict.fromkeys(reasons)),
                         max(fact.score if independent else 0, 3 if reasons else 0),
                         fact.financial_exempt or (include_description and bool(reasons)), fact.purpose)


__all__ = ["business_objects", "business_qualification", "detect_business_fact",
           "detect_reading_business_fact", "project_reading_business_fact",
           "reject_finance_only_text", "READING_BUSINESS_POLICY_VERSION"]
