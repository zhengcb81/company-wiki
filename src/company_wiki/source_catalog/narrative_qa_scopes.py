"""Closed answer scopes over source-owned QA records, before budget projection.

No document IO, geometry claims, second classifier or work account. Structural
QA association permits a bounded answer sequence; existing source semantics
decide dependencies. The original QA parent and original units remain intact.
"""
from __future__ import annotations

from hashlib import sha256
from typing import Any

from company_wiki.resource_budget import WorkBudgetExceeded
from company_wiki.document_understanding.operating_states.relations import (
    closed_source_statement, independent_statement_start,
    source_courtesy_statement,
)
from .narrative_antecedent import MAX_WINDOW_UNITS, MAX_ENVELOPE_CHARS

QA_SCOPE_FEATURE_VERSION = 'source-qa-scopes/1'


def _validate_fragment_order(answers, units, budget):
    previous = None
    for uid in answers:
        unit = units[uid]
        meta, coordinates = unit.metadata, unit.coordinates
        start, end = meta.get('cell_fragment_start'), meta.get('cell_fragment_end')
        if start is None and end is None:
            previous = None
            continue
        budget.charge(1 + len(unit.raw_text))
        if type(start) is not int or type(end) is not int or start < 0 or end-start != len(unit.raw_text):
            raise ValueError('qa_fragment_range_invalid')
        key = (unit.source_id, coordinates.page_number, coordinates.table_index,
               coordinates.row_index, coordinates.column_index, meta.get('cell_sha256'))
        if previous is not None and previous[0] == key:
            if start < previous[1]:
                raise ValueError('qa_fragment_order_invalid')
            cells = meta.get('row_cells', ())
            column = coordinates.column_index
            if (type(column) is not int or not 0 <= column < len(cells)
                    or not isinstance(cells[column], str)):
                raise ValueError('qa_fragment_gap_unobserved')
            cell = cells[column]
            budget.charge(start-previous[1] + len(unit.raw_text))
            if cell[previous[1]:start].strip() or cell[start:end] != unit.raw_text:
                raise ValueError('qa_fragment_gap_unread')
        previous = (key, end)


def _segments(ids, units, budget, dependencies):
    """Split only closed, independently started source statements/courtesies.

    A dependent continuation, unfinished fragment or postposed restriction is
    retained with its preceding source range, never guessed into a new fact.
    """
    result: list[list[str]] = []
    pending: list[str] = []
    previous_closed = False
    for uid in ids:
        text = units[uid].raw_text
        budget.charge(8 * len(text) + 1)
        courtesy = source_courtesy_statement(text)
        # An explicit new source subject does not become dependent merely
        # because a later clause contains a plan, negation or “其中”. Actual
        # deictic/restriction dependencies are closed by the shared owner below.
        independent = independent_statement_start(text)
        if pending and previous_closed and (courtesy or independent or uid in dependencies):
            result.append(pending)
            pending = []
        pending.append(uid)
        previous_closed = closed_source_statement(text)
    if pending:
        result.append(pending)
    return result


