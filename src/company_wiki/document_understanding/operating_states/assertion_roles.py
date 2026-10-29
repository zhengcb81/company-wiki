"""Shared bounded source assertion roles, independent of state/stage projection.

Product heads, local predicates and their argument roles prove a descriptive
assertion. Source purpose and support consume one prepared result; refs or a
recognized stage alone never manufacture an assertion.
"""
from __future__ import annotations

from dataclasses import dataclass
from bisect import bisect_left
from collections.abc import Iterator
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
    r"会计和内部控制系统|\baccounting\s+and\s+internal\s+control\s+systems?\b|"
    r"\b(?:costs?|expenses?|revenues?|profits?|income|assets?|liabilit\w*)\b", re.I)
_ARGUMENT_PURPOSE = re.compile(r"\b(?:to|in order to|so as to)\s+[a-z]+\b|"
                               r"(?:以便|从而|来)(?:降低|减少|提高|提升)", re.I)
_DESCRIPTION_SENTENCES = re.compile(r"[。！？；;]|(?<=[.!?])\s+")
_DESCRIPTION_PARTS = re.compile(r"(?<!\d)[,，]|[,，](?!\d)|\b(?:and|but|while|whereas)\s+(?=we\b|the company\b)", re.I)
_STATE_HEAD = re.compile(r"\b(?:projects?|plants?|factor(?:y|ies)|facilit(?:y|ies)|qualification|validation|certification)\b|项目|工厂|基地|生产设施|制造设施|厂房|生产线", re.I)
_EN_HEAD_TAIL = r"(?:\s+(?:coverage|scope|portfolio|range|lineup|suite|family|editions?|versions?|configurations?|launch|rollout|delivery|deployment|release)){0,3}\s+"
_EN_AUX = r"(?P<aux>(?:(?:is|are|was|were|can|may|will|would|could|has|have|had|been|be|not|also|currently|already|still|widely|further|now)\s+){0,8})"
_EN_FUNCTION = re.compile(_EN_HEAD_TAIL + _EN_AUX +
    r"(?P<verb>provid\w*|offer\w*|suppl\w*|support\w*|rout\w*|process\w*|deliver\w*|manufactur\w*|"
    r"includ\w*|compris\w*|forms?|cover\w*|serves?|uses?|produc\w*|identif\w*|utili[sz]\w*|launch\w*|releas\w*|introduc\w*|deploy\w*)"
    r"\b\s+(?P<target>[^,。;!?]{1,160})", re.I)
_EN_PASSIVE_USE = re.compile(_EN_HEAD_TAIL + _EN_AUX +
    r"(?P<verb>used|utili[sz]ed|deployed)\s+(?:by|for|to|in)\s+(?P<target>[^,。;!?]{1,160})", re.I)
_EN_CONSTRAINT = re.compile(_EN_HEAD_TAIL + _EN_AUX +
    r"(?P<verb>subject to|dependent on|exposed to)\s+(?P<target>[^,。;!?]{1,160})", re.I)
_EN_DESCRIPTION = re.compile(_EN_HEAD_TAIL + _EN_AUX +
    r"(?P<verb>for|comes? in|available in|offered in)\s+(?P<target>[^,。;!?]{1,160})", re.I)
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
_CN_PROVISION_BRIDGE = r"(?:(?:由|通过|经由)[^,，。;!?]{1,35}?(?=提供|供应|交付|制造|路由|处理|组装))?"
_CN_FUNCTION = re.compile(_CN_HEAD_TAIL + _CN_AUX + _CN_PROVISION_BRIDGE +
    r"(?P<verb>用于|用作|作为|支持|提供|覆盖|涵盖|包括|包含|供应|制造|设计|交付|处理|连接|面向|应用于|路由|组装)"
    r"(?P<target>[^,，。;!?]{1,160})")
_CN_STATE = re.compile(_CN_HEAD_TAIL + _CN_AUX +
    r"(?P<verb>进入|处于|开展|推进|进行|完成|启动|投入)?(?:客户)?(?P<target>认证|验证|试产|量产|生产|建设|投产|运行|运营|发布|上线)")
