"""Pure commercial-stage assertions shared by all current selector paths.

A candidate proof has an actor, predicate and object/complement. Negation and
modality bind within its clause; prior or future attributes do not change a
separate assertion. This classifies disclosed progress, not revenue recognition
or completion of every other stage. No original bytes are rewritten.
"""
from __future__ import annotations

from dataclasses import dataclass
import re

_OBJECT = re.compile(r"设备|产品|系统|平台|方案|服务|系列|型号|机型|"
    r"\b(?:products?|equipment|systems?|platforms?|services?|solutions?)\b", re.I)
_SENTENCE = re.compile(r"[。！？!?;；\n]|\.(?:\s|$)")
_CLAUSE = re.compile(r"[，,]|但是|但(?!凡)|然而|并且|且|"
    r"并(?=(?:已|正在|获得|取得|未|没有))|\b(?:but|and)\b", re.I)
_PREDICATE = re.compile(
    r"(?P<validation>(?:通过|完成)(?:了)?[^。；，]{0,12}?(?:验证|认证)|"
    r"(?:客户|现场)?验证(?:已|正在|顺利|持续)?(?:完成|通过|推进|进行)|"
    r"(?:正在|持续)[^。；，]{0,8}?(?:客户|现场)验证|"
    r"\b(?:completed|passed)\s+(?:(?:on[- ]site|customer|the|its|all)\s+){0,3}"
    r"(?:validation|qualification)\b|"
    r"\b(?:validated|qualified)\s+by\s+customers?\b|"
    r"\bcustomer\s+(?:qualification|validation)\s+"
    r"(?:(?:is|has been)\s+)?(?:progressing|advancing|completed)\b)|"
    r"(?P<orders>(?:获得|取得|获)[^。；，]{0,15}?(?:重复(?:性)?|追加|复购)(?:量产)?订单|"
    r"\b(?:secured|received|obtained)\s+(?:customer\s+)?repeat\s+orders?\b)|"
    r"(?P<validation_entry>进入[^。；，]{0,12}?客户(?:端)?(?:量产|试产)?验证阶段)|"
    r"(?P<permit>生产许可|充装许可|产品资质)|"
    r"(?P<certification>(?:获得|取得)(?:了)?[^。；，]{0,12}?(?:客户|产品)(?:的)?认证|"
    r"\b(?:obtained|received|secured)\s+customer\s+(?:qualification|certification)\b)|"
    r"(?P<production>量产|\b(?:achieved|started|commenced)\s+mass\s+production\b)|"
    r"(?P<shipment>交付|出货|发货|付运|发运|\bcumulative\s+(?:shipments?|deliveries)\b|"
    r"\b(?:shipped|delivered|dispatched)\b)", re.I)
_NEGATION = re.compile(r"不是|并非|并未|尚未|未曾|未能|没有|没能|并不|不曾|不再|无法|未|没|不|"
    r"\b(?:not|never|no longer|cannot|can't|didn't|hasn't|haven't|wasn't|weren't)\b", re.I)
_MODAL = re.compile(r"尚待|预计|预期|计划|拟|将|若|如果|一旦|待(?:到|其)?|"
    r"\b(?:will|would|may|might|could|expected|planned|intends?|once|when|upon|after|if|unless)\b", re.I)
_CONDITIONAL = re.compile(r"^\s*(?:若|如果|一旦|当|待|但凡|if\b|once\b|when\b|upon\b|after\b|unless\b)", re.I)
_REFERENCE = re.compile(r"^\s*(?:(?:同时|也|目前|现在|现阶段)\s*){0,2}"
    r"(?:(?:并|且|陆续|先后)\s*)*(?:已|已经|正在|持续|现场验证|客户验证|获得|取得|获|未|没有)|"
    r"^\s*(?:(?:it|this (?:product|equipment|system))\s+)?"
    r"(?:has|have|had|was|were)\b", re.I)
_PLAN_ADVERB = re.compile(r"(?:根据|按照|按)[^，。；]{0,16}?(?:计划|规划|安排)")
_ATTRIBUTE_NEGATION = re.compile(r"(?:未发现|没有|不存在)(?:任何)?(?:缺陷|故障|问题)")
_NONPRODUCT = re.compile(r"保证金|款项|货款|现金|资金|付款|资料|文件|合同|所有权|"
    r"\b(?:payments?|deposits?|funds|documents?|contracts?|ownership)\b", re.I)
_REALIZED_PRODUCTION = re.compile(r"已经|已|实现|达到|\b(?:achieved|started|commenced)\b", re.I)
_FOREIGN_ACTOR = re.compile(r"(?:竞争对手|供应商|客户)的[^，。；]{0,12}(?:产品|设备)|"
                            r"\b(?:competitor|supplier|customer)'s\s+(?:product|equipment)\b", re.I)