def close_qa_packages(packages, budget_packages, session):
    """Return same-index original/material packages and explicit partials.

    Called once before any index-addressed dependency sidecars are populated.
    Non-QA packages retain their exact object and behavior. The caller's one
    session owns all relation/reference work and immutable support owners.
    """
    if len(packages) != len(budget_packages):
        raise ValueError('source/material package index mismatch')
    originals: list[dict[str, Any]] = []
    material: list[dict[str, Any]] = []
    withheld: list[dict[str, Any]] = []
    units, budget = session.units, session.work_budget
    position = None
    for index in range(len(packages)):
        package, projected = packages[index], budget_packages[index]
        try:
            budget.charge()
            if package['kind'] != 'qa_exchange':
                originals.append(package)
                material.append(projected)
                continue
            ids = package.get('member_unit_ids', ())
            anchors = package.get('anchor_unit_ids', ())
            required = package.get('required_context_unit_ids', ())
            budget.charge(len(ids) + len(anchors) + len(required) + 1)
            if (package.get('completeness') == 'partial' or package.get('truncated') or len(ids) > 64
                    or any(uid not in units for uid in (*ids, *required))):
                raise ValueError('qa_member_scope_incomplete')
            # Structure owns record/role pairing. Validate its actual ID domain,
            # not a second interpretation of group-name strings or text.
            if any(package.get(key, ()) != projected.get(key, ()) for key in (
                    'member_unit_ids', 'anchor_unit_ids', 'required_context_unit_ids')):
                raise ValueError('qa_material_scope_changed')
            selected = set(anchors)
            answers = [uid for uid in ids if uid in selected]
            if not answers:
                originals.append(package)
                material.append(projected)
                continue
            source = units[answers[0]].source_id
            if any(units[uid].source_id != source for uid in (*ids, *required)):
                raise ValueError('qa_source_scope_mismatch')
            if (len(answers) > MAX_WINDOW_UNITS
                    or sum(len(units[uid].raw_text) for uid in answers) > MAX_ENVELOPE_CHARS):
                raise ValueError('qa_scope_window_clipped')
            _validate_fragment_order(answers, units, budget)
            # Prepare immutable answer-only owners. Model questions are never
            # semantic predecessors or actor donors.
            owners = {uid: session.support_owner((uid,)) for uid in answers}
            extra, intrinsic = {}, {}
            for offset, uid in enumerate(answers):
                budget.charge(1 + offset)
                predecessors = tuple(answers[:offset])
                session.antecedents[owners[uid]] = (predecessors, not package.get('truncated', False))
                closure = session.reference(owners[uid])
                if closure['status'] in {'ambiguous', 'missing', 'partial'}:
                    raise ValueError('qa_reference_' + closure['status'])
                needed = set(closure.get('required_original_unit_ids', ()))
                if not needed <= set(answers):
                    raise ValueError('qa_reference_outside_answer')
                extra[uid] = needed
                intrinsic[uid] = (set(closure.get('support_original_unit_ids', ()))
                                  if closure.get('reference_kind') == 'causal_result' else set())
            # Reuse the semantic pair matcher after this actual QA sequence
            # established scope. Do not create source_body_adjacency edges.
            bound_heads: dict[str, str] = {}
            qualification_roots: dict[str, tuple[str, int, int]] = {}
            for offset, right in enumerate(answers):
                matches = []
                for left in answers[:offset]:
                    budget.charge()
                    left_scope = session._source_material_range(left, left)
                    right_scope = session._source_material_range(right, right)
                    if left_scope is None or right_scope is None:
                        raise ValueError('qa_original_range_unavailable')
                    matched = session._qualification_pair(left, right, left_scope, right_scope,
                        inherited_head=bound_heads.get(left), left_owner=owners[left],
                        right_owner=owners[right], qa_sequence=True)
                    if matched is not None:
                        matches.append((left, matched))
                identities = {qualification_roots.get(left, matched.object_ref)
                              if matched.object_ref is not None else ('scope', left)
                              for left, matched in matches}
                if len(identities) > 1:
                    raise ValueError('qa_qualification_ambiguous')
                if matches:
                    matched = matches[0][1]
                    if matched.head and matched.object_ref is not None:
                        bound_heads[right] = matched.head
                        qualification_roots[right] = qualification_roots.get(matches[0][0], matched.object_ref)
                    for left, _ in matches:
                        intrinsic.setdefault(left, set()).add(right)
                        intrinsic.setdefault(right, set()).add(left)
            dependent_ids = {uid for uid in answers if extra.get(uid) or intrinsic.get(uid)}
            segments = _segments(answers, units, budget, dependent_ids)
            # Necessary support dependencies merge components; ordinary product
            # declarations remain context and cannot donate another predicate.
            groups = [set(segment) for segment in segments]
            for uid, dependencies in intrinsic.items():
                related = {uid, *dependencies}
                merged = set(related)
                keep = []
                for group in groups:
                    budget.charge(1 + len(group))
                    if group & related:
                        merged.update(group)
                    else:
                        keep.append(group)
                groups = [*keep, merged]
            if position is None:
                budget.charge(len(units))
                position = {uid: n for n, uid in enumerate(units)}
            groups.sort(key=lambda group: min(position[uid] for uid in group))
            children = []
            for group in groups:
                support = tuple(sorted(group, key=position.__getitem__))
                context = set(required)
                for uid in group:
                    context.update(extra.get(uid, ()))
                context.difference_update(group)
                members = sorted(group | context, key=position.__getitem__)
                budget.charge(1 + len(members) + sum(len(uid) for uid in support))
                suffix = sha256('\0'.join(support).encode()).hexdigest()[:24]
                child: dict[str, Any] = {**package,
                    'package_id': str(package['package_id']) + ':scope:' + suffix,
                    'member_unit_ids': members, 'anchor_unit_ids': list(support),
                    'required_context_unit_ids': sorted(context, key=position.__getitem__),
                    'citation_support_views': [list(support)]}
                # Only source-answer declarations affect meaning. Questions
                # and section navigation remain model context exclusively.
                meaning = tuple(sorted(context & selected, key=position.__getitem__))
                child['_source_scope_owner'] = session.support_owner(support, meaning_context=meaning)
                children.append(child)
            originals.extend(children)
            material.extend(children)
        except ValueError as exc:
            # Keep the source readable without inventing a smaller complete
            # answer when closure could not be proved.
            partial = {**package, 'completeness':'partial', '_qa_scope_complete':False}
            originals.append(partial)
            material.append({**projected, 'completeness':'partial', '_qa_scope_complete':False})
            withheld.append({'package_id':str(package['package_id']), 'reason':'QA_SCOPE_PARTIAL',
                             'status':str(exc), 'known_unit_ids':[]})
        except WorkBudgetExceeded:
            session.complete = False
            withheld.append({'package_id':'qa-source-closure', 'reason':'OPERATING_WORK_BUDGET',
                'unexamined_from_index':index, 'unexamined_package_count':len(packages)-index,
                'known_unit_ids':[]})
            break
    return originals, material, withheld
