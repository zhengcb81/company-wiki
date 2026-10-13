"""Assemble the summary request from a routed, structured, prioritised document.

This is the missing half of ``implementation.md`` step 5 ("选择与摘要统一 ... 按 profile 聚合
摘要"). The profile already carries ``summary_focus``, ``semantic_units`` and
``negative_hints``; until now nothing consumed them, so a summary would have been driven by
a generic instruction rather than by what kind of document it is.

What this module does and deliberately does not do:

* it **builds the request** -- focus, selected evidence with provenance, budget accounting,
  and the honest list of what was not read;
* it does **not** call a model, read the network, or raise a paid budget. The existing
  transport and budget still decide whether anything is sent;
* it does **not** produce or store an investment conclusion. The output is a task
  description plus source-anchored text; every claim the model later makes must point back
  at one of these units and their locators.

Two properties are load-bearing:

1. **Provenance survives.** Every materialised member keeps its ``unit_id`` and ``locator``,
   and a unit that is not in the observation is dropped rather than invented. A summary whose
   evidence cannot be replayed to the original is not evidence.
2. **A budget cut is stated, never hidden.** Packages dropped for budget are reported as
   ``deferred`` with their ids, so "we did not read this" stays visible instead of becoming
   an implicit claim of completeness.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any
from hashlib import sha256
import json

from .observation_adapter import is_selectable
from .selection_bridge import build_context_graph, dependency_closure

SCHEMA_VERSION = "du-summary-input/1"
SUMMARY_FEATURE_VERSION = "1.1.0"

#: Exported alias so callers can refer to the wire version without importing the constant
#: through a private path.
SUMMARY_INPUT_SCHEMA_VERSION = SCHEMA_VERSION

#: Default bounds. These are *assembly* bounds, not the paid budget: the caller may lower
#: them, and the existing global limits still apply downstream.
DEFAULT_MAX_PACKAGES = 40
DEFAULT_MAX_CHARS = 48000

#: Instruction fragments shared by every profile. The per-type focus is appended to these,
#: so a new document type changes what is emphasised, never whether these hold.
_SHARED_CONSTRAINTS: tuple[str, ...] = (
    "只使用下面给出的原文单元，不补充任何未出现的数字、主体或时间。",
    "保留原语言，不翻译、不改写单位与币种。",
    "每个事实必须能回指到给出的 locator；无法回指的内容不要输出。",
    "区分已发生事实、公司计划与预测；保留否定与限定条件。",
    "未读到的内容标注为未读到，不要写成“没有”。",
    "不输出评级、目标价、仓位或估值结论。",
    "业务关注项只是阅读提示，不代表原文已经证明对应事实；定性陈述不强制补出数字。",
)


def build_summary_input(
    pipeline_result: Mapping[str, Any],
    *,
    selected_unit_ids: Sequence[str] | None = None,
    max_packages: int = DEFAULT_MAX_PACKAGES,
    max_chars: int = DEFAULT_MAX_CHARS,
    max_context_units: int = 64,
) -> dict[str, Any]:
    """Turn a ``du-pipeline/1`` result into a ``du-summary-input/1`` request.

    ``pipeline_result`` is the output of
    :func:`company_wiki.document_understanding.understand_units`.

    ``selected_unit_ids`` is what the *selector* chose, when the caller has it.
    Supplying it applies the dependency closure before anything is sent: the
    required context of every selected unit (a unit caption, a period header, a
    table header) is restored, and a negation is kept with the package it
    belongs to.  Without it the request is built from the ranked packages alone,
    and that fact is reported as ``closure.applied = False`` rather than being
    left for a reader to assume.

    This matters because a number separated from its unit caption is not a
    cheaper version of the evidence, it is a different and usually false claim.
    """
    observation = pipeline_result.get("observation") or {}
    route = pipeline_result.get("route") or {}
    packages = pipeline_result.get("packages") or {}
    structure = pipeline_result.get("structure") or {}

    units_by_id = {
        str(unit.get("unit_id")): unit
        for unit in observation.get("units", ())
        if unit.get("unit_id") is not None
    }
    texts = {
        unit_id: str(unit.get("text") or "") for unit_id, unit in units_by_id.items()
    }

    graph = build_context_graph(packages, texts)
    closure = _apply_closure(packages, texts, selected_unit_ids, max_added=max_context_units,
                             graph=graph)
    units_for_summary = packages.get("packages", ())

    selected, dropped, used_chars, withheld = _materialise(
        units_for_summary,
        units_by_id,
        max_packages=max_packages,
        max_chars=max_chars,
        allowed_unit_ids=closure["allowed_unit_ids"],
        graph=graph, texts=texts, max_context_units=max_context_units,
    )

    selected, unsafe = _validate_sent_context(selected, graph["groups"], units_by_id, index=graph["index"])
    dropped.extend(unsafe)
    used_chars = sum(len(member["text"]) for entry in selected for member in entry["members"])
    policies, facets, policy_version = _sent_policies(pipeline_result, selected)
    return {
        "schema_version": SCHEMA_VERSION,
        "feature_version": SUMMARY_FEATURE_VERSION,
        "source_ref": pipeline_result.get("source_ref", {}),
        "source_metadata": dict(observation.get("metadata") or {}),
        "profile_id": route.get("profile_id"),
        "profile_version": route.get("profile_version"),
        "family": route.get("family"),
        "regime": route.get("regime"),
        "confidence": route.get("confidence"),
        "disposition_hint": route.get("disposition_hint"),
        "focus": " ".join(_unique([str(p.get("summary_focus") or "") for p in policies
                                   if p.get("summary_focus")])),
        "modifiers": dict(route.get("modifiers") or {}),
        "prefer_semantic_units": _unique([kind for p in policies for kind in p.get("semantic_units") or ()]),
        "section_priorities": _unique([row for p in policies for row in p.get("section_priorities") or ()]),
        "negative_hints": _unique([hint for p in policies for hint in p.get("negative_hints") or ()]),
        "constraints": list(_SHARED_CONSTRAINTS),
        "evidence_packages": selected,
        "reading_policies": policies,
        "business_facets": facets,
        "reading_policy_version": policy_version,
        "layout_coverage": dict((pipeline_result.get("layout_hints") or {}).get("coverage") or {}),
        "layout_feature_version": (pipeline_result.get("layout_hints") or {}).get("feature_version"),
        "budget": {
            "max_packages": max_packages,
            "max_chars": max_chars,
            "packages_used": len(selected),
            "chars_used": used_chars,
        },
        "excluded": {"not_selectable": withheld},
        "closure": {
            "applied": closure["applied"],
            "reason": closure["reason"],
            "added_unit_ids": closure["added_unit_ids"],
            "added_count": len(closure["added_unit_ids"]),
            "diagnostics": closure["diagnostics"],
        },
        "deferred": dropped,
        "unread": _unread(structure, observation),
        "diagnostics": list(pipeline_result.get("diagnostics", ())),
    }



def _unique(values: Sequence[Any]) -> list[Any]:
    output = []
    seen = set()
    for value in values:
        key = json.dumps(value, ensure_ascii=False, sort_keys=True)
        if key not in seen:
            seen.add(key)
            output.append(value)
    return output


def _sent_policies(
    pipeline: Mapping[str, Any], entries: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], str]:
    """Version only used policies; select hints only from the final source material.

    Deduplication here bounds *probing*; it does not claim that the existing
    package transport sends shared text once. chars_used measures actual output.
    """
    from .profiles import select_business_facets

    material = {member["unit_id"]: member for entry in entries for member in entry["members"]}
    per_unit = (pipeline.get("reading_plan") or {}).get("unit_profiles") or {}
    fallback = pipeline.get("profile") or {}
    used: dict[str, dict[str, Any]] = {}
    for uid in material:
        chosen = per_unit.get(uid, fallback)
        policy = {key: chosen.get(key) for key in (
            "profile_id", "profile_version", "family", "summary_focus", "policy_components",
            "reading_questions", "context_requirements", "family_policy", "negative_hints", "semantic_units")}
        policy["section_priorities"] = ([{"section_role": chosen.get("section_role"),
                                           "priority": chosen.get("priority", 2)}]
                                        if "section_role" in chosen else chosen.get("section_priorities", []))
        fingerprint = json.dumps(policy, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        used[fingerprint] = policy
    policies = [used[key] for key in sorted(used)]
    facets = [{key: item.get(key) for key in (
        "id", "version", "content_digest", "selection_basis", "business_questions",
        "summary_focus", "required_context", "absence_rules", "confusion_checks", "applicable_mechanisms")}
        for item in select_business_facets(list(material.values()))]
    manifest = {"schema_version": "du-sent-policy/1", "reading_policies": policies,
                "pipeline_feature_version": pipeline.get("feature_version"),
                "summary_feature_version": SUMMARY_FEATURE_VERSION,
                "layout_feature_version": (pipeline.get("layout_hints") or {}).get("feature_version"),
                "business_facets": [{k: v for k, v in f.items() if k != "selection_basis"}
                                    for f in facets], "constraints": list(_SHARED_CONSTRAINTS)}
    digest = sha256(json.dumps(manifest, ensure_ascii=False, sort_keys=True,
                               separators=(",", ":")).encode()).hexdigest()
    return policies, facets, "du-sent-policy/1+" + digest


def _apply_closure(
    packages: Mapping[str, Any],
    texts: Mapping[str, str],
    selected_unit_ids: Sequence[str] | None,
    *, max_added: int, graph: Mapping[str, Any],
) -> dict[str, Any]:
    """Closure over the caller's selection, or an explicit "not applied".

    Returns the set of unit ids the request may carry (``None`` meaning no
    restriction) plus the closure's own record, so its diagnostics reach the
    request instead of dying in a helper.
    """
    if selected_unit_ids is None:
        return {
            "applied": False,
            "allowed_unit_ids": None,
            "added_unit_ids": [],
            "diagnostics": [],
            "reason": "no selector selection was supplied",
        }
    closure = dependency_closure(selected_unit_ids, packages, texts,
                                 max_added=max_added, include_members=True, context_graph=graph)
    allowed = set(closure["selected_unit_ids"])
    return {
        "applied": True,
        "allowed_unit_ids": allowed,
        "added_unit_ids": list(closure["added_unit_ids"]),
        "diagnostics": list(closure["diagnostics"]),
        "reason": None,
    }


def _materialise(
    packages: Sequence[Mapping[str, Any]],
    units_by_id: Mapping[str, Mapping[str, Any]],
    *,
    max_packages: int,
    max_chars: int,
    allowed_unit_ids: set[str] | None = None,
    graph: Mapping[str, Any] | None = None,
    texts: Mapping[str, str] | None = None,
    max_context_units: int = 64,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], int, int]:
    """Copy the highest-priority packages, with text and provenance, inside the budget.

    Packages arrive already ranked by the orchestrator (profile section priority first,
    then semantic kind), so this function preserves their order and never re-ranks: a
    summary must read the document in the order the profile chose.

    A non-selectable member is withheld from the model-facing evidence.  It is the
    text-layer duplicate of a Q&A page, so sending it would pay twice for the same
    sentence and invite the model to report one fact as two.  Withholding is counted and
    returned, and a package left with nothing selectable is *deferred* rather than
    emitted empty, because an empty package is indistinguishable from "no content here".

    ``allowed_unit_ids`` restricts the request to what the dependency closure endorsed.
    It is ``None`` when no closure was applied, which is different from an empty set.
    """
    selected: list[dict[str, Any]] = []
    dropped: list[dict[str, Any]] = []
    used_chars = 0
    withheld_count = 0
    restored_sent: set[str] = set()

    for index, package in enumerate(packages):
        package_id = str(package.get("package_id", ""))
        if len(selected) >= max_packages:
            dropped.append({"package_id": package_id, "reason": "PACKAGE_BUDGET"})
            continue

        original_members = list(dict.fromkeys(package.get("member_unit_ids", ())))
        required_ids = list(package.get("required_context_unit_ids", ()))
        candidate_ids = original_members
        added_context = []
        if graph is not None:
            seeds = [uid for uid in original_members if allowed_unit_ids is None or uid in allowed_unit_ids]
            recovered = dependency_closure(seeds, {"packages": graph["items"]}, texts or {},
                                           max_added=max_context_units, context_graph=graph)
            if not recovered["complete"]:
                dropped.append({"package_id": package_id, "reason": "CONTEXT_BUDGET_EXCEEDED",
                                "diagnostics": recovered["diagnostics"]})
                continue
            added_context = recovered["added_unit_ids"]
            candidate_ids = list(dict.fromkeys(original_members + added_context))
            required_ids = list(dict.fromkeys(required_ids + added_context))
            if len(restored_sent | set(added_context)) > max_context_units:
                dropped.append({"package_id": package_id, "reason": "CONTEXT_BUDGET_EXCEEDED"})
                continue

        members: list[dict[str, Any]] = []
        member_chars = 0
        package_withheld = 0
        for unit_id in candidate_ids:
            unit = units_by_id.get(str(unit_id))
            if unit is None:
                # Never invent evidence: a unit the observation does not contain is skipped.
                continue
            if allowed_unit_ids is not None and str(unit_id) not in allowed_unit_ids:
                continue
            if not is_selectable(unit):
                package_withheld += 1
                continue
            text = str(unit.get("text") or "")
            members.append(
                {
                    "unit_id": str(unit_id),
                    "locator": unit.get("locator"),
                    "page": unit.get("page"),
                    "kind": unit.get("kind"),
                    "role": unit.get("role"),
                    "text": text,
                }
            )
            member_chars += len(text)

        present_ids = {member["unit_id"] for member in members}
        missing_required = []
        for required_id in required_ids:
            required_id = str(required_id)
            if required_id in present_ids:
                continue
            required_unit = units_by_id.get(required_id)
            # An explicitly marked Q&A shadow may be represented by an exact
            # structured copy in this same semantic package. No wording-only
            # substitution is permitted for ordinary source units.
            equivalent_shadow = bool(required_unit and not is_selectable(required_unit) and any(
                member["text"] == str(required_unit.get("text") or "")
                and member["page"] == required_unit.get("page") for member in members))
            if not equivalent_shadow:
                missing_required.append(required_id)
        if missing_required and (members or not package_withheld):
            dropped.append({"package_id": package_id, "reason": "MISSING_REQUIRED_CONTEXT",
                            "unit_ids": missing_required})
            withheld_count += package_withheld
            continue
        withheld_count += package_withheld
        if not members:
            dropped.append(
                {
                    "package_id": package_id,
                    "reason": "NOT_SELECTABLE" if package_withheld else "EMPTY_TEXT",
                }
            )
            continue
        if not any(member["text"].strip() for member in members):
            dropped.append({"package_id": package_id, "reason": "EMPTY_TEXT"})
            continue
        if used_chars + member_chars > max_chars:
            dropped.append({"package_id": package_id, "reason": "CHAR_BUDGET"})
            continue

        used_chars += member_chars
        restored_sent.update(added_context)
        entry: dict[str, Any] = {
            "package_id": package_id,
            "rank": index,
            "kind": package.get("kind"),
            "section_role": package.get("section_role"),
            "section_ids": list(package.get("section_ids", ())),
            "completeness": "partial" if package.get("truncated") or any(
                str(uid) not in present_ids and not (
                    uid in units_by_id and not is_selectable(units_by_id[uid]))
                for uid in package.get("member_unit_ids", ())) else package.get("completeness"),
            "omitted_unit_ids": [str(uid) for uid in package.get("member_unit_ids", ())
                if str(uid) not in present_ids and not (
                    uid in units_by_id and not is_selectable(units_by_id[uid]))],
            "truncated": bool(package.get("truncated")),
            "members": members,
        }
        entry["required_locators"] = [units_by_id[uid]["locator"]
            for uid in required_ids
            if uid in units_by_id and is_selectable(units_by_id[uid])]
        entry["dependencies_resolved"] = True
        entry["restored_context_unit_ids"] = added_context
        for key in ("reading_profile_id", "reading_profile_version", "summary_focus"):
            if key in package:
                entry[key] = package[key]
        if package_withheld:
            entry["not_selectable_withheld"] = package_withheld
        selected.append(entry)

    return selected, dropped, used_chars, withheld_count


def _validate_sent_context(
    entries: list[dict[str, Any]], groups: Sequence[Mapping[str, Any]],
    units: Mapping[str, Mapping[str, Any]], *, index: Mapping[str, list[int]] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Verify the actual output, including cuts made after initial closure.

    Removing one unsafe package can remove another package's context, so pruning
    reaches a fixed point over this finite output list. The dependency graph is
    source-owned and independent of package ranking or summary budget.
    """
    from collections import deque

    if index is None:
        index = {}
        for i, group in enumerate(groups):
            for uid in group["member_unit_ids"]:
                index.setdefault(uid, []).append(i)
    kept = list(entries)
    dropped = []
    while kept:
        sent = {member["unit_id"] for entry in kept for member in entry["members"]}
        unsafe: set[str] = set()
        for entry in kept:
            queue = deque(member["unit_id"] for member in entry["members"])
            visited_units = set(queue)
            visited_groups: set[int] = set()
            required = set()
            missing = set()
            while queue:
                uid = queue.popleft()
                for i in index.get(uid, ()):
                    if i in visited_groups:
                        continue
                    visited_groups.add(i)
                    group = groups[i]
                    for dep in group["required_unit_ids"]:
                        if dep not in sent:
                            original = units.get(dep)
                            # Only an explicit shadow can have a structured
                            # substitute, within the same evidenced group/page.
                            equivalents = [other for other in group["member_unit_ids"]
                                if other in sent and original and not is_selectable(original)
                                and units.get(other, {}).get("text") == original.get("text")
                                and units.get(other, {}).get("page") == original.get("page")]
                            if equivalents:
                                dep = sorted(equivalents)[0]
                            else:
                                missing.add(dep)
                                continue
                        required.add(dep)
                        if dep not in visited_units:
                            visited_units.add(dep)
                            queue.append(dep)
            if missing:
                unsafe.add(entry["package_id"])
                dropped.append({"package_id": entry["package_id"],
                                "reason": "MISSING_TRANSITIVE_CONTEXT", "unit_ids": sorted(missing)})
            else:
                entry["required_locators"] = [units[uid]["locator"] for uid in sorted(required)]
                entry["dependencies_resolved"] = True
        if not unsafe:
            break
        kept = [entry for entry in kept if entry["package_id"] not in unsafe]
    return kept, dropped


