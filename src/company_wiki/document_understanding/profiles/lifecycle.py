"""Orthogonal extent/revision hints from this document's own identification."""
from __future__ import annotations

import re

from .observation import Observation
from .signals import is_title_evidence, looks_like_cross_reference, normalize

_SUMMARY = re.compile(r"(?:(?:报告|報告|说明书|說明書|意向书|意向書|招股章程)摘要|report summary|summary (?:annual|interim|quarterly) report)")
_AMENDED = re.compile(r"(?:修订|修訂|更正|\bamend(?:ed|ment)?\b|\bform\s+(?:10-k|10-q|20-f|s-1|f-1|8-k|6-k)/a\b)")
_SUPPLEMENT = re.compile(r"(?:补充公告|補充公告|補充文件|补充文件|\bsupplement(?:al)?\b)")


def lifecycle_modifiers(observation: Observation, *, family: str) -> dict:
    """No generic 'Summary' section or cited amendment changes the whole filing."""
    leading = observation.units[:6]
    leading_ids = {unit.unit_id for unit in leading}
    own = [unit.text for unit in observation.probes if unit.unit_id in leading_ids
           and is_title_evidence(unit) and not looks_like_cross_reference(unit.text)]
    text = normalize(" ".join([observation.title or "", *own]))
    revision_claim = normalize(observation.revision or "")
    form_claim = normalize(observation.form_type or "")
    if revision_claim in {"original", "原稿", "原始稿"}:
        revision = "original"
    elif revision_claim in {"amended", "amendment", "修订", "修订稿", "修訂稿", "更正"} or _AMENDED.search(text) or form_claim.endswith("/a"):
        revision = "amended"
    elif revision_claim in {"supplement", "supplemental", "补充", "補充"} or _SUPPLEMENT.search(text):
        revision = "supplement"
    else:
        revision = "unknown"
    if _SUMMARY.search(text):
        extent = "summary"
    elif family in {"annual", "interim", "quarterly", "prospectus", "offering"}:
        extent = "full"
    else:
        extent = "unknown"
    return {"extent": extent, "revision": revision}
