"""Independent small DOCX normalize/select/replay check; no runtime state writes."""
from __future__ import annotations
from collections.abc import Mapping
from dataclasses import fields, is_dataclass, replace
from datetime import datetime, timezone
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import sys
import zipfile

OUT = Path(__file__).resolve().parent
BASE = OUT.parent.parent
TREE = BASE.parents[5]
sys.dont_write_bytecode = True
sys.path.insert(0, str(TREE / 'src'))
from company_wiki import document_normalization as dn
from company_wiki.source_catalog.narrative_normalization import NarrativeNormalization
from company_wiki.source_catalog.narrative_evidence import select_narrative_evidence
from company_wiki.source_contract import source_id_for_sha256
from company_wiki.source_contract.evidence_span import output_sha256_for, evidence_span_id_for

MIME = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
SOURCES = (
    'src/company_wiki/document_normalization/docx_parser.py',
    'src/company_wiki/document_normalization/units.py',
    'src/company_wiki/document_normalization/__init__.py',
    'src/company_wiki/document_normalization/replay.py',
    'src/company_wiki/source_catalog/narrative_normalization.py',
    'src/company_wiki/source_catalog/narrative_business_groups.py',
    'src/company_wiki/source_catalog/narrative_evidence.py',
    'src/company_wiki/automation/narrative_batch.py',
    'config/source_catalog.yaml',
)

def plain(value):
    if is_dataclass(value):
        return {f.name: plain(getattr(value, f.name)) for f in fields(value)}
    if isinstance(value, Mapping):
        return {k: plain(v) for k, v in value.items()}
    if isinstance(value, (tuple, list, set, frozenset)):
        return [plain(v) for v in value]
    return value

def digest(data):
    return sha256(data).hexdigest()

def hashes():
    return {p: digest((TREE / p).read_bytes()) for p in SOURCES}

def normalize(data, version=None):
    sha = digest(data)
    return dn.normalize_document(data, source_id=source_id_for_sha256(sha),
        source_sha256=sha, mime_type=MIME, parser_version=version)

def old_record(doc):
    return {
        'source_sha256': doc.source_sha256, 'parser_version': doc.parser_version,
        'metadata': plain(doc.metadata), 'errors': list(doc.structure.errors),
        'units': [{k: plain(getattr(u, k)) for k in (
            'unit_id', 'source_id', 'parser_name', 'parser_version', 'coordinates',
            'raw_text', 'unit_kind', 'source_role', 'language', 'quality_flags', 'metadata')}
            for u in doc.units],
    }

def select_and_replay(data, doc):
    selected = select_narrative_evidence(NarrativeNormalization.language_structure(doc, 'en'),
        title='Company communication', existing_kind='investor_relations', selector_version='0.7.1')
    port = NarrativeNormalization()
    count = port.replay(data, source_id=doc.source_id, source_sha256=doc.source_sha256,
        mime_type=MIME, evidence_spans=selected.evidence_spans, language='en')
    all_text = dn.replay_units(data, source_sha256=doc.source_sha256,
        units=doc.units, limits=dn.NormalizationLimits())
    assert all_text == tuple(u.raw_text for u in doc.units)
    return selected, count

def p(text, props=''):
    from xml.sax.saxutils import escape
    return '<w:p>' + ('<w:pPr>' + props + '</w:pPr>' if props else '') + '<w:r><w:t>' + escape(text) + '</w:t></w:r></w:p>'

def own_package():
    styles = f'''<w:styles xmlns:w="{W}">
      <w:style w:type="paragraph" w:default="1" w:styleId="Ordinary"><w:name w:val="Ordinary"/></w:style>
      <w:style w:type="paragraph" w:styleId="OutlineRoot"><w:name w:val="Root"/><w:pPr><w:outlineLvl w:val="0"/></w:pPr></w:style>
      <w:style w:type="paragraph" w:styleId="ReviewMiddle"><w:basedOn w:val="OutlineRoot"/></w:style>
      <w:style w:type="paragraph" w:styleId="ReviewChild"><w:name w:val="Neutral Child"/><w:basedOn w:val="ReviewMiddle"/></w:style>
      <w:style w:type="paragraph" w:styleId="ReviewBody"><w:name w:val="Body Override"/><w:basedOn w:val="ReviewChild"/><w:pPr><w:outlineLvl w:val="9"/></w:pPr></w:style>
    </w:styles>'''
    body = (
        p('The return calculation has not changed')
        + p('Efficiency assumptions', '<w:pStyle w:val="ReviewChild"/>')
        + p('Efficiency depends on workload mix, token usage and silicon price performance.')
        + '<w:tbl><w:tr><w:tc>' + p('Company launched a new product and expanded overseas production capacity.', '<w:pStyle w:val="ReviewChild"/>') + '</w:tc></w:tr></w:tbl>'
        + p('The workload calculation has not changed', '<w:pStyle w:val="ReviewChild"/><w:outlineLvl w:val="9"/>')
        + p('Efficiency depends on customer workload mix, token usage and memory price performance.', '<w:pStyle w:val="ReviewBody"/>')
        + p('Other programme assumptions', '<w:pStyle w:val="ReviewBody"/><w:outlineLvl w:val="2"/>')
        + p('The operating plan has not changed. Efficiency depends on inference workload mix, token usage and chip price performance.')
    )
    parts = {
        '[Content_Types].xml': '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/><Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/></Types>',
        '_rels/.rels': '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="main" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>',
        'word/document.xml': f'<w:document xmlns:w="{W}"><w:body>{body}<w:sectPr/></w:body></w:document>',
        'word/_rels/document.xml.rels': '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="styles" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>',
        'word/styles.xml': styles,
    }
    out = BytesIO()
    with zipfile.ZipFile(out, 'w') as z:
        for name, text in parts.items():
            z.writestr(zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0)), text.encode())
    return out.getvalue()

