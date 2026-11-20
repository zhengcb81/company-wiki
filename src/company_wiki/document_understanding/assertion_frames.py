"""Finite source-owned clause hints, never NLP truth or a source quotation.

One normalized matching view is divided into local clauses. The original span
and its locator remain authoritative. No offsets or verbatim-quote claim are
implied by ``matching_text``. Unsupported grammar stays unclassified. Production
integration must version the recipe; historical assessments are unchanged.
"""
from dataclasses import dataclass, replace
import re

from company_wiki.document_model.text_matching import matching_reading_text
from .statement_grammar.lexical import chinese_word_boundaries

LEGACY_ASSERTION_FRAME_PROFILE = 'source_frames/1'
ASSERTION_FRAME_PROFILE = 'source_frames/2'
ASSERTION_FRAME_PROFILES = frozenset({LEGACY_ASSERTION_FRAME_PROFILE, ASSERTION_FRAME_PROFILE})

_SENTENCES = re.compile(r'([。；;!?]|(?<!\d)\.(?!\d))')
_SCOPED_SENTENCES = re.compile(r'([。；;！!？?]|(?<!\d)\.(?!\d))')
_CLAUSES = re.compile(r'(?<!\d)[,，]|[,，](?!\d)')
_REPORT = re.compile(
    r'^(?:(?:根据|据).{1,70}?(?:报道|信息|消息|披露|报告)|according to\s+.{1,100})$', re.I)
_PREFIX_PREDICATE = re.compile(
    r'正在|已经|将|计划|希望|建设|开发|\b(?:is|are|was|were|has|have|will|would|plans?|hopes?)\b', re.I)
_PREFIX_PROCEDURE = re.compile(r'需要|要求|准则|标准|\b(?:requirements?|needs?|guidelines?|standards?)\b', re.I)
# A coordinator alone does not establish shared subject: "and Beta ..." must
# not inherit Alpha's attribution. Only these finite subjectless predicates do.
_CONTINUATION = re.compile(
    r'^(?:(?:并且|并|且|而且)(?:已|正|持续|积极|希望|计划|将|拟|未|没有|不)|'
    r'(?:and|also)\s+(?:also\s+)?(?:will|has|have|is|are|hopes?|plans?|intends?|expects?|continues?|not)\b)', re.I)
_FUTURE = re.compile(
    r'(?<!已)(?<!经)(?:将)|拟(?:于|在|申请|建设|投产)|'
    r'计划(?=(?:将|持续|在|于|明年|开展|扩展|开发|投产|建设|合作))|'
    r'希望|预期|预计|明年|\b(?:will|plans? to|intends? to|expects? to|hopes? to)\b', re.I)
_ONGOING = re.compile(
    r'(?:正在|持续|积极)(?:开发|完善|推进|拓展|改善|研制|建设)|'
    r'\b(?:is|are)\s+(?:actively\s+)?(?:developing|expanding|improving|building)|'
    r'\bcontinues? to\s+(?:develop|expand|improve|build)\b', re.I)
_CAPACITY_QUANTITY = re.compile(
    r'(?:产能|\bcapacity\b)\s*(?:(?:约为|约|为|达到|达|合计|of|is|at|about|around|approximately|to)\s*)*'
    r'(?:\d|[一二三四五六七八九十百千万亿两])', re.I)
_PROJECT = re.compile(r'建设|项目|\b(?:construction|project)\b', re.I)
_PROJECT_ANAPHOR = re.compile(
    r'^(?:该项目|本项目|其项目|this project\b|the same project\b|'
    r'项目(?=\s*(?:建成|投产|完成|获批)后)|'
    r'the project(?=\s+(?:following|upon|after) completion\b))', re.I)
_PROJECT_CONTINUATION = re.compile(
    r'^(?:其中(?:(?:设计|年)?产能|包括|含有)|包括|设计产能|年产能|产能|建成后|投产后|完成后|'
    r'with\s+(?:(?:an?|annual|designed|installed)\s+)*capacity\b|capacity\b|'
    r'(?:following|upon|after) completion\b)', re.I)
_EXISTING = re.compile(r'现有|已(?:经)?投产|已建成|\b(?:existing|commissioned)\b', re.I)
_NEGATED_PREFIX = re.compile(r'(?:未|不|没有|尚无|(?:\bnot|\bnever)(?:\s+\w+){0,2})\s*$', re.I)
_CONDITION = re.compile(r'(?:建成|投产|完成|获批)后|'
                        r'\b(?:following|upon|after) completion\b', re.I)