_PROVISION_EN = re.compile(r"\b(?:provid\w*|offer\w*|suppl\w*|manufactur\w*|design\w*|deliver\w*|"
    r"hir\w*|employ\w*|recruit\w*|launch\w*|releas\w*|introduc\w*|deploy\w*|acquir\w*|commission\w*|open\w*|expand\w*)\b", re.I)
_PROVISION_CN = re.compile(r"提供|供应|制造|设计|打造|交付|聘用|招聘|招募|收购|收購|建设|建造|搭建|定制")
_PROVISION_ACTOR_EN = re.compile(
    r"\s*(?:(?i:we|(?:the|our|this)\s+(?:company|group|team|supplier|partner|bank))|"
    r"[A-Z][A-Za-z0-9&.-]*(?:\s+[A-Z][A-Za-z0-9&.-]*){0,4})"
    r"(?:\s+(?i:already|also|now|currently|still|will|can|may|have|has|had|"
    r"continue\s+to|continues\s+to|continued\s+to)){0,8}"
    r"(?:\s+(?i:using|through|via|based\s+on)\s+[^,。;!?]{1,70})?"
    r"(?:\s+[a-z][\w-]*(?:\s+[a-z][\w-]*){0,9}\s+(?:and|but))?\s*")
_PROVISION_ACTOR_CN = re.compile(
    r"\s*(?:未来|今后)?(?:我们|本公司|公司|本集团|集团|企业|供应商|厂商|团队)"
    r"(?:已经|正在|持续|继续|计划|预计|主要|还|已|将|正){0,6}"
    r"(?:(?:能够|可以|能)?(?:及时)?(?:响应|回应)(?:并|及|和))?"
    r"(?:(?:凭借|基于|通过|采用|向|为|在)[^,，。;!?]{1,70})?\s*")
_RESOURCE_OBJECT = re.compile(r"\b(?:engineers|researchers|technical staff|research staff)\b|研发人员|工程师|研究人员", re.I)
_ACTOR_PHASE = re.compile(r"^(?:本公司|公司|本集团|集团|我们|企业)[^,，。;!?]{0,32}"
    r"(?:推进|开展|进入|进行|完成)(?:客户|产品|设备)?(?:认证|验证|生产|量产)|"
    r"^(?:本公司|公司|本集团|集团|我们|企业)(?:目前|现时|仍|尚|已经|已|正在){0,4}"
    r"(?:处于|在)(?:客户|产品|设备)(?:认证|验证)(?:阶段|过程)")
_ACTOR_SCOPE = re.compile(r"^(?:本公司|公司|本集团|集团|我们|企业)(?:主要|已|正在|目前|尚未|不|未)?"
    r"(?:参与|从事|经营|涉及)(?P<target>[^,，。;!?]{1,60})")
_ENTITY_OPERATION = re.compile(
    r"(?:本公司|公司|本集团|集团|我们)(?:主要)?通过[^。;!?]{1,160}"
    r"(?:子公司|可变利益实体)[^。;!?]{0,80}(?:开展业务|进行(?:主要)?业务营运|进行(?:主要)?业务运营)|"
    r"\b(?:we|the (?:company|group))\s+(?:operate[sd]?|conduct\w* (?:our )?business)\s+"
    r"through\s+[^。;!?]{0,80}\b(?:subsidiaries|variable interest entities)\b", re.I)
_CONSTRAINT_STATUS = re.compile(
    r"^(?:(?:于|在)?报告期内[，,]?\s*)?(?:本公司|公司|本集团|集团|我们)"
    r"(?:目前|现时|并|亦|尚|仍|已|未|无|不|涉及|任何){1,7}"
    r"[^。;!?]{0,120}(?:诉讼|仲裁|申索)|"
    r"\b(?:we|the (?:company|group))\s+(?:is|are|was|were)\s+(?:not\s+)?"
    r"(?:involved in|subject to)\s+[^。;!?]{0,80}\b(?:litigation|arbitration|claims?)\b", re.I)
