"""Observe printed turns without changing PDF text, coordinates or replay roles."""

from collections.abc import Mapping, Sequence
from dataclasses import replace
import re
from typing import Any

from company_wiki.document_model.narrative import DocumentStructure, NarrativeUnit
from company_wiki.document_model.turns import (
    DISCLOSURE_HEADING, END, NATURAL_START, QA_HEADING,
    declared_speaker_role, legacy_speaker_fields, speaker_fields,
)
from company_wiki.document_understanding.source_turn_markers import ROLE_INVESTOR, explicit_qa_marker
from company_wiki.resource_budget import WorkBudget


_SENTENCE_GAP = re.compile(r"[.!?。！？][”’\"）】]?\s+")
_PRINTED_LABEL_PREFIX = 192


def _later_label(line: str) -> bool:
    """Detect a second printed role at a sentence boundary, not a quoted word."""
    for boundary in _SENTENCE_GAP.finditer(line):
        start = boundary.end()
        prefix = line[start:start + _PRINTED_LABEL_PREFIX]
        if explicit_qa_marker(prefix) is not None:
            return True
        name, title, _, _ = speaker_fields([prefix], 0, legacy_speaker_fields, allow_affiliation=True)
        if name is not None and declared_speaker_role(name, title or "") != "unknown":
            return True
    return False


def _block_turn(unit: NarrativeUnit) -> tuple[dict[str, Any] | None, int, bool]:
    offset = 0
    body_end = len(unit.raw_text)
    preamble = True
    turn: dict[str, Any] | None = None
    ended = False
    qa_section = False
    for line in unit.raw_text.splitlines(keepends=True):
        value = line.strip()
        qa_heading = QA_HEADING.fullmatch(value) is not None
        if END.fullmatch(value) or DISCLOSURE_HEADING.fullmatch(value) or (
            qa_heading and (turn is not None or not preamble)
        ):
            body_end = offset
            ended = True
            break
        qa_section |= qa_heading
        if _later_label(value):
            return {"role": "mixed"}, body_end, ended
        qa_role = explicit_qa_marker(value)
        name, title, body, _ = speaker_fields([value], 0, legacy_speaker_fields, allow_affiliation=True)
        if qa_role is not None or name is not None:
            if turn is not None or not preamble:
                # There is no single source role for this physical block.
                turn = {"role": "mixed"}
            elif qa_role is not None:
                # A question is context. An answer marker alone does not prove its speaker.
                turn = {"role": "analyst" if qa_role == ROLE_INVESTOR else "unknown"}
            else:
                content_end = offset + len(line.rstrip())
                body_start = content_end - len(body) if body else offset + len(line)
                turn = {
                    "speaker": name, "title": title or "",
                    "role": declared_speaker_role(name, title or ""), "body_start": body_start,
                }
        elif value and not (NATURAL_START.fullmatch(value) or qa_heading):
            preamble = False
        offset += len(line)
    if turn is not None and "body_start" in turn:
        body_start = turn["body_start"]
        while body_start < body_end and unit.raw_text[body_start].isspace():
            body_start += 1
        turn.update(body_start=body_start, body_end=body_end)
    return turn or ({"role": "unknown"} if qa_section else None), body_end, ended


def printed_pdf_turns(
    units: Sequence[NarrativeUnit], *, work_budget: WorkBudget | None = None,
) -> dict[str, dict[str, Any]]:
    """Follow printed role boundaries in the same order as physical PDF prose."""
    observed: dict[str, dict[str, Any]] = {}
    active: dict[str, Any] | None = None
    previous_source: str | None = None
    previous_page: int | None = None
    for unit in units:
        if unit.unit_kind != "pdf_text_block":
            continue  # Table enhancement can differ between selection and replay.
        if work_budget is not None:
            work_budget.charge(3 * len(unit.raw_text) + 1)
        page = unit.coordinates.page_number
        if unit.source_id != previous_source:
            active = None
        elif active is not None and previous_page is not None and page is not None and page > previous_page + 1:
            # A missing intervening page can contain a new speaker.
            active = {**active, "role": "unknown"}
        previous_source, previous_page = unit.source_id, page
        turn, body_end, ended = _block_turn(unit)
        label = {"turn_id": unit.unit_id, "label_locator": unit.coordinates.locator()}
        if turn is not None:
            observed[unit.unit_id] = {**label, **turn}
            active = {**label, **{key: value for key, value in turn.items()
                                  if key not in {"body_start", "body_end"}}}
        elif (ended and body_end == 0) or (active is not None and NATURAL_START.fullmatch(unit.raw_text)):
            active = {**label, "role": "unknown"}
            observed[unit.unit_id] = active
        elif active is not None:
            observed[unit.unit_id] = {**active, "body_start": 0, "body_end": body_end}
        if ended:
            active = {**label, "role": "unknown"}
    return observed


def observe_pdf_transcript_turns(parsed: DocumentStructure, *, work_budget: WorkBudget) -> DocumentStructure:
    """Annotate only the transcript strategy's already parsed PDF prose."""
    observed = printed_pdf_turns(parsed.units, work_budget=work_budget)
    return replace(parsed, units=tuple(
        replace(unit, metadata={**unit.metadata, "printed_turn": observed[unit.unit_id]})
        if unit.unit_id in observed else unit for unit in parsed.units
    ))


def printed_turn_is_context(unit: Any) -> bool:
    metadata = unit.get("metadata", {}) if isinstance(unit, Mapping) else getattr(unit, "metadata", {})
    turn = metadata.get("printed_turn") if isinstance(metadata, Mapping) else None
    return isinstance(turn, Mapping) and turn.get("role") != "management"