_ANAPHORIC_MARKER = (
    r'(?:该|此|上述|本|这一|该项)(?:安排|计划|项目|事项|交易|合作|订单|申请|承诺|方案)|'
    r'(?:this|that|the aforementioned|such a)\s+'
    r'(?:arrangement|plan|project|matter|transaction|cooperation|order|application|commitment|proposal)\b'
)
_ANAPHORIC_REFERENCE = re.compile(rf'^(?:{_ANAPHORIC_MARKER})', re.I)
_COORDINATED_REFERENCE = re.compile(
    rf'^(?:并且|而且|同时|并|且|(?:and|also|moreover)\s+)\s*(?:{_ANAPHORIC_MARKER})', re.I,
)
_PENDING_REQUIREMENT = re.compile(
    r'(?<!无)(?<!不)(?<!不再)(?:仍|尚|还)?(?:须|需要|需|必须|有待|取决于|依赖于)|'
    r'\b(?:remains?\s+(?:subject to|conditional on)|is\s+subject to|'
    r'depends?\s+on|requires?|pending)\b',
    re.I,
)
_PREDICATE_REQUIREMENT = re.compile(
    r'(?P<chinese>(?P<continuing>仍|尚|还)?(?:(?P<need>需要|需(?!求))|必须|须|有待|取决于|依赖于))|'
    r'\b(?:remains?\s+(?:subject to|conditional on)|is\s+subject to|'
    r'depends?\s+on|requires?|pending)\b', re.I,
)
_NEED_COMPLEMENT = re.compile(
    r'经|取得|获得|获批|通过|完成|满足|提交|接受|达到|具备|符合|履行|提供|申请|'
    r'审批|批准|核准|同意|验收|确认|认证|'
    r'[^:：]{1,48}?(?:审批|批准|核准|许可|同意|验收|确认|认证|审核|备案)(?:后|方可|才能|$)',
)
_REQUIREMENT_MODIFIER = re.compile(
    r'(?:所|按|无|不|不再|是否|能否)\s*$|'
    r'\b(?:does not|do not|did not|no longer|never)\s+(?:remain\s+)?$', re.I,
)
_NEGATED_REQUIREMENT = re.compile(
    r'(?:无需|不需要|不再需要|无须|已无需|已不再需要)|'
    r'\b(?:does not|do not|did not|no longer|never)\s+'
    r'(?:remain\s+)?(?:require\w*|depend\w*\s+on|be\s+subject\s+to|be\s+conditional\s+on)\b',
    re.I,
)
_REQUIREMENT_CONSEQUENCE = re.compile(
    r'后(?:方可|才能|才可|才会)|\b(?:before|prior to)\b', re.I,
)
_NON_ASSERTION_PREFIX = (
    r'^(?:请问|问[:：]|问题[:：]|模板[:：]|示例[:：]|例如[:：]|填写说明[:：]|'
    r'根据(?:需要|要求|准则|标准)|'
    r'(?:(?:accounting policy|template|example)(?:\s+example)?\s*[:：]))'
)
_NON_ASSERTION = re.compile(_NON_ASSERTION_PREFIX + r'|是否|能否', re.I)
_SCOPED_NON_ASSERTION = re.compile(_NON_ASSERTION_PREFIX, re.I)
_REPORTING_PERIOD = (
    r'(?:本?报告期内|本(?:年度|季度|半年度|财年)内|'
    r'(?:during|in)\s+(?:this|the)\s+(?:(?:reporting|fiscal|financial)\s+)?'
    r'(?:period|quarter|half(?:[- ]year)?|year))'
)
_REPORTING_PERIOD_HEADING = re.compile(rf'{_REPORTING_PERIOD}\s*[:：]?', re.I)
_REPORTING_PERIOD_PREFIX = re.compile(rf'^{_REPORTING_PERIOD}\s*[:：]\s*', re.I)
_ACTION_START = r'(?:启动|开工|动工|开始|开启|开展|投入)'
_REPORTED_START = re.compile(
    rf'已(?:经)?(?:提前|正式)?{_ACTION_START}|'
    r'\b(?:began|commenced|started|initiated|broke ground)\b', re.I,
)
_START_WITH_PERIOD = re.compile(rf'(?:提前|正式){_ACTION_START}')
_CONDITIONAL_ACTION = re.compile(
    r'^(?:若|倘若|如果|待(?=获|完|验|审|批|签))|'
    r'(?:获批|批准|通过|完成|签署|验收)后|\b(?:if|unless|once|provided that|subject to)\b', re.I,
)
_START_QUALIFIER = re.compile(
    r'(?P<chinese>拟|计划|打算|希望|预期|预计|考虑|有望|可能|争取|是否|能否|'
    r'讨论|商议|建议|提议|缺少|缺乏|(?:尚|仍|还|暂)?(?:没有|未能|未必|不会|不再|无需|未|不|无))|'
    r'\b(?:will|would|should|could|may|might|plans?|intends?|expect\w*|'
    r'propos\w*|discuss\w*|consider\w*|suggest\w*|not|never|without|whether)\b', re.I,
)
_ACTION_NOMINAL = re.compile(r'^的|的(?:条件|前提|计划|安排|建议|方案|可能性)')


