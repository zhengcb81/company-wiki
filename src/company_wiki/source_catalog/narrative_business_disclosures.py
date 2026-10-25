"""Bounded source disclosure relations and material value, never issuer facts.

Called on the existing normalized clause view. These observations label the
uses of the unchanged source, not its truth, issuer attribution or completion.
The budget planner consumes the existing value/topic fields and reads no text.
"""
from __future__ import annotations

from typing import Literal
import re

from .n6_candidate_operating_facts import OperatingFact
from .narrative_business_meaning import _component_structure, _STRUCTURE, _OBJECT
from .narrative_predicate_state import predicate_scope
from .n6_scope_changes import scope_change_reasons


READING_DISCLOSURE_SCAN_PASSES = 6
_CN_SCOPE = re.compile(
    r"(?:业务(?:类型|范围)?|服务范围)(?:可以|主要|现有|目前|分别|可)?"
    r"(?:分为|包括|包含|由)(?P<parts>[^。；;!?]{1,240})|"
    r"收入.{0,20}(?:来源于|来自).{0,12}业务类型[：:]?(?P<types>[^。；;!?]{1,240})")
_EN_SCOPE = re.compile(
    r"\b(?:our|the company['’]s|the group['’]s)\s+(?:business|operations?|products?|services?|systems?)\s+"
    r"(?:consists? of|comprises?|includes?|is divided into)\s+(?P<parts>[^。;!?]{1,240})|"
    r"\b(?:we|our company|the company|the group)\s+operates?\s+"
    r"(?:through|in|via)\s+(?:(?:\d+|one|two|three|four|five|several)\s+)?"
    r"(?:businesses|divisions|segments)\s*[:：]?\s*(?P<businesses>[^。;!?]{1,240})", re.I)
_CN_NAMED_LINE_DETAIL = re.compile(
    r"[\u3400-\u9fffA-Za-z0-9][\u3400-\u9fffA-Za-z0-9（）()·&/\- ]{0,36}?"
    r"(?:业务|服务|产品线|分部|板块)"
    r"(?:（[^）\n]{1,48}）|\([^\)\n]{1,48}\))?\s*"
    r"(?:提供|涵盖|覆盖|经营|从事|开展|专注于)"
    r"[\s\S]{0,180}?(?:从[\s\S]{1,80}?(?:到|至)|包括|涵盖|覆盖)")
_EN_REVENUE_LINE_DETAIL = re.compile(
    r"\b(?:revenues?|sales)\s+(?:(?:is|are|was|were)\s+)?(?:primarily|mainly)\s+"
    r"(?:generated|derived|earned)\s+(?:from|by)\s+(?:the\s+)?following\s+"
    r"(?:(?:business|service|operating)\s+)?(?:line|segment)\s*[:\-]\s*"
    r"[A-Za-z][A-Za-z0-9&/'\-]*(?:\s+[A-Za-z][A-Za-z0-9&/'\-]*){0,3}\s+"
    r"(?:provides?|covers?|offers?|delivers?|spans?)\b"
    r"[^.;!?]{0,180}\b(?:from\b[^.;!?]{1,100}\b(?:through|to)\b|"
    r"including\b|covering\b|spanning\b|across\b)", re.I)
_EN_MEMBERS = re.compile(r",|\band\b|\bor\b", re.I)
_GENERIC_MEMBER = re.compile(
    r"(?:the\s+)?(?:products?|services?|solutions?|research|development|manufacturing|"
    r"production|sales|operations?|business(?:es)?)", re.I)
_ENGLISH_REVENUE_SUBJECT = r"(?<!cost of )(?<!costs of )\b(?:revenues?|sales)\b"
_REVENUE = re.compile(rf"收入|营业额|{_ENGLISH_REVENUE_SUBJECT}", re.I)
_CUSTOMER_LOCATION = re.compile(
    r"客户(?:的)?(?:母公司|总部)?所在地|客户(?:的)?(?:母公司)?总部|"
    r"\bcustomers?['’]s?\s+(?:headquarters|location|domicile)|"
    r"\b(?:location|domicile|headquarters)\s+of\s+(?:the\s+)?customers?\b", re.I)
