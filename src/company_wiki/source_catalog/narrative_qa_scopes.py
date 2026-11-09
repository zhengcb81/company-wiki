"""Closed answer scopes over source-owned QA records, before budget projection.

No document IO, geometry claims, second classifier or work account. Structural
QA association permits a bounded answer sequence; existing source semantics
decide dependencies. The original QA parent and original units remain intact.
"""
from __future__ import annotations

from hashlib import sha256
import re
from typing import Any

from company_wiki.resource_budget import WorkBudgetExceeded
from company_wiki.document_understanding.operating_states.relations import (
    closed_source_statement, independent_statement_start,
    source_courtesy_statement, DEPENDENT_STATEMENT,
)
from company_wiki.document_understanding.operating_states import classify_qualifiers
from .narrative_antecedent import MAX_WINDOW_UNITS, MAX_ENVELOPE_CHARS
from .narrative_operating_relations import SOURCE_SUPPORT_MAX_MEMBERS
from .narrative_source_purpose import NON_OPERATING_PURPOSES
from company_wiki.document_understanding.operating_states.assertion_roles import explicit_description_subject

from company_wiki.document_understanding.operating_states.product_reference import product_head_spans

QA_SCOPE_FEATURE_VERSION = 'source-qa-scopes/2'
QA_DEPENDENCY_SCAN_PASSES = 16
_OTHER_SOURCE_FRAME = re.compile(
    r'^\s*(?:另一(?:家|个|個|项|項)?|另外一家|其他|其它|another\b|a different\b|the other\b)', re.I)
_REQUIRED_QUALIFIER = re.compile(
    r'仍[须需]|[须須](?:要)?|需要(?:先|取得|获得)|取决于|以[^。.!?]{0,40}为准|'
    r'\b(?:must|required|requires?|subject to|depends? on)\b', re.I)



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
        independent = independent_statement_start(text) or explicit_description_subject(text)
        if pending and previous_closed and (courtesy or independent or uid in dependencies):
            result.append(pending)
            pending = []
        pending.append(uid)
        previous_closed = closed_source_statement(text)
    if pending:
        result.append(pending)
    return result


def _dependency_observations(answers, units, session):
    """Index candidates, not entity truth; exact source roles still own binding."""
    observed = {}
    for uid in answers:
        text = units[uid].raw_text
        session.work_budget.charge(QA_DEPENDENCY_SCAN_PASSES * len(text) + 1)
        roles = session.relations(uid)
        heads: set[str] = set()
        for relation in roles['relations']:
            for ref in relation['object_refs']:
                session.work_budget.charge()
                if ref['unit_id'] == uid and 0 <= ref['char_start'] < ref['char_end'] <= len(text):
                    value = text[ref['char_start']:ref['char_end']]
                    session.work_budget.charge(QA_DEPENDENCY_SCAN_PASSES * len(value) + 1)
                    heads.update(head for _, _, head in product_head_spans(value))
        # Unsupported source vocabulary can nominate a literal head only; it
        # can never establish a binding without the qualification owner.
        if not heads:
            heads = {head for _, _, head in product_head_spans(text)}
        fact = session.fact(uid)
        qualifiers = classify_qualifiers(text)
        planned = bool('operating_plan' in fact.reasons or qualifiers.planned or any(
            relation['modality'] == 'planned' for relation in roles['relations']))
        directive = _REQUIRED_QUALIFIER.search(text)
        restricted = bool(qualifiers.negated or qualifiers.conditional or directive)
        backward = bool(restricted and (DEPENDENT_STATEMENT.match(text.lstrip()) or directive)
                        and not independent_statement_start(text))
        if (fact.purpose in NON_OPERATING_PURPOSES or session.financial_only(uid)
                or units[uid].source_role in {
                'investor_question', 'analyst', 'analyst_question', 'question', 'operator'}):
            heads, planned, backward = set(), False, False
        observed[uid] = {'heads': heads, 'plan': planned, 'backward': backward,
                         'other': bool(_OTHER_SOURCE_FRAME.match(text))}
    return observed


