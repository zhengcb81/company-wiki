"""Read-only observer of one existing source through the PDF/selector ports."""
from pathlib import Path
import dataclasses
import gzip
import hashlib
import json
import os
import sys
import time
from collections.abc import Mapping

def json_default(value):
    if isinstance(value, Mapping):
        return dict(value)
    if isinstance(value, (set, frozenset)):
        return sorted(value)
    raise TypeError(type(value).__name__)

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / 'src')]
os.environ.pop('COMPANY_WIKI_PDF_ENHANCEMENT_CONFIG', None)
from company_wiki.source_catalog.config import load_catalog_config
from company_wiki.source_catalog.service import SourceCatalog
from company_wiki.source_catalog.source_reader import SourceRef, SourceVersionReader
from company_wiki.source_catalog.narrative_pdf_reading import PdfReading, PdfReadingRequest
from company_wiki.source_catalog import narrative_reading as nr
from company_wiki.resource_budget import new_document_work_budget

base = ROOT / '.planning/c3-20261026'
out = base / 'native-selection-observation.json.gz'
assert not out.exists()
ref = SourceRef(**json.loads((base/'hk-ref.json').read_text(encoding='utf-8')))
sample = json.loads((base/'prepared-hk-development.json').read_text(encoding='utf-8'))['samples'][0]
meta = sample['source_metadata_observation']
catalog = SourceCatalog(load_catalog_config(ROOT/'config/source_catalog.yaml', project_root=ROOT))
protected = [ROOT/'config/source_catalog.yaml', ROOT/'config/resource_budget.yaml', catalog.config.database_path]
before = {str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}
calls = []
original = nr._admitted
def observe(unit, reading, kind, **kwargs):
    result = original(unit, reading, kind, **kwargs)
    if unit.coordinates.page_number in {11, 13}:
        calls.append({'unit_id':unit.unit_id, 'text':unit.raw_text, 'reading':dict(reading),
            'kind':kind, 'admitted':result[0], 'fact':dataclasses.asdict(result[1]),
            'required':list(kwargs.get('required_unit_ids', ()))})
    return result
nr._admitted = observe
started=time.monotonic()
try:
    data=SourceVersionReader(catalog).open_version(ref,purpose='narrative_derivation').data
    budget=new_document_work_budget()
    reader=PdfReading()
    parsed=reader.read(data,PdfReadingRequest(ref.source_id,ref.content_sha256,meta.get('language') or 'unknown',meta['title'],meta['document_kind']),selector_version='0.9.0',work_budget=budget,deadline=started+90)
    selected=nr.select_reading_evidence(parsed,title=meta['title'],existing_kind=meta['document_kind'],work_budget=budget)
    result={'schema':'c3-native-selection-observation/1','source_sha256':ref.content_sha256,
        'recipe':reader.describe_recipe(),'units':[{'unit_id':u.unit_id,'coordinates':dataclasses.asdict(u.coordinates),'text':u.raw_text,'kind':u.unit_kind,'metadata':dict(u.metadata)} for u in parsed.units if u.coordinates.page_number in {11,13}],
        'admission':calls,'selected_spans':[s.to_dict() for s in selected.evidence_spans],
        'reading_context':selected.reading_context,'work_used':budget.used,'work_limit':budget.max_work_units,
        'seconds':time.monotonic()-started,'model_calls':0,'source_copies':0}
    assert before=={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}
    result['production_unchanged']=True
    out.write_bytes(gzip.compress(json.dumps(result,ensure_ascii=False,default=json_default).encode('utf-8'),mtime=0))
    print(json.dumps({'output':str(out),'units':len(result['units']),'admissions':len(calls),'seconds':result['seconds'],'work':budget.used}))
finally:
    catalog.close()
