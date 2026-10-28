"""Provisional discovery from the parser's current measured DICT only.

The existing table-purpose owner supplies all business vocabulary. Geometry
establishes nearby aligned fields/rows; discovery never certifies final table
purpose. Cross-page state contains only bounded measured columns and short
source field labels, never native objects, row values or full-page text.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
import math
from typing import Any, TypeGuard

from company_wiki.document_understanding.structure.table_purpose import (
    operating_header, qualify_table,
)
from company_wiki.resource_budget import WorkBudget, WorkBudgetExceeded

SIGNATURE_VERSION = "pdf-measured-candidate/1"
MAX_SPANS = 20000
MAX_COLUMNS = 16
MAX_FIELD = 128
MAX_MEMO = 4096


class _CandidateWork:
    """Call-local reuse of actual measured views and semantic owner results.

    Cache lookups pay for keys/hashing; misses also reserve the actual text
    interpretation. Nothing is cached across source pages or modifies the
    caller account's ceiling. Once bounded caches fill, work is recomputed and
    charged normally rather than silently extending their memory.
    """

    def __init__(self, budget):
        self.budget = budget
        self.texts, self.headers, self.purposes = {}, {}, {}

    def charge(self, count=1):
        return self.budget.charge(count)

    def text(self, cells):
        self.charge()
        key = id(cells)  # rows retain these lists for this entire invocation
        if key not in self.texts:
            self.charge(1 + sum(len(c['text']) + 3 for c in cells))
            value = ' | '.join(c['text'] for c in cells)
            if len(self.texts) < MAX_MEMO:
                self.texts[key] = value
            return value
        return self.texts[key]

    def operating(self, text):
        self.charge(1 + len(text) // 64)
        if text not in self.headers:
            self.charge(1 + len(text))
            value = operating_header(text)
            if len(self.headers) < MAX_MEMO:
                self.headers[text] = value
            return value
        return self.headers[text]

    def purpose(self, headers, body):
        self.charge(1 + len(headers) + (sum(len(s) for s in headers) + len(body)) // 64)
        key = (tuple(headers), body)
        if key not in self.purposes:
            self.charge(1 + sum(len(s) for s in headers) + len(body))
            value = qualify_table(headers, [body])
            if len(self.purposes) < MAX_MEMO:
                self.purposes[key] = value
            return value
        return self.purposes[key]


def _sequence(value: Any) -> TypeGuard[Sequence[Any]]:
    return isinstance(value, Sequence) and not isinstance(value, (str, bytes))


def _number(value: Any) -> TypeGuard[int | float]:
    if type(value) not in (int, float):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def _measure_rows(snapshot, budget, width, height):
    spans: list[tuple[float, float, float, float, str]] = []
    blocks = snapshot.get('blocks', ())
    if not _sequence(blocks):
        return [], True
    malformed = False
    for block in blocks:
        budget.charge()
        if not isinstance(block, Mapping):
            malformed = True
            continue
        if block.get('type') != 0:
            continue
        lines = block.get('lines', ())
        if not _sequence(lines):
            malformed = True
            continue
        for line in lines:
            budget.charge()
            values = line.get('spans', ()) if isinstance(line, Mapping) else None
            if not _sequence(values):
                malformed = True
                continue
            for span in values:
                budget.charge()
                if len(spans) >= MAX_SPANS:
                    return [], True
                if not isinstance(span, Mapping):
                    malformed = True
                    continue
                text, box = span.get('text'), span.get('bbox')
                if not isinstance(text, str):
                    malformed = True
                    continue
                budget.charge(1 + len(text))
                if not text.strip():
                    continue
                if (not _sequence(box) or len(box) != 4
                        or not all(_number(x) for x in box)
                        or not 0 <= box[0] < box[2] <= width
                        or not 0 <= box[1] < box[3] <= height):
                    malformed = True
                    continue
                spans.append((float(box[0]), float(box[1]), float(box[2]), float(box[3]), text))
    budget.charge(1 + len(spans) * max(1, len(spans).bit_length()))
    spans.sort(key=lambda s: ((s[1] + s[3]) / 2, s[0]))
    groups: list[dict[str, Any]] = []
    for span in spans:
        budget.charge()
        center, height = (span[1] + span[3]) / 2, span[3] - span[1]
        if (groups and abs(center - groups[-1]['center']) <= min(height, groups[-1]['height']) * .45):
            groups[-1]['spans'].append(span)
        else:
            groups.append({'center': center, 'height': height, 'spans': [span]})
    rows = []
    for group in groups:
        raw = group['spans']
        budget.charge(1 + len(raw) * max(1, len(raw).bit_length()))
        raw.sort(key=lambda s: s[0])
        cells: list[dict[str, Any]] = []
        for x0, y0, x1, y1, text in raw:
            budget.charge()
            if cells and x0 <= cells[-1]['x1'] + 3:
                cell = cells[-1]
                cell['parts'].append(text)
                cell['x1'] = max(cell['x1'], x1)
                cell['y0'], cell['y1'] = min(cell['y0'], y0), max(cell['y1'], y1)
            else:
                cells.append({'x0': x0, 'x1': x1, 'y0': y0, 'y1': y1, 'parts': [text]})
        for cell in cells:
            parts = cell.pop('parts')
            budget.charge(1 + len(parts) + sum(len(s) for s in parts))
            cell['text'] = ''.join(parts).strip()
        rows.append({'cells': cells, 'y0': min(s[1] for s in raw),
                     'y1': max(s[3] for s in raw), 'height': group['height']})
    return rows, malformed


def _aligned(first, second, budget, *, exact=False, qa=False):
    budget.charge(1 + len(first) * len(second))
    # A question and its answer often occupy a single wide table cell.  This
    # only requests discovery: native extraction still owns cells and speakers.
    # A wide prose box overlaps almost any other box, so one-column continuity
    # needs the measured text margin rather than the multi-column overlap rule.
    if qa and len(first) == len(second) == 1:
        return [(0, 0)] if abs(first[0]['x0'] - second[0]['x0']) <= 8 else []
    if not 2 <= len(first) <= MAX_COLUMNS or not 2 <= len(second) <= MAX_COLUMNS:
        return []
    if exact and len(first) != len(second):
        return []
    pairs, j = [], 0
    for i, left in enumerate(first):
        while j < len(second):
            right = second[j]
            overlap = min(left['x1'], right['x1']) - max(left['x0'], right['x0'])
            width = min(left['x1'] - left['x0'], right['x1'] - right['x0'])
            aligned = (overlap >= .2 * width
                       or abs(left['x0'] - right['x0']) <= 8
                       or abs(left['x1'] - right['x1']) <= 8)
            if aligned:
                pairs.append((i, j))
                j += 1
                break
            if right['x1'] < left['x0']:
                j += 1
                continue
            break
    if len(pairs) < 2 or (exact and len(pairs) != len(first)):
        return []
    return pairs


def _text(cells, budget):
    return budget.text(cells)


def _field_eligibility(headers, body, pairs, budget):
    observed_fields = []
    for i, j in pairs:
        label = headers[i]['text']
        budget.charge(1 + len(label))
        field_like = (len(label) <= MAX_FIELD and not any(mark in label for mark in '。；!?！？')
                      and headers[i]['x1'] - headers[i]['x0'] <= 160)
        if field_like and budget.operating(label):
            observed_fields.append((label, j))
    # No actual operating field means there is nothing to classify. Avoid
    # constructing/interpreting an entire unrelated financial row twice.
    if not observed_fields:
        return []
    header_texts = [c['text'] for c in headers]
    row_text = _text(body, budget)
    purpose = budget.purpose(header_texts, row_text)
    # Actual project overview fields may be mixed with allocation amounts.
    # Column-local non-money fields still justify provisional discovery; the
    # whole-table purpose owner remains responsible after real extraction.
    if not purpose.eligible and purpose.reason != 'PROJECT_AMOUNTS_WITHOUT_OPERATING_RELATION':
        return []
    fields = []
    for label, j in observed_fields:
        value = body[j]['text']
        budget.charge()
        if budget.purpose([label], value).eligible:
            fields.append(label)
    return fields[:MAX_COLUMNS]


def _qa_marker(text, parser_version):
    # This is the existing source grammar, not a second Q&A classifier.
    from .narrative_evidence import _has_pdf_question, _QA_ANSWER

    return _has_pdf_question(text, parser_version) or bool(_QA_ANSWER.search(text))


def _pair_candidate(first, second, budget, qa, parser_version):
    pairs = _aligned(first['cells'], second['cells'], budget, qa=qa)
    if not pairs:
        return None
    if qa:
        first_text, second_text = _text(first['cells'], budget), _text(second['cells'], budget)
        budget.charge(1 + len(first_text) + len(second_text))
        if _qa_marker(first_text, parser_version) or _qa_marker(second_text, parser_version):
            return {'kind': 'qa', 'fields': [], 'reason': 'aligned_source_qa_grid'}
    # The one-column exception belongs to an observed Q/A marker, not merely
    # the document's reading intent. Ordinary field/value tables still need
    # the original two-column structural observation.
    if len(pairs) < 2:
        return None
    fields = _field_eligibility(first['cells'], second['cells'], pairs, budget)
    if not fields:
        fields = _field_eligibility(second['cells'], first['cells'], [(j, i) for i, j in pairs], budget)
    if fields:
        return {'kind': 'operating', 'fields': fields, 'reason': 'aligned_operating_fields_and_rows'}
    return None


def _continuation(previous, width, height, budget, qa):
    budget.charge()
    if not isinstance(previous, Mapping) or previous.get('schema_version') != SIGNATURE_VERSION:
        return None
    if previous.get('kind') not in ('operating', 'qa') or previous.get('kind') == 'qa' and not qa:
        return None
    old_width, old_height = previous.get('width'), previous.get('height')
    if (not _number(old_width) or not _number(old_height)
            or abs(old_width - width) > width * .01 or abs(old_height - height) > height * .01):
        return None
    columns, fields = previous.get('columns'), previous.get('fields')
    minimum = 1 if previous['kind'] == 'qa' else 2
    if not _sequence(columns) or not minimum <= len(columns) <= MAX_COLUMNS:
        return None
    if not _sequence(fields) or len(fields) > MAX_COLUMNS:
        return None
    budget.charge(1 + len(columns) + len(fields))
    if any(not isinstance(s, str) or len(s) > MAX_FIELD for s in fields):
        return None
    cells = []
    for pair in columns:
        if (not _sequence(pair) or len(pair) != 2 or not all(_number(x) for x in pair)
                or not 0 <= pair[0] < pair[1] <= width):
            return None
        cells.append({'x0': pair[0], 'x1': pair[1]})
    if previous['kind'] == 'operating' and not fields:
        return None
    return {'kind': previous['kind'], 'fields': list(fields), 'columns': cells,
            'reason': 'measured_table_continuation'}


def _eligible_continuation(active, row, budget):
    if active['kind'] == 'qa':
        return True
    text = _text(row['cells'], budget)
    return budget.purpose(active['fields'], text).eligible


def observe_pdf_candidate(snapshot, *, work_budget: WorkBudget, qa: bool = False,
                          parser_version: str | None = None,
                          previous: Mapping | None = None) -> dict:
    """Return a bounded provisional observation on one already-read DICT.

    ROOT ensures a previous signature is from this source's immediately prior
    page. Missing/malformed or resource-limited observations never retain it.
    """
    result: dict[str, Any] = {'candidate': False, 'continuation': None,
                               'reason': 'no_measured_operating_grid', 'partial': False}
    budget = _CandidateWork(work_budget)
    try:
        budget.charge()
        if not isinstance(snapshot, Mapping):
            return dict(result, reason='malformed_snapshot', partial=True)
        width, height = snapshot.get('width'), snapshot.get('height')
        if not _number(width) or not _number(height) or width <= 0 or height <= 0:
            return dict(result, reason='malformed_snapshot', partial=True)
        rows, malformed = _measure_rows(snapshot, budget, width, height)
        result['partial'] = malformed
        if not rows:
            return dict(result, reason='empty_or_malformed_snapshot')
        budget.charge(1 + len(rows) * max(1, len(rows).bit_length()))
        typical = sorted(r['height'] for r in rows)[len(rows) // 2]
        body = []
        for row in rows:
            budget.charge()
            cells = row['cells']
            running_header = (len(cells) == 1 and row['y1'] <= height * .1
                              and row['height'] < typical * .9)
            footer = (len(cells) == 1 and row['y0'] >= height * .92
                      and cells[0]['x1'] - cells[0]['x0'] < width * .25)
            if not running_header and not footer:
                body.append(row)
        prior = _continuation(previous, width, height, budget, qa)
        active, last = None, None
        for index, row in enumerate(body):
            budget.charge()
            cells = row['cells']
            # Keep the existing multi-column date interstitial before the
            # Q/A-specific minimum; accepting one-column Q/A must not turn a
            # previously skipped date into a break in a two-column grid.
            if last is not None and len(last['cells']) >= 2 and len(cells) == 1:
                text = _text(cells, budget)
                budget.charge(1 + len(text))
                if (len(text) <= 32 and any(c.isdigit() for c in text)
                        and all(c.isdigit() or c in ' \t-–—/年月日季度半至止' for c in text)
                        and not budget.operating(text)
                        and cells[0]['x1'] - cells[0]['x0'] < width * .4):
                    continue
            if not (1 if qa else 2) <= len(cells) <= MAX_COLUMNS:
                active, last = None, None
                continue
            close = last is not None and row['y0'] - last['y1'] <= max(24, 3 * typical)
            if (active and last is not None and close
                    and _aligned(last['cells'], cells, budget, exact=True, qa=active['kind'] == 'qa')
                    and _eligible_continuation(active, row, budget)):
                active['rows'] += 1
                if active['rows'] >= 2:
                    result.update(candidate=True, reason=active['reason'])
            else:
                candidate = _pair_candidate(last, row, budget, qa, parser_version) if close else None
                if candidate:
                    active = dict(candidate, rows=2)
                    result.update(candidate=True, reason=candidate['reason'])
                elif (index == 0 and prior and row['y0'] <= height * .2
                      and _aligned(prior['columns'], cells, budget, exact=True, qa=prior['kind'] == 'qa')
                      and _eligible_continuation(prior, row, budget)):
                    active = dict(prior, rows=1)
                else:
                    active = None
            last = row
        if (active and active['rows'] >= 2 and last is not None and body[-1] is last
                and last['y1'] >= height * .75 and not malformed):
            budget.charge(1 + len(last['cells']) + len(active['fields']))
            result['continuation'] = {
                'schema_version': SIGNATURE_VERSION, 'kind': active['kind'],
                'width': width, 'height': height,
                'columns': [[c['x0'], c['x1']] for c in last['cells']],
                'fields': active['fields'][:MAX_COLUMNS],
            }
        return result
    except WorkBudgetExceeded:
        return dict(result, candidate=False, continuation=None,
                    reason='work_budget_exhausted', partial=True)


__all__ = ['observe_pdf_candidate']