def _sparse_qualifications(answers, owners, observed, session, union, failures, position):
    """Query at most eight candidates from prepared object/plan indexes.

    The bounded search window cannot prove that an older condition is absent.
    Literal head mentions nominate candidates only; the existing qualification
    owner proves a binding. Unsupported or overflowing matches stay partial.
    """
    indexes: dict[str, list[str]] = {}
    all_members: dict[str, dict[str, None]] = {}
    tainted: set[str] = set()
    budget = session.work_budget

    def add(label, uid):
        budget.charge()
        all_members.setdefault(label, {})[uid] = None
        bucket = indexes.setdefault(label, [])
        if len(bucket) < MAX_WINDOW_UNITS and uid not in bucket:
            bucket.append(uid)

    def flush_tainted():
        budget.charge(len(tainted) * max(1, len(tainted).bit_length()))
        for label in sorted(tainted):
            budget.charge(1 + len(all_members.get(label, ())))
            for member in all_members.get(label, ()):
                failures[member] = 'qa_qualification_index_incomplete'

    for uid in answers:
        data = observed[uid]
        if data['other']:
            # An explicit other-business frame ends the prior issuer candidate
            # scope. Later bare caveats cannot jump back over that source frame.
            flush_tainted()
            indexes.clear()
            all_members.clear()
            tainted.clear()
        if uid not in owners:
            continue
        owner = owners[uid]
        # A qualified original may be one fragment of a larger closed source
        # component. Same-component statements are already retained together.
        if data['backward'] and not data['other']:
            labels = sorted(data['heads']) or (['@plan'] if indexes.get('@plan') else ['@object'])
            budget.charge(1 + len(labels))
            candidates: set[str] = set()
            overflow = False
            for label in labels:
                members = all_members.get(label, {})
                budget.charge()
                if len(members) > MAX_WINDOW_UNITS:
                    tainted.add(label)
                    overflow = True
                candidates.update(indexes.get(label, ()))
            internal = any(owners[left] == owner for left in candidates)
            candidates = {left for left in candidates if owners[left] != owner}
            if overflow or len(candidates) > MAX_WINDOW_UNITS:
                failures[uid] = 'qa_qualification_index_incomplete'
                tainted.update(labels)
            elif candidates:
                matches = []
                budget.charge(len(candidates) * max(1, len(candidates).bit_length()))
                for left in sorted(candidates, key=position.__getitem__):
                    budget.charge()
                    left_scope = session._source_material_range(left, left)
                    right_scope = session._source_material_range(uid, uid)
                    matched = None if left_scope is None or right_scope is None else session._qualification_pair(
                        left, uid, left_scope, right_scope, left_owner=owners[left],
                        right_owner=owner, qa_sequence=True)
                    if matched is not None:
                        matches.append((left, matched))
                identities = {match.object_ref if match.object_ref is not None else ('scope', left)
                              for left, match in matches}
                if len(identities) == 1 and len(matches) == len(candidates):
                    for left, _ in matches:
                        union(left, uid)
                else:
                    # A plan may have no supported typed predicate yet. Do not
                    # claim closure or attach its caveat to the nearest delivery.
                    failures[uid] = 'qa_qualification_unresolved'
                    for left in sorted(candidates, key=position.__getitem__):
                        failures[left] = 'qa_qualification_unresolved'
                        union(left, uid)
            elif not internal:
                failures[uid] = 'qa_qualification_target_unresolved'
        # Explicit other-business statements are a new frame, never candidates
        # for issuer antecedents. Questions were excluded by the QA source owner.
        if not data['other'] and not data['backward']:
            for head in sorted(data['heads']):
                add(head, uid)
            if data['heads']:
                add('@object', uid)
            if data['plan']:
                add('@plan', uid)
    # Each source frame's overflowing index is invalidated once, not once per
    # dependent statement. Unrelated object classes remain readable.
    flush_tainted()