_REVENUE_ALLOCATION = re.compile(
    r"^\s*(?:主要)?(?:按|根据|依据|基于)|"
    r"^\s*(?:(?:is|are|was|were)\s+)?(?:attribut\w*|allocat\w*|based on)\b", re.I)
_COORDINATED_REVENUE_COST = re.compile(
    r"^\s*(?:和|及|与|以及|、|and\s+)"
    r"(?:(?:主营业务|营业|销售|服务)?成本(?=(?:分别|主要)?(?:按|根据|依据|基于|$|[\s,，]))|"
    r"(?:cost\s+of\s+(?:sales|revenue|services?)|(?:operating\s+)?costs?)\b)",
    re.I,
)
_REGION_CUSTOMER_REVENUE = re.compile(
    r"(?:来自|源自|来源于)[^，。；;!?]{0,30}(?:国|洲|地区|国家|省|市|区域|市场|境内|境外|海外|国内)"
    r"客户(?:的)?收入|"
    rf"{_ENGLISH_REVENUE_SUBJECT}\s+from\s+customers?\s+in\s+[^,，。;!?]{{1,60}}"
    r"\b(?:markets?|regions?|countries)\b|"
    r"\bcustomer\s+revenues?\s+by\s+geographic(?:al)?\s+(?:location|region|market)\b", re.I)
_STOCK = re.compile(
    r"在手订单|未交付订单|未履行订单|订单(?:余额|结余)|剩余履约义务|"
    r"履约义务所?对应的?收入|\b(?:RPO|remaining (?:performance obligations?|obligations?(?=\s+revenue\b))|"
    r"(?:order|contracted|contract) backlog|order book|unfulfilled customer contracts?)\b|合同负债|未履行客户合同", re.I)
_STOCK_VALUE = re.compile(
    # Anchor to the stock's own predicate. Another subject's amount cannot
    # complete it. A bare year is never a stock amount without a money unit.
    r"^\s*(?:[)）]\s*)?(?:\([^)]{0,40}\)\s*)?(?:余额|金额)?"
    r"(?:(?:were|was|are|is|of|total(?:ed|s)?|stood at|amounted to)\s+|为|达到|合计|约为|[:：=])?\s*"
    r"(?:(?:approximately|about|over|nearly)\s+)?"
    r"(?:(?:人民币|港币|美元|USD|HKD|RMB|US\$)\s*|[$¥€£]\s*)?"
    r"\d[\d,.]*\s*(?:(?:billion|million|thousand)\b|亿元|万元|亿|万|元)?", re.I)
_MONEY = re.compile(r"人民币|港币|美元|\b(?:USD|HKD|RMB|billion|million|thousand)\b|[$¥€£]|亿元|万元|亿|万|元", re.I)
_CONVERSION = re.compile(r"确认(?:其中[^，。;!?]{0,30})?(?:的)?收入|确认其中|交付|转化|"
                         r"\b(?:recogniz\w*|recognis\w*|invoic\w*|ship\w*|deliver\w*|convert\w*)\b", re.I)
_FORWARD = re.compile(r"预计|预期|将|\b(?:expect\w*|will|scheduled|due)\b", re.I)
_PERIOD = re.compile(
    r"\d{4}(?:年(?:度)?|(?:会计|财务)年度)|(?:会计|财务)年度\s*\d{4}|"
    r"(?:下一|未来)(?:会计|财务)?年(?:度)?|未来|之后期间|以后期间|\bFY\s*\d{4}\b|"
    r"\b(?:fiscal|calendar)\s+year\s+\d{4}\b|\b(?:future periods?|thereafter|"
    r"over the next|within the next|next\s+(?:year|quarter|(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|eighteen|twenty(?:[- ]four)?|thirty(?:[- ]six)?)\s+(?:months?|quarters?|years?)))\b", re.I)

