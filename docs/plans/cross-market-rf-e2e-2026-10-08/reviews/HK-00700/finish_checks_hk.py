import json, sys, os, hashlib, datetime as dt, re, subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent
EX=HERE.parents[1]/'executions/HK-00700'
ROOT=EX.parents[4]
m=json.loads((EX/'manifest.json').read_text(encoding='utf-8'))
OUT=Path(m['output_root'])
TMP=OUT.parent/'review-HK-00700-rf_hk_independent_review'
TMP.mkdir(exist_ok=True)
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(n,v): (HERE/n).write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
if sys.argv[1]=='annual-discovery':
 import requests
 from bs4 import BeautifulSoup
 from urllib.parse import urljoin
 receipts=[]
 url=sys.argv[2] if len(sys.argv)>2 else 'https://www.tencent.com/investors/financial-reports/'
 response=requests.get(url,timeout=(20,60))
 html=response.content
 suffix='-zhhk' if '/zh-hk/' in url else ''
 (TMP/('official-financial-reports'+suffix+'.html')).write_bytes(html)
 soup=BeautifulSoup(html,'html.parser')
 links=[dict(text=a.get_text(' ',strip=True),url=urljoin(response.url,a['href']),parent_context=a.parent.get_text(' ',strip=True)[:1500]) for a in soup.select('a[href]')]
 receipts.append(dict(action='official_index',requested_url=url,final_url=response.url,status=response.status_code,accessed_at=dt.datetime.now(dt.timezone.utc).isoformat(),bytes=len(html),sha256=hashlib.sha256(html).hexdigest(),content_type=response.headers.get('Content-Type'),links=links))
 save('annual_2025_official_url_discovery'+suffix+'.json',receipts)
 print(json.dumps(receipts,ensure_ascii=False))
elif sys.argv[1]=='annual-download':
 import requests
 records=[]
 for p in HERE.glob('annual_2025_official_url_discovery*.json'):records.extend(json.loads(p.read_text(encoding='utf-8')))
 url=sys.argv[2]
 assert any(q['url']==url for rec in records for q in rec['links']), 'URL not found in original official archive'
 response=requests.get(url,stream=True,timeout=(20,60));data=bytearray()
 for part in response.iter_content(65536):
  data.extend(part)
  assert len(data)<=41943040, '40MiB bound exceeded'
 p=TMP/'official-archive-annual-2025.pdf';p.write_bytes(data)
 match=[q for rec in records for q in rec['links'] if q['url']==url]
 rec=dict(action='official_pdf_readonly_capture',requested_url=url,final_url=response.url,status=response.status_code,accessed_at=dt.datetime.now(dt.timezone.utc).isoformat(),bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),content_type=response.headers.get('Content-Type'),file=str(p),archive_link=match,existing_source_sha256=m['sources'][0]['sha256'] if 'sha256' in m['sources'][0] else None)
 rec['same_bytes_as_registered_raw']=rec['sha256']==sha(ROOT/'companies/腾讯/raw/financial_reports/annual/腾讯：2025年年度报告.pdf')
 save('annual_2025_official_capture.json',rec);print(json.dumps(rec,ensure_ascii=False))
elif sys.argv[1]=='mupdf-visual':
 import fitz
 records=json.loads((HERE/'pypdf_context_and_poppler_render_receipts.json').read_text(encoding='utf-8'))
 new=[]
 for q in records:
  doc=fitz.open(q['source']);page=doc[q['page']-1];dest=TMP/(q['document']+'-page-'+str(q['page'])+'-mupdf.png')
  page.get_pixmap(matrix=fitz.Matrix(1.7,1.7)).save(dest)
  new.append(dict(document=q['document'],page=q['page'],source=q['source'],source_sha256=sha(q['source']),render_path=str(dest),render_sha256=sha(dest),renderer='PyMuPDF '+fitz.VersionBind,reason='Independent alternate rendering to inspect Chinese table headers and missing Poppler body glyphs'))
 save('mupdf_visual_receipts.json',new);print(json.dumps(new,ensure_ascii=False))
