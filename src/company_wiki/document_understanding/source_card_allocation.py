"""Finite whole-card allocation order over source-owned hints and coordinates."""
from collections import defaultdict

from .source_cards import SourceCard

SOURCE_CARD_ALLOCATION_VERSION = "source-card-allocation/2"


def _support_position(card: SourceCard):
    positions = []
    for span in card.support:
        c = span.coordinates
        if type(c.page_number) is not int or type(c.paragraph_index) is not int:
            return None
        positions.append((c.page_number, c.paragraph_index, c.char_start or 0))
    return min(positions) if positions else None


def source_allocation_order(cards):
    """Keep source priority; discover proof groups without starving early text.

    Coordinates break ties within a priority and original parent only. Unknown
    hints keep their slots; missing coordinates keep tie slots. Context never
    lends position/priority.
    No text is rendered, classified, truncated or given a new evidence identity.
    """
    ranked = []
    for slot, card in enumerate(cards):
        hint = card.reading_hint()
        if "priority" in hint:
            best = (hint["priority"],
                    0 if hint["value_band"] == "meaningful_fact" else 1,
                    -hint["score"])
            ranked.append((slot, best, card))
    by_priority = defaultdict(list)
    for slot, best, card in ranked:
        by_priority[best].append((slot, card))
    ordered: list[SourceCard] = []
    for priority in sorted(by_priority):
        bucket = by_priority[priority]
        positions = defaultdict(list)
        for index, (slot, card) in enumerate(bucket):
            source_position = _support_position(card)
            if source_position is not None:
                positions[card.task.source_id].append((index, source_position, slot, card))
        for entries in positions.values():
            for (index, *_), (_, _, slot, card) in zip(
                    entries, sorted(entries, key=lambda row: (row[1], row[2]))):
                bucket[index] = (slot, card)
        ordered.extend(card for _, card in bucket)
    result = list(cards)
    for (slot, _, _), card in zip(ranked, ordered):
        result[slot] = card
    return result

__all__ = [
    'SOURCE_CARD_ALLOCATION_VERSION',
    'source_allocation_order',
]