# Labelled metric definitions commonly arrive as one flattened native HTML
# paragraph in SEC exhibits. A colon alone is not enough: require a business
# metric label and a definitional relation in the same short source clause.
_METRIC_LABEL_NOUN = re.compile(
    r"(?:\b(?:bookings?|remaining\s+performance\s+obligations?|RPO|revenue|sales|"
    r"growth|gross\s+margin|margins?|seats?|users?|customers?|orders?|backlog|"
    r"consumption|usage|operating\s+segments?)\s*)$", re.I)
_METRIC_LABEL_WORDS = frozenset({
    "a", "an", "and", "at", "average", "backlog", "billings", "booking",
    "bookings", "billed", "business", "businesses", "cloud", "commercial",
    "company", "company's", "consumer", "consumption", "contract", "contracted",
    "customer", "customers", "deferred", "ex", "gross", "growth", "group",
    "industry", "license", "licenses", "licensing", "margin", "margins", "net",
    "of", "operating", "obligation", "obligations", "order", "orders", "other",
    "our", "paid", "percentage", "performance", "per", "product", "products",
    "remaining", "reportable", "revenue", "revenues", "sales", "search", "seat",
    "seats", "segment", "segments", "server", "service", "services", "solution",
    "solutions", "subscription", "subscriptions", "tac", "total", "unearned",
    "the", "usage", "user", "users", "xbox", "yoy", "y/y",
})
_METRIC_LABEL_HEAD_WORDS = frozenset({
    "backlog", "booking", "bookings", "growth", "margin", "margins", "obligation",
    "obligations", "order", "orders", "revenue", "revenues", "rpo", "sales",
    "seat", "seats", "usage", "user", "users",
})
_METRIC_LABEL_NONBUSINESS = re.compile(
    r"\b(?:audit(?:or|ing)?|training|train(?:ed|ing)?|test(?:ed|ing)?|"
    r"review(?:ed|ing)?|inspect(?:ed|ing|ion)?|employee)\b", re.I)
_METRIC_LABEL_TOKEN = re.compile(r"[A-Za-z][A-Za-z0-9’'./&+-]*|\d+")
_METRIC_DEFINITION_CUE = re.compile(
    r"\b(?:sum\s+of|revenue\s+from|revenue\s+allocated|commercial\s+portion|"
    r"number\s+of|count\s+of|includes?|including|compris\w*|consists?\s+of|"
    r"defined\s+as|calculated\s+(?:as|by)|measured\s+by)\b|"
    r"(?:按.{0,12}(?:計算|计算|统计)|由.{0,24}(?:組成|组成|包括|包含))", re.I)
_METRIC_ASSERTION_SUBJECT = re.compile(
    r"\b(?:(?:active|average|cloud|commercial|contracted|customer|daily|gross|"
    r"licensed|monthly|new|operating|paid|remaining|reportable|service|subscription|"
    r"total|unbilled|unearned)\s+)*(?:remaining\s+performance\s+obligations?|"
    r"bookings?|revenues?|sales|margins?|seats?|users?|customers?|orders?|backlog|"
    r"consumption|usage|subscribers?|projects?|capacity|output|volumes?)\b"
    r"(?:\s+(?:growth|margin|usage|count|number|volume))?", re.I)
_INDEPENDENT_METRIC_ASSERTION = re.compile(
    r"^\s*(?:(?:has|have|had|is|are|was|were|will|would|may|might|could|can|"
    r"expects?|expected|plans?|planned)\s+)*(?:to\s+|be\s+)?"
    r"(?:increas\w*|decreas\w*|expand\w*|grow(?:s|ing)?|grew|grown|rise|rises|"
    r"rose|risen|fall|falls|fell|fallen|declin\w*|reach\w*|number(?:s|ed|ing)?|"
    r"total(?:s|ed|led|ing|ling)?|account(?:s|ed)?\s+for|represent(?:s|ed)|"
    r"amount(?:s|ed)\s+to|remain(?:s|ed)|continue(?:s|d)\s+to\s+"
    r"(?:grow|increase|expand|decline)|contribut\w*\s+to)\b|"
    r"^\s*(?:is|are|was|were|has|have|had)\s+(?:(?:about|approximately|nearly|over)\s+)?"
    r"(?:up|down|higher|lower|[$¥€£]?\s*\d)", re.I)


