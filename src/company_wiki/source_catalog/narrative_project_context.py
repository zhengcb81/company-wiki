"""Pure visual association of fundraising introductions and project rows."""
from collections.abc import Mapping, Sequence
from dataclasses import replace
import hashlib
import math
import re
from types import MappingProxyType

from .n6_candidate_completion import MAX_COMPLETION_UNITS, PROJECT_CHARACTER_WINDOW
from .narrative_candidates import EvidenceCandidate
from .narrative_document import NarrativeUnit
from .narrative_group_candidates import GroupEnrichmentResult
from .narrative_pdf_groups import PdfContextGroup


_INTRO = re.compile(r"(?:募集资金|募投)[^。；]{0,180}(?:投资于|用于|投向)(?:以下|下列|这些).{0,12}项目")
_PURPOSE = re.compile(r"运用方向|投资方向|投资项目|募投项目|项目名称|资金用途")
_PROJECT = re.compile(r"(?:设备|装备|生产线|车间|基地|研发|材料|工厂|厂房|产业园|产品|软件|系统|平台)"
                      r".{0,30}(?:项目|建设|扩建|扩产|技改|升级)")
_FINANCE_ONLY = re.compile(r"补充流动资金|补充营运资金|偿还|还贷|合计|总计")
_CAPTION = re.compile(r"^\s*[（(]?(?:单位|币种)\s*[:：]")
Box = tuple[float, float, float, float]
Identity = tuple[str, str, str, str, str, int | None]


def _identity(unit: NarrativeUnit) -> Identity:
    return (unit.source_id, unit.parser_name, unit.parser_version, unit.language,
            unit.source_role, unit.coordinates.page_number)


def _box(unit: NarrativeUnit) -> Box | None:
    value = unit.metadata.get('bbox')
    if not isinstance(value, (list, tuple)) or len(value) != 4:
        return None
    try:
        x0, y0, x1, y1 = (float(v) for v in value)
    except (ValueError, TypeError):
        return None
    if not all(math.isfinite(v) for v in (x0,y0,x1,y1)) or x1 <= x0 or y1 <= y0:
        return None
    return x0,y0,x1,y1


def _bounds(units: Sequence[NarrativeUnit]) -> Box | None:
    boxes = [_box(u) for u in units]
    if not boxes or any(b is None for b in boxes):
        return None
    valid = [b for b in boxes if b is not None]
    return min(b[0] for b in valid),min(b[1] for b in valid),max(b[2] for b in valid),max(b[3] for b in valid)


def _overlap(left: Box, right: Box) -> bool:
    width = min(left[2]-left[0], right[2]-right[0])
    return min(left[2],right[2])-max(left[0],right[0]) >= 0.6 * width


def _project_row(unit: NarrativeUnit) -> bool:
    headers = unit.metadata.get('table_headers', ())
    cells = unit.metadata.get('row_cells', ())
    if not isinstance(headers,(list,tuple)) or not isinstance(cells,(list,tuple)):
        return False
    if not any('募集资金' in str(h) or '募投' in str(h) for h in headers):
        return False
    columns = [i for i,h in enumerate(headers) if _PURPOSE.search(str(h))]
    if len(columns) != 1 or columns[0] >= len(cells):
        return False
    purpose = str(cells[columns[0]])
    return bool(_PROJECT.search(purpose) and not _FINANCE_ONLY.search(purpose))


def _visible_relation(intro: Sequence[NarrativeUnit], rows: Sequence[NarrativeUnit],
                      units: Sequence[NarrativeUnit]) -> float | None:
    identity = _identity(intro[0])
    if identity[4] != 'company_filing' or identity[5] is None:
        return None
    if any(_identity(u) != identity for u in (*intro,*rows)):
        return None
    above, below = _bounds(intro), _bounds(rows)
    if above is None or below is None or not _overlap(above,below):
        return None
    gap = below[1]-above[3]
    if not 0 <= gap <= 72:
        return None
    for unit in units:
        if unit.unit_kind != 'pdf_text_block' or _identity(unit) != identity:
            continue
        box = _box(unit)
        if box is not None and above[3] <= box[1] < below[1] and _overlap(above,box):
            if not _CAPTION.search(unit.raw_text):
                return None
    return gap


def _members(units: Sequence[NarrativeUnit], intro: tuple[NarrativeUnit,...]) -> tuple[NarrativeUnit,...]:
    tables: dict[tuple[Identity,int],list[NarrativeUnit]] = {}
    for unit in units:
        index = unit.coordinates.table_index
        if unit.unit_kind == 'pdf_table_row' and index is not None and _project_row(unit):
            tables.setdefault((_identity(unit),index),[]).append(unit)
    choices = []
    for rows in tables.values():
        gap = _visible_relation(intro,rows,units)
        if gap is not None:
            choices.append((gap,rows))
    choices.sort(key=lambda choice:choice[0])
    if not choices or (len(choices)>1 and choices[1][0]-choices[0][0] <= 1):
        return ()  # an ambiguous table must not acquire this introduction
    rows = sorted(choices[0][1],key=lambda u:(u.coordinates.row_index or 0,u.unit_id))
    members = (*intro,*rows)
    if len(members)>MAX_COMPLETION_UNITS or sum(len(u.raw_text) for u in members)>PROJECT_CHARACTER_WINDOW:
        return ()
    return members


def enrich_fundraising_table_context(
    units: Sequence[NarrativeUnit], groups: Sequence[PdfContextGroup], *,
    initial_candidates: Sequence[EvidenceCandidate], initial_group_ids: Mapping[str, str],
) -> GroupEnrichmentResult:
    """Enrich replayable units without changing parser output or raw bytes."""
    candidates = {c.unit.unit_id:c for c in initial_candidates}
    group_ids = dict(initial_group_ids)
    for _, intro, text in groups:
        if not intro or not _INTRO.search(text):
            continue
        members = _members(units,intro)
        if not members:
            continue
        ids = {u.unit_id for u in members}
        old_groups = {group_ids[uid] for uid in ids if uid in group_ids}
        if any(uid not in ids and gid in old_groups for uid,gid in group_ids.items()):
            continue
        digest = hashlib.sha256('|'.join(u.unit_id for u in members).encode()).hexdigest()
        group_id = 'urn:company-wiki:fundraising-context:sha256:'+digest
        for unit in members:
            old = candidates.get(unit.unit_id)
            if old is None:
                old = EvidenceCandidate(unit,('capacity_projects',),(),8)
            candidates[unit.unit_id] = replace(old,
                topics=tuple(dict.fromkeys((*old.topics,'capacity_projects'))),
                reasons=tuple(dict.fromkeys((*old.reasons,'concrete_fundraising_project',
                                           'fundraising_table_context','project_plan_or_status'))))
            group_ids[unit.unit_id] = group_id
    return GroupEnrichmentResult(tuple(candidates.values()),MappingProxyType(group_ids))
