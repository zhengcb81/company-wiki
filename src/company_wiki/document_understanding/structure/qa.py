"""QA exchange semantic units with role separation and preserved negation.

The management answer is the evidence; the question is only the prompt.  A
question that a manager denied must keep the denial inside the package, and a
question with no answer must not acquire an invented one.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
import re

from . import layout as layout_mod
from .contract import ObservationUnit

_QUESTION_MARK = re.compile(r"^\s*(?:\d{1,3}\s*[、.．]\s*)?(?:问|问题)\s*[:：]")
_ANSWER_MARK = re.compile(r"^\s*(?:答复|回答|答|回复)\s*[:：]")
_QUESTION_WORD = re.compile(r"[？?]|请问|请介绍|如何|是否|多少|什么|怎样|吗|能否")
_SENTENCE_END = re.compile(r"[。！？!?；;]+[”’\"'）】》」』]*")

ROLE_INVESTOR = "investor_question"
ROLE_MANAGEMENT = "management"


@dataclass
class QaDraft:
    semantic_id: str
    member_ids: list[str]
    question_ids: list[str]
    answer_ids: list[str]
    section_ids: list[str] = field(default_factory=list)
    completeness: str = "complete"
    diagnostics: list[dict] = field(default_factory=list)

    def as_wire(self) -> dict:
        return {
            "semantic_id": self.semantic_id,
            "kind": "qa_exchange",
            "section_ids": list(self.section_ids),
            "member_unit_ids": list(self.member_ids),
            "anchor_unit_ids": list(self.question_ids[:1]),
            "required_context_unit_ids": list(self.question_ids[:1]),
            "completeness": self.completeness,
            "diagnostics": list(self.diagnostics),
        }


def _is_question_start(unit: ObservationUnit) -> bool:
    if unit.kind in {"table_row", "table_header", "table_caption", "header", "footer"}:
        return False
    if _QUESTION_MARK.match(unit.text):
        return True
    if unit.speaker and unit.speaker.casefold() in {"investor", "analyst", "questioner"}:
        return True
    return False


def _is_answer_start(unit: ObservationUnit) -> bool:
    if _ANSWER_MARK.match(unit.text):
        return True
    if unit.speaker and unit.speaker.casefold() in {"management", "company", "speaker"}:
        return _QUESTION_WORD.search(unit.text) is None
    return False


def _ends_sentence(text: str) -> bool:
    return bool(_SENTENCE_END.search(text.rstrip())) or text.rstrip().endswith(
        ("，", ",", "、", "：", ":")
    )


def build_qa_exchanges(
    units: Sequence[ObservationUnit],
    ordering: layout_mod.Ordering,
    unit_section: dict[str, str],
    *,
    limits: dict[str, int],
    consumed: set[str],
) -> tuple[tuple[QaDraft, ...], tuple[dict, ...]]:
    diagnostics: list[dict] = []
    drafts: list[QaDraft] = []
    counter = 0
    current: QaDraft | None = None
    by_id = {unit.unit_id: unit for unit in units}

    def flush(draft: QaDraft | None) -> None:
        if draft is None:
            return
        if not draft.answer_ids:
            draft.completeness = "partial"
            draft.diagnostics.append(
                {
                    "code": "ANSWER_MISSING",
                    "unit_ids": list(draft.question_ids),
                    "detail": "question recognized without a matching answer unit",
                }
            )
        if len(draft.member_ids) > limits["max_group_members"]:
            draft.completeness = "partial"
            draft.diagnostics.append(
                {
                    "code": "GROUP_BUDGET_EXCEEDED",
                    "unit_ids": list(draft.member_ids[: limits["max_group_members"]]),
                    "detail": (
                        f"{len(draft.member_ids)} members exceed "
                        f"max_group_members={limits['max_group_members']}"
                    ),
                }
            )
        drafts.append(draft)

    for unit in ordering.ordered:
        if unit.unit_id in ordering.toc_ids or unit.unit_id in ordering.running_header_ids:
            continue
        section_ids = [unit_section[unit.unit_id]] if unit.unit_id in unit_section else []

        is_answer = _is_answer_start(unit)
        is_question = _is_question_start(unit)

        # An open question whose sentence ran off the bottom of the page keeps
        # its tail, even when that tail carries no marker of its own.  This is
        # checked first so the tail is not mistaken for a fresh question.
        if (
            current is not None
            and not is_answer
            and not current.answer_ids
            and _tail_open(current, by_id)
            and not layout_mod.is_heading(unit)
            and not unit.is_table_furniture
        ):
            current.member_ids.append(unit.unit_id)
            current.question_ids.append(unit.unit_id)
            consumed.add(unit.unit_id)
            continue

        if is_question:
            counter += 1
            flush(current)
            current = QaDraft(
                semantic_id=f"m{counter}",
                member_ids=[unit.unit_id],
                question_ids=[unit.unit_id],
                answer_ids=[],
                section_ids=section_ids,
            )
            consumed.add(unit.unit_id)
            continue

        if is_answer:
            if current is None:
                counter += 1
                current = QaDraft(
                    semantic_id=f"m{counter}",
                    member_ids=[],
                    question_ids=[],
                    answer_ids=[],
                    section_ids=section_ids,
                )
                current.diagnostics.append(
                    {
                        "code": "ANSWER_WITHOUT_QUESTION",
                        "unit_ids": [unit.unit_id],
                        "detail": "management answer found without a preceding question",
                    }
                )
                current.completeness = "partial"
            current.answer_ids.append(unit.unit_id)
            current.member_ids.append(unit.unit_id)
            consumed.add(unit.unit_id)
            continue

        if current is not None:
            if layout_mod.is_heading(unit):
                flush(current)
                current = None
                continue
            if unit.is_table_furniture:
                continue
            # A question that has not been answered yet only keeps absorbing
            # text when its own sentence is still unfinished (the IR question
            # that runs off the bottom of a page).  Otherwise a new topic
            # paragraph must not be swallowed into the previous exchange.
            if not current.answer_ids and not _tail_open(current, by_id):
                flush(current)
                current = None
                continue
            current.member_ids.append(unit.unit_id)
            if current.answer_ids:
                current.answer_ids.append(unit.unit_id)
            else:
                current.question_ids.append(unit.unit_id)
            consumed.add(unit.unit_id)
            continue

    flush(current)
    return tuple(drafts), tuple(diagnostics)


def _tail_open(draft: QaDraft, by_id: dict[str, ObservationUnit]) -> bool:
    """True when the exchange's last unit ends mid-sentence or mid-page-break."""
    last_id = draft.member_ids[-1] if draft.member_ids else None
    if last_id is None:
        return False
    last = by_id.get(last_id)
    if last is None:
        return False
    if not _ends_sentence(last.text):
        return True
    # A line that ends with a comma or an open clause on a page boundary is
    # still one sentence; a complete sentence is a new paragraph.
    return last.text.rstrip().endswith(("，", ",", "、"))


def qa_available(units: Sequence[ObservationUnit]) -> bool:
    return any(
        _is_question_start(unit) or _is_answer_start(unit) or unit.turn_id
        for unit in units
    )


__all__ = [
    "QaDraft",
    "ROLE_INVESTOR",
    "ROLE_MANAGEMENT",
    "build_qa_exchanges",
    "qa_available",
]
