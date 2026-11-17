"""Observe local scope loss in assertions with an issuer and a named quantity."""

from collections.abc import Sequence
from dataclasses import dataclass
import re

from company_wiki.document_model.text_matching import matching_reading_text


_SENTENCE_END = re.compile(r"([。！？!?；;]|(?<!\d)\.|\.(?!\d))")
_CLAUSE_END = re.compile(r"(?<!\d)[,，]|[,，](?!\d)")
_ZH_TIME = r"(?:目前|现阶段|当前|报告期内|本期)"
_ZH_ISSUER = r"(?:本?公司|本?集团|我们|我司)"
_ZH_SCOPE = re.compile(
    rf"^(?:{_ZH_TIME}\s*)?(?P<issuer>{_ZH_ISSUER})?\s*"
    r"在\s*(?P<domain>[^,，。！？!?;；]+?)(?:领域|板块|业务中)(?P<body>.*)$"
)
_EN_SCOPE_TERM = (r"(?:in|within)\s+(?:the\s+|our\s+)?"
                  r"(?P<domain>[a-z][a-z0-9& /-]+?)\s+(?:business|segment|division|field)\b")
_EN_SCOPE = re.compile(rf"^{_EN_SCOPE_TERM}(?P<body>.*)$", re.I)
_EN_TRAILING_SCOPE = re.compile(rf"\s+{_EN_SCOPE_TERM}$", re.I)
_SUBJECT = re.compile(rf"^(?P<period>{_ZH_TIME}\s*)?"
                      rf"(?P<issuer>{_ZH_ISSUER}|(?:we|(?:our|the) (?:company|group))\b)\s*", re.I)
_QUESTION = re.compile(r"^(?:请问|问\s*[:：]|是否|(?:can we|could you|what|whether)\b)", re.I)
_LINK = re.compile(r"^(?:(?:并且|同时|亦|并|且)\s*|(?:and|also|then)\b\s+)*", re.I)
_ACTION = re.compile(
    r"^(?P<qualifiers>(?:(?:已经|已|现|迄今|累计|一直|未能|尚未|并未|没有|并非|不再|未|不|"
    r"将|拟|正|仍|计划|预计)\s*)*)"
    r"(?P<action>开发|研发|推出|拓展|覆盖|交付|生产|销售|获得|完成)|"
    r"^(?P<en_qualifiers>(?:(?:has|have|had|already|now|never|not|will|did|do|does|"
    r"to date|plans? to|expects? to)\s+)*)"
    r"(?P<en_action>(?:develop|launch|expand|cover|deliver|produc|sell|obtain|complet|serv)[a-z]*|sold)\b",
    re.I,
)
_NEGATIVE = re.compile(r"未|不|没有|\b(?:never|not)\b", re.I)
_FUTURE = re.compile(r"将|拟|计划|预计|\b(?:will|plans?|expects?)\b", re.I)
_MEASURE_LINK = re.compile(r"\s*(?:了|过)?\s*")
_MEASURE = re.compile(
    r"(?:(?P<op>不少于|不低于|超过?|多于|至少|不足|少于|约|more than|over|at least|"
    r"fewer than|less than|under|about|around|approximately)\s*)?"
    r"(?P<value>\d+(?:,\d{3})*(?:\.\d+)?)\s*"
    r"(?P<object>[种项个件台套座条家款]\s*[\u3400-\u9fff]+|[a-z][a-z-]{2,}\b)",
    re.I,
)
_OPERATORS = {
    "超": ">", "超过": ">", "多于": ">", "more than": ">", "over": ">",
    "至少": ">=", "不少于": ">=", "不低于": ">=", "at least": ">=",
    "不足": "<", "少于": "<", "fewer than": "<", "less than": "<", "under": "<",
    "约": "~", "about": "~", "around": "~", "approximately": "~",
}
_CJK = re.compile(r"[\u3400-\u9fff]")


def _issuer_key(label: str) -> str:
    if label.endswith("公司") or label.casefold().endswith("company") or label == "我司":
        return "company"
    if label.endswith("集团") or label.casefold().endswith("group"):
        return "group"
    return "speaker"


def _measure_key(measure: re.Match[str]) -> tuple[str, str, str]:
    return (_OPERATORS.get((measure["op"] or "").casefold(), "="),
            measure["value"].replace(",", ""), "".join(measure["object"].casefold().split()))


