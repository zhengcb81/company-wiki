"""Call-local, original-ID native dependencies after structural ownership.

Sections remain the only parent owner. This projector preserves per-target
readable dependencies and binds the producer's separately charged structural
edge endpoints and positively identified running furniture. It creates no source state, carrier, text or permission.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from company_wiki.resource_budget import WorkBudget
from company_wiki.document_understanding.observation_adapter import _wire_kind


@dataclass(frozen=True)
class NativeDependencies:
    readable: Mapping[str, frozenset[str]]
    physical: Mapping[str, frozenset[str]]
    blocked: frozenset[str]
    diagnostics: tuple[dict[str, Any], ...]
    proofs: Mapping[str, tuple[Mapping[str, Any], ...]] = field(default_factory=dict)
    proof_targets: Mapping[str, frozenset[str]] = field(default_factory=dict)

    def context_for(self, target: str) -> frozenset[str]:
        return self.readable.get(target, frozenset())

    def source_for(self, target: str) -> frozenset[str]:
        return self.physical.get(target, frozenset())

    def proofs_for(self, target: str) -> tuple[Mapping[str, Any], ...]:
        return self.proofs.get(target, ())

    def proof_targets_for(self, target: str) -> frozenset[str]:
        return self.proof_targets.get(target, frozenset())


def collect_native_dependencies(
    semantics: Sequence[Mapping[str, Any]], *, originals: Mapping[str, Any],
    furniture_ids: frozenset[str], work_budget: WorkBudget,
) -> NativeDependencies:
    """Reserve before expansion, reject corrupt proofs, then close actual edges.

    Source-only refs carry the physical producer's typed edge: list endpoints
    plus positively proved running furniture. Their USE is structural even when
    an independent endpoint also contains business text. This never removes a
    separate real meaning/deictic/footnote dependency from the model envelope.
    """
    work_budget.charge(1 + len(semantics) + 3 * len(originals))
    ordinal: dict[str, int] = {}
    source_counts: dict[str, int] = {}
    for uid, original in originals.items():
        source = original.source_id
        ordinal[uid] = source_counts.get(source, 0)
        source_counts[source] = ordinal[uid] + 1
    readable: dict[str, set[str]] = {}
    physical: dict[str, set[str]] = {}
    blocked: set[str] = set()
    reasons: dict[str, str] = {}
    direct_proofs: dict[str, dict[tuple[str, str], Mapping[str, Any]]] = {}

    def reject(targets, reason):
        for target in targets:
            blocked.add(target)
            reasons.setdefault(target, reason)

    for semantic in semantics:
        work_budget.charge()
        raw_members = semantic.get("member_unit_ids", ())
        if not isinstance(raw_members, (list, tuple)):
            continue  # Existing structure validation owns malformed membership.
        work_budget.charge(len(raw_members))
        members = {uid for uid in raw_members if isinstance(uid, str) and uid in originals}
        for field_name, destination, source_only in (
            ("required_context_by_unit_id", readable, False),
            ("required_source_unit_ids_by_unit_id", physical, True),
        ):
            if field_name not in semantic:
                continue
            mapping = semantic[field_name]
            if not isinstance(mapping, Mapping):
                reject(members, "native_dependency_shape")
                continue
            work_budget.charge(len(mapping))
            for target, refs in mapping.items():
                work_budget.charge()
                if not isinstance(target, str) or target not in members or target in furniture_ids:
                    reject(members, "native_dependency_target")
                    continue
                if not isinstance(refs, (list, tuple)):
                    reject((target,), "native_dependency_shape")
                    continue
                work_budget.charge(1 + 2 * len(refs))
                if any(not isinstance(uid, str) or uid not in originals for uid in refs):
                    reject((target,), "native_dependency_missing")
                    continue
                source = originals[target].source_id
                if any(originals[uid].source_id != source for uid in refs):
                    reject((target,), "native_dependency_foreign")
                    continue
                destination.setdefault(target, set()).update(refs)
        proof_mapping = semantic.get("native_source_proofs_by_unit_id", {})
        if not isinstance(proof_mapping, Mapping):
            reject(members, "native_dependency_proof_shape")
            continue
        work_budget.charge(len(proof_mapping))
        for target, rows in proof_mapping.items():
            work_budget.charge()
            if target not in members or not isinstance(rows, (tuple, list)):
                reject(members, "native_dependency_proof_target")
                continue
            work_budget.charge(len(rows))
            for row in rows:
                if not isinstance(row, Mapping):
                    reject((target,), "native_dependency_proof_shape")
                    continue
                left, right, furniture = row.get("left"), row.get("right"), row.get("furniture_unit_ids")
                if (not isinstance(left, str) or not isinstance(right, str)
                        or left not in originals or right not in originals or left == right
                        or not isinstance(furniture, (list, tuple))):
                    reject((target,), "native_dependency_proof_missing")
                    continue
                work_budget.charge(1 + len(row) + 2 * len(furniture))
                if any(not isinstance(uid, str) or uid not in originals for uid in furniture):
                    reject((target,), "native_dependency_proof_missing")
                    continue
                source = originals[target].source_id
                if any(originals[uid].source_id != source for uid in (left, right, *furniture)):
                    reject((target,), "native_dependency_foreign")
                    continue
                if (row.get("basis") != "observed_adjacent_page_flow"
                        or row.get("left_page") != originals[left].coordinates.page_number
                        or row.get("right_page") != originals[right].coordinates.page_number
                        or type(row.get("left_page")) is not int or type(row.get("right_page")) is not int
                        or row["right_page"] != row["left_page"] + 1
                        or originals[target].coordinates.page_number != row["right_page"]
                        or row.get("left_ordinal") != ordinal[left]
                        or row.get("right_ordinal") != ordinal[right]
                        or ordinal[target] < ordinal[right]
                        or not isinstance(row.get("coordinate_frame"), str)
                        or not row.get("coordinate_frame")
                        or type(row.get("column")) not in (int, str)):
                    reject((target,), "native_dependency_proof_shape")
                    continue
                if (any(uid not in furniture_ids
                        or _wire_kind(originals[uid], originals[uid].coordinates) not in {"paragraph", "heading"}
                        for uid in furniture)
                        or any(_wire_kind(originals[uid], originals[uid].coordinates) != "paragraph"
                               for uid in (left, right))):
                    reject((target,), "native_dependency_role")
                    continue
                previous = direct_proofs.setdefault(target, {}).get((left, right))
                if previous is not None and previous != row:
                    reject((target,), "native_dependency_proof_conflict")
                direct_proofs[target][(left, right)] = row
    # The producer owns geometry/scope. The consumer only binds original refs
    # to that proof; it does not repeat physical discovery, hashes or approvals.
    work_budget.charge(len(physical) + len(direct_proofs))
    for target in set(physical) | set(direct_proofs):
        rows = direct_proofs.get(target, {})
        expected: set[str] = set()
        for row in rows.values():
            work_budget.charge(2 + len(row["furniture_unit_ids"]))
            expected.update((row["left"], row["right"], *row["furniture_unit_ids"]))
        expected.discard(target)
        if not rows or physical.get(target, set()) != expected:
            reject((target,), "native_dependency_incomplete_proof")

    # One iterative DFS with real edge reservations. A cycle or corrupt child
    # invalidates every dependent target, never a smaller apparently complete
    # context. No recursion limit or document-sized speculative expansion.
    work_budget.charge(len(readable) + len(physical))
    roots = set(readable) | set(physical)
    closed_readable: dict[str, frozenset[str]] = {}
    closed_physical: dict[str, frozenset[str]] = {}
    closed_proofs: dict[str, tuple[Mapping[str, Any], ...]] = {}
    closed_proof_targets: dict[str, frozenset[str]] = {}
    colors: dict[str, int] = {}
    for root in roots:
        stack = [(root, False)]
        while stack:
            work_budget.charge()
            target, exiting = stack.pop()
            if not exiting:
                if colors.get(target) == 2:
                    continue
                if colors.get(target) == 1:
                    reject((target,), "native_dependency_cycle")
                    continue
                colors[target] = 1
                edges = readable.get(target, set())
                work_budget.charge(1 + len(edges))
                stack.append((target, True))
                for uid in edges:
                    if uid in roots:
                        if colors.get(uid) == 1:
                            reject((target, uid), "native_dependency_cycle")
                        elif colors.get(uid) != 2:
                            stack.append((uid, False))
                continue
            own_context = readable.get(target, set())
            own_source = physical.get(target, set())
            work_budget.charge(1 + len(own_context) + len(own_source))
            context, source_refs = set(own_context), set(own_source)
            proof_rows = dict(direct_proofs.get(target, {}))
            proof_target_ids = {target} if proof_rows else set()
            for uid in own_context:
                if uid in blocked:
                    reject((target,), "native_dependency_incomplete")
                nested_context = closed_readable.get(uid, frozenset())
                nested_source = closed_physical.get(uid, frozenset())
                work_budget.charge(1 + len(nested_context) + len(nested_source))
                context.update(nested_context)
                source_refs.update(nested_source)
                nested_proofs = closed_proofs.get(uid, ())
                nested_proof_targets = closed_proof_targets.get(uid, frozenset())
                work_budget.charge(len(nested_proofs) + len(nested_proof_targets))
                proof_rows.update({(row["left"], row["right"]): row for row in nested_proofs})
                proof_target_ids.update(nested_proof_targets)
            work_budget.charge(1 + len(context) + len(source_refs))
            work_budget.charge(len(proof_target_ids))
            closed_readable[target] = frozenset(context)
            closed_physical[target] = frozenset(source_refs)
            closed_proofs[target] = tuple(proof_rows.values())
            closed_proof_targets[target] = frozenset(proof_target_ids)
            colors[target] = 2
    work_budget.charge(len(blocked) * (1 + len(blocked).bit_length()))
    diagnostics = tuple({"package_id": "native-proof:" + target,
        "reason": "REFERENCE_UNRESOLVED", "status": reasons.get(target, "native_dependency_incomplete"),
        "known_unit_ids": [target]} for target in sorted(blocked))
    return NativeDependencies(closed_readable, closed_physical, frozenset(blocked), diagnostics,
                              closed_proofs, closed_proof_targets)
