"""Read one already-verified original; persist only bounded DOM evidence."""
from pathlib import Path
import hashlib,json,sys
root=Path(__file__).resolve().parents[2];sys.path.insert(0,str(root/'src'))
from company_wiki.source_catalog.config import load_catalog_config
from company_wiki.source_catalog.service import SourceCatalog
from company_wiki.source_catalog.source_reader import SourceRef,SourceVersionReader
from company_wiki.document_normalization import normalize_document
from bs4 import BeautifulSoup
sha='99d693f6c1544144ebeee92954f151a85bc62111837530a42855953bc01d0bbe'
cfg=load_catalog_config(root/'config/source_catalog.yaml',project_root=root)
protected=[root/'config/source_catalog.yaml',cfg.database_path]
before={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}
catalog=SourceCatalog(cfg)
try:
 ref=SourceRef(document_id='urn:company-wiki:document:sha256:'+sha,source_id='urn:company-wiki:source:sha256:'+sha,content_sha256=sha,byte_size=8158067,mime_type='text/html')
 raw=SourceVersionReader(catalog).open_version(ref,purpose='preview').data
 assert hashlib.sha256(raw).hexdigest()==sha and catalog._store is None
 normalized=normalize_document(raw,source_id=ref.source_id,source_sha256=sha,mime_type='text/html')
 tree=BeautifulSoup(raw,'html.parser')
 terms=['Intelligent Cloud','This segment primarily comprises:', 'Azure and other cloud services', 'consumption-based']
 units=[]
 for i,u in enumerate(normalized.units):
  if any(t in u.raw_text for t in terms) and len(units)<24:
   units.append({'ordinal':i,'unit_id':u.unit_id,'kind':u.unit_kind,'text':u.raw_text[:1800],'metadata':{k:u.metadata[k] for k in ('dom_path','heading_level','tag_name') if k in u.metadata}})
 excerpts=[]
 for t in terms:
  for found in tree.find_all(string=lambda s:isinstance(s,str) and t in s)[:4]:
   owner=found.parent
   while owner.parent and owner.name not in ('p','div','li'):owner=owner.parent
   parent=owner.parent
   excerpts.append({'needle':t,'owner_html':str(owner)[:2800],'parent_html':str(parent)[:9000]})
 result={'source_sha256':sha,'parse_units':len(normalized.units),'units':units,'dom_excerpts':excerpts,'protected_unchanged':all(hashlib.sha256(p.read_bytes()).hexdigest()==before[str(p)] for p in protected),'paid_calls':0,'downloads':0}
 out=root/'docs/plans/du11-source-closure-2026-10-18/review/cf-source-20261025';out.mkdir(parents=True,exist_ok=True)
 (out/'cf1-dom-source-observation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps({'units':units,'excerpt_count':len(excerpts),'protected_unchanged':result['protected_unchanged']},ensure_ascii=False)[:12000])
finally:
 catalog.close()