def _close_long_answer(package, answers, required, session, source_position):
    """Close bounded statements inside one observed long answer, in linear work.

    The record is not a material envelope. Proven independent source boundaries establish
    provisional components; actual reference/restriction edges may merge them.
    A merged/open/oversized component stays partial, never a truncated prefix.
    """
    units, budget = session.units, session.work_budget
    _validate_fragment_order(answers, units, budget)
    # Use the existing proof of an independently started closed statement.
    # A full stop alone cannot detach a later condition from its plan/object.
    observed = _dependency_observations(answers, units, session)
    boundaries = {uid for uid, data in observed.items() if data['backward'] or data['other']}
    segments = _segments(answers, units, budget, boundaries)
    position = {uid: n for n, uid in enumerate(answers)}
    budget.charge(3 * len(answers))
    frame_start, frames = 0, {}
    for offset, uid in enumerate(answers):
        if observed[uid]['other']:
            frame_start = offset
        frames[uid] = frame_start
    parent = {uid: uid for uid in answers}
    failures = {}

    def root(uid):
        while parent[uid] != uid:
            parent[uid] = parent[parent[uid]]
            uid = parent[uid]
        return uid

    def union(left, right):
        parent[root(right)] = root(left)

    owners, extra = {}, {}
    answer_set = set(answers)
    for segment in segments:
        for uid in segment[1:]:
            union(segment[0], uid)
        chars = sum(len(units[uid].raw_text) for uid in segment)
        budget.charge(len(segment))
        if len(segment) > SOURCE_SUPPORT_MAX_MEMBERS or chars > MAX_ENVELOPE_CHARS:
            failures[segment[0]] = 'qa_scope_window_clipped'
            continue
        if not closed_source_statement(units[segment[-1]].raw_text):
            failures[segment[0]] = 'qa_statement_open'
            continue
        owner = session.support_owner(tuple(segment))
        for uid in segment:
            owners[uid] = owner
        offset = position[segment[0]]
        frame_start = frames[segment[0]]
        first = max(frame_start, offset - MAX_WINDOW_UNITS)
        predecessors = tuple(answers[first:offset])
        budget.charge(1 + len(predecessors))
        session.antecedents[owner] = (predecessors, first == frame_start)
        closure = session.reference(owner)
        if closure['status'] in {'ambiguous', 'missing', 'partial'}:
            failures[segment[0]] = 'qa_reference_' + closure['status']
            continue
        needed = set(closure.get('required_original_unit_ids', ()))
        if not needed <= answer_set:
            failures[segment[0]] = 'qa_reference_outside_answer'
            continue
        for uid in segment:
            extra[uid] = needed
        if closure.get('reference_kind') == 'causal_result':
            for other in closure.get('support_original_unit_ids', ()):
                union(segment[0], other)

    # Only the actual bounded predecessor slice is examined. No repeated full
    # prefix scans or whole-record Cartesian matching as record length grows.
    bound_heads: dict[str, str] = {}
    qualification_roots: dict[str, tuple[str, int, int]] = {}
    for offset, right in enumerate(answers):
        if right not in owners or observed[right]['other']:
            continue
        matches = []
        first = max(frames[right], offset - MAX_WINDOW_UNITS)
        for left in answers[first:offset]:
            budget.charge()
            if left not in owners or owners[left] == owners[right]:
                continue
            left_scope = session._source_material_range(left, left)
            right_scope = session._source_material_range(right, right)
            if left_scope is None or right_scope is None:
                failures[right] = 'qa_original_range_unavailable'
                continue
            matched = session._qualification_pair(left, right, left_scope, right_scope,
                inherited_head=bound_heads.get(left), left_owner=owners[left],
                right_owner=owners[right], qa_sequence=True)
            if matched is not None:
                matches.append((left, matched))
        identities = {qualification_roots.get(left, match.object_ref)
                      if match.object_ref is not None else ('scope', left)
                      for left, match in matches}
        for left, _ in matches:
            union(left, right)
        if len(identities) > 1:
            failures[right] = 'qa_qualification_ambiguous'
        elif matches:
            left, matched = matches[0]
            if matched.head and matched.object_ref is not None:
                bound_heads[right] = matched.head
                qualification_roots[right] = qualification_roots.get(left, matched.object_ref)

    _sparse_qualifications(answers, owners, observed, session, union, failures, position)

    groups: dict[str, list[str]] = {}
    for uid in answers:
        budget.charge()
        groups.setdefault(root(uid), []).append(uid)
    failed_roots = {root(uid): reason for uid, reason in failures.items()}
    children, withheld = [], []
    for support in groups.values():
        group = set(support)
        meaning: set[str] = set()
        for uid in support:
            budget.charge(1 + len(extra.get(uid, ())))
            meaning.update(extra.get(uid, ()))
        meaning.difference_update(group)
        proof = group | meaning
        budget.charge(1 + len(proof) + len(required))
        reason = failed_roots.get(root(support[0]))
        if any(root(uid) in failed_roots for uid in meaning):
            reason = 'qa_reference_partial_component'
        if (len(proof) > SOURCE_SUPPORT_MAX_MEMBERS
                or sum(len(units[uid].raw_text) for uid in proof) > MAX_ENVELOPE_CHARS):
            reason = 'qa_scope_window_clipped'
        # Questions retain model context only; they never enter the prepared
        # source owner's meaning context or declare a product/actor.
        ordered_context = sorted((set(required) | meaning) - group, key=source_position.__getitem__)
        members = sorted(set(ordered_context) | group, key=source_position.__getitem__)
        budget.charge(1 + len(members) + sum(len(uid) for uid in support))
        suffix = sha256('\0'.join(support).encode()).hexdigest()[:24]
        child = {**package, 'package_id':str(package['package_id']) + ':scope:' + suffix,
            'member_unit_ids':members, 'anchor_unit_ids':support,
            'required_context_unit_ids':ordered_context,
            'citation_support_views':[support]}
        if reason is not None:
            child.update(completeness='partial', _qa_scope_complete=False)
            withheld.append({'package_id':child['package_id'], 'reason':'QA_SCOPE_PARTIAL',
                'status':reason, 'known_unit_ids':support})
        else:
            child['_source_scope_owner'] = session.support_owner(tuple(support),
                meaning_context=tuple(sorted(meaning, key=position.__getitem__)))
        children.append(child)
    return children, withheld


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
                if position is None:
                    budget.charge(len(units))
                    position = {uid: n for n, uid in enumerate(units)}
                children, partials = _close_long_answer(package, answers, required, session, position)
                originals.extend(children)
                material.extend(children)
                withheld.extend(partials)
                continue
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
