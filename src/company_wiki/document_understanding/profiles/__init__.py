"""Composable document-type profiles and pure-function routing.

Frozen public surface (``docs/plans/document-understanding-2026-10-13/INTERFACES.md``
section 3)::

    route_document(observation, *, limits=None) -> dict   # schema du-route/1
    get_profile(profile_id) -> dict
    list_profiles() -> list[dict]

Scope and non-goals:

* load one installed policy asset at import; calls are pure, with no docs/config/network/clock/model reads;
* the input observation is never mutated;
* identical input yields identical output, with stable ordering;
* no company name, security code or file path is ever used as a routing rule;
* the router never returns the final ``skip``; the most it says about a low-value
  document is ``administrative_candidate``, and ROOT decides what to do with it.

The package is deliberately self-contained: it depends only on the standard library and
does not import any other ``company_wiki`` module, so ROOT can compose it without pulling
in the production pipeline.
"""

from __future__ import annotations

from typing import Any, Mapping

from . import vocabulary as v
from .decision import decide
from .child_ranges import attachment_routes
from .lifecycle import lifecycle_modifiers
from .observation import Limits, Observation, ObservationError, UnitRef, parse_observation
from .registry import (
    profile_by_id, profile_wire, resolve_reading_profile, select_business_facets,
)
from .signals import Signal, SignalBag, detect_signals

SCHEMA_VERSION = v.SCHEMA_VERSION_ROUTE
INPUT_SCHEMA_VERSION = v.SCHEMA_VERSION_INPUT

#: Families that consume business narrative and therefore never low-value skip.
_BUSINESS_FAMILIES = frozenset(
    {
        "annual",
        "interim",
        "quarterly",
        "prospectus",
        "offering",
        "results_release",
        "presentation",
        "investor_qa",
        "earnings_call",
    }
)


def list_profiles() -> list[dict]:
    """Return every registered profile as a JSON-serializable mapping.

    The registry is static and frozen at import time; the returned list is a fresh copy
    each call, so a caller cannot mutate shared state.
    """
    from .registry import listed_profiles

    return listed_profiles()


def get_profile(profile_id: str) -> dict:
    """Return one profile by id.

    Raises ``TypeError``/``ValueError`` for a malformed id and ``KeyError`` for an
    unknown one. Inventing a profile on demand would hide a real wiring mistake.
    """
    return profile_wire(profile_id)


def route_document(
    observation: Mapping[str, Any], *, limits: Mapping[str, Any] | None = None
) -> dict:
    """Route one ``du-input/1`` observation to a document profile.

    ``limits`` may only tighten the frozen probe budgets; profiles cannot raise them.
    The returned mapping conforms to ``du-route/1``.
    """
    parsed = parse_observation(observation, limits)
    bag = detect_signals(parsed)
    winner = decide(parsed, bag)
    profile = profile_by_id(winner.profile_id)

    reasons = list(winner.to_wire_reasons())
    _extend_coverage_reasons(parsed, reasons)
    _extend_conflict_reasons(parsed, bag, winner, reasons)

    alternatives = _alternatives(parsed, bag, winner)
    child_routes = _child_routes(parsed, bag, limits, reasons)
    disposition = _disposition(parsed, winner)
    confidence = _confidence(parsed, bag, winner, disposition)

    return {
        "schema_version": SCHEMA_VERSION,
        "profile_id": profile.profile_id,
        "profile_version": profile.profile_version,
        "regime": winner.regime,
        "family": winner.family,
        "subtype": winner.subtype,
        "confidence": confidence,
        "reasons": _bounded_reasons(reasons, parsed),
        "alternatives": alternatives,
        "child_routes": child_routes,
        "disposition_hint": disposition,
        "modifiers": lifecycle_modifiers(parsed, family=winner.family),
    }


# --- reason assembly ------------------------------------------------------------------


