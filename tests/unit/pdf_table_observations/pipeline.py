"""Real production pipeline helpers (parse → observation → layout hints).

Only the existing public entrypoints are used; nothing here is written or read
by the component under test.  One call = one parse, mirroring the C-node rule
that the component never repeats the parser's work.
"""

from __future__ import annotations

import hashlib
from typing import Any

PARSE_COUNT = {"n": 0}


def parse_and_observe(raw: bytes, *, language: str = "en", table_pages=()) -> tuple:
    import pytest

    pytest.importorskip("fitz")
    from company_wiki.document_understanding.layout_bridge import apply_layout_hints
    from company_wiki.document_understanding.layout_hints.contract import WorkBudget
    from company_wiki.document_understanding.observation_adapter import build_observation
    from company_wiki.source_catalog.narrative_evidence import parse_pdf_bytes
    from company_wiki.source_contract import source_id_for_sha256

    digest = hashlib.sha256(raw).hexdigest()
    common: dict[str, Any] = {
        "source_id": source_id_for_sha256(digest),
        "source_sha256": digest,
        "language": language,
    }
    PARSE_COUNT["n"] += 1
    parsed = parse_pdf_bytes(
        raw, **common, selector_version="0.9.0", table_pages=tuple(table_pages)
    )
    observation = build_observation(
        parsed.units,
        **common,
        mime_type="application/pdf",
    )
    budget = WorkBudget(2_000_000)
    observation, hints = apply_layout_hints(observation, work_budget=budget)
    return parsed, observation, hints, budget
