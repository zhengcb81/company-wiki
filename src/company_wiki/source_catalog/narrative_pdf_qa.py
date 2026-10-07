"""Pure, range-preserving PDF-cell Q&A parsing for parser 0.1.1.

The legacy parser remains dispatched by its existing caller. This module has
no storage, selector, provider or model dependency: markers only describe the
source's discourse, and each emitted sentence is an exact trimmed cell slice.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any


QA_FRAGMENT_VERSION = '0.1.1'
_EXPLICIT = re.compile(r'(?m)(?:^|\n|\s)(?P<number>\d{1,3}\s*[、.．]\s*)?(?:问|问题)\s*[:：]')
_NUMBERED = re.compile(r'(?m)^[ \t]*(?P<number>\d{1,3})[ \t]*[:：][ \t]*'
                       r'(?:(?:问|问题)[ \t]*[:：][ \t]*)?')
_ANSWER = re.compile(r'(?:答复|回答|答|回复)\s*[:：]')
_QUESTION_WORD = re.compile(r'[？?]|请问|请介绍|如何|是否|多少|什么|怎样|吗|能否')
_SENTENCE_END = re.compile(r'[。！？!?；;]+[”’"\'）】》」』]*')


@dataclass(frozen=True)
class PdfQuestion:
    start: int
    end: int
    number: str | None


def question_markers(text: str) -> tuple[PdfQuestion, ...]:
    """Recognize explicit markers and conservative line-start numeric questions."""
    explicit = [PdfQuestion(m.start(), m.end(),
                            (m.group('number') or '').strip(' 、.．') or None)
                for m in _EXPLICIT.finditer(text)]
    numbered = list(_NUMBERED.finditer(text))
    accepted: list[PdfQuestion] = []
    for index, match in enumerate(numbered):
        if match.end() == len(text) or text[match.end()].isdigit():
            continue  # clock times and numeric ratios
        next_start = numbered[index + 1].start() if index + 1 < len(numbered) else len(text)
        next_explicit = next((q.start for q in explicit if q.start >= match.end()), len(text))
        end = min(next_start, next_explicit, match.end() + 2_000)
        answer = _ANSWER.search(text, match.end(), end)
        body = text[match.end():answer.start() if answer else end]
        if not _QUESTION_WORD.search(body):
            continue
        accepted.append(PdfQuestion(match.start(), match.end(), match.group('number')))
    markers = accepted + [q for q in explicit
                          if not any(n.start <= q.start < n.end for n in accepted)]
    return tuple(sorted(markers, key=lambda q: q.start))


def _part(text: str, start: int, end: int, *, role: str, state: str,
          group: str | None, number: str | None) -> dict[str, Any] | None:
    while start < end and text[start].isspace():
        start += 1
    while end > start and text[end - 1].isspace():
        end -= 1
    if start == end:
        return None
    return {'text': text[start:end], 'start': start, 'end': end, 'role': role,
            'state': state, 'qa_group_id': group, 'question_number': number}


def _sentences(text: str, start: int, end: int, *, state: str,
               group: str | None, number: str | None) -> list[dict[str, Any]]:
    parts: list[dict[str, Any]] = []
    boundaries = [m.end() for m in _SENTENCE_END.finditer(text, start, end)]
    for right in (*boundaries, end):
        part = _part(text, start, right, role='management', state=state, group=group, number=number)
        if part:
            parts.append(part)
        start = right
    return parts


def _prefix(text: str, end: int, *, has_question: bool) -> list[dict[str, Any]]:
    answer = _ANSWER.search(text, 0, end)
    if answer is None:
        part = _part(text, 0, end, role='unknown', state='before_first_question',
                     group=None, number=None) if has_question else None
        return [part] if part else []
    question_tail = _part(text, 0, answer.start(), role='investor_question',
                          state='question_continuation', group=None, number=None)
    parts = [question_tail] if question_tail else []
    parts.extend(_sentences(text, answer.start(), end, state='answer_continuation',
                            group=None, number=None))
    return parts


def pdf_qa_parts(text: str, *, group_prefix: str) -> list[dict[str, Any]]:
    questions = question_markers(text)
    parts = _prefix(text, questions[0].start if questions else len(text), has_question=bool(questions))
    for index, question in enumerate(questions):
        end = questions[index + 1].start if index + 1 < len(questions) else len(text)
        answer = _ANSWER.search(text, question.end, end)
        group = f'{group_prefix}:q{index + 1}'
        part = _part(text, question.start, answer.start() if answer else end,
                     role='investor_question', state='question_paired' if answer else 'question_unanswered',
                     group=group, number=question.number)
        if part:
            parts.append(part)
        if answer:
            parts.extend(_sentences(text, answer.start(), end, state='answer_paired',
                                    group=group, number=question.number))
    return parts


__all__ = ['QA_FRAGMENT_VERSION', 'pdf_qa_parts', 'question_markers']