def _bounded_reasons(
    reasons: list[dict], parsed: Observation
) -> list[dict]:
    """Deduplicate and bound reasons; drop ones citing units that do not exist."""
    valid_ids = set(parsed.unit_ids)
    seen: set[tuple[str, tuple[str, ...]]] = set()
    output: list[dict] = []
    for reason in reasons:
        unit_ids = tuple(
            unit_id for unit_id in dict.fromkeys(reason["unit_ids"]) if unit_id in valid_ids
        )
        key = (reason["code"], unit_ids)
        if key in seen:
            continue
        seen.add(key)
        output.append(
            {
                "code": reason["code"],
                "unit_ids": list(unit_ids),
                "detail": reason["detail"][: v.MAX_REASON_DETAIL_CHARS],
            }
        )
    return output


def _extend_coverage_reasons(parsed: Observation, reasons: list[dict]) -> None:
    """Report what was actually read: scan coverage and page-level gaps."""
    fallback_ids = _fallback_unit_ids(parsed)
    if parsed.native_scan == "unavailable":
        reasons.append(
            {
                "code": v.REASON_NATIVE_SCAN_UNAVAILABLE,
                "unit_ids": list(parsed.opaque_pages and fallback_ids or fallback_ids),
                "detail": "原生文本不可用，需有限 OCR 后再判断",
            }
        )
    elif parsed.native_scan == "partial":
        reasons.append(
            {
                "code": v.REASON_PARTIAL_NATIVE_SCAN,
                "unit_ids": list(fallback_ids),
                "detail": "原生扫描不完整，未覆盖页按未读处理",
            }
        )
    if parsed.opaque_pages:
        reasons.append(
            {
                "code": v.REASON_OPAQUE_PAGES,
                "unit_ids": list(fallback_ids),
                "detail": f"{len(parsed.opaque_pages)} 个不可读页未参与判断",
            }
        )
    if not any(unit.text.strip() for unit in parsed.units):
        reasons.append(
            {
                "code": v.REASON_NO_READABLE_BODY,
                "unit_ids": list(fallback_ids),
                "detail": "没有可读正文，只能按有限证据保守判断",
            }
        )
    if parsed.probe_limited:
        reasons.append(
            {
                "code": v.REASON_ROUTE_PROBE_LIMIT,
                "unit_ids": [unit.unit_id for unit in parsed.probes[:1]],
                "detail": (
                    f"探测到预算上限：已探测 {len(parsed.probes)}/{len(parsed.units)} 单元、"
                    f"{parsed.probed_chars} 字符"
                ),
            }
        )


def _fallback_unit_ids(parsed: Observation) -> tuple[str, ...]:
    if parsed.probes:
        return (parsed.probes[0].unit_id,)
    if parsed.units:
        return (parsed.units[0].unit_id,)
    return ()


def _extend_conflict_reasons(
    parsed: Observation,
    bag: SignalBag,
    winner,
    reasons: list[dict],
) -> None:
    """Surface a metadata claim the body contradicts instead of silently overriding it."""
    claimed_regime = (parsed.regime_claim or "unknown").casefold()
    if claimed_regime in {"cn_exchange", "hkex", "sec"} and claimed_regime != winner.regime:
        reasons.append(
            {
                "code": v.REASON_REGIME_CONFLICT,
                "unit_ids": list(_fallback_unit_ids(parsed)),
                "detail": f"元数据 regime={claimed_regime} 与正文证据 {winner.regime} 不一致",
            }
        )

    declared = (parsed.declared_kind or "unknown").casefold()
    if declared and declared != "unknown":
        expected_family = _family_for_declared_kind(declared)
        if expected_family is not None and expected_family != winner.family:
            reasons.append(
                {
                    "code": v.REASON_DECLARED_KIND_CONFLICT,
                    "unit_ids": list(_fallback_unit_ids(parsed)),
                    "detail": f"declared_kind={parsed.declared_kind} 暗示 {expected_family}，正文证据不同",
                }
            )
    if winner.subtype and "未指定" in winner.subtype:
        reasons.append(
            {
                "code": v.REASON_METADATA_CONFLICT,
                "unit_ids": list(_fallback_unit_ids(parsed)),
                "detail": "类型特征不完整，按同类通用策略阅读",
            }
        )

    title_tokens = _declared_kind_token_in_title(parsed)
    if title_tokens and declared != "unknown" and declared != title_tokens:
        reasons.append(
            {
                "code": v.REASON_METADATA_CONFLICT,
                "unit_ids": list(_fallback_unit_ids(parsed)),
                "detail": f"标题提示 {title_tokens} 与 declared_kind={parsed.declared_kind} 不同",
            }
        )


