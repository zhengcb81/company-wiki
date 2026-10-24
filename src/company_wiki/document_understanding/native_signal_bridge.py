"""Project existing native carriers to the single source-signal collector."""
from collections.abc import Mapping
from typing import Any

from .layout_hints.contract import WorkBudget
from .source_signals import collect_source_signals


def collect_native_signals(observation: Mapping[str, Any], *, work_budget: WorkBudget) -> dict:
    units = {}
    carriers = []
    parent = observation['source_ref']['source_id']
    mime = (observation.get('metadata') or {}).get('mime_type')
    for raw in observation.get('units', ()):
        work_budget.charge()
        hints = raw.get('hints') or {}
        uid = raw['unit_id']
        owner = hints.get('source_id') or parent
        # The neutral adapter permits absent role/kind. Unknown stays unknown;
        # source-signal validation must not turn optional parser metadata into
        # a new prerequisite for reading an otherwise valid document.
        units[uid] = {'text': raw['text'], 'parent_id': owner, 'role': raw.get('role') or 'unknown',
                      'kind': raw.get('kind') or 'unknown', 'locator': raw.get('locator')}
        for carrier in hints.get('native_source_carriers', ()):
            work_budget.charge()
            # Reserve the actual native string ranges before the collector
            # slices/normalizes them. Never infer an absent native carrier.
            for ref in carrier.get('value_refs', ()):
                work_budget.charge()
                work_budget.charge(max(0, ref['char_end'] - ref['char_start']))
            carriers.append(carrier)
        native_turn = hints.get('native_speaker_turn')
        if native_turn or (mime == 'text/plain' and raw.get('role') in {'management', 'operator', 'investor_question'}):
            speaker = hints.get('native_speaker') or hints.get('speaker')
            if speaker:
                work_budget.charge()
                carriers.append({'kind': 'native_speaker_turn', 'parent_id': owner,
                    'unit_ids': [uid], 'value_refs': [], 'attributes': {
                        'speaker': speaker, 'turn_id': hints.get('turn_id') or uid,
                        'turn_role': ('unknown' if native_turn else
                                      'analyst' if raw['role']=='investor_question' else 'prepared_remarks')}})
    return collect_source_signals({'schema_version':'du4-source-signal-observation/1',
        'units':units, 'carriers':carriers,
        'declared_form':(observation.get('metadata') or {}).get('form_type')}, work_budget=work_budget)
