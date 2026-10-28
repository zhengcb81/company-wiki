"""Shared bounded source assertion roles, independent of state/stage projection.

Product heads, local predicates and their argument roles prove a descriptive
assertion. Source purpose and support consume one prepared result; refs or a
recognized stage alone never manufacture an assertion.
"""
from __future__ import annotations

from dataclasses import dataclass
from bisect import bisect_left
import re

from company_wiki.document_normalization.text_matching import matching_reading_text
from company_wiki.document_normalization.table_shapes import observe_value_cells
from company_wiki.document_understanding.structure.table_purpose import unbound_numeric_row_role
from .product_reference import product_head_spans

# A new explicit actor starts an independent assertion even after a comma.
# Subordinate audit test descriptions do not manufacture a company event.
_ASSERTION_ACTOR = re.compile(
    r"[,，]\s*(?:(?:and|but)\s+)?(?=(?:公司|本公司|集团|本集团|我们|"
    r"the company\b|the group\b|our company\b|we\b))", re.I)

_DESCRIPTION_OBJECT = re.compile(r"云产品|服务器|服务|软件|平台|产品|设备|解决方案|工作负载|"
    r"\b(?:products?|services?|equipment|platforms?|software|workloads?)\b", re.I)
_MEMBERSHIP_FINANCIAL_HEAD = re.compile(
    r"成本|费用|收入|利润|资产|负债|毛利|"
    r"\b(?:costs?|expenses?|revenues?|profits?|income|assets?|liabilit\w*)\b", re.I)
_DESCRIPTION_SENTENCES = re.compile(r"[。！？；;]|(?<=[.!?])\s+")
_DESCRIPTION_PARTS = re.compile(r"(?<!\d)[,，]|[,，](?!\d)|\b(?:and|but|while|whereas)\s+(?=we\b|the company\b)", re.I)
_STATE_HEAD = re.compile(r"\b(?:projects?|plants?|factor(?:y|ies)|facilit(?:y|ies)|qualification|validation|certification)\b|项目|工厂|基地", re.I)
_EN_HEAD_TAIL = r"(?:\s+(?:coverage|scope|portfolio|range|lineup|suite|family|editions?|versions?|configurations?|launch|rollout|delivery|deployment|release)){0,3}\s+"
_EN_AUX = r"(?P<aux>(?:(?:is|are|was|were|can|may|will|would|could|has|have|had|been|be|not|also|currently|already|still|widely|further|now)\s+){0,8})"
_EN_FUNCTION = re.compile(_EN_HEAD_TAIL + _EN_AUX +
    r"(?P<verb>provid\w*|offer\w*|suppl\w*|support\w*|rout\w*|process\w*|deliver\w*|manufactur\w*|"
    r"includ\w*|compris\w*|cover\w*|serves?|uses?|produc\w*|identif\w*|utili[sz]\w*|launch\w*|releas\w*|introduc\w*|deploy\w*)"
    r"\b\s+(?P<target>[^,。;!?]{1,100})", re.I)
_EN_PASSIVE_USE = re.compile(_EN_HEAD_TAIL + _EN_AUX +
    r"(?P<verb>used|utili[sz]ed|deployed)\s+(?:by|for|to|in)\s+(?P<target>[^,。;!?]{1,100})", re.I)
_EN_DESCRIPTION = re.compile(_EN_HEAD_TAIL + _EN_AUX +
    r"(?P<verb>for|comes? in|available in|offered in)\s+(?P<target>[^,。;!?]{1,100})", re.I)
_EN_COPULA = re.compile(r"\b(?:is|are|was|were|be|been)\b",re.I)
_EN_STATE = re.compile(_EN_HEAD_TAIL + _EN_AUX +
    r"(?P<verb>(?:is|are|remains?)\s+(?:in|under)|remains?|expand\w*|enter\w*|start\w*|complet\w*|finish\w*|began|begin\w*)"
    r"\s+(?P<target>[^,。;!?]{1,100})", re.I)
_EN_PLAN = re.compile(_EN_HEAD_TAIL + r"(?:is|are|remains?)\s+(?:planned|scheduled|expected)\s+"
    r"(?:for|in|during|before|after)\s+(?P<target>[^,。;!?]{1,100})", re.I)
_STATE_TARGET = re.compile(r"\b(?:qualification|validation|certification|production|delivery|development|construction|"
    r"commercialization|pending|regions?|markets?)\b|认证|验证|生产|交付|研发|地区|市场", re.I)
