"""Named operating scope attached to a recognition rule, not a policy noun.

The reading policy supplies normalized native text. It describes a source use
only: no amounts,
issuer identity, timing conclusion or support/context edge is manufactured.
"""
from __future__ import annotations

import re

from .narrative_source_purpose import revenue_recognition_mechanism
from .narrative_predicate_state import split_predicate_assertions


READING_RECOGNITION_SCOPE_SCAN_PASSES = 8
_SENTENCES = re.compile(r"[。！？!?]|(?<=\.)\s+")
_CONDITIONS = re.compile(r"[；;]")
_CN_OWNER = r"(?:本集团|本公司|本企业|我们)"
_CN_CONTINUATION = re.compile(
    rf"^\s*(?:或(?:者)?\s*(?:(?:{_CN_OWNER}(?:在)?)?履约|"
    rf"客户(?:(?:能够|能|可以)?控制(?:履约|在建)|在(?:{_CN_OWNER})?履约))|"
    rf"(?:且|并且)\s*(?:{_CN_OWNER})?(?:在[^,，;；]{{0,20}}合同期间(?:内)?)?"
    r"有权[^,，;；]{0,80}(?:收取|收款|收回|获得|取得))")
_CN_RULE_REFERENCE = re.compile(
    r"^\s*(?:因此|因而|所以|故)?(?:上述|该等|该|这些)(?:业务|服务)(?:均|皆)?(?:属于|为)")
_CN_SCOPE = re.compile(
    r"(?:本集团|本公司|本企业|我们)(?:的)?"
    r"(?P<scope>[\u3400-\u9fffA-Za-z0-9（）()·&/\-、\s]{1,120}?"
    r"(?:业务|服务|分部))\s*"
    r"(?=(?:的)?客户在[^。；;!?]{0,30}履约[^。；;!?]{0,30}(?:取得|消耗)|"
    r"属于(?:在)?某一|为(?:在)?某一)")
_CN_MEMBER = re.compile(r"[、,，]|以及|和|及|与")
_CN_GENERIC_PREFIX = re.compile(r"^(?:(?:的|部分|其他|某些|相关|上述|这些|全部|所有|各类)\s*)+")
_CN_GENERIC_NAME = re.compile(
    r"(?:业务|服务|分部|产品|客户|合同|经营|运营|一般|主要|其他|主营|核心)*")
_CN_KIND = re.compile(r"(?:业务|服务|分部)$")
_EN_SCOPE = re.compile(
    r"\b(?:our|(?:the|this)\s+(?:group|company)['’]s)\s+"
    r"(?P<scope>(?:[a-z][a-z0-9&()/\-]*\s+){0,10}"
    r"(?:services?|business(?:es)?|products?|segments?))\s*"
    r"(?=(?:(?:are|is|represent|represents|constitute|constitutes)\s+"
    r"(?:(?:our|the)\s+)?)?performance obligations?\b)", re.I)
_EN_GENERIC_WORDS = frozenset({
    "a", "an", "the", "all", "and", "or", "certain", "some", "other", "various",
    "these", "those", "such", "related", "general", "main", "principal",
    "business", "businesses", "service", "services", "product", "products",
    "segment", "segments", "customer", "customers", "contract", "contracts",
    "operating", "operations", "core",
})


def _named_cn_scope(text: str) -> bool:
    for match in _CN_SCOPE.finditer(text):
        # The owner is the anchored company. A second possessive changes the
        # owner (e.g. the company's customer's service), not the service name.
        if "的" in match["scope"]:
            continue
        for member in _CN_MEMBER.split(match["scope"]):
            name = _CN_KIND.sub("", _CN_GENERIC_PREFIX.sub("", member.strip())).strip()
            if name and not _CN_GENERIC_NAME.fullmatch(name):
                return True
    return False


def named_recognition_scope(text: str) -> bool:
    """Require a named owned business grammatically attached to the rule.

    A separate business sentence or a supplier's named service cannot lend
    scope to a generic rule. Generic subsets (some/other businesses) do not
    establish which operating line uses a mechanism.
    """
    for sentence in _SENTENCES.split(text):
        pending_owned_condition = False
        # Each disjoint condition is scanned once. Never rescan the remaining
        # paragraph for every scope match: that would cost quadratic work.
        for condition in _CONDITIONS.split(sentence):
            for assertion in split_predicate_assertions(condition):
                continuation = bool(pending_owned_condition and _CN_CONTINUATION.match(assertion))
                conclusion = bool(pending_owned_condition and _CN_RULE_REFERENCE.match(assertion))
                cn_named = _named_cn_scope(assertion)
                en_named = any(
                    any(word.lower() not in _EN_GENERIC_WORDS for word in match["scope"].split())
                    for match in _EN_SCOPE.finditer(assertion)
                )
                if (cn_named or en_named or conclusion) and revenue_recognition_mechanism(assertion):
                    return True
                # New assertions reset ownership. Only customer-performance,
                # owned contract/payment conditions and explicit back-references
                # preserve the pending business; punctuation alone never does.
                pending_owned_condition = cn_named or continuation or conclusion
    return False
