import json, hashlib, re, pathlib, datetime

HERE=pathlib.Path(__file__).resolve().parent
PLAN=HERE.parent.parent
EX=PLAN/'executions'/'CN-688012'
M=json.loads((EX/'manifest.json').read_text(encoding='utf-8'))
OUT=pathlib.Path(M['output_root'])
D=json.loads((OUT/'input.json').read_text(encoding='utf-8'))
def sha(p): return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def save(name,obj): (HERE/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8')
art=[]
for a in M['artifacts']:
 p=pathlib.Path(a['absolute_path']); b=p.read_bytes() if p.exists() else b''
 art.append({**a,'actual_sha256':hashlib.sha256(b).hexdigest(),'actual_bytes':len(b),'status':'PASS' if p.exists() and len(b)==a['bytes'] and hashlib.sha256(b).hexdigest()==a['sha256'] else 'FAIL'})
save('artifact_integrity.json',art)
events=[json.loads(l) for l in pathlib.Path(M['command_index']).read_text(encoding='utf-8').splitlines() if l.strip()]
save('execution_command_ledger_copy.json',events)
print('ARTIFACTS',len(art),'FAIL',sum(x['status']=='FAIL' for x in art))
print('LEDGER sample',json.dumps(events[:2],ensure_ascii=False))
for f in ['annual2025.pdf','half2026_current.pdf']:
 import fitz
 doc=fitz.open(OUT/f)
 pages=[{'page':i+1,'text':p.get_text()} for i,p in enumerate(doc)]
 save(f.replace('.pdf','_independent_pages.json'),pages)
 print('PDF',f,'PAGES',len(pages),'SHA',sha(OUT/f))
print('PARAMETERS')
for p in D['parameters']: print(json.dumps(p,ensure_ascii=False))
print('CLAIMS')
for c in D['evidence_claims']: print(json.dumps(c,ensure_ascii=False))
for key in ['historical_revenue','research_coverage','management_communication_coverage','management_targets','growth_driver_tree']:
 print(key,json.dumps(D[key],ensure_ascii=False,indent=2))
for f in ['semi_web_open_snapshot.json','roadshow_public_questions.json','roadshow_precollect_questions_page1.json']:
 q=json.loads((OUT/f).read_text(encoding='utf-8')); print('FORMAT',f,type(q).__name__,list(q)[:12] if isinstance(q,dict) else len(q)); print(json.dumps(q,ensure_ascii=False)[:2500])
