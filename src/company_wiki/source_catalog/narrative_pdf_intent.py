"""Execute the shared geometry plan over the parser's current native material.

Navigation allocates resources only. Actual table qualification remains with
the structure owner. No originals, page snapshots or second task store persist.
"""
from __future__ import annotations

from collections import Counter
from typing import Any

from company_wiki.document_understanding.geometry_intent import (
    admit_geometry_request, new_admission_state, summarize_admission_state,
)
from company_wiki.document_understanding.geometry_intent.reading import (
    PdfReadingContext, prepare_geometry_reading,
)
from company_wiki.resource_budget import WorkBudgetExceeded
from .narrative_pdf_candidates import observe_pdf_candidate

PDF_INTENT_EXECUTION_VERSION = "pdf-reading-execution/1"
# Unknown navigation is exploratory work, not an instruction to fully analyse
# the document again. Reserve seven eighths of the existing account for matched
# reading intent, native extraction and the downstream semantic selector.
UNKNOWN_NAVIGATION_WORK_DIVISOR = 8
UNKNOWN_NAVIGATION_MAX_WORK = 250_000


class SourceGeometrySession:
    """One source round, one shared account and one original PLANNER state."""

    def __init__(self, units, *, context, state, outline, budget, collector):
        self.budget = budget
        self.collector = collector
        self.prepared = prepare_geometry_reading(units, context=context or PdfReadingContext(),
            source_id=state.source_id, source_sha256=state.source_sha256,
            native_outline=outline, page_count=state.page_count,
            limits={'max_pages': collector.limits['max_pages'], 'max_requests': collector.limits['max_pages']},
            work_budget=budget)
        self.plan = self.prepared['plan']
        self.state = new_admission_state(self.plan)
        self.reasons: Counter[str] = Counter()
        self.deferred: set[int] = set()
        self.blocked = self.prepared.get('blocked_navigation', ())
        self.explored: set[int] = set()
        self.maximum = collector.limits['max_pages']
        self.explore_limit = max(0, self.maximum - self.plan['summary']['pages_reserved'])
        self.navigation_missing = not outline or self.prepared['partial']
        self.unresolved = self.prepared.get('unresolved_navigation', ())
        self.exploration_budget = budget.scoped(min(UNKNOWN_NAVIGATION_MAX_WORK,
            budget.max_work_units // UNKNOWN_NAVIGATION_WORK_DIVISOR))
        self.parser_version = state.parser_version
        self.previous_signature = None

    def request(self, page, snapshot):
        try:
            self.budget.charge()
            self.budget.charge(len(self.blocked))
            if any(row['physical_start'] <= page <= row['physical_end'] for row in self.blocked):
                self.deferred.add(page)
                self.reasons['navigation_conflict_deferred'] += 1
                self.previous_signature = None
                return False, False
            if self.collector.exhausted or not self.maximum:
                self.reasons['resource_deferred'] += 1
                self.deferred.add(page)
                return False, False
            self.budget.charge(len(self.plan['allocations']))
            covering = [row for row in self.plan['allocations']
                        if row['physical_start'] <= page <= row['physical_end']]
            keys = [row['window_key'] for row in covering if row['status'] == 'reserved']
            self.budget.charge(len(self.unresolved))
            unexplained = not covering and any(
                row['physical_start'] <= page <= row['physical_end'] for row in self.unresolved)
            exploration_allowed = self.navigation_missing or unexplained
            if not keys and not exploration_allowed:
                self.previous_signature = None
                self.reasons['not_requested_by_intent'] += 1
                if any(row.get('consumable') for row in covering):
                    self.deferred.add(page)
                    self.reasons['plan_capacity_deferred'] += 1
                return False, False
            observation = observe_pdf_candidate(snapshot,
                work_budget=self.budget if keys else self.exploration_budget,
                qa=self.prepared['route'].get('family') == 'investor_qa',
                parser_version=self.parser_version, previous=self.previous_signature)
            self.previous_signature = observation['continuation']
            candidate = observation['candidate']
            if observation['partial']:
                self.deferred.add(page)
                self.reasons['candidate_observation_partial'] += 1
            if keys:
                decision, self.state = admit_geometry_request(self.plan, self.state,
                    page=page, window_keys=keys[:64],
                    tabular_evidence='observed_candidate' if candidate else
                                     'unknown' if observation['partial'] else 'absent',
                    remaining=max(0, self.maximum - len(self.explored) - self.state['spent']['pages']))
                self.reasons[decision['decision']] += 1
                if candidate and decision['decision'] == 'exhausted':
                    self.deferred.add(page)
                request = decision.get('request') or {}
                return bool(request.get('discover')), bool(request.get('fine'))
            # No navigation means no defensible global section allocation.
            # Limited online exploration borrows only unreserved capacity from
            # the same collector limit; it is explicitly not a matched policy.
            if candidate and exploration_allowed and len(self.explored) < self.explore_limit:
                self.budget.charge()
                self.explored.add(page)
                self.reasons['unknown_navigation_exploration'] += 1
                return True, True
            if candidate and exploration_allowed:
                self.deferred.add(page)
                self.reasons['exploration_deferred'] += 1
            else:
                self.reasons['not_requested_by_intent'] += 1
            return False, False
        except WorkBudgetExceeded:
            self.deferred.add(page)
            self.reasons['work_budget_exhausted'] += 1
            return False, False

    def summary(self):
        return {'feature_version': PDF_INTENT_EXECUTION_VERSION,
                'request_digest': self.prepared['request_digest'],
                'profile_id': self.prepared['resolved_profile']['profile_id'],
                'profile_scope': {key: self.prepared['resolved_profile'].get(key, 'unknown')
                                  for key in ('profile_id', 'family', 'regime', 'form_type')},
                'policy_digest': self.prepared['policy']['content_digest'],
                'route': self.prepared['route'],
                'plan_digest': self.plan['plan_digest'],
                'complete': not self.prepared['partial'] and not self.deferred and not self.budget.exhausted
                            and not self.navigation_missing and not self.unresolved and not self.blocked,
                'navigation_missing': self.navigation_missing,
                'unresolved_navigation_count': len(self.unresolved),
                'window_count': len(self.prepared['windows']),
                'reason_counts': dict(self.reasons),
                'exploration_pages': sorted(self.explored)[:64],
                'deferred_pages': sorted(self.deferred)[:128],
                'deferred_page_count': len(self.deferred),
                'diagnostics': self.prepared['diagnostics'],
                'admission': summarize_admission_state(self.plan, self.state)}


def scan_planned_pages(state, document, *, reading_context, work_budget):
    """Reuse two cover pages, then emit in physical order without a second parse."""
    from .narrative_evidence import (
        _emit_pdf_page, _emit_pdf_text_units, _pdf_text_blocks, _record_pdf_native_view,
    )

    collector = state.layout_collector
    collector.defer_capture = True
    collector.capture_mode = 'reading-policy'
    collector.source_page_count = state.page_count
    budget = work_budget
    session: SourceGeometrySession | None = None
    cover: list[tuple[int, list[Any]]] = []
    try:
        try:
            budget.charge()
            outline = document.get_toc(simple=True)
        except (AttributeError, RuntimeError, ValueError):
            outline = []

        def prepare():
            # Generate actual canonical cover units once using the existing
            # source emitter, then let physical-order emission reuse them.
            probes: list[Any] = []
            for number, blocks in cover:
                start = len(state.units)
                _emit_pdf_text_units(state, number, blocks)
                members = tuple(state.units[start:])
                state.prepared_text_units[number] = members
                probes.extend(members)
                del state.units[start:]
            return SourceGeometrySession(tuple(probes), context=reading_context,
                state=state, outline=outline, budget=budget, collector=collector)

        def emit(number, blocks):
            if session is None:
                raise RuntimeError("geometry session is not prepared")
            material = collector.pending_pages.get(number)
            discover, fine = session.request(number, material[2] if material else {})
            collector.capture_pending_page(number, requested=fine)
            if discover:
                state.table_scan_pages.add(number)
            _emit_pdf_page(state, document, number, blocks)

        for number, page in enumerate(document, start=1):
            try:
                geometry: dict[str, Any] = {}
                blocks = _pdf_text_blocks(page, geometry_out=geometry,
                                          layout_collector=collector, page_number=number)
                state.page_geometry[number] = geometry
                _record_pdf_native_view(state, number, blocks)
                state.pages_read += 1
                if not blocks:
                    state.empty_pages.add(number)
            except Exception as exc:
                state.errors.append(f'page_text:{number}:{type(exc).__name__}')
                state.empty_pages.add(number)
                blocks = []
            if session is None:
                cover.append((number, blocks))
                if len(cover) < 2 and number < state.page_count:
                    continue
                session = prepare()
                state.geometry_session = session
                for previous in cover:
                    emit(*previous)
                cover.clear()
            else:
                emit(number, blocks)
        if session is None:
            session = prepare()
        state.geometry_session = session
    finally:
        collector.pending_pages.clear()
        collector.pages.clear()
