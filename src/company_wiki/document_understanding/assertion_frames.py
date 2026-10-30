"""Finite source-owned clause hints, never NLP truth or a source quotation.

One normalized matching view is divided into local clauses. The original span
and its locator remain authoritative. No offsets or verbatim-quote claim are
implied by ``matching_text``. Unsupported grammar stays unclassified. Production
integration must version the recipe; historical assessments are unchanged.
"""
from dataclasses import dataclass, replace
import re

from company_wiki.document_normalization.text_matching import matching_reading_text

_SENTENCES = re.compile(r'([。；;!?]|(?<!\d)\.(?!\d))')
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
_NON_ASSERTION = re.compile(
    r'^(?:请问|问[:：]|问题[:：]|模板[:：]|示例[:：]|例如[:：]|填写说明[:：]|'
    r'根据(?:需要|要求|准则|标准)|'
    r'(?:(?:accounting policy|template|example)(?:\s+example)?\s*[:：]))|是否|能否', re.I)


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


def source_assertion_frames(source: str) -> tuple[SourceAssertionFrame, ...]:
    """Observe finite local qualifiers without borrowing another subject's proof.

    A project condition/stage propagates only inside a local project clause
    chain, with explicit anaphora or a subjectless capacity/condition clause.
    Independent project clauses start a new chain. No production or numeric
    evidence is manufactured by these hints.
    """
    frames = []
    chunks = _SENTENCES.split(matching_reading_text(source))
    for offset in range(0, len(chunks), 2):
        sentence = chunks[offset]
        ending = chunks[offset + 1] if offset + 1 < len(chunks) else ''
        non_assertion = ending == '?' or bool(_NON_ASSERTION.search(sentence.strip()))
        reporting = None
        pending = False
        active_project = None
        next_project = 0
        existing_project = False
        conditions = {}
        scoped_frames = []
        clauses = [text.strip() for text in _CLAUSES.split(sentence) if text.strip()]
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
            frame = SourceAssertionFrame(
                matching_text=text, reporting_prefix=prefix, reporting_inherited=inherited,
                ongoing_activity=not non_assertion and ongoing is not None and not future,
                future_marker=future, quantity_basis=basis,
            )
            scoped_frames.append((frame, active_project))
        for frame, group in scoped_frames:
            if frame.quantity_basis == 'project_capacity_specification' and group is not None:
                frame = replace(frame, project_condition=conditions.get(group))
            frames.append(frame)
    return tuple(frames)