def _has_independent_metric_assertion(tail: str) -> bool:
    """Require a predicate directly after the new metric subject phrase."""
    subject = _METRIC_ASSERTION_SUBJECT.search(tail)
    return bool(subject and _INDEPENDENT_METRIC_ASSERTION.match(tail[subject.end():]))
_METRIC_DEFINITION_TAG = re.compile(
    r"\bmetric\s+(?:definition\s+(?:(?:has|have|was|were|is)\s+)?"
    r"(?:(?:been)\s+)?(?:updated|changed|revised|created)|"
    r"(?:is\s+)?created\s+by\s+combining)\b", re.I)
_UPDATED_METRIC_DEFINITION = re.compile(
    r"\b[^。！？;；.!?\n]{0,100}\b(?:revenue|sales|bookings?|seats?|growth|"
    r"margin|usage|consumption|customer|subscriber)[^。！？;；.!?\n]{0,35}"
    r"\bmetric\s+definition\s+(?:(?:has|have|was|were|is)\s+)?"
    r"(?:(?:been)\s+)?(?:updated|changed|revised|created)\b|"
    r"\bmetric\s+(?:definition\s+)?(?:is\s+)?created\s+by\s+combining\b", re.I)
_MECHANICAL_OUTLOOK = re.compile(
    r"\bmechanical\s+adjustments?\s+only\b.{0,100}\b(?:outlook|guidance)\b|"
    r"\b(?:outlook|guidance)\b.{0,80}\b(?:only\s+mechanical\s+adjustments?|"
    r"mechanical\s+adjustments?\s+only)\b", re.I)
_UNCHANGED_OUTLOOK = re.compile(
    r"\b(?:outlook|guidance)\b.{0,100}\b(?:unchanged|no\s+change)\b|"
    r"\bno\s+change\s+to\s+(?:the\s+)?(?:company\s+)?outlook\b|"
    r"(?:展望|指引).{0,40}(?:保持不變|保持不变|沒有變化|没有变化|無變化|无变化)|"
    r"(?:展望|指引).{0,30}(?:沒有改變|没有改变|不變|不变)", re.I)
_SINGLE_OPERATING_SEGMENT = re.compile(
    r"\b(?:only\s+(?:(?:has|have|reports?|is|are)\s+)?(?:one|a\s+single)|"
    r"(?:one|a\s+single)\s+and\s+only)\s+(?:(?:reportable|operating|reporting)\s+)?segments?\b|"
    r"(?:僅有|仅有|只有|僅為|仅为|只有)\s*(?:一個|一个)\s*(?:經營|经营|報告|报告)?分部", re.I)
_NO_FUTURE_MATERIAL_INVESTMENT = re.compile(
    r"\bno\s+(?:future\s+)?material\s+investments?\b.{0,90}"
    r"\b(?:capital\s+assets?|capital\s+expenditures?|plans?|commitments?)\b|"
    r"\b(?:no|not\s+(?:have|plan)|does\s+not\s+have|has\s+no)\b.{0,70}"
    r"\b(?:future\s+)?material\s+(?:investments?|capital\s+assets?)\b.{0,70}"
    r"(?:計劃|计划|投資|投资)|"
    r"(?:並無|并无|沒有|没有|未有).{0,18}(?:未來|未来).{0,16}重大"
    r".{0,30}(?:投資|投资).{0,50}(?:資本資產|资本资产|計劃|计划)", re.I)
# Finite links connect a contract head/part to a conversion predicate. Only
# grammatical carriers, quantities and time frames may intervene; another
# actor/object cannot borrow this contract's relation, even after "of which".
_AMOUNT = (r"(?:(?:人民币|港币|美元|USD|HKD|RMB)\s*|[$¥€£]\s*)?"
           r"\d[\d,.]*\s*(?:[%％]|billion|million|thousand|亿元|万元|亿|万|元)?")
_CONVERSION_LINK_TOKEN = re.compile(
    r"(?:\s+|[,，]|\b(?:and|of which|with|the remainder|is|are|was|were|will|be|to|"
    r"expected|scheduled|due|approximately|about|nearly)\b|"
    r"\bwe\s+expect\s+to\b|其中|其余|并|预计|预期|将|于|在|未来|个月|季度|年度|年|"
    r"\d{4}(?:会计|财务)?年(?:度)?|" + _AMOUNT + r")", re.I)