_DECLARED_KIND_FAMILY = {
    "annual_report": "annual",
    "semi_annual_report": "interim",
    "quarterly_report": "quarterly",
    "prospectus": "prospectus",
    "equity_offering_prospectus": "offering",
    "convertible_bond_prospectus": "offering",
    "investor_relations": "investor_qa",
    "investor_call_transcript": "earnings_call",
    "ir_policy": "administrative",
    "meeting_notice": "administrative",
    "results_release": "results_release",
    "presentation": "presentation",
}

_TITLE_KIND_TOKENS = (
    ("招股说明书", "prospectus"),
    ("募集说明书", "equity_offering_prospectus"),
    ("可转换公司债券", "convertible_bond_prospectus"),
    ("半年度报告", "semi_annual_report"),
    ("年度报告", "annual_report"),
    ("季度报告", "quarterly_report"),
)


def _family_for_declared_kind(declared: str) -> str | None:
    return _DECLARED_KIND_FAMILY.get(declared)


def _declared_kind_token_in_title(parsed: Observation) -> str | None:
    from .signals import normalize

    title = normalize(parsed.title or "")
    if not title:
        return None
    for token, kind in _TITLE_KIND_TOKENS:
        if normalize(token) in title:
            return kind
    return None


# --- alternatives and child routes ----------------------------------------------------


def _alternatives(parsed: Observation, bag: SignalBag, winner) -> list[dict]:
    """List genuine runners-up; never pad the list with noise."""
    alternatives: list[dict] = []
    seen = {winner.profile_id}

    def add(profile_id: str, reason: str) -> None:
        if profile_id in seen or len(alternatives) >= 3:
            return
        seen.add(profile_id)
        alternatives.append({"profile_id": profile_id, "reason": reason[: v.MAX_REASON_DETAIL_CHARS]})

    details = " ".join(signal.detail for signal in bag.all)
    if winner.profile_id == "prospectus" and "再融资" in details:
        add("offering", "存在募集资金用途措辞，可能是再融资募集说明书")
    if winner.profile_id == "offering" and "招股" in details:
        add("prospectus", "存在招股措辞")
    if winner.profile_id == "cn_annual" and "半年度报告" in details:
        add("cn_interim", "同时出现半年度措辞")
    if winner.profile_id == "cn_interim" and "年度报告" in details:
        add("cn_annual", "同时出现年度报告措辞")
    if winner.profile_id == "results_release" and "presentation" in details.casefold():
        add("presentation", "同时出现演示稿特征")
    if winner.profile_id == "administrative" and _has_prospectus_evidence(details):
        add("prospectus", "标题含招股措辞但正文为行政用途")

    declared_family = _family_for_declared_kind((parsed.declared_kind or "").casefold())
    if declared_family and declared_family != winner.family:
        for profile in _profiles_for_family(declared_family):
            add(profile, f"declared_kind={parsed.declared_kind} 指向 {declared_family}")
    return alternatives


def _has_prospectus_evidence(details: str) -> bool:
    return "招股" in details or "首次公开发行" in details or "global offering" in details.casefold()


def _profiles_for_family(family: str) -> tuple[str, ...]:
    return tuple(
        profile["profile_id"]
        for profile in list_profiles()
        if profile["family"] == family
    )