_PRODUCTION_PREPARATION = re.compile(r"^\s*(?:验证|认证|测试|准备|要求|条件|许可)")
_REALIZED_SHIPMENT = re.compile(r"已经|已|首次|首批|首台|累计|\b(?:has|have|had|was|were)\b", re.I)
_COMPLEMENT_GATE = re.compile(r"^\s*(?:前|后|时|的?前提|方可)")


@dataclass(frozen=True)
class StageAssertion:
    stage: str
    predicate: str
    realized: bool
    diagnostic: str


def _shipment_is_nonproduct(prefix: str, suffix: str) -> bool:
    # Quantities/currency can sit before the transferred noun. Compare object
    # order, rather than matching only the immediately adjacent next character.
    nonproduct = _NONPRODUCT.search(suffix)
    business = _OBJECT.search(suffix)
    if nonproduct and (business is None or nonproduct.start() < business.start()):
        return True
    transfer = re.search(r"(?:将|把)([^。；，]{0,45})$", prefix)
    return bool(transfer and _NONPRODUCT.search(transfer.group(1)))


def stage_assertions(text: str) -> tuple[StageAssertion, ...]:
    """Return finite proofs and diagnostics, bounded by native sentence/actor."""
    results = []
    for sentence in _SENTENCE.split(text):
        conditional_sentence = bool(_CONDITIONAL.search(sentence))
        known_subject = False
        for clause in _CLAUSE.split(sentence):
            objects = tuple(_OBJECT.finditer(clause))
            predicates = tuple(_PREDICATE.finditer(clause))
            last_predicate_end = 0
            for proof in predicates:
                prefix = clause[:proof.start()]
                before = [obj for obj in objects if obj.end() <= proof.start()]
                after = [obj for obj in objects if obj.start() >= proof.end()]
                direct_subject = bool(before)
                # English active "we shipped equipment" has the object after
                # its action; an amount/deposit cannot masquerade as equipment.
                active = bool(after and re.search(r"\b(?:we|the company)\b", prefix, re.I))
                reference = known_subject and bool(_REFERENCE.search(clause))
                cumulative = proof.group().lower().startswith("cumulative")
                actor = direct_subject or active or reference or bool(cumulative and after)
                scope_start = max(last_predicate_end, before[-1].end() if before else 0)
                scope = clause[scope_start:proof.start()]
                scope = _PLAN_ADVERB.sub("", scope)
                scope = _ATTRIBUTE_NEGATION.sub("", scope)
                # Completed active 已将 is an aspect marker, not future 将.
                scope = re.sub(r"(?:已经|已)将", "已", scope)
                diagnostic = "observed"
                if not actor:
                    diagnostic = "missing_business_actor"
                elif conditional_sentence or _CONDITIONAL.search(clause):
                    diagnostic = "conditional"
                elif _NEGATION.search(scope):
                    diagnostic = "negated"
                elif _MODAL.search(scope):
                    diagnostic = "planned_or_conditional"
                elif _COMPLEMENT_GATE.search(clause[proof.end():]):
                    diagnostic = "prerequisite_or_preparation"
                elif proof.lastgroup == "validation_entry" and not re.search(r"已经|已", prefix):
                    diagnostic = "validation_entry_without_actual_aspect"
                elif proof.lastgroup == "permit" and not re.search(r"已经|已|取得|获得|获批", prefix):
                    diagnostic = "permit_without_actual_aspect"
                elif proof.lastgroup in {"production", "certification", "permit", "validation_entry"} and (
                    _FOREIGN_ACTOR.search(clause) or _NONPRODUCT.search(scope)):
                    diagnostic = "foreign_actor_or_nonproduct"
                elif proof.lastgroup == "production" and (
                    _PRODUCTION_PREPARATION.search(clause[proof.end():])
                    or re.search(r"是否|\bwhether\b", scope, re.I)):
                    diagnostic = "prerequisite_or_unresolved_stage"
                elif proof.lastgroup == "production" and not _REALIZED_PRODUCTION.search(prefix+proof.group()):
                    diagnostic = "production_without_actual_aspect"
                elif proof.lastgroup == "shipment":
                    if _shipment_is_nonproduct(prefix, clause[proof.end():]):
                        diagnostic = "nonproduct_transfer"
                    elif not (cumulative or _REALIZED_SHIPMENT.search(prefix)
                        or (proof.group().isascii() and active)):
                        diagnostic = "shipment_without_actual_aspect"
                results.append(StageAssertion(proof.lastgroup or "unknown", proof.group(),
                                              diagnostic == "observed", diagnostic))
                last_predicate_end = proof.end()
            known_subject = known_subject or bool(objects)
    return tuple(results)


def commercialization_milestone(text: str) -> bool:
    return any(assertion.realized for assertion in stage_assertions(text))