_COMPOSITION_VERB = re.compile(r"(?:consist\w*|compris\w*|divided into|made up of)", re.I)

_INTENT_MARKER = re.compile(
    r"计划|拟|打算|希望|将|会(?!不)|\b(?:plans?|intends?|hopes?|aims?|will)\b", re.I)
_INTENT_ACTION = re.compile(
    r"更新|迭代|推出|采用|延续|稳住|稳定|减少|降低|拓展|开发|"
    r"\b(?:update|release|launch|adopt|continue|stabili[sz]e|reduce|expand|develop)\b", re.I)
_INTENT_LINK_TOKEN = re.compile(
    r"\s+|能够|在一个|新的水平|更多地?|尽量|主动|持续|继续|集中|跟随|跟着|"
    r"这些节点|这些|节点|之后|未来|目前|还是|我们|本公司|本集团|公司|"
    r"会|将|能|在|去|再|更|的|地|也|"
    r"\b(?:to|further|continue|continuously|gradually|selectively|also)\b", re.I)
_INTENT_TARGET_PREFIX = re.compile(
    r"\s+|我们的|一些|这款|该|这一|创新|更新|迭代|现有|新的|对|的|"
    r"\b(?:reliance\s+on|the|our|new|existing|paid|these|those)\b", re.I)
_INTENT_OBJECT = re.compile(
    r"产品|服务|业务|平台|渠道|版本|存量运营|用户留存|客户留存|广告投放|买量|营销方式|"
    r"\b(?:products?|services?|business(?:es)?|platforms?|channels?|versions?|"
    r"customer\s+(?:retention|acquisition|support)|user\s+retention|advertising)\b", re.I)
_INTENT_SUBJECT = re.compile(
    r"(?:产品|服务|业务|平台|渠道|版本)(?:的(?:运营|经营|发展|营销)?(?:思路|方式|策略|方向))?"
    r"(?:还是|仍然|后续|未来|的话|\s)*$|"
    r"\b(?:products?|services?|business|platforms?|channels?)\s*$", re.I)
_INTENT_QUESTION = re.compile(r"请问|是否|会不会|\b(?:whether|will\s+(?:you|the\s+company))\b", re.I)

_PLAN_REFERENCE = re.compile(
    r"^\s*(?:(?:但|但是|不过|不過)\s*)?(?:具体|具體|上述|该|該|这项|這項|这一|這一)?"
    r"(?:计划|計劃|上线时间|上線時間|推出时间|推出時間)|"
    r"^\s*(?:(?:but|however)[, ]+)?(?:this|that|the above)\s+"
    r"(?:(?:launch|release|expansion|development|operating)\s+)?(?:plan|schedule|timing)\b", re.I)
_PLAN_UNCERTAINTY = re.compile(
    r"尚未确定|尚未確定|还没有确定|還沒有確定|没有明确|沒有明確|可能.{0,8}(?:变化|變化|调整|調整)|"
    r"\b(?:not (?:yet )?(?:been )?(?:finalized|finalised|confirmed|determined)|"
    r"may (?:still )?change|subject to change|remains? uncertain)\b", re.I)


def is_backward_plan_qualification(text: str) -> bool:
    """Explicit reference to the preceding plan, never a free-floating caveat."""
    prefix = _PLAN_REFERENCE.match(text)
    return bool(prefix and _PLAN_UNCERTAINTY.search(text, prefix.end(), prefix.end() + 160))


def _after_tokens(text: str, tokens: re.Pattern[str], *, stop: re.Pattern[str] | None = None) -> str:
    """Consume each grammar token once; reject unrelated actors/objects."""
    offset = 0
    while offset < len(text):
        if stop is not None and stop.match(text, offset):
            break
        token = tokens.match(text, offset)
        if token is None:
            break
        offset = token.end()
    return text[offset:]


