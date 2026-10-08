import json, sys, hashlib, datetime as dt, os, collections
from pathlib import Path
HERE=Path(__file__).resolve().parent
EX=HERE.parents[1]/'executions/HK-00700'
def load(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(n,v): (HERE/n).write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
m=load(EX/'manifest.json'); OUT=Path(m['output_root'])
if sys.argv[1]=='inventory':
 i=load(OUT/'input.json'); f=load(OUT/'forecast.json')
 print('INPUT_KEYS',list(i)); print('FORECAST_KEYS',list(f))
 print('MANIFEST_END',json.dumps({k:v for k,v in m.items() if k not in ['runtime_file_sha256','sources','artifacts']},ensure_ascii=False))
 print('SOURCE_RECORDS',json.dumps(i['sources'],ensure_ascii=False))
 print('PARAMETERS',json.dumps(i['parameters'],ensure_ascii=False))
 print('CLAIMS',json.dumps(i.get('evidence_claims'),ensure_ascii=False))
 print('HISTORY',json.dumps(i.get('historical_revenue'),ensure_ascii=False))
 print('COVERAGE',json.dumps(i.get('research_coverage'),ensure_ascii=False))
 print('COMMUNICATION',json.dumps(i.get('management_communications'),ensure_ascii=False))
 print('TARGETS',json.dumps(i.get('management_targets'),ensure_ascii=False))
 print('SEGMENTS',json.dumps(i.get('segments'),ensure_ascii=False))
 print('DRIVERS',json.dumps(i.get('growth_driver_tree'),ensure_ascii=False))
elif sys.argv[1]=='ledger':
 records=[json.loads(q) for q in (EX/'commands/index.jsonl').read_text(encoding='utf-8').splitlines()]
 pairs=collections.defaultdict(list)
 for q in records:pairs[q['id']].append(q)
 audits=[]
 for key,qs in pairs.items():
  end=next((q for q in qs if q['event']=='finish'),{})
  files=[]
  for kind,v in end.get('outputs',{}).items():files.append(dict(kind=kind,hash_ok=sha(v['path'])==v['sha256'],bytes_ok=Path(v['path']).stat().st_size==v['byte_size']))
  audits.append(dict(id=key,pair=[q['event'] for q in qs],command=end.get('command'),cwd=end.get('cwd'),rc=end.get('returncode'),elapsed=end.get('elapsed_seconds'),outputs=files))
 traces={p.name:[json.loads(q) for q in p.read_text(encoding='utf-8').splitlines()] for p in (EX/'processes').glob('*.jsonl')}
 artifacts=[dict(path=q['absolute_path'],expected=q['sha256'],current=sha(q['absolute_path']),expected_bytes=q['bytes'],current_bytes=Path(q['absolute_path']).stat().st_size) for q in m['artifacts']]
 runtimes=[dict(file=k,expected=v,current=sha(Path(m['skill_root'])/k)) for k,v in m['runtime_file_sha256'].items()]
 save('ledger_audit.json',dict(commands=audits,traces=traces,artifacts=artifacts,runtime=runtimes,events=[json.loads(q) for q in (EX/'events.jsonl').read_text(encoding='utf-8').splitlines()]))
 print(json.dumps(dict(commands=len(audits),failures=[q for q in audits if q['rc']!=0],bad_pairs=[q for q in audits if q['pair']!=['start','finish']],bad_outputs=[q for q in audits if any(not v['hash_ok'] or not v['bytes_ok'] for v in q['outputs'])],runtime_drift=[q for q in runtimes if q['expected']!=q['current']],artifact_drift=[q for q in artifacts if q['expected']!=q['current']],all_commands=[dict(label=q['id'],command=q['command'],rc=q['rc']) for q in audits],trace_count=len(traces)),ensure_ascii=False))
elif sys.argv[1]=='extract':
 import fitz
 dest=Path(os.environ['TEMP'])/'cwp-rf-independent-review-20261008-HK-00700';dest.mkdir(exist_ok=True)
 originals=[]
 for y in [2024,2025]:originals.append((f'annual_{y}',EX.parents[4]/'companies/腾讯/raw/financial_reports/annual'/f'腾讯：{y}年年度报告.pdf'))
 for p in OUT.glob('*.pdf'):originals.append((p.stem,p))
 report=[]
 for name,p in originals:
  try:
   d=fitz.open(p);pages=[dict(page=k+1,text=q.get_text()) for k,q in enumerate(d)]
   save(name+'_review_pages.json',pages)
   report.append(dict(name=name,path=str(p),sha256=sha(p),bytes=p.stat().st_size,pages=len(d),page_texts=str(HERE/(name+'_review_pages.json'))))
  except Exception as e:report.append(dict(name=name,path=str(p),sha256=sha(p),bytes=p.stat().st_size,error=str(e)))
 save('independent_original_inventory.json',report);print(json.dumps(report,ensure_ascii=False))
elif sys.argv[1]=='refs':
 root=Path(m['skill_root'])/'references'
 for n in ['model-library.md','extended-models.md','input-schema.md','output-schema.md','backtesting.md','input-construction.md']:
  print('\nREFERENCE',n);print((root/n).read_text(encoding='utf-8'))
elif sys.argv[1]=='compact':
 i=load(OUT/'input.json'); f=load(OUT/'forecast.json')
 print('KEYS',list(i))
 for k in ['company','as_of_date','base_year','forecast_years','historical_revenue','research_coverage','management_communications','official_communications','management_targets','segments','growth_driver_tree','sensitivities','scenario_rationale','data_gaps']:
  print(k,json.dumps(i.get(k),ensure_ascii=False))
 print('SOURCES',json.dumps([{k:q.get(k) for k in ['source_id','title','url','published_date','source_type','snapshot_path']} for q in i['sources']],ensure_ascii=False))
 print('PARAMS',json.dumps([{k:q.get(k) for k in ['parameter_id','value','unit','period','scenario','kind','classification','source_ids','claim_ids','rationale','range']} for q in i['parameters']],ensure_ascii=False))
 print('CLAIMS',json.dumps([{k:q.get(k) for k in ['claim_id','source_id','target','locator','excerpt','extracted_value','extracted_unit','extracted_period']} for q in i['evidence_claims']],ensure_ascii=False))
 print('FORECAST_SENSITIVITY',json.dumps(f['sensitivities'],ensure_ascii=False))
 print('CONFIDENCE',json.dumps(f.get('confidence'),ensure_ascii=False))
elif sys.argv[1]=='claims':
 import re
 i=load(OUT/'input.json')
 names={m['sources'][0]['source_id']:'annual_2025',m['sources'][1]['source_id']:'annual_2024','tencent_h1_2026_official':'interim_2026_official','tencent_corporate_overview_sep2026':'corporate_overview_20260916','tencent_results_2q2026':'results_2q2026'}
 params={q['parameter_id']:q for q in i['parameters']}; audits=[]
 normal=lambda s:' '.join(s.split())
 for q in i['evidence_claims']:
  pages=load(HERE/(names[q['source_id']]+'_review_pages.json'))
  hits=[p['page'] for p in pages if normal(q['excerpt']) in normal(p['text'])]
  p=params.get(q['target_id'],{})
  audits.append(dict(claim_id=q['claim_id'],target_type=q['target_type'],target_id=q['target_id'],support_type=q['support_type'],source_id=q['source_id'],locator=q['locator'],matched_pdf_pages=hits,extracted_value=q.get('extracted_value'),period=q.get('period'),unit=q.get('unit'),parameter_value=p.get('value'),parameter_type=p.get('parameter_type'),parameter_kind=p.get('kind'),parameter_period=p.get('period'),parameter_unit=p.get('unit'),parameter_range=p.get('range'),parameter_rationale=p.get('rationale'),excerpt=q['excerpt'],excerpt_hash_ok=hashlib.sha256(q['excerpt'].encode()).hexdigest()==q['excerpt_sha256']))
 save('all_claims_independent_excerpt_matches.json',audits)
 for q in audits:print(json.dumps(q,ensure_ascii=False))
 print('PARAMS',json.dumps(i['parameters'][:7],ensure_ascii=False))
