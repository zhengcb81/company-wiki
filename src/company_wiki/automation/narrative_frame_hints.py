"""Compact annotations of existing factual fragments, with no copied prose."""
from collections.abc import Iterable
from typing import Any

from company_wiki.document_understanding.assertion_frames import source_assertion_frames

MAX_HINTS_PER_SOURCE = 64
MAX_HINTS = 256


def compact_frame_hints(parts: Iterable[tuple[str, str]]) -> dict[str, Any]:
    """Source keys/ordinals are model references, never new evidence locators."""
    unique: dict[str, str] = {}
    for key, text in parts:
        if key in unique and unique[key] != text:
            raise ValueError('one source key refers to different fragment text')
        unique[key] = text
    sources: dict[str, list[dict[str, Any]]] = {}
    observed = retained = 0
    for key, text in unique.items():
        rows: list[dict[str, Any]] = []
        for ordinal, frame in enumerate(source_assertion_frames(text)):
            flags: dict[str, Any] = {}
            for name, value in (('ongoing', frame.ongoing_activity),
                                ('future', frame.future_marker),
                                ('reported', bool(frame.reporting_prefix)),
                                ('inherits_reporting', frame.reporting_inherited),
                                ('condition_present', bool(frame.project_condition))):
                if value:
                    flags[name] = True
            if frame.quantity_basis is not None:
                flags['quantity_basis'] = frame.quantity_basis
            if not flags:
                continue
            observed += 1
            if len(rows) < MAX_HINTS_PER_SOURCE and retained < MAX_HINTS:
                rows.append({'ordinal': ordinal, **flags})
                retained += 1
        if rows:
            sources[key] = rows
    return {'schema_version': 'source-frame-hints/1',
            'interpretation': 'finite_source_observations_not_business_facts',
            'sources': sources, 'observed_count': observed, 'limited': observed > retained}