def _operating_object_head(text: str) -> bool:
    """The business noun must head its phrase, not modify another head noun."""
    match = _INTENT_OBJECT.match(text)
    if match is None:
        return False
    rest = text[match.end():].strip()
    # A sequence of business nouns may form a compound whose final head is
    # still operational (service platform). Administrative
    # heads such as training manuals/expense records cannot complete it.
    while compound := _INTENT_OBJECT.match(rest):
        rest = rest[compound.end():].strip()
    return not rest or bool(re.match(
        r"^(?:的(?:一个)?(?:依赖|方式|思路|模式|策略|方案))(?:[。；;!?]|$)|"
        r"^(?:在|向|以|从|并|与|及)|"
        r"^(?:for|in|on|at|with|by|through|across|that|which|and|to)\b", rest, re.I))


def _qualitative_operating_intent(clause: str) -> bool:
    """A local plan→action→business-object relation, not a completed event.

    Descriptive qualitative plans carry source value even without a metric.
    Tight grammar links prevent an employee/financial plan borrowing a product
    noun elsewhere. Questions and unchanged raw uncertainties stay unasserted.
    """
    for piece in re.split(r"[,，]|但是|然而|\b(?:but|while|whereas)\b", clause):
        if _INTENT_QUESTION.search(piece):
            continue
        for marker in _INTENT_MARKER.finditer(piece):
            tail = piece[marker.end():marker.end() + 96]
            verb_text = _after_tokens(tail, _INTENT_LINK_TOKEN, stop=_INTENT_ACTION)
            action = _INTENT_ACTION.match(verb_text)
            if action is None:
                continue
            target = _after_tokens(verb_text[action.end():], _INTENT_TARGET_PREFIX)
            if _operating_object_head(target) or (
                not target.strip() and _INTENT_SUBJECT.search(piece[:marker.start()])
            ):
                return True
    return False

_STOCK_CONVERSION_PREFIX = re.compile(
    r"\b(?:recogniz\w*|recognis\w*|invoic\w*|ship\w*|deliver\w*|convert\w*)\s+"
    r"(?:(?:approximately|about|nearly)\s+)?(?:\d[\d,.]*\s*[%％]?|some|most|all)\s+"
    # SEC disclosures commonly scope the conversion quantity as "of our total
    # company RPO". Keep this list short and bounded so dates or unrelated
    # sentence material cannot bridge the conversion verb to the stock.
    r"of\s+(?:(?:the|our|their|total|commercial|company|group|business)\s+){0,4}$", re.I)


def _conversion_link(text: str) -> bool:
    """Consume each grammar token once, without ambiguous regex repetition.

    A repeated regex over variable-length quantities can split a long number
    exponentially on a failed suffix. Greedy token consumption is linear and
    rejects an unknown subject immediately, within the source work reservation.
    """
    offset = 0
    while offset < len(text):
        token = _CONVERSION_LINK_TOKEN.match(text, offset)
        if token is None:
            return False
        offset = token.end()
    return bool(text)


def _contract_uses(clause: str) -> tuple[str, ...]:
    """Observe a stock and only its own direct or partitive conversion."""
    uses: list[str] = []
    for stock in _STOCK.finditer(clause):
        left, right = predicate_scope(clause, stock.start(), stock.end())
        tail = clause[stock.end():right]
        amount = _STOCK_VALUE.match(tail)
        measured = amount is not None and _MONEY.search(amount.group()) is not None
        if measured:
            uses.append("operating_contract_stock")
        # A following assertion must itself start with a part/quantity and
        # link directly to conversion. No unbounded sentence-wide predicate
        # conjunction and no special case for a particular issuer or date.
        direct = tail[amount.end():] if measured and amount is not None else tail
        following = clause[right:]
        conversion = None
        for view in (direct, following):
            for action in _CONVERSION.finditer(view):
                if not _conversion_link(view[:action.start()]):
                    continue
                _a, b = predicate_scope(view, action.start(), action.end())
                local = view[:b]
                if _PERIOD.search(local) and (_FORWARD.search(local) or not measured):
                    conversion = local
                    break
            if conversion is not None:
                break
        if conversion is None and _STOCK_CONVERSION_PREFIX.search(clause[left:stock.start()]):
            local = clause[left:right]
            if _PERIOD.search(local) and _FORWARD.search(local):
                conversion = local
        if conversion is not None:
            uses.append("contract_revenue_conversion")
    return tuple(dict.fromkeys(uses))


