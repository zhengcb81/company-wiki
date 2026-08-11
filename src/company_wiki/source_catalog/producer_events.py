"""FC-905-a: producer-event journal reads (append-only trace).

Every artifact INSERT is journaled by the ``trg_artifact_producer_event``
trigger into ``producer_events``.  Consumers derive parser/LLM counts from
this journal — never from the resolution output.  Reads only; the journal is
written exclusively by the trigger.
"""

from __future__ import annotations

from typing import Any


def count_producer_events(
    store: Any, document_id: str,
) -> dict[str, int]:
    """Return {'parser_calls': n, 'llm_calls': m} for the document.

    ``store`` must expose ``fetchone(sql, params)`` (CatalogStore-compatible).
    The counts are the journal's event_type tallies — zero means the journal
    exists and recorded no such event (honest), not an absence of evidence.
    """
    parser = store.fetchone(
        "SELECT COUNT(*) AS n FROM producer_events "
        "WHERE document_id=? AND event_type='parser'",
        (document_id,),
    )
    llm = store.fetchone(
        "SELECT COUNT(*) AS n FROM producer_events "
        "WHERE document_id=? AND event_type='llm'",
        (document_id,),
    )
    return {
        "parser_calls": int(parser[0] if parser is not None else 0),
        "llm_calls": int(llm[0] if llm is not None else 0),
    }