def _unread(
    structure: Mapping[str, Any], observation: Mapping[str, Any]
) -> dict[str, Any]:
    """Report what this request does not cover, so a gap cannot read as completeness.

    Two distinct kinds of "not read" are reported separately, because they mean different
    things to a reader: pages that could not be read at all (opaque) versus pages/units the
    caller deliberately deferred. Furniture the structure lane excluded (TOC entries,
    repeated running headers) is *not* listed here: it was classified, not missed.
    """
    coverage = dict(structure.get("coverage") or {})
    observation_coverage = observation.get("coverage") or {}
    return {
        "native_scan": coverage.get("native_scan") or observation_coverage.get("native_scan"),
        "opaque_pages": list(
            coverage.get("opaque_pages") or observation_coverage.get("opaque_pages") or ()
        ),
        "deferred_pages": list(
            coverage.get("deferred_pages") or observation_coverage.get("deferred_pages") or ()
        ),
        "deferred_unit_ids": list(coverage.get("deferred_unit_ids", ())),
        "unassigned_unit_ids": list(coverage.get("unassigned_unit_ids", ())),
        "structure_complete": coverage.get("complete"),
    }


__all__ = [
    "DEFAULT_MAX_CHARS",
    "DEFAULT_MAX_PACKAGES",
    "SCHEMA_VERSION",
    "SUMMARY_INPUT_SCHEMA_VERSION",
    "build_summary_input",
]