@dataclass(frozen=True)
class SourceAssertionFrame:
    matching_text: str
    reporting_prefix: str | None = None
    reporting_inherited: bool = False
    ongoing_activity: bool = False
    future_marker: bool = False
    quantity_basis: str | None = None
    # The finite matching marker, not another copy of its full consequence.
    project_condition: str | None = None
    # An explicit backward reference plus an unresolved requirement. This is
    # only a candidate for binding to earlier cited evidence, not a truth test.
    anaphoric_pending_condition: bool = False
    pending_requirement: str | None = None
    requirement_proposition: str | None = None
    coordinated_pending_condition: bool = False
    reported_start: bool = False


def is_reporting_period_heading(source: str) -> bool:
    """Recognize a bare period scope; a named party or sentence is not a heading."""
    return _REPORTING_PERIOD_HEADING.fullmatch(matching_reading_text(source).strip()) is not None


def assertion_clause_key(clause: str) -> str:
    """Compare a normalized local clause without borrowing partial actor matches."""
    return ' '.join(_REPORTING_PERIOD_PREFIX.sub('', clause).casefold().split())


def _predicate_requirement(text: str) -> re.Match[str] | None:
    cues = tuple(_PREDICATE_REQUIREMENT.finditer(text))
    boundaries = chinese_word_boundaries(text) if any(cue['chinese'] for cue in cues) else None
    for cue in cues:
        if cue['chinese'] and (boundaries is None or not {cue.start(), cue.end()} <= boundaries):
            continue
        modifier = _REQUIREMENT_MODIFIER.search(text[:cue.start()])
        if modifier is not None and (not cue['chinese'] or (boundaries is not None and modifier.start() in boundaries)):
            continue
        if cue['need'] and not (cue['continuing'] or _NEED_COMPLEMENT.match(text[cue.end():].lstrip())):
            continue
        return cue
    return None


def _qualified_action_prefix(text: str) -> bool:
    cues = tuple(_START_QUALIFIER.finditer(text))
    if any(not cue['chinese'] for cue in cues):
        return True
    if not cues:
        return False
    boundaries = chinese_word_boundaries(text)
    return boundaries is None or any({cue.start(), cue.end()} <= boundaries for cue in cues)


def _action_scope(text: str, *, reporting_period: bool, qualified: bool) -> tuple[bool, bool]:
    """Observe start in a matrix clause and carry qualifications to implicit continuations."""
    clause = _REPORTING_PERIOD_PREFIX.sub('', text)
    explicit_start = _REPORTED_START.search(clause)
    start = explicit_start or (_START_WITH_PERIOD.search(clause) if reporting_period else None)
    prefix = clause[:start.start()] if start else clause
    if (_CONDITIONAL_ACTION.search(clause) or _FUTURE.search(prefix) or _qualified_action_prefix(prefix)
            or (start is not None and _ACTION_NOMINAL.search(clause[start.end():]))):
        return True, False
    if start is None or (qualified and explicit_start is None):
        return qualified, False
    # An explicitly asserted, unqualified past action can start its own scope
    # after a distinct conditioned/anticipated clause in the same sentence.
    return False, True


def _existing_stage(text: str) -> bool:
    match = _EXISTING.search(text)
    if match is None:
        return False
    before = text[max(0, match.start() - 32):match.start()]
    if _NEGATED_PREFIX.search(before):
        return False
    if match.group().lower() == 'commissioned' and _FUTURE.search(text[:match.start()]):
        return False
    return True