def rejection(fn):
    try:
        fn()
    except (dn.ReplayError, ValueError) as exc:
        return {'rejected': True, 'error_type': type(exc).__name__, 'message': str(exc)}
    return {'rejected': False}

before_source = hashes()
checks = []
def check(name, value, details=None):
    checks.append({'id': name, 'status': 'PASS' if value else 'FAIL', 'details': details})

minimal_path = BASE / 'evidence/independent-review/docx_heading_minimal.docx'
minimal = minimal_path.read_bytes()
check('old_minimal_original_unchanged', digest(minimal) == 'c29c7c0d1a40da78cdf6215bb9675f27773b461af49d71f8e1877136d944702c')
current = normalize(minimal)
old_minimal = normalize(minimal, '1.0.0')
selected, count = select_and_replay(minimal, current)
check('minimal_default_real_version', current.parser_version == dn.DOCX_PARSER_VERSION == '1.1.0')
heading = current.units[1]
check('minimal_real_heading_and_original_locator', heading.unit_kind == 'docx_heading'
    and heading.metadata.get('heading_level') == 1 and heading.metadata.get('paragraph_style_id') == 'Heading1'
    and heading.metadata.get('source_locator') == 'cwp-docx-body/1|p=1')
check('minimal_no_context_crosses_heading', [s.raw_text for s in selected.evidence_spans] == [current.units[2].raw_text])
check('minimal_old_new_locators_match', [u.metadata['source_locator'] for u in current.units] == [u.metadata['source_locator'] for u in old_minimal.units])
check('minimal_versions_unit_ids_separate', {u.unit_id for u in current.units}.isdisjoint(u.unit_id for u in old_minimal.units))
check('minimal_selected_original_replay', count == len(selected.evidence_spans))
check('minimal_old_unit_exact_replay', dn.replay_units(minimal, source_sha256=old_minimal.source_sha256, units=old_minimal.units,
    limits=dn.NormalizationLimits()) == tuple(u.raw_text for u in old_minimal.units))
forged = replace(heading, metadata={**heading.metadata, 'heading_level': 7})
tampered_unit = rejection(lambda: dn.replay_unit(minimal, source_sha256=current.source_sha256, unit=forged, limits=dn.NormalizationLimits()))
check('forged_heading_unit_metadata_rejected', tampered_unit['rejected'], tampered_unit)
span = heading.to_evidence_span(topics=[], selection_reasons=[])
forged_meta = {**span.structured_value, 'outline_level': 8}
forged_output = output_sha256_for(raw_text=span.raw_text, structured_value=forged_meta)
forged_span = replace(span, structured_value=forged_meta, output_sha256=forged_output,
    span_id=evidence_span_id_for(source_id=span.source_id, locator=span.locator, output_sha256=forged_output))
tampered_span = rejection(lambda: NarrativeNormalization().replay(minimal, source_id=current.source_id,
    source_sha256=current.source_sha256, mime_type=MIME, evidence_spans=(forged_span,)))
check('forged_heading_span_metadata_rejected', tampered_span['rejected'], tampered_span)

own = own_package()
own_path = OUT / 'own-inheritance-outline.docx'
own_path.write_bytes(own)
own_doc = normalize(own)
own_selected, own_count = select_and_replay(own, own_doc)
own_by_locator = {s.structured_value['source_locator']: s for s in own_selected.evidence_spans}
u_by_locator = {u.metadata['source_locator']: u for u in own_doc.units}
prefix = 'cwp-docx-body/1|'
inherited = u_by_locator[prefix+'p=1']
direct_body = u_by_locator[prefix+'p=3']
style_body = u_by_locator[prefix+'p=4']
direct_heading = u_by_locator[prefix+'p=5']
check('own_three_level_style_inheritance', inherited.unit_kind == 'docx_heading' and inherited.metadata.get('outline_style_id') == 'OutlineRoot'
    and inherited.metadata.get('heading_level') == 1)
check('own_direct_outline9_body_override', direct_body.unit_kind == 'docx_paragraph' and direct_body.metadata.get('outline_level') == 9
    and 'heading_level' not in direct_body.metadata)
check('own_inherited_outline9_body_override', style_body.unit_kind == 'docx_paragraph' and style_body.metadata.get('outline_level') == 9
    and style_body.metadata.get('outline_style_id') == 'ReviewBody')