@dataclass(frozen=True)
class _Clause:
    domain: str | None
    assertion: tuple[str, str, bool, bool, str, str, str] | None
    surface: str


def _clauses(text: str) -> tuple[_Clause, ...]:
    """Bind a scope to an issuer action and subjectless continuations locally."""
    clauses = []
    sentences = _SENTENCE_END.split(matching_reading_text(text))
    for sentence, ending in zip(sentences[::2], [*sentences[1::2], ""]):
        sentence = sentence.strip()
        if not sentence:
            continue
        if ending in {"?", "？"} or _QUESTION.search(sentence):
            clauses.append(_Clause(None, None, sentence.casefold() + ending))
            continue
        domain: str | None = None
        issuer: str | None = None
        header_only = False
        for part in filter(None, (part.strip() for part in _CLAUSE_END.split(sentence))):
            explicit = _ZH_SCOPE.fullmatch(part) or _EN_SCOPE.fullmatch(part)
            body = explicit["body"].strip() if explicit else part
            trailing = _EN_TRAILING_SCOPE.search(body)
            if trailing:
                body = body[:trailing.start()]
            subject = _SUBJECT.match(body)
            if subject:
                body = (subject["period"] or "") + body[subject.end():]
            body = _LINK.sub("", body, count=1)
            action = _ACTION.match(body)
            if explicit:
                domain = " ".join(explicit["domain"].casefold().split())
                label = subject["issuer"] if subject else explicit.groupdict().get("issuer")
                if label:
                    issuer = _issuer_key(label)
                if body and not action:
                    issuer = None
            elif subject:
                issuer = _issuer_key(subject["issuer"]) if action else None
                if not header_only:
                    domain = None
            elif not action:
                issuer = None
                domain = None
            header_only = bool(explicit and not body)
            measure = _MEASURE.search(body, action.end()) if issuer and action else None
            assertion = None
            if issuer and action and measure and _MEASURE_LINK.fullmatch(body[action.end():measure.start()]):
                qualifier = action["qualifiers"] or action["en_qualifiers"] or ""
                predicate = (action["action"] or action["en_action"]).casefold()
                assertion = (issuer, predicate, bool(_NEGATIVE.search(qualifier)),
                             bool(_FUTURE.search(qualifier)), *_measure_key(measure))
            surface = _MEASURE.sub(lambda m: " ".join(_measure_key(m)), body.casefold())
            surface = ("" if _CJK.search(body) else " ").join(surface.split())
            local_domain = " ".join(trailing["domain"].casefold().split()) if trailing else domain
            clauses.append(_Clause(local_domain, assertion, surface or part.casefold()))
    return tuple(clauses)


@dataclass(frozen=True)
class BusinessScopeAssessment:
    source_indices: tuple[int, ...]
    exact_quote_recovers_scope: bool


def assess_business_scope(sources: Sequence[str], claim: str) -> BusinessScopeAssessment:
    """Return local observations, with a separate proof for a verbatim fallback.

    The same action and measure under competing source domains are ambiguous.
    Exact-quote recovery additionally requires an omitted domain and a complete
    surface alignment. A different explicit domain or extra claims can only
    produce a diagnostic.
    """
    originals = [_clauses(source) for source in sources]
    targets = _clauses(claim)
    affected: set[int] = set()
    quote_recovers_scope = False
    for position, target in enumerate(targets):
        if target.assertion is None:
            continue
        matches = [(index, ordinal, clause) for index, original in enumerate(originals)
                   for ordinal, clause in enumerate(original) if clause.assertion == target.assertion]
        domains = {clause.domain for _, _, clause in matches}
        if len(domains) != 1 or None in domains or target.domain in domains:
            continue
        affected.update(index for index, _, _ in matches)
        if len(originals) == len(matches) == 1 and all(clause.domain is None for clause in targets):
            start = matches[0][1] - position
            if start >= 0:
                aligned = originals[0][start:start + len(targets)]
                quote_recovers_scope |= (tuple(clause.surface for clause in aligned)
                                        == tuple(clause.surface for clause in targets))
    return BusinessScopeAssessment(tuple(sorted(affected)), quote_recovers_scope)


def business_scope_sha256() -> str:
    from company_wiki.implementation_identity import code_sha256

    return code_sha256(__file__)


__all__ = ["BusinessScopeAssessment", "assess_business_scope", "business_scope_sha256"]