_CN_HEAD_TAIL = (r"(?:的|范围|组合|系列|产品线|覆盖范围|业务|功能){0,3}\s*"
    r"(?:[A-Za-z][A-Za-z0-9.-]{0,15}(?:(?:及|和|与|、|/)[A-Za-z][A-Za-z0-9.-]{0,15}){0,5})?\s*")
_CN_AUX = r"(?P<aux>(?:已经|正在|尚未|持续|继续|计划|预计|可以|能够|主要|正式|亦|已|将|正|可|能|未){0,6})"
_CN_PROVISION_BRIDGE = r"(?:(?:由|通过|经由)[^,，。;!?]{1,35}?(?=提供|供应|交付|制造))?"
_CN_FUNCTION = re.compile(_CN_HEAD_TAIL + _CN_AUX + _CN_PROVISION_BRIDGE +
    r"(?P<verb>用于|用作|作为|支持|提供|覆盖|涵盖|包括|包含|供应|制造|设计|交付|处理|连接|面向|应用于)"
    r"(?P<target>[^,，。;!?]{1,100})")
_CN_STATE = re.compile(_CN_HEAD_TAIL + _CN_AUX +
    r"(?P<verb>进入|处于|开展|推进|进行|完成|启动|投入)?(?:客户)?(?P<target>认证|验证|试产|量产|生产|建设|投产|运行|运营|发布|上线)")
_PROVISION_EN = re.compile(r"\b(?:provid\w*|offer\w*|suppl\w*|manufactur\w*|design\w*|deliver\w*|"
    r"hir\w*|employ\w*|recruit\w*|launch\w*|releas\w*|introduc\w*|deploy\w*|acquir\w*|commission\w*|open\w*)\b", re.I)
_PROVISION_CN = re.compile(r"提供|供应|制造|设计|打造|交付|聘用|招聘|招募|收购|收購")
_PROVISION_ACTOR_EN = re.compile(
    r"\s*(?:(?i:we|(?:the|our|this)\s+(?:company|group|team|supplier|partner))|"
    r"[A-Z][A-Za-z0-9&.-]*(?:\s+[A-Z][A-Za-z0-9&.-]*){0,4})"
    r"(?:\s+(?i:already|also|now|currently|still|will|can|may|have|has|had|"
    r"continue\s+to|continues\s+to|continued\s+to)){0,8}"
    r"(?:\s+(?i:using|through|via|based\s+on)\s+[^,。;!?]{1,70})?\s*")
_PROVISION_ACTOR_CN = re.compile(
    r"\s*(?:我们|本公司|公司|本集团|集团|企业|供应商|厂商|团队)"
    r"(?:已经|正在|持续|继续|计划|预计|主要|还|已|将|正){0,6}"
    r"(?:(?:凭借|基于|通过|采用|向|为|在)[^,，。;!?]{1,70})?\s*")
_RESOURCE_OBJECT = re.compile(r"\b(?:engineers|researchers|technical staff|research staff)\b|研发人员|工程师|研究人员", re.I)
_ACTOR_PHASE = re.compile(r"^(?:本公司|公司|本集团|集团|我们|企业)[^,，。;!?]{0,32}"
    r"(?:推进|开展|进入|进行|完成)(?:客户|产品|设备)?(?:认证|验证|生产|量产)")
_ACTOR_SCOPE = re.compile(r"^(?:本公司|公司|本集团|集团|我们|企业)(?:已|正在|目前|尚未|不|未)?"
    r"(?:参与|从事|经营|涉及)(?P<target>[^,，。;!?]{1,60})")
_AGENT_DERIVATION = re.compile(r"^(?:者|人员|人員|商(?=的|使|及|和|与|为|向|$))")


def _source_clauses(value: str, *, descriptions: bool = True):
    for sentence in _DESCRIPTION_SENTENCES.split(value):
        # A rule's object can precede a comma and its measurement predicate
        # follow it. Purpose retains that assertion; descriptive proofs use
        # smaller clauses so unrelated heads cannot donate a predicate.
        for clause in (_DESCRIPTION_PARTS if descriptions else _ASSERTION_ACTOR).split(sentence):
            clause = clause.strip()
            if clause:
                yield clause