_AGENT_DERIVATION = re.compile(r"^(?:者|人员|人員|商(?=的|使|及|和|与|为|向|$))")

# Closed abstract-argument grammar. Only a fully observed generic objective is
# negative evidence; an unfamiliar technical argument is never a stop word.
# These are compositional argument roles, not sentences, issuers or industries.
_ABSTRACT_EN_WORDS = frozenset((
    "a an the our their its we us and or of for to in across all various "
    "rich wide broad range high quality high-quality comprehensive diverse "
    "product products service services platform platforms technology technical "
    "business businesses industry industries customer customers client clients "
    "development innovation transformation digital upgrade upgrading growth "
    "needs need demand demands engagement satisfaction value success benefits "
    "basis foundation changing continuously continually improve improving "
    "support supporting meet meeting enable enabling aim aims aiming "
    "help helping enhance enhancing can could will would allow allows "
    "better evolving constantly is are be as capabilities ability "
    "software equipment workloads solutions solution provide provides provided "
    "support supports supported form forms formed"
).split())
_ABSTRACT_EN_TOKEN = re.compile(r"[a-z]+(?:-[a-z]+)*|[^\s.,:()]+", re.I)
_ABSTRACT_CN = re.compile(
    r"(?:我们|公司|本公司|集团|本集团|以|的|及|和|与|或|为|向|在|各|各个|各类|"
    r"所有|广大|丰富|广泛|优质|全面|多样|产品|服务|技术|平台|业务|行业|客户|需求|"
    r"发展|开发|创新|数字化|转型|升级|增长|基础|能力|价值|成功|利益|满意度|参与度|"
    r"不断|持续|变化|提升|提高|满足|支持|提供|作为|软件|设备|工作负载|解决方案|"
    r"助力|推动|促进|使|能够|可以|旨在|目标|是|"
    r"[\s.。:：()（）])+")
_OBJECTIVE_PREDICATE = re.compile(
    r"旨在|目标|使我们|\b(?:aims?|aiming|enabl\w*|help\w*)\b", re.I)
_FUNCTION_ARGUMENT = re.compile(
    r"\b(?:process\w*|rout\w*|transactions?|maintenan\w*|repair\w*|diagnos\w*|"
    r"filter\w*|sterili[sz]\w*|assembl\w*|comput\w*|sequenc\w*|access|connect\w*|collateral)\b|"
    r"处理|维护|维修|诊断|过滤|消毒|装配|计算|接入|连接|抵押|质押", re.I)
_SPECIFIC_APPLICATION = re.compile(r"云(?:产品|服务)|基础设施|网络|"
    r"\b(?:cloud (?:products?|services?)|networks?|infrastructure)\b", re.I)
_FUNCTIONAL_OFFERING = re.compile(
    r"(?:管理|处理|维护|分析|计算|识别)(?:软件|平台|系统)\s*$|"
    r"\b(?:management|processing|maintenance|analytics?|computation|identification)\s+"
    r"(?:software|platforms?|systems?)\s*\.?$", re.I)
_WEAK_FUNCTION = re.compile(r"^(?:support\w*|provid\w*|offer\w*|includ\w*|compris\w*|forms?|"
                            r"suppl\w*|cover\w*|serves?|uses?|used|utili[sz]ed|deployed|for|subject to|dependent on|exposed to|"
                            r"作为|支持|提供|覆盖|涵盖|包括|包含|面向|用于|用作|应用于)$", re.I)


def abstract_source_argument(value: str) -> bool:
    """Prove the whole local argument contains only abstract benefit roles."""
    if _ABSTRACT_CN.fullmatch(value):
        return True
    tokens = _ABSTRACT_EN_TOKEN.findall(value.casefold())
    return bool(tokens) and all(token in _ABSTRACT_EN_WORDS for token in tokens)