def _child_routes(
    parsed: Observation, bag: SignalBag, limits: Mapping[str, Any] | None, reasons: list[dict]
) -> list[dict]:
    """In-document sub-ranges that need their own reading, plus unread external links.

    Only ranges inside the already-supplied units are reported. An external attachment is
    never opened, downloaded or turned into a SourceRef; it is reported as unread so ROOT
    can route it through the normal acquisition path.
    """
    resolved = Limits.from_mapping(limits)
    cap = resolved.max_child_routes
    child_routes: list[dict] = []
    if cap <= 0:
        return child_routes

    for signal in bag.all:
        if signal.code != v.REASON_EXTERNAL_ATTACHMENT_NOT_READ:
            continue
        for unit_id in signal.unit_ids:
            if len(child_routes) >= cap:
                return child_routes
            child_routes.append(
                {
                    "unit_ids": [unit_id],
                    "profile_id": "generic",
                    "reason": v.REASON_EXTERNAL_ATTACHMENT_NOT_READ,
                }
            )

    attachments, gaps = attachment_routes(parsed, cap=cap - len(child_routes))
    child_routes.extend(attachments)
    reasons.extend(gaps)

    for signal in bag.all:
        if signal.code != v.REASON_QA_STRUCTURE:
            continue
        for unit_id in signal.unit_ids:
            if len(child_routes) >= cap:
                return child_routes
            if any(unit_id in route["unit_ids"] for route in child_routes):
                continue
            child_routes.append(
                {
                    "unit_ids": [unit_id],
                    "profile_id": "investor_qa",
                    "reason": "IN_DOCUMENT_QA_RANGE",
                }
            )
    return child_routes


# --- disposition and confidence -------------------------------------------------------


def _disposition(parsed: Observation, winner) -> str:
    """Suggest what to do, never the final skip decision (owned by ROOT).

    A ``read`` hint requires something actually readable. A document whose native text is
    unavailable or whose units are all empty cannot be handed downstream as ``read``: that
    would assert a body was examined when only the title and layout were. It routes to
    ``generic_read`` instead, and the coverage reasons record why.
    """
    if winner.profile_id == "administrative":
        return "administrative_candidate"
    if winner.family == "unknown":
        return "generic_read"
    if not _has_readable_body(parsed):
        return "generic_read"
    if winner.family in _BUSINESS_FAMILIES:
        return "read"
    return "generic_read"


def _has_readable_body(parsed: Observation) -> bool:
    """True when at least one probed unit carries non-whitespace text."""
    return any(unit.text.strip() for unit in parsed.probes)


def _confidence(
    parsed: Observation,
    bag: SignalBag,
    winner,
    disposition: str,
) -> str:
    """Coarse confidence only; no calibrated probability without calibration."""
    if winner.profile_id == "generic":
        if not any(unit.text.strip() for unit in parsed.units):
            return "unknown"
        return "low"
    if winner.subtype and "未指定" in winner.subtype:
        return "low"
    if parsed.native_scan == "unavailable" and not any(unit.text.strip() for unit in parsed.units):
        return "low"

    structural = {
        signal.code
        for signal in bag.cover_signals + bag.toc_signals
        if signal.code in {v.REASON_COVER_HEADING, v.REASON_TOC_STRUCTURE, "SLIDE_STRUCTURE"}
    }
    body_evidence = {signal.code for signal in bag.body_signals}

    score = 0
    if v.REASON_COVER_HEADING in structural or "SLIDE_STRUCTURE" in structural:
        score += 2
    if v.REASON_TOC_STRUCTURE in structural:
        score += 1
    if body_evidence & {
        v.REASON_SECTION_VOCABULARY,
        v.REASON_QA_STRUCTURE,
        v.REASON_SPEAKER_TURNS,
    }:
        score += 1

    if winner.profile_id == "administrative":
        score = max(score, 1)

    if parsed.probe_limited:
        score = min(score, 1)
    if parsed.native_scan == "unavailable":
        score = min(score, 1)
    if parsed.native_scan == "partial":
        score = min(score, 2)
    if disposition == "generic_read":
        score = min(score, 1)

    if score >= 3:
        return "high"
    if score == 2:
        return "medium"
    if score == 1:
        return "low"
    return "unknown"


__all__ = [
    "INPUT_SCHEMA_VERSION",
    "SCHEMA_VERSION",
    "Observation",
    "ObservationError",
    "Signal",
    "SignalBag",
    "UnitRef",
    "get_profile",
    "list_profiles",
    "route_document",
    "resolve_reading_profile",
    "select_business_facets",
]