elif sys.argv[1]=='protected':
 before=json.loads((EX/'before.json').read_text(encoding='utf-8'))
 after=json.loads((EX/'after_protected_and_runtime.json').read_text(encoding='utf-8'))
 audits=[]
 for q in before['protected']:
  current=sha(q['path']);audits.append(dict(path=q['path'],before_sha256=q['sha256'],current_sha256=current,current_bytes=Path(q['path']).stat().st_size,same=current==q['sha256'],runtime_file='revenue-forecast' in q['path'] and ('scripts' in q['path'] or q['path'].endswith('SKILL.md'))))
 save('protected_review_inputs.json',dict(before=before,after=after,current=audits))
 print(json.dumps(dict(all=len(audits),changed=[q for q in audits if not q['same']],raw_and_config_unchanged=all(q['same'] for q in audits if not q['runtime_file'])),ensure_ascii=False))
elif sys.argv[1]=='sourcefacts-readonly':
 for n in ['db_readonly_documents.json','source_facts_2024.request.json','source_facts_2024.response.json','source_facts_2025.request.json','source_facts_2025.response.json','source_facts_receipts.json','deterministic_local_parse.json','delivery_verification.json']:
  print(n,(EX/n).read_text(encoding='utf-8'))
elif sys.argv[1]=='registry-verify':
 os.environ['REVENUE_PUBLICATION_REGISTRY']=str(OUT/'publications.jsonl')
 sys.path.insert(0,str(Path(m['skill_root'])/'scripts'))
 import publication_registry as reg
 from contracts.evidence import canonical_sha256
 entries=reg._read_entries()
 f=json.loads((OUT/'forecast.json').read_text(encoding='utf-8'));s=json.loads((OUT/'snapshot-v2.json').read_text(encoding='utf-8'))
 assert any(q['artifact_type']=='forecast' and q['input_sha256']==f['input_sha256'] and q['result_sha256']==f['result_sha256'] for q in entries)
 assert any(q['artifact_type']=='snapshot' and q['input_sha256']==s['input_sha256'] and q['artifact_id']==s['snapshot_id'] and q['result_sha256']==s['forecast_result_sha256'] for q in entries)
 c=[sys.executable,'-B',str(Path(m['skill_root'])/'scripts/publication_registry.py'),'audit','--result',str(OUT/'forecast.json')]
 r=subprocess.run(c,capture_output=True,text=True,encoding='utf-8')
 record=dict(entries=entries,original_registry_sha256=sha(OUT/'publications.jsonl'),registry_runtime_sha256=sha(Path(m['skill_root'])/'scripts/publication_registry.py'),all_chain_hashes='PASS',matching_forecast_snapshot_registration='PASS',audit_command=c,audit_exit=r.returncode,audit_stdout=r.stdout,audit_stderr=r.stderr,artifact_input_anchor=f['input_sha256'],matching_anchor_entries=reg.lookup(f['input_sha256']))
 suffix='-after-main-fix' if len(sys.argv)>2 else ''
 save('independent_registry_audit'+suffix+'.json',record);print(json.dumps(record,ensure_ascii=False))
elif sys.argv[1]=='output-shapes':
 f=json.loads((OUT/'forecast.json').read_text(encoding='utf-8'))
 print('KEYS',list(f));print('CONSOLIDATED',json.dumps(f['consolidated_forecast'],ensure_ascii=False));print('DRIVERS',json.dumps(f.get('growth_driver_analysis'),ensure_ascii=False));print('SEGMENT',json.dumps(f['segments'][0],ensure_ascii=False))
elif sys.argv[1]=='compact':
 i=json.loads((OUT/'input.json').read_text(encoding='utf-8'));f=json.loads((OUT/'forecast.json').read_text(encoding='utf-8'))
 for k in ['management_targets','research_coverage','management_communication_coverage','growth_driver_tree','data_gaps','model_quality','company_name','historical_revenue']:
  print(k,json.dumps(i.get(k),ensure_ascii=False))
 print('SEGMENTS',json.dumps(i['segments'],ensure_ascii=False))
 print('OUTPUTCONF',json.dumps(f.get('confidence'),ensure_ascii=False))
 print('OUTPUT_KEYS',json.dumps(list(f),ensure_ascii=False))