def _argument_payload(value: str, *, concrete_action: bool = False,
                      complete: bool = True) -> bool | None:
    if not complete:
        return None
    if concrete_action:
        return True
    if abstract_source_argument(value):
        return False
    # Positive proof is independent of failure to match the abstract grammar:
    # an actual operation, typed offering, or explicit application/function.
    concrete_head = any(kind not in {"product", "platform", "solution", "service", "system"}
                        for _, _, kind in product_head_spans(value))
    financial = tuple(_MEMBERSHIP_FINANCIAL_HEAD.finditer(value))
    # Lease-liability/stock-incentive management SOFTWARE is an offering; a
    # technical modifier cannot reverse a governing financial noun head.
    financial_offering = bool(financial and _DESCRIPTION_OBJECT.search(value, financial[-1].end()))
    if (concrete_head or financial_offering or _FUNCTIONAL_OFFERING.search(value) or _FUNCTION_ARGUMENT.search(value)
            or _SPECIFIC_APPLICATION.search(value)):
        return True
    return None


def _argument_closed(value: str, end: int) -> bool:
    # Do not copy/rescan a potentially huge unread suffix for every head.
    return len(value)-end <= 8 and not value[end:].strip(" .。!?；;，,\t\r\n")


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
    # A purpose adjunct is not the governing object: routing workloads to
    # reduce costs remains a function, while service costs remain an account.
    purpose = _ARGUMENT_PURPOSE.search(value)
    argument = value[:purpose.start()] if purpose else value
    financial = tuple(_MEMBERSHIP_FINANCIAL_HEAD.finditer(argument))
    return not financial or bool(_DESCRIPTION_OBJECT.search(argument, financial[-1].end()))


@dataclass(frozen=True)
class _DescriptionProof:
    independent: bool | None
    witness: str
    descriptive_only: bool = False


_UNSPECIFIED_VARIANTS = re.compile(
    r"(?:(?:several|multiple|various|different)\s+)+(?:editions?|versions?|configurations?)\.?", re.I)


def _clause_description_proofs(value: str) -> Iterator[_DescriptionProof]:
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
                yield _DescriptionProof(_argument_payload(description['target'],
                    concrete_action=description['verb'].casefold() != 'for',
                    complete=_argument_closed(value, end+description.end('target'))), value,
                    bool(_UNSPECIFIED_VARIANTS.fullmatch(description['target'].strip())))
            continue
        for grammar in (_EN_FUNCTION, _EN_PASSIVE_USE, _EN_CONSTRAINT, _EN_STATE, _EN_PLAN):
            match = grammar.match(tail)
            if match is None or not _description_payload(match['target']):
                continue
            if grammar is _EN_STATE and not _STATE_TARGET.search(match['target']):
                continue
            if grammar is _EN_PASSIVE_USE and not match['aux'].strip():
                continue
            if grammar is _EN_CONSTRAINT and not _EN_COPULA.search(match['aux']):
                continue
            if grammar is _EN_FUNCTION:
                verb, head = match['verb'].casefold(), value[start:end].casefold()
                if not match['aux'] and not head.endswith('s') and not verb.endswith(('s', 'ed')):
                    continue
            yield _DescriptionProof(_argument_payload(match['target'],
                concrete_action=not _WEAK_FUNCTION.fullmatch(match.groupdict().get('verb', 'for')),
                complete=_argument_closed(value, end+match.end('target'))), value)
        match = _CN_FUNCTION.match(tail)
        if (match is not None and not _AGENT_DERIVATION.match(match['target'])
                and _description_payload(match['target'])):
            yield _DescriptionProof(_argument_payload(match['target'],
                concrete_action=not _WEAK_FUNCTION.fullmatch(match['verb']),
                complete=_argument_closed(value, end+match.end('target'))), value)
        match = _CN_STATE.match(tail)
        if match is not None and (match['aux'] or match['verb']):
            yield _DescriptionProof(True, value)
    if _ACTOR_PHASE.search(value):
        yield _DescriptionProof(True, value)
    scope=_ACTOR_SCOPE.match(value)
    if scope is not None and (product_head_spans(scope['target']) or _STATE_HEAD.search(scope['target'])
                              or _DESCRIPTION_OBJECT.search(scope['target'])):
        yield _DescriptionProof(_argument_payload(scope['target'],
            complete=_argument_closed(value, scope.end('target'))), value)
    if _ENTITY_OPERATION.search(value) or _CONSTRAINT_STATUS.search(value):
        yield _DescriptionProof(True, value)
    # Provision/hiring may name the operating object after its verb. There
    # still must be an actual subject before that verb in this same clause.
    for predicate in (*_PROVISION_EN.finditer(value), *_PROVISION_CN.finditer(value)):
        if predicate.start() > 100:
            continue
        subject = value[:predicate.start()]
        target_end=min(len(value),predicate.end()+160)
        target = value[predicate.end():target_end]
        index=bisect_left(ordered_heads,(predicate.end(),-1))
        if ((_PROVISION_ACTOR_EN.fullmatch(subject) or _PROVISION_ACTOR_CN.fullmatch(subject))
                and _description_payload(target)
                and index<len(ordered_heads) and ordered_heads[index][1]<=target_end):
            yield _DescriptionProof(_argument_payload(target,
                concrete_action=not _WEAK_FUNCTION.fullmatch(predicate.group()),
                complete=_argument_closed(value, target_end)), value)