def _description_payload(value: str) -> bool:
    if not any(character.isalpha() for character in value):
        return False
    # A technical modifier cannot turn a financial noun head into an offering.
    financial = tuple(_MEMBERSHIP_FINANCIAL_HEAD.finditer(value))
    return not financial or bool(_DESCRIPTION_OBJECT.search(value, financial[-1].end()))


def _clause_description(value: str) -> bool:
    # One clause-local index supplies both head-first descriptions and
    # actor/action-first objects. Resource heads remain object-only here.
    heads = {(match.start(), match.end()): True for match in _DESCRIPTION_OBJECT.finditer(value)}
    heads.update({(start, end): True for start, end, _ in product_head_spans(value)})
    heads.update({(match.start(), match.end()): True for match in _STATE_HEAD.finditer(value)})
    for resource_head in _RESOURCE_OBJECT.finditer(value):
        heads.setdefault((resource_head.start(),resource_head.end()),False)
    ordered_heads=sorted(heads)
    for start, end in ordered_heads:
        if not heads[start,end]:
            continue
        # Only a bounded tail attached to this head is inspected. An earlier
        # noun cannot donate itself to a later clause's stage or predicate.
        tail = value[end:end + 160]
        description = _EN_DESCRIPTION.match(tail)
        if description is not None:
            # 'product for ...' and 'product offered in ...' are NP modifiers.
            # Copular predicates or finite 'comes in' form an assertion; a
            # reduced relative must not fall through as a bare function verb.
            if (_description_payload(description['target'])
                    and (description['verb'].casefold().startswith('come')
                         or _EN_COPULA.search(description['aux']))):
                return True
            continue
        for grammar in (_EN_FUNCTION, _EN_PASSIVE_USE, _EN_STATE, _EN_PLAN):
            match = grammar.match(tail)
            if match is None or not _description_payload(match['target']):
                continue
            if grammar is _EN_STATE and not _STATE_TARGET.search(match['target']):
                continue
            if grammar is _EN_PASSIVE_USE and not match['aux'].strip():
                continue
            if grammar is _EN_FUNCTION:
                verb, head = match['verb'].casefold(), value[start:end].casefold()
                if not match['aux'] and not head.endswith('s') and not verb.endswith(('s', 'ed')):
                    continue
            return True
        match = _CN_FUNCTION.match(tail)
        if (match is not None and not _AGENT_DERIVATION.match(match['target'])
                and _description_payload(match['target'])):
            return True
        match = _CN_STATE.match(tail)
        if match is not None and (match['aux'] or match['verb']):
            return True
    if _ACTOR_PHASE.search(value):
        return True
    scope=_ACTOR_SCOPE.match(value)
    if scope is not None and (product_head_spans(scope['target']) or _STATE_HEAD.search(scope['target'])):
        return True
    # Provision/hiring may name the operating object after its verb. There
    # still must be an actual subject before that verb in this same clause.
    for predicate in (*_PROVISION_EN.finditer(value), *_PROVISION_CN.finditer(value)):
        if predicate.start() > 100:
            continue
        subject = value[:predicate.start()]
        target_end=min(len(value),predicate.end()+100)
        target = value[predicate.end():target_end]
        index=bisect_left(ordered_heads,(predicate.end(),-1))
        if ((_PROVISION_ACTOR_EN.fullmatch(subject) or _PROVISION_ACTOR_CN.fullmatch(subject))
                and _description_payload(target)
                and index<len(ordered_heads) and ordered_heads[index][1]<=target_end):
            return True
    return False


def descriptive_operating_relation(text: str, *, prepared: SourceAssertionRoles | None = None) -> bool:
    """Same-clause subject/head--predicate--function proof, never a stage label."""
    return (prepared if prepared is not None else prepare_source_assertions(text)).operating


# These are grammatical head/predicate roles, not a list of filing locations.
# Rule objects do not become product objects just because an actor or a plan
# verb also occurs in the same sentence. Customer-facing product modifiers,
# in contrast, are governed by a real provision/function predicate above.
_REPORTING_HEAD = re.compile(r"财务报表|财务资料|财务信息|財務報表|財務資料|財務信息|"
    r"\b(?:financial statements?|financial information|financial reporting)\b",re.I)
_REPORTING_ACTION = re.compile(r"编制|編製|编製|编报|假设|假設|持续经营基|持續經營基|"
    r"\b(?:prepar\w*|assum\w*|going.concern)\b",re.I)