def source_assertion_frames(
    source: str, *, profile: str = LEGACY_ASSERTION_FRAME_PROFILE, reporting_period: bool = False,
) -> tuple[SourceAssertionFrame, ...]:
    """Observe finite local qualifiers without borrowing another subject's proof.

    A project condition/stage propagates only inside a local project clause
    chain, with explicit anaphora or a subjectless capacity/condition clause.
    Independent project clauses start a new chain. No production or numeric
    evidence is manufactured by these hints.
    """
    if profile not in ASSERTION_FRAME_PROFILES:
        raise ValueError('unknown source assertion frame profile')
    scoped = profile == ASSERTION_FRAME_PROFILE
    frames = []
    sentences = _SCOPED_SENTENCES if scoped else _SENTENCES
    non_assertion_pattern = _SCOPED_NON_ASSERTION if scoped else _NON_ASSERTION
    chunks = sentences.split(matching_reading_text(source))
    for offset in range(0, len(chunks), 2):
        sentence = chunks[offset]
        ending = chunks[offset + 1] if offset + 1 < len(chunks) else ''
        non_assertion = ending in {'?', '？'} or bool(non_assertion_pattern.search(sentence.strip()))
        reporting = None
        pending = False
        active_project = None
        next_project = 0
        existing_project = False
        qualified_action = False
        conditions = {}
        scoped_frames = []
        clauses = [text.strip() for text in _CLAUSES.split(sentence) if text.strip()]
        within_period = reporting_period or (scoped and bool(clauses) and (
            _REPORTING_PERIOD_HEADING.fullmatch(clauses[0]) is not None
            or _REPORTING_PERIOD_PREFIX.match(clauses[0]) is not None
        ))
        for index, text in enumerate(clauses):
            # A source-only prefix requires an actual following clause. This
            # cannot consume an undelimited English sentence as the reporter.
            if (index + 1 < len(clauses) and _REPORT.fullmatch(text)
                    and not _PREFIX_PREDICATE.search(text) and not _PREFIX_PROCEDURE.search(text)
                    and not non_assertion):
                reporting, pending = text, True
                continue
            inherited = not pending and bool(reporting and _CONTINUATION.match(text))
            prefix = reporting if pending or inherited else None
            if prefix is None:
                reporting = None
            pending = False
            local_project = bool(_PROJECT.search(text))
            if local_project:
                if active_project is None or not _PROJECT_ANAPHOR.match(text):
                    next_project += 1
                    active_project = next_project
                    existing_project = False
                existing_project = existing_project or _existing_stage(text)
            elif active_project is None or not _PROJECT_CONTINUATION.match(text):
                active_project = None
                existing_project = False
            condition = _CONDITION.search(text)
            if condition and active_project is not None and not non_assertion:
                conditions[active_project] = condition.group().strip()
            basis = None
            if not non_assertion and _CAPACITY_QUANTITY.search(text):
                if _existing_stage(text) or existing_project:
                    basis = 'existing_capacity'
                elif active_project is not None:
                    basis = 'project_capacity_specification'
            future = not non_assertion and bool(_FUTURE.search(text))
            ongoing = _ONGOING.search(text)
            if ongoing and _NEGATED_PREFIX.search(text[max(0, ongoing.start() - 32):ongoing.start()]):
                ongoing = None
            requirement = None
            reported_start = False
            if not non_assertion:
                if scoped:
                    requirement = _predicate_requirement(text)
                    qualified_action, reported_start = _action_scope(
                        text, reporting_period=within_period, qualified=qualified_action,
                    )
                elif not _NEGATED_REQUIREMENT.search(text):
                    requirement = _PENDING_REQUIREMENT.search(text)
            requirement_text = None
            if requirement is not None:
                body = text[requirement.end():].strip()
                requirement_text = _REQUIREMENT_CONSEQUENCE.split(body, maxsplit=1)[0].strip() or None
            frame = SourceAssertionFrame(
                matching_text=text, reporting_prefix=prefix, reporting_inherited=inherited,
                ongoing_activity=not non_assertion and ongoing is not None and not future,
                future_marker=future, quantity_basis=basis,
                anaphoric_pending_condition=requirement is not None and bool(_ANAPHORIC_REFERENCE.search(text)),
                pending_requirement=requirement_text,
                requirement_proposition=text[:requirement.start()].strip() if requirement_text and requirement else None,
                coordinated_pending_condition=requirement is not None and bool(_COORDINATED_REFERENCE.search(text)),
                reported_start=reported_start,
            )
            scoped_frames.append((frame, active_project))
        for frame, group in scoped_frames:
            if frame.quantity_basis == 'project_capacity_specification' and group is not None:
                frame = replace(frame, project_condition=conditions.get(group))
            frames.append(frame)
    return tuple(frames)

__all__ = [
    'ASSERTION_FRAME_PROFILE', 'ASSERTION_FRAME_PROFILES', 'LEGACY_ASSERTION_FRAME_PROFILE',
    'assertion_clause_key', 'is_reporting_period_heading',
    'source_assertion_frames',
]