def _clause_description(value: str) -> bool:
    return next(_clause_description_proofs(value), None) is not None


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
    independent_payload: bool | None = None
    # Normalized local witnesses, NOT original offsets or canonical EvidenceSpan.
    payload_witnesses: tuple[str, ...] = ()
    material_payload: bool = False


@dataclass(frozen=True)
class SourceAssertionRoles:
    clauses: tuple[AssertionRole, ...]
    numeric_ambiguous: bool = False
    numeric_role: str = "unknown"
    bound_operating: bool = False
    raw_structure_complete: bool = False
    numeric_cells_observed: bool = False
    bound_payload: bool = False

    @property
    def operating(self) -> bool:
        return self.bound_operating or any(clause.operating and not clause.rule_purpose for clause in self.clauses)

    @property
    def independent_payload(self) -> bool | None:
        if self.bound_payload:
            return True
        values = [clause.independent_payload for clause in self.clauses if not clause.rule_purpose]
        if any(value is True for value in values):
            return True
        if self.clauses and all(value is False for value in values):
            return False
        return None

    @property
    def descriptive_only(self) -> bool:
        return (not self.bound_payload and self.independent_payload is True
                and not any(clause.material_payload for clause in self.clauses if not clause.rule_purpose))


def prepare_source_assertions(text: str) -> SourceAssertionRoles:
    """Prepare one scope's local role evidence; no stage or attribution guess."""
    value=matching_reading_text(text)
    clauses=[]
    for text_clause in _source_clauses(value,descriptions=False):
        parts = [(part, tuple(_clause_description_proofs(part)))
                 for part in _source_clauses(text_clause)]
        operating = any(proofs for _, proofs in parts)
        payloads = [True if any(proof.independent is True for proof in proofs) else False if
                    ((proofs and all(proof.independent is False for proof in proofs))
                     or _OBJECTIVE_PREDICATE.search(part)) and abstract_source_argument(part) else None
                    for part, proofs in parts]
        independent = (True if any(value is True for value in payloads) else
                       False if payloads and all(value is False for value in payloads) else None)
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
        witnesses = tuple(dict.fromkeys(proof.witness for _, proofs in parts
                                        for proof in proofs if proof.independent is True))
        material = any(proof.independent is True and not proof.descriptive_only
                       for _, proofs in parts for proof in proofs)
        clauses.append(AssertionRole(text_clause,operating,purpose,independent,witnesses,material))
    shape=observe_value_cells(text)
    numeric=shape.unbound_numeric_cells
    return SourceAssertionRoles(tuple(clauses),numeric,
        unbound_numeric_row_role(text) if shape.has_numeric_cell else "unknown",
        raw_structure_complete=shape.complete_value_row,
        numeric_cells_observed=shape.has_numeric_cell)
