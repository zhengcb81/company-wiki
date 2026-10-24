"""Financial reporting-object treatments, distinct from customer operations.

An accounting instrument has actions and risks too. Match its treatment rather
than interpreting every change/manage/translate verb as a business event. An
explicit operating event or product structure remains useful in a mixed clause.
These matches affect classification only; original material is never edited.
"""
from __future__ import annotations

import re

from .narrative_business_meaning import concrete_operating_event, describes_business_structure


_RULES = tuple(re.compile(pattern, re.I) for pattern in (
    # Translation rules concern monetary items/statements, not the company's
    # customer receipts or an observed currency impact on operating revenue.
    r"(?:外币货币性项目|外币财务报表|外币报表)[^。；;!?]{0,80}汇率[^。；;!?]{0,35}(?:折算|换算)|"
    r"\b(?:translat\w*|remeasur\w*)\b.{0,24}\bforeign.currency monetary items?\b"
    r".{0,80}\b(?:closing|spot)\b.{0,35}\b(?:exchange )?rates?\b|"
    r"\bforeign.currency (?:monetary items?|financial statements?)\b.{0,50}"
    r"\b(?:translated|remeasured)\b.{0,60}\b(?:closing|spot)\b.{0,35}\b(?:exchange )?rates?\b",
    # Designation/recognition is the accounting treatment of a financial
    # instrument, not a newly launched customer product named 'hedging'.
    r"(?:指定|划定)[^。；;!?]{0,32}金融(?:工具|资产|负债)[^。；;!?]{0,32}(?:作为|为)套期工具|"
    r"(?:采用|应用)[^。；;!?]{0,16}套期会计(?:方法|政策)?|"
    r"\bdesignat\w*\b.{0,40}\bfinancial instruments?\b.{0,35}\bas hedging instruments?\b|"
    r"\b(?:appl(?:y|ies|ied|ying)|us(?:e|es|ed|ing))\b.{0,24}\bhedge accounting\b",
    # A hypothetical assessment criterion is not an observed change in the
    # operating customer's demand, pricing, qualification or delivery.
    r"金融工具[^。；;!?]{0,100}信用风险[^。；;!?]{0,65}是否[^。；;!?]{0,32}(?:显著|指标)|"
    r"\b(?:assess|determine|evaluate)\w*\b.{0,35}\bwhether\b.{0,35}\bcredit risk\b"
    r".{0,45}\bfinancial instruments?\b.{0,70}\b(?:increased|changed)\b",
))


def reporting_rule_without_operating_event(text: str) -> bool:
    """A treatment or its generic risk-reduction purpose is not an operation.

    Inspect the complete clause: a reporting match can contain an actual
    launched/delivered customer product or its explicit use. Erasing matched
    text would lose that fact. A generic 'reduce risk/improve efficiency' tail
    is a benefit of the reporting treatment, not proof of a separate business.
    """
    return bool(any(rule.search(text) for rule in _RULES)
                and not concrete_operating_event(text)
                and not describes_business_structure(text))
