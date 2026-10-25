"""Read-only native boundary observation, one source parse, one page image."""
from dataclasses import asdict
import hashlib
import importlib.metadata
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))
import pymupdf
from company_wiki.resource_budget import new_document_work_budget
from company_wiki.document_understanding.geometry_intent.reading import PdfReadingContext
from company_wiki.source_catalog import narrative_evidence as engine
from company_wiki.source_catalog.config import load_catalog_config
from company_wiki.source_catalog.service import SourceCatalog
from company_wiki.source_catalog.source_reader import SourceRef, SourceVersionReader

sha = '4f589193fae39fb53cb7d2121d93925b382bb052cfecbdc24e8e8271ea41bd36'
cfg = load_catalog_config(ROOT/'config/source_catalog.yaml', project_root=ROOT)
protected = [ROOT/'config/source_catalog.yaml', cfg.database_path, ROOT/'config/resource_budget.yaml']
before = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}
node = ROOT/'docs/plans/du11-source-closure-2026-10-18/review/cf-source-20261025'
output = node/'cf2-source-boundaries.json'
if output.exists():
    raise FileExistsError(output)
catalog = SourceCatalog(cfg)
try:
    ref = SourceRef(document_id='urn:company-wiki:document:sha256:'+sha,
        source_id='urn:company-wiki:source:sha256:'+sha, content_sha256=sha,
        byte_size=3396644, mime_type='application/pdf')
    raw = SourceVersionReader(catalog).open_version(ref, purpose='preview').data
    assert hashlib.sha256(raw).hexdigest() == sha and catalog._store is None
    budget = new_document_work_budget()
    parsed = engine.parse_pdf_bytes(raw, source_id=ref.source_id, source_sha256=sha,
        language='zh-hant', selector_version='0.9.0',
        reading_context=PdfReadingContext('2025 中期報告','semi_annual_report','zh-hant'),
        work_budget=budget)
    assert not budget.exhausted
    pages = (9, 11, 13, 50, 66)
    native = []
    with pymupdf.open(stream=raw, filetype='pdf') as doc:
        for number in pages:
            page = doc[number-1]
            blocks = []
            for b in page.get_text('dict', sort=False)['blocks']:
                if b.get('type') != 0:
                    continue
                lines = [{'bbox': line['bbox'], 'text': ''.join(s['text'] for s in line['spans'])}
                         for line in b.get('lines', [])]
                blocks.append({'bbox': b['bbox'], 'lines': lines})
            native.append({'page':number, 'size':list(page.rect), 'blocks':blocks})
        image = ROOT/'.planning/cf-source-20261025/cf2-p13.png'
        doc[12].get_pixmap(matrix=pymupdf.Matrix(1.3,1.3)).save(image)
    units = []
    for u in parsed.units:
        if u.coordinates.page_number not in pages:
            continue
        units.append({'unit_id':u.unit_id,'text':u.raw_text,'coordinates':asdict(u.coordinates),
            'page':u.coordinates.page_number,'kind':u.unit_kind,
            'source_role':u.source_role,'quality_flags':list(u.quality_flags),
            'parser_version':u.parser_version,
            'metadata':{k:u.metadata[k] for k in ('source_role','block_index','line_index','reading_layout','native_char_start','native_char_end') if k in u.metadata}})
    assert catalog._store is None
    stable = all(hashlib.sha256(p.read_bytes()).hexdigest()==before[str(p.relative_to(ROOT))] for p in protected)
    assert stable
    result = {'schema_version':'cf2-native-boundary-observation/1','source_ref':asdict(ref),
        'runtime':{'python':sys.version,'pymupdf':importlib.metadata.version('pymupdf')},
        'scope':'One parse; native page/block/line observations only, not content acceptance or model input',
        'parse_work':budget.used,'work_limit':budget.max_work_units,'unit_count':len(parsed.units),
        'native_pages':native,'parsed_units_on_observed_pages':units,
        'protected_sha256':before,'protected_unchanged':stable,'write_store_constructed':False,
        'calls':{'model':0,'api':0,'download':0,'raw_copy':0},
        'temporary_image':str(image.relative_to(ROOT)),'temporary_image_cleanup':'PENDING_VISUAL_INSPECTION'}
    output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'observed_pages':pages,'units':len(units),'parse_units':len(parsed.units),
                      'parse_work':budget.used,'output':str(output),'temporary_image':str(image)},ensure_ascii=False))
finally:
    catalog.close()