def _customer_geography(clause: str) -> bool:
    if _REGION_CUSTOMER_REVENUE.search(clause):
        return True
    for revenue in _REVENUE.finditer(clause):
        _left, right = predicate_scope(clause, revenue.start(), revenue.end())
        tail = clause[revenue.end():right]
        coordinated_cost = _COORDINATED_REVENUE_COST.match(tail)
        if coordinated_cost is not None:
            tail = tail[coordinated_cost.end():]
        if _REVENUE_ALLOCATION.match(tail) and _CUSTOMER_LOCATION.search(tail):
            return True
    return False


def _metric_label_noun_phrase(label: str) -> bool:
    """Accept a metric noun phrase, not any sentence that happens to end in revenue."""
    if _METRIC_LABEL_NOUN.search(label) is None or _METRIC_LABEL_NONBUSINESS.search(label):
        return False
    tokens = _METRIC_LABEL_TOKEN.findall(label)
    if not tokens:
        return False
    unknown = [token for token in tokens
               if token.casefold() not in _METRIC_LABEL_WORDS and not token.isdigit()]
    metric_heads = sum(token.casefold() in _METRIC_LABEL_HEAD_WORDS for token in tokens)
    # Capitalization alone cannot turn prose headings or verbs into metric
    # names. Unknown title-case words are tolerated only when the label has a
    # strong, multiword metric signature (for example, "Azure revenue growth").
    return not unknown or (
        metric_heads >= 2
        and all(token[0].isupper() or token.isupper() for token in unknown)
    )


def _metric_label_candidates(text: str, end: int, start: int) -> tuple[tuple[int, str], ...]:
    """Find bounded label candidates before a colon or definition marker."""
    candidates = {start}
    candidates.update(
        start + match.start()
        for match in re.finditer(r"(?<!\w)[A-Z][A-Za-z0-9’'./&+-]*", text[start:end])
    )
    return tuple(
        (candidate, text[candidate:end].strip())
        for candidate in sorted(candidates)
        if not _METRIC_LABEL_NONBUSINESS.search(text[start:candidate])
        if _metric_label_noun_phrase(text[candidate:end].strip())
    )


def reporting_metric_definition_spans(clause: str) -> tuple[tuple[int, int], ...]:
    """Return source-local label/definition ranges, excluding separate assertions.

    SEC exhibits often flatten adjacent definitions into one paragraph. The
    label boundary is grammatical and local: metric noun phrase + definition
    cue. Updated metric labels without a colon are bounded at their own
    "metric definition" marker. A new issuer assertion after a definition is
    left outside the range so it can still be recognized as an actual change.
    """
    spans: list[tuple[int, int]] = []

    for colon in re.finditer(r"[:：]", clause):
        previous = max(
            (match.end() for match in re.finditer(r"[。！？.!?;；:：]", clause[:colon.start()])),
            default=0,
        )
        label = next(iter(_metric_label_candidates(clause, colon.start(), previous)), None)
        if label is None:
            continue
        label_start, _label_text = label
        next_colon = re.search(r"[:：]", clause[colon.end():])
        body_end = colon.end() + next_colon.start() if next_colon else len(clause)
        terminator = re.search(r"[。！？.!?;；\n]", clause[colon.end():body_end])
        if terminator is not None:
            body_end = colon.end() + terminator.start()
        restart = re.search(
            r"(?:[,，;；]\s*(?:and\s+)?|\band\s+)"
            r"(?:we|our|the company|the group)\b",
            clause[colon.end():body_end], re.I,
        )
        restart_tail = (
            clause[colon.end() + restart.end():body_end]
            if restart is not None else ""
        )
        if restart is not None and _has_independent_metric_assertion(restart_tail):
            body_end = colon.end() + restart.start()
        body = clause[colon.end():body_end]
        if _METRIC_DEFINITION_CUE.search(body):
            spans.append((label_start, body_end))

    for marker in _METRIC_DEFINITION_TAG.finditer(clause):
        previous = max(
            (match.end() for match in re.finditer(r"[。！？.!?;；:：]", clause[:marker.start()])),
            default=0,
        )
        label = next(iter(_metric_label_candidates(clause, marker.start(), previous)), None)
        if label is not None:
            spans.append((label[0], marker.end()))

    return tuple(sorted(set(spans)))


