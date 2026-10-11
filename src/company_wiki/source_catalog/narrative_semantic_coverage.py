"""Bounded whole-context signatures for conservative soft redundancy ranking.

This is an overlap hint, never logical claim equivalence or candidate removal.
Protected sentences retain their subjects, quantities and predicate polarity;
we do not compare numeric bags or infer cross-sentence subject substitutions.
"""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
import re
import unicodedata

from .narrative_stage_assertions import stage_assertions

_MAX_CHARS = 8192
_MAX_TOKENS = 512
_CHUNKS = re.compile(r"[a-zA-Z][a-zA-Z0-9-]*|[\u4e00-\u9fff]+|\d+(?:\.\d+)?(?:%|％)?")
_QUANTITY = re.compile(r"\d|[零〇一二两三四五六七八九十百千万亿]+"
    r"(?:个|台|套|腔|英寸|周|月|年|米|亩|元|%|％)")
_SENTENCE = re.compile(r"[。！？!?;；]|\.(?:\s|$)")
_SUBJECT = re.compile(r"设备|产品|系统|平台|方案|服务|系列|型号|机型|公司|项目|客户|"
    r"业务|市场|行业|供应|订单|收入|营收|利润|产能|良率|反应腔|晶圆|"
    r"\b(?:products?|equipment|systems?|platforms?|services?|solutions?|company|"
    r"projects?|customers?|business|market|industry|supply|orders?|revenue|sales|"
    r"capacity|yield|reactors?|chambers?|wafers?)\b", re.I)
_STAGE_HINT = re.compile(r"验证|认证|订单|交付|出货|发货|投产|计划|预计|尚未|"
    r"\b(?:validation|qualification|orders?|shipments?|deliveries|shipped|delivered|"
    r"planned|plans?|expected|production)\b", re.I)


@dataclass(frozen=True)
class CoverageSignature:
    """Pure metadata built once from the entire group in native source order.

    ``complete=False`` means the finite hint cannot safely penalize another
    group. The hard evidence budget is independent of this completeness flag.
    """

    tokens: tuple[str, ...]
    protected_sentences: tuple[str, ...]
    stage_signals: tuple[tuple[str, str, bool, str], ...]
    complete: bool


def _normalize(text: str) -> str:
    # Comparison only: emitted raw text remains byte-for-byte unchanged.
    text = unicodedata.normalize("NFKC", text).casefold()
    text = re.sub(r"\s+", " ", text)
    # Native PDF line breaks/spacing inside Chinese text and quantities are
    # formatting, but English word boundaries must remain word boundaries.
    return re.sub(r"(?<=[\u4e00-\u9fff])\s+|\s+(?=[\u4e00-\u9fff])", "", text).strip()


def _all_tokens(text: str) -> set[str]:
    tokens: set[str] = set()
    english: list[str] = []
    for chunk in _CHUNKS.findall(text):
        if chunk[0].isdigit():
            tokens.add("number:" + chunk)
        elif chunk.isascii():
            english.append(chunk.casefold())
        else:
            tokens.update("zh:" + chunk[i:i+3] for i in range(max(0, len(chunk)-2)))
    tokens.update("en:" + " ".join(english[i:i+2]) for i in range(max(0, len(english)-1)))
    return tokens


def coverage_tokens(text: str) -> tuple[str, ...]:
    """Public bounded tokenizer; standalone numbers are never silently erased."""
    return tuple(sorted(_all_tokens(_normalize(text[:_MAX_CHARS])))[:_MAX_TOKENS])


def coverage_signature(text: str) -> CoverageSignature:
    """Build a finite whole-group hint, protecting verbatim factual context.

    A changed protected sentence is treated as novel even if it may paraphrase
    an existing fact. This conservative ranking does not assert equivalence.
    Missing subject context, missing actor proofs or truncation disable the
    penalty entirely. No files, payloads, model, issuer or page rules are read.
    """
    normalized = _normalize(text[:_MAX_CHARS])
    tokens = _all_tokens(normalized)
    assertions = stage_assertions(normalized)
    protected: list[str] = []
    bound = True
    for sentence in _SENTENCE.split(normalized):
        sentence = sentence.strip()
        if not sentence:
            continue
        if _QUANTITY.search(sentence) or _STAGE_HINT.search(sentence) or _SUBJECT.search(sentence):
            protected.append(sentence)
            if not _SUBJECT.search(sentence):
                bound = False
    signals = tuple((proof.stage, _normalize(proof.predicate), proof.realized, proof.diagnostic)
        for proof in assertions)
    complete = (len(text) <= _MAX_CHARS and len(tokens) <= _MAX_TOKENS
        and len(protected) <= _MAX_TOKENS and len(signals) <= _MAX_TOKENS and bound
        and not any(proof.diagnostic == "missing_business_actor" for proof in assertions))
    return CoverageSignature(tuple(sorted(tokens)[:_MAX_TOKENS]),
        tuple(protected[:_MAX_TOKENS]), signals[:_MAX_TOKENS], complete)


def group_coverage_signature(parts: Iterable[str]) -> CoverageSignature:
    """Bound temporary concatenation; parts must already be in native order."""
    text = ""
    for part in parts:
        if not part:
            continue
        if (text and text[-1].isascii() and text[-1].isalnum()
            and part[0].isascii() and part[0].isalnum()):
            text += " "
        text += part[:max(0, _MAX_CHARS + 1 - len(text))]
        if len(text) > _MAX_CHARS:
            break
    return coverage_signature(text)


def softly_repeats(current: CoverageSignature | None, previous: CoverageSignature | None) -> bool:
    """Only near-complete symmetric overlap with unchanged facts gets a hint."""
    if current is None or previous is None or not current.complete or not previous.complete:
        return False
    if (current.protected_sentences != previous.protected_sentences
        or current.stage_signals != previous.stage_signals):
        return False
    left, right = frozenset(current.tokens), frozenset(previous.tokens)
    if min(len(left), len(right)) < 12:
        return False
    overlap = len(left & right)
    return 100 * overlap >= 85 * len(left) and 100 * overlap >= 85 * len(right)
