"""A new reading policy discovers operating matrices; old parser replay is stable."""
from hashlib import sha256
import fitz
from company_wiki.source_catalog.narrative_evidence import parse_pdf_bytes
from company_wiki.source_catalog.narrative_replay import (
    prepare_pdf_replay_bytes, verify_replayed_pdf_spans,
)
from company_wiki.source_contract import source_id_for_sha256


def _original():
    doc = fitz.open()
    doc.new_page().insert_text((72,72), 'Annual Report 2025')
    page = doc.new_page()
    page.insert_text((72,60), 'Store network by operating model')
    xs = [72,372,442,512]
    ys = [90,120,150,180,210]
    for x in xs:
        page.draw_line((x,ys[0]),(x,ys[-1]))
    for y in ys:
        page.draw_line((xs[0],y),(xs[-1],y))
    rows = [('Stores by operating model','2024','2025'),
            ('Directly operated stores','16','21'),
            ('Stores operated under distributor model','38','47'),
            ('Total','54','68')]
    for index, row in enumerate(rows):
        for col, text in enumerate(row):
            page.insert_text((xs[col]+4, ys[index]+19), text, fontsize=9)
    data = doc.tobytes()
    doc.close()
    return data


def test_actual_store_matrix_discovery_does_not_require_recent_event_word():
    raw = _original()
    digest = sha256(raw).hexdigest()
    common = {'source_id':source_id_for_sha256(digest), 'source_sha256':digest, 'language':'en'}
    old = parse_pdf_bytes(raw, **common, selector_version='0.8.0')
    new = parse_pdf_bytes(raw, **common, selector_version='0.9.0')
    assert 2 not in old.table_scan_pages
    assert 2 in new.table_scan_pages
    original_units = [(u.coordinates,u.raw_text,u.unit_kind) for u in old.units]
    assert [(u.coordinates,u.raw_text,u.unit_kind) for u in new.units
            if u.unit_kind != 'pdf_table_row'] == original_units
    rows = [u for u in new.units if u.unit_kind == 'pdf_table_row' and u.coordinates.page_number==2]
    assert len(rows) == 4
    assert rows[0].metadata['table_headers'] == ('Stores by operating model','2024','2025')
    assert rows[-1].raw_text == 'Total | 54 | 68'
    assert sha256(raw).hexdigest() == digest


def test_new_operating_matrix_locators_replay_without_reapplying_reading_policy():
    raw = _original()
    digest = sha256(raw).hexdigest()
    common = {'source_id':source_id_for_sha256(digest), 'source_sha256':digest, 'language':'en'}
    parsed = parse_pdf_bytes(raw, **common, selector_version='0.9.0')
    spans = tuple(unit.to_evidence_span(selection_reasons=('operating_table',), topics=('operating_metrics',))
                  for unit in parsed.units if unit.unit_kind == 'pdf_table_row')
    assert len(spans) == 4
    plan = prepare_pdf_replay_bytes(raw, source_id=common['source_id'], source_sha256=digest,
                                   evidence_spans=spans, default_parser_version=parsed.units[0].parser_version)
    assert plan.table_pages == (2,)
    replayed = parse_pdf_bytes(raw, **common, parser_version=plan.parser_version,
                              table_pages=plan.table_pages)
    verified, failed = verify_replayed_pdf_spans(spans, replayed.units)
    assert not failed
    assert verified == tuple(span.span_id for span in spans)