def reporting_basis_relations(clause: str) -> tuple[str, ...]:
    """Observe metric definitions, reporting changes and explicit outlook limits.

    These are source-defined business bases, not numeric results. The same
    observer is reused by reading purpose and fact projection so a revenue or
    accounting term cannot make two competing classifiers disagree.
    """
    relations: list[str] = []
    definition_spans = reporting_metric_definition_spans(clause)
    if definition_spans:
        relations.append("reporting_metric_definition")
    if _UPDATED_METRIC_DEFINITION.search(clause) and any(
        span for span in definition_spans
        if _METRIC_DEFINITION_TAG.search(clause[span[0]:span[1]])
    ):
        relations.append("reporting_definition_change")
        # A metric-definition change is still metadata about how to read a
        # comparison. Keep it distinct from an observed change in the metric.
        relations.append("reporting_metric_definition")
    relations.extend(reason for reason in scope_change_reasons(clause)
                     if reason in {"reporting_definition_change", "scope_unchanged"})
    if _MECHANICAL_OUTLOOK.search(clause) or _UNCHANGED_OUTLOOK.search(clause):
        relations.append("reporting_outlook_recast")
    if _SINGLE_OPERATING_SEGMENT.search(clause):
        relations.append("reporting_segment_scope")
    if _NO_FUTURE_MATERIAL_INVESTMENT.search(clause):
        relations.append("future_investment_disclosure")
    return tuple(dict.fromkeys(relations))


# Readability is intentionally broader than scarce summary material. Unknown
# state and generic benefit/vision remain retrievable descriptions. Independently
# observed quantities, scope, mechanisms, plans or constraints retain their value.
_DESCRIPTION_REASONS = frozenset({"operating_mechanism", "business_strategy",
                                "business_structure"})


def disclosure_relations(clause: str) -> tuple[str, ...]:
    """Finite reading uses; no country/company list, numeric conversion or IO."""
    relations = []
    for match in _CN_SCOPE.finditer(clause):
        parts = match.group("parts") or match.group("types")
        if (_component_structure("业务包括" + parts)
                or _CN_NAMED_LINE_DETAIL.search(parts)):
            relations.append("business_scope")
            break
    for match in _EN_SCOPE.finditer(clause):
        parts = [part.strip(" .:") for part in _EN_MEMBERS.split(
            match.group("parts") or match.group("businesses")) if part.strip(" .:")]
        if len(parts) >= 2 and any(not _GENERIC_MEMBER.fullmatch(part) for part in parts):
            relations.append("business_scope")
            break
    if _EN_REVENUE_LINE_DETAIL.search(clause):
        relations.append("business_scope")
    # The legacy structure label also matches bare "comprises/consists".
    # Named scope above and concrete use/channel mechanics below supply the
    # reader's material interpretation; legacy DTO recognition stays intact.
    if (_OBJECT.search(clause) and any(not _COMPOSITION_VERB.fullmatch(match.group())
            for match in _STRUCTURE.finditer(clause))):
        relations.append("business_structure_mechanism")
    if _customer_geography(clause):
        relations.append("customer_revenue_geography")
    if _qualitative_operating_intent(clause):
        relations.append("operating_plan")
    relations.extend(_contract_uses(clause))
    relations.extend(reporting_basis_relations(clause))
    return tuple(dict.fromkeys(relations))


def reading_material_value(fact: OperatingFact) -> Literal["meaningful_fact", "description"]:
    """Interpret source observations without changing admission or raw bytes."""
    return ("meaningful_fact" if fact.eligible and set(fact.reasons) - _DESCRIPTION_REASONS
            else "description")
