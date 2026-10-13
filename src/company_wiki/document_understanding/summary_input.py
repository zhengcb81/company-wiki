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

from .observation_adapter import is_selectable
from .selection_bridge import dependency_closure

SCHEMA_VERSION = "du-summary-input/1"

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
)


def build_summary_input(
    pipeline_result: Mapping[str, Any],
    *,
    selected_unit_ids: Sequence[str] | None = None,
    max_packages: int = DEFAULT_MAX_PACKAGES,
    max_chars: int = DEFAULT_MAX_CHARS,
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
    profile = pipeline_result.get("profile") or {}
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

    closure = _apply_closure(packages, texts, selected_unit_ids)
    units_for_summary = packages.get("packages", ())

    selected, dropped, used_chars, withheld = _materialise(
        units_for_summary,
        units_by_id,
        max_packages=max_packages,
        max_chars=max_chars,
        allowed_unit_ids=closure["allowed_unit_ids"],
    )

    return {
        "schema_version": SCHEMA_VERSION,
        "source_ref": pipeline_result.get("source_ref", {}),
        "profile_id": route.get("profile_id"),
        "profile_version": route.get("profile_version"),
        "family": route.get("family"),
        "regime": route.get("regime"),
        "confidence": route.get("confidence"),
        "disposition_hint": route.get("disposition_hint"),
        "focus": str(profile.get("summary_focus") or ""),
        "prefer_semantic_units": list(profile.get("semantic_units", ())),
        "section_priorities": [
            {
                "section_role": entry.get("section_role"),
                "priority": entry.get("priority"),
            }
            for entry in profile.get("section_priorities", ())
        ],
        "negative_hints": list(profile.get("negative_hints", ())),
        "constraints": list(_SHARED_CONSTRAINTS),
        "evidence_packages": selected,
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


def _apply_closure(
    packages: Mapping[str, Any],
    texts: Mapping[str, str],
    selected_unit_ids: Sequence[str] | None,
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
    closure = dependency_closure(selected_unit_ids, packages, texts)
    allowed = set(closure["selected_unit_ids"])
    # Units the closure neither selected nor added are still eligible when they
    # belong to a package the closure touched: dropping them would silently
    # shrink the evidence below what the packages already justify.
    for package in packages.get("packages", ()):
        members = {str(unit_id) for unit_id in package.get("member_unit_ids", ())}
        if members & allowed:
            allowed |= members
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

    for index, package in enumerate(packages):
        package_id = str(package.get("package_id", ""))
        if len(selected) >= max_packages:
            dropped.append({"package_id": package_id, "reason": "PACKAGE_BUDGET"})
            continue

        members: list[dict[str, Any]] = []
        member_chars = 0
        package_withheld = 0
        for unit_id in package.get("member_unit_ids", ()):
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
        entry: dict[str, Any] = {
            "package_id": package_id,
            "rank": index,
            "kind": package.get("kind"),
            "section_role": package.get("section_role"),
            "section_ids": list(package.get("section_ids", ())),
            "completeness": package.get("completeness"),
            "truncated": bool(package.get("truncated")),
            "members": members,
        }
        if package_withheld:
            entry["not_selectable_withheld"] = package_withheld
        selected.append(entry)

    return selected, dropped, used_chars, withheld_count


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
