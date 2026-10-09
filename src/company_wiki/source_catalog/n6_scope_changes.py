"""Concrete operating membership/reporting changes, never revenue growth claims."""

from __future__ import annotations
import re

_EN_OBJECT = (
    r"\b(?:business(?:es)?|products?|services?|segments?|offerings?|subscriptions?|"
    r"solutions?|cloud|(?:customer|user|subscriber|advertising|booking|usage|retention|growth)"
    r"[^.;\n]{0,40}\bmetrics?)\b"
)
_EN_MEMBER = r"(?:the\s+|our\s+)?(?![$\d])[A-Za-z][^.;\n]{5,180}"
_CN_OBJECT = r"(?:业务|产品|服务|分部|指标|统计口径|报告口径|口径)"

_MEMBERSHIP = re.compile(
    rf"{_EN_OBJECT}[^.;\n]{{0,75}}?\b(?:now|will(?:\s+now)?|currently)\s+"
    rf"(?:include[sd]?|exclude[sd]?)\s+{_EN_MEMBER}"
    rf"|{_EN_OBJECT}[^.;\n]{{0,75}}?\b(?:has|have|will be)\s+"
    rf"(?:moved|reclassified|transferred)\s+(?:from|to|into)\s+{_EN_MEMBER}"
    rf"|{_CN_OBJECT}[^。；]{{0,80}}?(?:本期|现(?:在)?|将)[^。；]{{0,15}}?"
    r"(?:包含|包括|纳入|不再包含|不再包括|剔除|排除|调整至|调整为|划入|划出)"
    r"[^。；\d]{2,60}"
    rf"|{_CN_OBJECT}[^。；]{{0,40}}?从[^。；]{{2,40}}?"
    r"(?:调整至|调整为|划入|转入|重分类至)[^。；]{2,40}",
    re.IGNORECASE,
)
_REPORTING = re.compile(
    rf"{_EN_OBJECT}[^.;\n]{{0,65}}?\b(?:will(?:\s+now)?\s+be|are\s+now|is\s+now)\s+"
    rf"(?:reported|included|grouped)\s+(?:in|under|within|as)\s+{_EN_MEMBER}"
    r"|\b(?:will|are going to)\s+transition\s+to\s+"
    r"(?:\d+|one|two|three|four|five|six)\s+(?:reporting\s+)?segments?\b"
    r"|\b(?:are|is|will be|have been)\s+(?:updating|changing|revising)\s+"
    r"[^.;\n]{0,60}(?:product|service|business|segment|metric)[^.;\n]{0,60}"
    r"(?:reporting\s+definitions?|reporting\s+scope|metric\s+definitions?)"
    r"[^.;\n]{0,60}\b(?:represent|reflect|include|exclude)\b"
    rf"|{_CN_OBJECT}[^。；]{{0,100}}?(?:本期|现|将)[^。；]{{0,15}}?"
    r"(?:口径调整为|重新定义为|口径变更为|重分类为|按[^。；]{1,15}分部报告)"
    r"[^。；]{2,60}",
    re.IGNORECASE,
)
_RENAME = re.compile(
    rf"{_EN_OBJECT}[^.;\n]{{0,65}}?\b(?:has been|have been|will be|was|is now|are now)\s+"
    rf"renamed\s+(?:from|to|as)\s+{_EN_MEMBER}"
    rf"|{_EN_OBJECT}[^.;\n]{{0,65}}?\b(?:was|were)\s+previously\s+reported\s+as\s+{_EN_MEMBER}"
    rf"|{_CN_OBJECT}[^。；]{{0,45}}?(?:现|将|已)[^。；]{{0,8}}?"
    r"(?:更名为|改名为|重命名为)[^。；]{2,40}",
    re.IGNORECASE,
)
_UNCHANGED = re.compile(
    r"\botherwise\s+unchanged\b|范围(?:保持)?不变|业务(?:保持)?不变", re.IGNORECASE
)
SCOPE_CHANGE_JOIN = re.compile(
    "|".join(p.pattern for p in (_MEMBERSHIP, _REPORTING, _RENAME)), re.IGNORECASE
)


def scope_change_reasons(text: str) -> tuple[str, ...]:
    """Require a concrete relational change; future/rename/continuity stay textual."""
    reasons = []
    if _MEMBERSHIP.search(text):
        reasons.append("business_scope_change")
    if _REPORTING.search(text):
        reasons.append("reporting_definition_change")
    if _RENAME.search(text):
        reasons.extend(("business_scope_change", "reporting_rename"))
    if reasons and _UNCHANGED.search(text):
        reasons.append("scope_unchanged")
    return tuple(dict.fromkeys(reasons))
