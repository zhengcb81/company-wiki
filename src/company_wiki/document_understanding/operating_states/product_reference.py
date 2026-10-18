"""Bounded product-reference grammar for source-authored prose.

Pure string functions only: no IO, parser, model, registry or work balance.
A declaration names a product family (or enumerates its members). A deictic
such as "该系列产品" or "these products" requires a preceding declaration; the
caller supplies only the permitted original predecessors and the shared budget.

Head vocabulary is derived from the existing operating patterns: every
declaration head is either an existing PRODUCT_SUFFIX token or one of the
family markers below. No second product dictionary is introduced; the import
time assertion and tests enforce the subset relation.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import re

from . import patterns as p

SCHEMA = "du11-product-reference/1"

# Family markers are what make a reference a *series/collective* dependency.
_FAMILY_MARKERS = {"系列": "series", "产品线": "series", "產線": "series",
                   "series": "series"}

# PRODUCT_SUFFIX tokens, longest first so 产品线/設備 never match partially.
_SUFFIX_HEADS = (
    "產品", "产品", "設備", "设备", "材料", "添加剂", "產線", "产线",
    "模组", "模块", "器件", "试剂", "药品",
    "equipment", "prototype", "product", "platform", "system", "device",
    "additive", "chemical", "solution", "tool", "tools", "line", "membrane",
    "resin", "filter", "filters", "material", "module", "sensor", "panel",
    "film", "coating", "service",
    "products", "systems", "platforms", "devices", "solutions", "modules",
    "services", "materials", "films", "coatings", "panels", "lines",
    "additives", "chemicals", "resins", "sensors", "prototypes",
)
_HEAD_ALT = "|".join(re.escape(head) for head in
                     sorted((*_FAMILY_MARKERS, *_SUFFIX_HEADS), key=len, reverse=True))

_FAMILY_CLASS = dict(_FAMILY_MARKERS)
_HEAD_CLASS_BY_TOKEN = {
    "產品": "product", "产品": "product", "product": "product",
    "設備": "device", "设备": "device", "device": "device", "equipment": "device",
    "system": "system",
    "platform": "platform",
    "solution": "solution",
    "tool": "tool", "tools": "tool",
    "module": "module", "模组": "module", "模块": "module",
    "器件": "device", "sensor": "device",
    "film": "material", "material": "material", "coating": "material",
    "resin": "material", "材料": "material", "添加剂": "material",
    "additive": "material", "chemical": "material",
    "filter": "component", "panel": "component",
    "line": "line", "产线": "line", "產線": "line",
    "prototype": "prototype", "service": "service",
    "试剂": "material", "药品": "material",
    "products": "product", "systems": "system", "platforms": "platform",
    "devices": "device", "solutions": "solution", "modules": "module",
    "services": "service", "materials": "material", "films": "material",
    "coatings": "material", "panels": "component", "lines": "line",
    "additives": "material", "chemicals": "material", "resins": "material",
    "sensors": "device", "prototypes": "prototype",
}
# Import-time contract: no head outside the shared vocabulary.
for _token in _SUFFIX_HEADS:
    assert (p.PRODUCT_SUFFIX.fullmatch(_token)
            or p.PRODUCT_SUFFIX.fullmatch(_token[:-1])), f"unknown product head: {_token}"

_DEICTIC_CN = re.compile(
    r"(?:該|该|上述|這一|这一|此項|此项|這批|这批|該等|该等|這些|这些|前述)"
    r"(?:系列)?(?:產品|产品|設備|设备|系統|系统|平台|方案|產品線|产品线|器件|模組|模组|模塊|模块)"
    r"|(?:該|该|上述|這些|这些|該等|前述)(?:系列|產品線|产品线)"
)
_DEICTIC_EN = re.compile(
    r"\b(?:these|those|such|this|the\s+above(?:-mentioned)?|the\s+aforementioned|said)"
    r"\s+(?:[A-Za-z][\w-]*\s+){0,2}"
    r"(?:products?|series|systems?|platforms?|devices?|solutions?|tools?|modules?)\b",
    re.IGNORECASE,
)
_PLURAL = re.compile(r"^(?:這些|这些|該等|该等|these|those|such)", re.IGNORECASE)
_FAMILY_MARK = re.compile(r"系列|產品線|产品线|上述|前述|該等|该等|這些|这些|所有|全部")

# Deictic surfaces may name a head we cannot declare (系统/平台/方案/技术).
# Recognise the actual head first, then gate only heads the declaration
# vocabulary can resolve; otherwise a plural "这些平台" would be treated as a
# product reference that no declaration can ever satisfy.
_DEICTIC_HEADS = ("系列", "产品线", "產線", "產品", "产品", "設備", "设备", "系統",
                  "系统", "平台", "方案", "技術", "技术", "器件", "模組", "模组",
                  "模塊", "模块", "材料", "產品線",
                  "products", "product", "series", "systems", "system", "platforms",
                  "platform", "devices", "device", "solutions", "solution", "tools",
                  "tool", "modules", "module")

_GENERIC_CJK = frozenset({
    "产品", "產品", "业务", "業務", "服务", "服務", "客户", "客戶", "市场", "市場",
    "行业", "行業", "企业", "企業", "公司", "集团", "集團", "技术", "技術", "平台",
    "系统", "系統", "方案", "产品线", "產品線", "系列", "这些", "這些", "该", "該",
    "上述", "前述", "该等", "該等", "本集团", "本集團", "本公司", "我们", "我們",
})
_GENERIC_LATIN = frozenset({
    "we", "our", "us", "the", "its", "their", "this", "these", "those", "such",
    "company", "business", "products", "product", "services", "service", "market",
    "customers", "customer", "sell", "sells", "offer", "offers", "provide",
    "provides", "has", "have", "is", "are", "was", "were", "and", "or",
})
_ISSUER_PREFIX = re.compile(
    r"^(?:本公司|本集團|本集团|我们|我們|公司|集團|集团|该|該|其|the|our|we|its|their)\s*",
    re.IGNORECASE)

# A product name starts with a capitalised proper token; generic sentence
# openers ("The Company launched ...") therefore cannot swallow the name.
_HEAD_ONLY = re.compile(_HEAD_ALT)
_FAMILY_SUFFIX = re.compile(r"(系列|产品线|產線)$")
_LATIN_TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9&./+-]*$")
_CJK_TAIL = re.compile(r"[\u3400-\u9fff]{2,10}$")
_CJK_PARTICLES = ("的", "和", "與", "与", "及", "或", "等", "各", "所有", "全部",
                  "主要", "上述", "前述", "公司", "集團", "集团", "我们", "我們",
                  "客户", "客戶", "开发", "開發", "推出", "生产", "生產", "销售",
                  "銷售", "覆盖", "覆蓋", "包括", "可", "未", "已", "将", "將")
# Leading words that introduce a name but are not part of it.
_CJK_STRIP = ("本公司", "本集團", "本集团", "我们", "我們", "公司", "集團", "集团",
              "推出", "開發", "开发", "開發出", "开发出", "研发出", "發布", "发布",
              "生產", "生产", "銷售", "销售", "交付", "覆蓋", "覆盖", "採用", "采用",
              "實現", "实现", "提供", "支持", "包括", "成為", "成为", "進入", "进入",
              "完成", "同時", "同时", "目前", "本期", "报告期内", "報告期內")
# Descriptive technical morphemes: a category description is not a proper name.
_CJK_DESCRIPTOR = ("前道", "後道", "后道", "先進", "先进", "集成", "電路", "电路",
                   "薄膜", "沉積", "沉积", "刻蝕", "刻蚀", "存儲", "存储", "邏輯",
                   "逻辑", "工藝", "工艺", "製程", "制程", "技術", "技术", "應用",
                   "应用", "設備", "设备", "產品", "产品", "材料", "器件", "模組",
                   "模组", "系統", "系统", "平台", "方案", "系列")
_GENERIC_REFERENCE = re.compile(
    r"(?:products?|services?)\s+(?:or|and)\s+(?:products?|services?)"
    r"|internal\s+controls?"
    r"|accounting\s+systems?"
    r"|产品(?:和|及|与|與)服务|產品(?:和|及|與)服務"
    r"|各类产品|各類產品|各种产品|各種產品|所有产品|所有產品|主要产品|主要產品",
    re.IGNORECASE)
_COLLECTIVE_MARK = re.compile(
    r"(?:包括|包含|涵蓋|涵盖|分為|分为|分別為|分别为|含|"
    r"including|includes|comprising|comprises)\s*(?P<body>[^。；;.!?]+)",
    re.IGNORECASE,
)
_TRAILING_COUNT = re.compile(
    r"(?:等|共)?[一二三四五六七八九十百0-9]+(?:類|类|種|种|款|個|个)?"
    r"(?:產品|产品|設備|设备|系統|系统|平台)?$"
)
_ENCLOSED_MARK = re.compile(
    r"(?:包括|包含|涵蓋|涵盖)(?P<body>[^。；;.!?]{1,80}?)(?:在内的|在內的)", re.IGNORECASE)
_MEMBER_SPLIT = re.compile(r"[、,，;；]|以及|及|和|與|与|\band\b", re.IGNORECASE)
_MEMBER_TOKEN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9&./+-]{0,23}$|^[\u3400-\u9fff]{2,12}$")
_SENTENCE = re.compile(r"[。！？；;!?]|(?<=\.)\s+")


@dataclass(frozen=True)
class ProductDeictic:
    span: tuple[int, int]
    text: str
    head: str
    collective: bool
    family: bool = False


@dataclass(frozen=True)
class ProductDeclaration:
    span: tuple[int, int]
    family: str
    head: str
    collective: bool
    members: tuple[tuple[int, int], ...] = ()
    attribution: str = "issuer"


def head_class(head: str) -> str:
    lowered = head.casefold()
    if head in _FAMILY_MARKERS:
        return _FAMILY_MARKERS[head]
    return _HEAD_CLASS_BY_TOKEN.get(head, _HEAD_CLASS_BY_TOKEN.get(lowered, "product"))


def supports_head(head: str) -> bool:
    """True when a deictic head can be resolved by a recognised declaration."""
    return head in _FAMILY_MARKERS or head.casefold() in {
        token.casefold() for token in _SUFFIX_HEADS}


def _proper_name(name: str, head: str) -> bool:
    """A declaration names one product; generic prose cannot donate one."""
    stripped = _ISSUER_PREFIX.sub("", name.strip()).strip()
    if not stripped:
        return False
    if stripped.casefold() in _GENERIC_CJK or stripped.casefold() in _GENERIC_LATIN:
        return False
    if re.fullmatch(r"[\u3400-\u9fff]+", stripped):
        if re.fullmatch(r"[一二三四五六七八九十百千萬万0-9]+[類类種种款個个]?", stripped):
            return False
        if len(stripped) < 2 or any(part in stripped for part in _CJK_PARTICLES):
            return False
        if any(part in stripped for part in _CJK_DESCRIPTOR):
            return False
        # A name cannot contain a product head ("前道集成电路设备" is a
        # description of devices, not the name of a device).
        return not any(token in stripped for token in _SUFFIX_HEADS)
    tokens = [token for token in stripped.split() if token]
    if not tokens or tokens[0].casefold() in _GENERIC_LATIN:
        return False
    if any(token.casefold() in _GENERIC_LATIN for token in tokens):
        return False
    first = tokens[0]
    if not (any(character.isupper() for character in first)
            or (first[:1].isdigit() and any(character.isalpha() for character in first))):
        return False
    return True


def _latin_precedes(text: str, position: int) -> bool:
    """True when a capitalised Latin token ends right before this position."""
    prefix = text[max(0, position - 64):position].rstrip()
    match = re.search(r"[A-Za-z0-9][A-Za-z0-9&./+-]*$", prefix)
    if match is None:
        return False
    token = match.group()
    return (any(character.isupper() for character in token)
            or (token[:1].isdigit() and any(character.isalpha() for character in token)))


def _latin_precedes(text: str, position: int) -> bool:
    """True when a capitalised Latin token ends right before this position."""
    prefix = text[max(0, position - 64):position].rstrip()
    match = re.search(r"[A-Za-z0-9][A-Za-z0-9&./+-]*$", prefix)
    if match is None:
        return False
    token = match.group()
    return (any(character.isupper() for character in token)
            or (token[:1].isdigit() and any(character.isalpha() for character in token)))


def _name_before(prefix: str) -> tuple[str, int]:
    """The proper name immediately before a head, without swallowing prose."""
    stripped = prefix.rstrip()
    if not stripped:
        return "", 0
    latin_match = re.search(
        r"[A-Za-z0-9][A-Za-z0-9&./+-]*(?:\s+[A-Za-z0-9][A-Za-z0-9&./+-]*){0,3}$", stripped)
    cjk = _CJK_TAIL.search(stripped)
    if cjk is not None and cjk.group() in _FAMILY_MARKERS:
        # "X系列": the Latin token is glued to the CJK family marker.
        before = stripped[:cjk.start()]
        glued = re.search(
            r"[A-Za-z0-9][A-Za-z0-9&./+-]*(?:\s+[A-Za-z0-9][A-Za-z0-9&./+-]*){0,3}$", before)
        if glued is not None:
            return glued.group() + cjk.group(), glued.start()
    candidates: list[tuple[int, str]] = []
    if latin_match is not None:
        tokens = latin_match.group().split()
        while tokens and (tokens[0].casefold() in _GENERIC_LATIN
                          or not (any(character.isupper() for character in tokens[0])
                                  or (tokens[0][:1].isdigit()
                                      and any(character.isalpha() for character in tokens[0])))):
            tokens.pop(0)
        if tokens:
            name = " ".join(tokens)
            candidates.append((stripped.rfind(name), name))
    if cjk is not None:
        name, start = cjk.group(), cjk.start()
        changed = True
        while changed:
            changed = False
            for prefix in _CJK_STRIP:
                if name.startswith(prefix) and len(name) - len(prefix) >= 2:
                    name, start = name[len(prefix):], start + len(prefix)
                    changed = True
                    break
        candidates.append((start, name))
    if not candidates:
        return "", 0
    start, name = max(candidates, key=lambda item: item[0])
    return name, start


def _third_party_actor(prefix: str) -> bool:
    third = p.THIRD_PARTY.search(prefix)
    if third is None:
        return False
    issuer = p.ISSUER_WORD.search(prefix[:third.start()])
    if issuer is None:
        return True
    between = prefix[issuer.end():third.start()].strip()
    # Only a possessive modifier ("公司的客户") keeps the third party as actor.
    return not between or between in {"的"}


def is_generic_reference(text: str, span: tuple[int, int]) -> bool:
    """Generic 'products or services' prose is not a product-family dependency."""
    start, end = max(0, span[0] - 48), min(len(text), span[1] + 24)
    return bool(_GENERIC_REFERENCE.search(text[start:end]))


def _family(name: str, head: str) -> str:
    name = _LEADING_ARTICLE.sub("", name.strip())
    normalized = re.sub(r"\s+", "", name).casefold()
    return f"{normalized}|{head_class(head)}"


_LEADING_ARTICLE = re.compile(r"^(?:the|a|an|its|their|our)\s+", re.IGNORECASE)


def find_product_deictic(text: str) -> tuple[ProductDeictic, ...]:
    """Return product-deictic spans in source order; company/pronoun hits skip."""
    found: list[ProductDeictic] = []
    taken: list[tuple[int, int]] = []
    for match in sorted((*_DEICTIC_CN.finditer(text), *_DEICTIC_EN.finditer(text)),
                        key=lambda item: item.start()):
        if any(match.start() < end and start < match.end() for start, end in taken):
            continue
        surface = match.group()
        head = next((token for token in
                     sorted((*_FAMILY_MARKERS, *_DEICTIC_HEADS), key=len, reverse=True)
                     if token in surface), "产品")
        plural = bool(_PLURAL.match(surface))
        family = plural or bool(_FAMILY_MARK.search(surface)) or bool(
            re.search(r"\b(?:these|those|such|the\s+above)\b", surface, re.IGNORECASE))
        if not supports_head(head):
            family = False
        taken.append((match.start(), match.end()))
        found.append(ProductDeictic((match.start(), match.end()), surface, head, plural, family))
    return tuple(found)


def _sentence_bounds(text: str, position: int) -> tuple[int, int]:
    start = 0
    for match in _SENTENCE.finditer(text):
        if match.end() <= position:
            start = match.end()
        else:
            return start, match.start()
    return start, len(text)


def _members(text: str, match: re.Match[str] | None, bounds: tuple[int, int], *,
             enclosed: bool = False) -> tuple[tuple[int, int], ...]:
    if match is None or not (bounds[0] <= match.start() < bounds[1]):
        return ()
    body_start, body_end = match.span("body")
    body = text[body_start:min(body_end, bounds[1])]
    if enclosed:
        body = re.sub(r"(?:在内的|在內的|等|的)\s*$", "", body)
    trimmed = _TRAILING_COUNT.search(body)
    if trimmed is not None and trimmed.start() > 0:
        body = body[:trimmed.start()]
    spans: list[tuple[int, int]] = []
    cursor = 0
    for part in _MEMBER_SPLIT.split(body):
        if part is None:
            continue
        index = body.find(part, cursor)
        if index < 0:
            continue
        cursor = index + len(part)
        token = part.strip()
        leading = len(part) - len(part.lstrip())
        if not _MEMBER_TOKEN.match(token):
            continue
        spans.append((body_start + index + leading, body_start + index + leading + len(token)))
    return tuple(spans) if 2 <= len(spans) <= 8 else ()


@lru_cache(maxsize=512)
def _declarations_for(text: str) -> tuple[ProductDeclaration, ...]:
    """One scan per distinct source text; predecessors repeat across targets."""
    """Return explicitly named product declarations in source order.

    A CJK appositive without a Latin name or an explicit series marker is a
    description, not a named declaration; it cannot donate an antecedent.
    Collective members are only read from the declaration's own sentence.
    """
    declared: list[ProductDeclaration] = []
    seen: set[tuple[int, int, str]] = set()
    for match in _HEAD_ONLY.finditer(text):
        head = match.group()
        # Bounded look-behind: a whole-document prefix costs O(document) per
        # head and turns a long filing into minutes of repeated regex work.
        # Widen the window when the name touches its edge, and defer instead of
        # accepting a truncated name when even the widest window clips it.
        name, start = "", 0
        for width in (64, 256, 1024, 4096):
            window_start = max(0, match.start() - width)
            candidate, offset = _name_before(text[window_start:match.start()])
            if not candidate:
                break
            absolute = window_start + offset
            if window_start > 0 and absolute > 0 and _latin_precedes(text, absolute):
                # The visible prefix is a suffix of a longer Latin name; widen.
                continue
            name, start = candidate, absolute
            break
        if not name:
            continue
        series_in_name = _FAMILY_SUFFIX.search(name)
        if series_in_name and head not in _FAMILY_MARKERS:
            # "小米系列产品": the series marker belongs to the head, not the name.
            head = series_in_name.group()
            name = name[:series_in_name.start()]
            end = start + len(name) + len(head)
        else:
            end = match.end()
        if not _proper_name(name, head):
            continue
        bounds = _sentence_bounds(text, start)
        marker = _COLLECTIVE_MARK.search(text, end, bounds[1])
        collective = _members(text, marker, bounds)
        if not collective:
            # "包括 A、B 在内的 X 系列": the enumeration precedes its name.
            enclosed = _ENCLOSED_MARK.search(text, bounds[0], start)
            if enclosed is not None and enclosed.end() <= start:
                collective = _members(text, enclosed, bounds)
        prefix = text[bounds[0]:start]
        attribution = "issuer"
        if _third_party_actor(prefix):
            # A customer/supplier sentence cannot donate the issuer's product.
            attribution = "quoted_related_party"
        family = _family(name, head)
        key = (start, end, family)
        if key in seen:
            continue
        seen.add(key)
        declared.append(ProductDeclaration((start, end), family,
                                           head_class(head), bool(collective), collective,
                                           attribution))
    return tuple(declared)


def find_product_declarations(text: str) -> tuple[ProductDeclaration, ...]:
    """Public, identity-cached view of the declarations in one source text."""
    return _declarations_for(text)
