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


READING_DISCLOSURE_SCAN_PASSES = 4
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
_EN_MEMBERS = re.compile(r",|\band\b|\bor\b", re.I)
_GENERIC_MEMBER = re.compile(
    r"(?:the\s+)?(?:products?|services?|solutions?|research|development|manufacturing|"
    r"production|sales|operations?|business(?:es)?)", re.I)
_REVENUE = re.compile(r"收入|营业额|\b(?:revenues?|sales)\b", re.I)
_CUSTOMER_LOCATION = re.compile(
    r"客户(?:的)?(?:母公司|总部)?所在地|客户(?:的)?(?:母公司)?总部|"
    r"\bcustomers?['’]s?\s+(?:headquarters|location|domicile)|"
    r"\b(?:location|domicile|headquarters)\s+of\s+(?:the\s+)?customers?\b", re.I)
_REVENUE_ALLOCATION = re.compile(
    r"^\s*(?:主要)?(?:按|根据|依据|基于)|"
    r"^\s*(?:(?:is|are|was|were)\s+)?(?:attribut\w*|allocat\w*|based on)\b", re.I)
_REGION_CUSTOMER_REVENUE = re.compile(
    r"(?:来自|源自|来源于)[^，。；;!?]{0,30}(?:国|洲|地区|国家|省|市|区域|市场|境内|境外|海外|国内)"
    r"客户(?:的)?收入|"
    r"\b(?:revenues?|sales)\s+from\s+customers?\s+in\s+[^,，。;!?]{1,60}"
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
    r"of\s+(?:the\s+)?$", re.I)


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
        if _REVENUE_ALLOCATION.match(tail) and _CUSTOMER_LOCATION.search(tail):
            return True
    return False


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
        if _component_structure("业务包括" + parts):
            relations.append("business_scope")
            break
    for match in _EN_SCOPE.finditer(clause):
        parts = [part.strip(" .:") for part in _EN_MEMBERS.split(
            match.group("parts") or match.group("businesses")) if part.strip(" .:")]
        if len(parts) >= 2 and any(not _GENERIC_MEMBER.fullmatch(part) for part in parts):
            relations.append("business_scope")
            break
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
    return tuple(dict.fromkeys(relations))


def reading_material_value(fact: OperatingFact) -> Literal["meaningful_fact", "description"]:
    """Interpret source observations without changing admission or raw bytes."""
    return ("meaningful_fact" if fact.eligible and set(fact.reasons) - _DESCRIPTION_REASONS
            else "description")
