"""Bounded same-source attachment ranges; unread links remain diagnostics."""
from __future__ import annotations

from dataclasses import replace
import re

from .decision import decide
from .observation import Observation
from .signals import URL_PATTERN, detect_signals, is_title_evidence, normalize

_EXHIBIT = re.compile(r"^(?:exhibit|附件)\s*(?:no\.?\s*)?\d+(?:\.\d+)?(?:\s|[:：-]|$)", re.IGNORECASE)


def attachment_markers(parsed: Observation, *, probes_only: bool = True):
    return [unit for unit in (parsed.probes if probes_only else parsed.units)
            if unit.kind != 'reference' and (unit.kind == 'attachment' or is_title_evidence(unit))
            and _EXHIBIT.search(normalize(unit.text)) and not URL_PATTERN.search(unit.text)]


def primary_scope(parsed: Observation) -> Observation:
    """One observed container scope; a child's facts never name its parent."""
    if parsed.native_source_signals is None:
        return parsed
    markers = attachment_markers(parsed)
    if parsed.is_attachment_scope and parsed.units:
        markers = [marker for marker in markers if marker.unit_id != parsed.units[0].unit_id]
    if not markers:
        return parsed
    stop = min(marker.ordinal for marker in markers)
    probes = tuple(unit for unit in parsed.probes if unit.ordinal < stop)
    return replace(parsed, units=tuple(unit for unit in parsed.units if unit.ordinal < stop),
                   probes=probes, probed_chars=sum(len(unit.text) for unit in probes))


def reserve_native_scope(parsed: Observation, reserved_ids: tuple[str, ...]) -> tuple[str, ...]:
    """Boundary precedes its observed child carrier inside the original cap."""
    marker_ids = {unit.unit_id for unit in attachment_markers(parsed, probes_only=False)}
    reserved = set(reserved_ids)
    boundary = None
    result = {}
    for unit in parsed.units:
        if unit.unit_id in marker_ids:
            boundary = unit.unit_id
        if unit.unit_id in reserved:
            if boundary is not None:
                result[boundary] = None
            result[unit.unit_id] = None
    return tuple(result)


def attachment_routes(parsed: Observation, *, cap: int) -> tuple[list[dict], list[dict]]:
    """Only fully observed ranges receive a typed child, never a lone marker.

    A container's exhibit boundary is a heading/attachment marker, not a mention
    in prose. Every member through the next observed exhibit boundary must have
    been probed without character clipping. Missing members produce a gap and no
    false complete range. The final exhibit ends at the end of this source.
    """
    if cap <= 0:
        return [], []
    original = {unit.unit_id: (index, unit) for index, unit in enumerate(parsed.units)}
    probed = {unit.unit_id: unit for unit in parsed.probes}
    markers = attachment_markers(parsed)
    children: list[dict] = []
    diagnostics: list[dict] = []
    for position, marker in enumerate(markers):
        if URL_PATTERN.search(marker.text) or marker.kind in {"link", "external_link"}:
            continue
        start = original[marker.unit_id][0]
        stop = original[markers[position+1].unit_id][0] if position+1 < len(markers) else len(parsed.units)
        members = parsed.units[start:stop]
        complete = all(unit.unit_id in probed and not probed[unit.unit_id].text_clipped for unit in members)
        pages = [unit.page for unit in members if unit.page is not None]
        missing_pages = {*parsed.opaque_pages, *parsed.deferred_pages}
        if parsed.native_scan == "unavailable" or (
            pages and any(min(pages) <= page <= max(pages) for page in missing_pages)
        ) or (not pages and parsed.native_scan == "partial"):
            complete = False
        if not complete:
            diagnostics.append({"code": "CHILD_RANGE_NOT_READ", "unit_ids": [marker.unit_id],
                                "detail": "附件区间存在未探测/截短单元；未声明为完整已读子文档"})
            continue
        if not any(unit.text.strip() and unit.kind not in {"heading", "title", "attachment", "toc"} for unit in members[1:]):
            diagnostics.append({"code": "CHILD_RANGE_NOT_READ", "unit_ids": [marker.unit_id],
                                "detail": "附件标记后没有已读正文；标记不是附件内容"})
            continue
        child = replace(parsed, title=None, form_type=None, declared_kind=None, regime_claim=None,
                        units=tuple(members), probes=tuple(members),
                        probed_chars=sum(len(unit.text) for unit in members), probe_limited=False,
                        char_limited=False, is_attachment_scope=True)
        signals = detect_signals(child)
        winner = decide(child, signals)
        # A shared compatibility profile ID does not identify the observed
        # purpose. Keep the source-only route decision for the downstream
        # policy resolver; never make it guess the family from that ID again.
        children.append({"unit_ids": [unit.unit_id for unit in members], "profile_id": winner.profile_id,
                         "family": winner.family, "regime": winner.regime,
                         "form_type": winner.form_type or "unknown",
                         "subtype": winner.subtype, "reason": "IN_DOCUMENT_ATTACHMENT_RANGE"})
        if len(children) >= cap:
            break
    return children, diagnostics