check('own_direct_heading_overrides_body_style', direct_heading.unit_kind == 'docx_heading' and direct_heading.metadata.get('heading_level') == 3)
check('own_no_context_crosses_inherited_heading', prefix+'p=0' not in own_by_locator and prefix+'p=1' not in own_by_locator and prefix+'p=2' in own_by_locator)
positive_locators = [prefix+'p=3', prefix+'p=4']
positive_spans = [own_by_locator.get(loc) for loc in positive_locators]
check('own_override_body_positive_group_complete', all(positive_spans)
    and positive_spans[0].structured_value.get('selection_group_id') is not None
    and positive_spans[0].structured_value.get('selection_group_id') == positive_spans[1].structured_value.get('selection_group_id'))
table_loc = prefix+'t=0|r=0|c=0|p=0'
check('own_business_cell_retained_source_semantics', table_loc in own_by_locator and u_by_locator[table_loc].unit_kind == 'docx_table_cell'
    and own_by_locator[table_loc].structured_value.get('selection_group_id') is None)
check('own_same_paragraph_positive_exact', prefix+'p=6' in own_by_locator and own_by_locator[prefix+'p=6'].raw_text == u_by_locator[prefix+'p=6'].raw_text)
check('own_direct_heading_barrier', prefix+'p=5' not in own_by_locator)
check('own_selected_original_replay', own_count == len(own_selected.evidence_spans))

implementation = BASE / 'evidence/docx-heading-implementation'
old_before = json.loads((implementation/'before.json').read_text(encoding='utf-8-sig'))
old_after = json.loads((implementation/'after.json').read_text(encoding='utf-8-sig'))
legacy = (implementation/'legacy-original.docx').read_bytes()
legacy_doc = normalize(legacy, '1.0.0')
legacy_record = old_record(legacy_doc)
check('legacy_original_sha', digest(legacy) == old_before['legacy_original_sha256'] == old_after['legacy_original_sha256'])
check('legacy_all_record_fields_before_after_independent_equal', old_before['legacy_record'] == old_after['legacy_record'] == legacy_record)
legacy_fp = digest(json.dumps(legacy_record, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode())
check('legacy_full_record_fingerprint_unchanged', legacy_fp == old_before['legacy_fingerprint'] == 'a6580fca5dcd6c063e2447bf5cf489aaabd8f61c52856646db744cb68d0031e4')
check('legacy_all_unit_exact_replay', dn.replay_units(legacy, source_sha256=legacy_doc.source_sha256,
    units=legacy_doc.units, limits=dn.NormalizationLimits()) == tuple(u.raw_text for u in legacy_doc.units))
legacy_forged = replace(legacy_doc.units[1], metadata={**legacy_doc.units[1].metadata, 'heading_level': 1})
legacy_tamper = rejection(lambda: dn.replay_unit(legacy, source_sha256=legacy_doc.source_sha256, unit=legacy_forged, limits=dn.NormalizationLimits()))
check('legacy_forged_heading_unit_metadata_rejected', legacy_tamper['rejected'], legacy_tamper)
port = NarrativeNormalization(parser_versions={'old-saved-document': '1.0.0'})
check('saved_old_pin_stays_1_0', port.identity(MIME, document_id='old-saved-document')['parser_version'] == '1.0.0')
check('current_identity_really_1_1', dn.normalization_identity(MIME)['parser_version'] == NarrativeNormalization().identity(MIME)['parser_version'] == '1.1.0')
check('old_minimal_original_still_unchanged_after_probes', digest(minimal_path.read_bytes()) == digest(minimal))
after_source = hashes()
check('all_source_and_config_sha_unchanged', before_source == after_source)
results = {
    'schema_version': 'independent-final-docx-heading-probe/1', 'observed_at': datetime.now(timezone.utc).isoformat(),
    'source_tree': str(TREE), 'source_before': before_source, 'source_after': after_source,
    'checks': checks, 'status': 'PASS' if all(c['status']=='PASS' for c in checks) else 'FAIL',
    'minimal_original': {'path': str(minimal_path), 'sha256': digest(minimal), 'bytes': len(minimal),
        'current_document': plain(current), 'old_document': plain(old_minimal), 'selected': plain(selected.evidence_spans), 'selected_replay_count': count},
    'own_original': {'path': str(own_path), 'sha256': digest(own), 'bytes': len(own),
        'document': plain(own_doc), 'selected': plain(own_selected.evidence_spans), 'selected_replay_count': own_count},
    'legacy_equality': {'independent_record': legacy_record, 'fingerprint': legacy_fp,
        'before_path': str(implementation/'before.json'), 'after_path': str(implementation/'after.json')},
    'operations': {'provider_calls':0, 'external_model_calls':0, 'new_fee':0, 'source_edits':0, 'production_config_edits':0,
        'writes_limited_to': str(OUT), 'input_old_original_reencoded':False},
}
(OUT/'probe-results.json').write_text(json.dumps(results, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print(json.dumps({'status': results['status'], 'checks': checks, 'source_unchanged': before_source == after_source,
    'own_original_sha256':digest(own)}, ensure_ascii=False, indent=2))
sys.exit(0 if results['status']=='PASS' else 1)
