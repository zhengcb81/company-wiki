"""Conservative whole-group duplicate removal for narrative candidates.

The dedup unit is the *event group* (the same ``selection_group_id`` that the
budget and the summary later use), never a bare text hash:

* one record per narrative unit (the richest enrichment wins),
* inside one group only identical text with the same source/role/language and
  question, speaker and table-header context collapses,
* across groups a group is removed only when its complete content is already
  carried by a surviving group (equal or contained signature), so no unique
  sentence and no group context is ever lost,
* mixed source/role/language/discourse groups split into collision-free ids;
  the ordered sentence sequence also has to match for cross-group removal.

Nothing here reads files, models, or global state: only the candidates and the
group mapping handed in are used, and every dropped member keeps its locator
plus text digest for auditing.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import hashlib
import json
import re

from .narrative_candidates import EvidenceCandidate


STATEMENT_ROLES = frozenset({"company_filing", "management"})
QUESTION_ROLES = frozenset({"analyst", "investor_question"})

_DROP_REASON_ORDER = (
    "same_unit_repeat",
    "intra_group_repeat",
    "duplicate_event_group",
    "contained_group",
)


@dataclass(frozen=True)
class DedupDrop:
    """One candidate left out of the package, with its real location."""

    unit_id: str
    locator: str
    group_id: str | None
    kept_unit_id: str | None
    reason: str
    text_sha256: str


@dataclass(frozen=True)
class DedupResult:
    """Survivors, their effective group ids, and every removal."""

    candidates: tuple[EvidenceCandidate, ...]
    group_ids: Mapping[str, str]
    drops: tuple[DedupDrop, ...]


def normalize_text(text: str) -> str:
    """Whitespace- and table-separator-insensitive comparison form."""
    return re.sub(r"\s+", "", text.replace("|", " ").replace("｜", " ")).casefold()


def role_class(source_role: str) -> str:
    if source_role in STATEMENT_ROLES:
        return "statement"
    if source_role in QUESTION_ROLES:
        return "question"
    return "other"


def _order_key(candidate: EvidenceCandidate) -> tuple[int, ...]:
    coordinates = candidate.unit.coordinates
    return tuple(
        -1 if value is None else value
        for value in (
            coordinates.page_number,
            coordinates.paragraph_index,
            coordinates.table_index,
            coordinates.row_index,
            coordinates.column_index,
            coordinates.char_start,
            coordinates.char_end,
        )
    )


def _unit_order(candidate: EvidenceCandidate) -> tuple[object, ...]:
    return (
        -candidate.score,
        0 if candidate.unit.unit_kind == "pdf_table_row" else 1,
        _order_key(candidate),
        candidate.unit.unit_id,
    )


def _candidate_order(candidate: EvidenceCandidate) -> tuple[object, ...]:
    return (
        -candidate.score,
        candidate.unit.coordinates.locator(),
        candidate.unit.unit_id,
    )


def _text_sha256(candidate: EvidenceCandidate) -> str:
    return hashlib.sha256(candidate.unit.raw_text.encode("utf-8")).hexdigest()


def _context_key(candidate: EvidenceCandidate) -> tuple[str, ...]:
    """Same words only prove a repeat within the same source and discourse."""
    unit = candidate.unit
    return (
        unit.source_id, unit.parser_name, unit.parser_version,
        unit.language, unit.source_role,
        *(json.dumps(unit.metadata.get(name), sort_keys=True, ensure_ascii=False)
          for name in ("qa_group_id", "qa_parent_id", "qa_question_number",
                       "speaker", "speaker_title", "section")),
    )


def _content_key(candidate: EvidenceCandidate) -> tuple[str, ...]:
    return (
        normalize_text(candidate.unit.raw_text),
        *_context_key(candidate),
        json.dumps(candidate.unit.metadata.get("table_headers"), sort_keys=True, ensure_ascii=False),
    )


def _signature(members: Sequence[EvidenceCandidate]) -> tuple[tuple[str, ...], ...]:
    return tuple(_content_key(member) for member in sorted(
        members, key=lambda item: (_order_key(item), item.unit.unit_id)
    ))


def _contained(signature: tuple[tuple[str, ...], ...], other: tuple[tuple[str, ...], ...]) -> bool:
    """Require the same sequence; a reversed set of sentences is not a repeat."""
    remaining = iter(other)
    return all(any(member == match for match in remaining) for member in signature)


def _output_group_ids(
    candidates: Sequence[EvidenceCandidate],
    group_ids: Mapping[str, str],
) -> dict[str, str]:
    """Keep homogeneous groups stable; split mixed identities without aliases."""
    contexts_by_group: dict[str, set[tuple[str, ...]]] = {}
    for candidate in candidates:
        input_group = group_ids.get(candidate.unit.unit_id)
        if input_group is None:
            continue
        contexts_by_group.setdefault(input_group, set()).add(_context_key(candidate))
    mixed = {
        group_id
        for group_id, contexts in contexts_by_group.items()
        if len(contexts) > 1
    }
    reserved = set(group_ids.values())
    generated: dict[tuple[str, tuple[str, ...]], str] = {}
    for input_group in sorted(mixed):
        for context in sorted(contexts_by_group[input_group]):
            digest = hashlib.sha256(json.dumps(context).encode("utf-8")).hexdigest()
            output = f"{input_group}:n6-context:{digest}"
            while output in reserved:
                output += ":split"
            reserved.add(output)
            generated[(input_group, context)] = output
    effective: dict[str, str] = {}
    for candidate in candidates:
        input_group = group_ids.get(candidate.unit.unit_id)
        if input_group is None:
            continue
        if input_group in mixed:
            effective[candidate.unit.unit_id] = generated[(input_group, _context_key(candidate))]
        else:
            effective[candidate.unit.unit_id] = input_group
    return effective


def _collapse_units(
    candidates: Sequence[EvidenceCandidate],
    group_ids: Mapping[str, str],
    drops: list[DedupDrop],
) -> list[EvidenceCandidate]:
    richest: dict[str, EvidenceCandidate] = {}
    for candidate in sorted(candidates, key=_unit_order):
        unit_id = candidate.unit.unit_id
        previous = richest.get(unit_id)
        if previous is None:
            richest[unit_id] = candidate
            continue
        drops.append(
            DedupDrop(
                unit_id=unit_id,
                locator=candidate.unit.coordinates.locator(),
                group_id=group_ids.get(unit_id),
                kept_unit_id=previous.unit.unit_id,
                reason="same_unit_repeat",
                text_sha256=_text_sha256(candidate),
            )
        )
    return list(richest.values())


def _collapse_within_groups(
    buckets: Mapping[str, Sequence[EvidenceCandidate]],
    effective_groups: Mapping[str, str],
    drops: list[DedupDrop],
) -> dict[str, list[EvidenceCandidate]]:
    kept_by_group: dict[str, list[EvidenceCandidate]] = {}
    for group_key, members in buckets.items():
        by_content: dict[tuple[str, ...], EvidenceCandidate] = {}
        for candidate in sorted(members, key=_unit_order):
            content_key = _content_key(candidate)
            previous = by_content.get(content_key)
            if previous is None:
                by_content[content_key] = candidate
                continue
            prefer_table = (
                candidate.unit.unit_kind == "pdf_table_row"
                and previous.unit.unit_kind != "pdf_table_row"
            )
            kept = candidate if prefer_table else previous
            dropped = previous if prefer_table else candidate
            by_content[content_key] = kept
            drops.append(
                DedupDrop(
                    unit_id=dropped.unit.unit_id,
                    locator=dropped.unit.coordinates.locator(),
                    group_id=effective_groups.get(dropped.unit.unit_id),
                    kept_unit_id=kept.unit.unit_id,
                    reason="intra_group_repeat",
                    text_sha256=_text_sha256(dropped),
                )
            )
        kept_by_group[group_key] = list(by_content.values())
    return kept_by_group


def deduplicate_candidates(
    candidates: Sequence[EvidenceCandidate],
    group_ids: Mapping[str, str],
) -> DedupResult:
    """Return survivors, effective group ids, and auditable drop records."""
    drops: list[DedupDrop] = []
    survivors = _collapse_units(candidates, group_ids, drops)
    effective_groups = _output_group_ids(survivors, group_ids)

    buckets: dict[str, list[EvidenceCandidate]] = {}
    for candidate in survivors:
        output_group = effective_groups.get(candidate.unit.unit_id)
        key = f"group:{output_group}" if output_group is not None else f"unit:{candidate.unit.unit_id}"
        buckets.setdefault(key, []).append(candidate)

    kept_by_group = _collapse_within_groups(buckets, effective_groups, drops)
    signatures = {
        group_key: _signature(members) for group_key, members in kept_by_group.items()
    }

    def canonical(group_key: str) -> tuple[object, ...]:
        members = kept_by_group[group_key]
        return (
            -max(candidate.score for candidate in members),
            min(_order_key(candidate) for candidate in members),
            tuple(sorted(candidate.unit.unit_id for candidate in members)),
        )

    ordered_keys = sorted(
        kept_by_group,
        key=lambda group_key: (-len(signatures[group_key]), canonical(group_key)),
    )
    surviving_keys: set[str] = set()
    # Only groups containing the first member can possibly cover this sequence.
    # Avoid an all-pairs scan for thousands of unrelated singleton candidates.
    covering: dict[tuple[str, ...], list[tuple[tuple[str, ...], ...]]] = {}
    group_drops: list[tuple[EvidenceCandidate, str, str | None]] = []
    for group_key in ordered_keys:
        signature = signatures[group_key]
        options = covering.get(signature[0], [])
        if any(_contained(signature, other) for other in options):
            reason = (
                "duplicate_event_group"
                if any(signature == other for other in options)
                else "contained_group"
            )
            for candidate in kept_by_group[group_key]:
                group_drops.append(
                    (candidate, reason, effective_groups.get(candidate.unit.unit_id))
                )
            continue
        surviving_keys.add(group_key)
        for content in set(signature):
            covering.setdefault(content, []).append(signature)

    kept = [
        candidate
        for group_key in sorted(surviving_keys)
        for candidate in kept_by_group[group_key]
    ]
    kept.sort(key=_candidate_order)

    paired: dict[tuple[str, ...], str] = {}
    for candidate in kept:
        paired.setdefault(_content_key(candidate), candidate.unit.unit_id)
    for candidate, reason, output_group in group_drops:
        drops.append(
            DedupDrop(
                unit_id=candidate.unit.unit_id,
                locator=candidate.unit.coordinates.locator(),
                group_id=output_group,
                kept_unit_id=paired.get(_content_key(candidate)),
                reason=reason,
                text_sha256=_text_sha256(candidate),
            )
        )
    drops.sort(
        key=lambda drop: (
            _DROP_REASON_ORDER.index(drop.reason),
            drop.locator,
            drop.unit_id,
        )
    )

    kept_ids = {candidate.unit.unit_id for candidate in kept}
    return DedupResult(
        candidates=tuple(kept),
        group_ids={
            unit_id: effective_groups[unit_id]
            for unit_id in sorted(kept_ids)
            if unit_id in effective_groups
        },
        drops=tuple(drops),
    )


__all__ = [
    "DedupDrop",
    "DedupResult",
    "deduplicate_candidates",
    "normalize_text",
    "role_class",
]
