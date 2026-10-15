"""Bounded unit / scope / qualifier span detection over *label* texts.

Only provider-asserted label refs (row labels and column header path labels)
are scanned, plus the tightest-scope scan of a value's own text for inline
percent/currency units.  Value strings themselves are never rewritten: the
detected spans are returned as ``TextRef``s into the same original units.
"""

from __future__ import annotations

import re

_UNIT_GROUP = re.compile(r"[（(][^（）()]{1,60}[）)]")
_FOOTNOTE_GROUP = re.compile(r"^[（(]?\s*\*?\s*(\d{1,2})\s*[）)]?$")
_UNIT_WORDS = re.compile(
    r"[%％]|RMB|人民币|人民幣|HK\$|US\$|[$€£]|millions?|billions?|thousand"
    r"|百萬|百万|億元|亿元|千元|元"
    r"|per\s+transaction|每單|每单|每交易|客單價|客单价"
    r"|stores?|門店|门店|partners?|合作伙伴|transactions?|交易|SKU|件",
    re.IGNORECASE,
)
_BARE_UNIT = re.compile(
    r"(?:RMB|人民币|人民幣|HK\$|US\$)\s*(?:in\s+)?"
    r"(?:millions?|billions?|thousand|百萬|百万|億元|亿元|千元|元)?"
    r"|[%％]",
    re.IGNORECASE,
)
_SCOPE_WORDS = re.compile(
    r"mainland|China|中國|中国|overseas|海外|Asia|亞洲|亚洲"
    r"|North\s+America|北美洲|北美|Latin\s+America|拉丁美洲|拉美"
    r"|Europe|歐洲|欧洲|Americas|美洲|domestic|境內|境内|international"
    r"|first[- ]?tier|一線|一线|second[- ]?tier|二線|二线|third|三線|三线|低線|低线"
    r"|omni[- ]?channel|全渠道|offline|線下|线下|online|線上|线上"
    r"|retail|零售|wholesale|批發|批发|distributor|經銷|经销"
    r"|新增|存量|new\s+stores?|existing",
    re.IGNORECASE,
)
_QUALIFIER_PHRASES = re.compile(
    r"same[-\s]?store|同店|like[-\s]?for[-\s]?like|可比", re.IGNORECASE
)


def dedupe(refs: list[dict]) -> list[dict]:
    seen: set[tuple] = set()
    out: list[dict] = []
    for ref in refs:
        key = (ref["unit_id"], ref["char_start"], ref["char_end"])
        if key not in seen:
            seen.add(key)
            out.append(ref)
    return out


def _sub(ref: dict, start: int, end: int) -> dict:
    return {
        "unit_id": ref["unit_id"],
        "char_start": ref["char_start"] + start,
        "char_end": ref["char_start"] + end,
    }


def _overlaps(spans: list[tuple[int, int]], start: int, end: int) -> bool:
    return any(s < end and start < e for s, e in spans)


def scan_label(ref: dict, text: str) -> tuple[list[dict], list[dict], list[dict]]:
    """Return (unit_refs, scope_refs, qualifier_refs) for one label span."""
    units: list[dict] = []
    qualifiers: list[dict] = []
    group_spans: list[tuple[int, int]] = []
    for m in _UNIT_GROUP.finditer(text):
        span = (m.start(), m.end())
        group_spans.append(span)
        content = m.group(0)[1:-1]
        if _FOOTNOTE_GROUP.match(m.group(0)):
            qualifiers.append(_sub(ref, *span))
        elif _UNIT_WORDS.search(content):
            units.append(_sub(ref, *span))
    for m in _BARE_UNIT.finditer(text):
        if _overlaps(group_spans, m.start(), m.end()):
            continue
        units.append(_sub(ref, m.start(), m.end()))
    for m in _QUALIFIER_PHRASES.finditer(text):
        qualifiers.append(_sub(ref, m.start(), m.end()))
    scopes: list[dict] = []
    if _SCOPE_WORDS.search(text):
        scopes.append(dict(ref))
    return dedupe(units), dedupe(scopes), dedupe(qualifiers)


def scan_value(ref: dict, text: str) -> list[dict]:
    """Cell-scope unit detection inside a value string (percent/currency only)."""
    units: list[dict] = []
    for m in _BARE_UNIT.finditer(text):
        units.append(_sub(ref, m.start(), m.end()))
    return dedupe(units)


_DIMENSIONS = {
    'currency': re.compile(r'RMB|人民币|人民幣|HK\$|US\$|[$€£]|元',re.IGNORECASE),
    'scale': re.compile(r'millions?|billions?|thousand|百萬|百万|億|亿|千',re.IGNORECASE),
    'ratio': re.compile(r'[%％]|per\s+transaction|每單|每单|每交易|客單價|客单价',re.IGNORECASE),
    'count': re.compile(r'stores?|門店|门店|partners?|合作伙伴|transactions?|交易|SKU|件',re.IGNORECASE),
}


def select_scoped_units(scopes, unit_text):
    """Closest scope wins per dimension; currency does not erase scale.

    Original refs remain indivisible. A lower-scope composite that conflicts
    with a more specific dimension is not partially rewritten or rescaled.
    Inline ratios define their own metric and exclude inherited money/counts.
    """
    chosen = []
    occupied: set[str] = set()
    for refs in scopes:
        at_scope = []
        dimensions_at_scope = set()
        for ref in refs:
            text = unit_text[ref['unit_id']][ref['char_start']:ref['char_end']]
            dimensions = {name for name, pattern in _DIMENSIONS.items() if pattern.search(text)}
            if not dimensions:
                dimensions = {'other'}
            if 'ratio' in occupied or dimensions <= occupied:
                continue
            if dimensions & occupied:
                # Keep exact original subspans for compatible new dimensions;
                # never drop scale merely because currency is already known.
                for name in dimensions-occupied:
                    for match in _DIMENSIONS[name].finditer(text):
                        at_scope.append(_sub(ref,match.start(),match.end()))
            else:
                at_scope.append(ref)
            dimensions_at_scope.update(dimensions)
        chosen.extend(at_scope)
        occupied.update(dimensions_at_scope)
    return dedupe(chosen)