_STANDARD_HEAD = re.compile(r"会计准则|會計準則|财务报告准则|財務報告準則|\b(?:ASC\s*\d+|IFRS\s*\d+|accounting standards?)\b",re.I)
_STANDARD_ACTION = re.compile(r"采用|採用|对账|對賬|調節|调节|\b(?:adopt\w*|reconcil\w*)\b",re.I)
_AWARD_HEAD = re.compile(r"奖励|獎勵|购股权|購股權|股权激励|股權激勵|股份支付|\b(?:share awards?|employee share options?|share.based compensation)\b",re.I)
_AWARD_RULE = re.compile(r"授出|归属|歸屬|限额|限額|旨在|股东.{0,15}批准|股東.{0,15}批准|"
    r"\b(?:grant\w*|vest\w*|limits?|approval|conditions?|schemes?|aims?)\b",re.I)
_AUDIT_HEAD = re.compile(r"审计|審計|鉴证|鑒證|会计师事务所|會計師事務所|\b(?:auditors?|audit|assurance)\b",re.I)
_AUDIT_ACTION = re.compile(r"涉及|范围|範圍|意见|意見|结论|結論|\b(?:involv\w*|scope|opinions?|conclusions?|procedures?|tested)\b",re.I)
_METATEXT_HEAD = re.compile(r"前瞻性.{0,4}(?:陈述|陳述)|\bforward.looking statements?\b",re.I)
_METATEXT_ACTION = re.compile(r"识别|識別|字眼|词语|語句|历史事实|歷史事實|\b(?:identif\w*|words?|historical facts?)\b",re.I)
_RESULT_HEAD = re.compile(r"经营业绩|經營業績|\b(?:operating|interim) results?\b",re.I)
_RESULT_DISCLAIMER = re.compile(r"未必|不代表|并不反映|並不反映|\b(?:not necessarily|not indicative|not representative)\b",re.I)


@dataclass(frozen=True)
class AssertionRole:
    text: str
    operating: bool
    rule_purpose: str = ""


@dataclass(frozen=True)
class SourceAssertionRoles:
    clauses: tuple[AssertionRole, ...]
    numeric_ambiguous: bool = False
    numeric_role: str = "unknown"
    bound_operating: bool = False
    raw_structure_complete: bool = False
    numeric_cells_observed: bool = False

    @property
    def operating(self) -> bool:
        return self.bound_operating or any(clause.operating and not clause.rule_purpose for clause in self.clauses)


def prepare_source_assertions(text: str) -> SourceAssertionRoles:
    """Prepare one scope's local role evidence; no stage or attribution guess."""
    value=matching_reading_text(text)
    clauses=[]
    for text_clause in _source_clauses(value,descriptions=False):
        operating=any(_clause_description(part) for part in _source_clauses(text_clause))
        meta_head=_METATEXT_HEAD.search(text_clause)
        meta_action=_METATEXT_ACTION.search(text_clause) if meta_head else None
        product_head=_DESCRIPTION_OBJECT.search(text_clause) if meta_action else None
        # Defining/identifying the language of a statement governs its quoted
        # examples. In a product function the actual product head precedes that
        # predicate instead: software identifying such statements is an offering.
        meta_rule=bool(meta_action and (not product_head or meta_action.start()<product_head.start()))
        purpose=""
        if not operating and _AUDIT_HEAD.search(text_clause) and _AUDIT_ACTION.search(text_clause):
            purpose="audit_procedure"
        elif not operating and (_REPORTING_HEAD.search(text_clause) and _REPORTING_ACTION.search(text_clause)
              or _STANDARD_HEAD.search(text_clause) and _STANDARD_ACTION.search(text_clause)
              or _AWARD_HEAD.search(text_clause) and _AWARD_RULE.search(text_clause)):
            purpose="accounting_policy"
        elif meta_rule or (not operating and _RESULT_HEAD.search(text_clause) and _RESULT_DISCLAIMER.search(text_clause)):
            purpose="reporting_definition"
        clauses.append(AssertionRole(text_clause,operating,purpose))
    shape=observe_value_cells(text)
    numeric=shape.unbound_numeric_cells
    return SourceAssertionRoles(tuple(clauses),numeric,
        unbound_numeric_row_role(text) if shape.has_numeric_cell else "unknown",
        raw_structure_complete=shape.complete_value_row,
        numeric_cells_observed=shape.has_numeric_cell)
