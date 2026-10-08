import json, hashlib, re, collections
from pathlib import Path
import fitz
H=Path(__file__).resolve().parent;P=H.parent.parent;E=P/'executions'/'CN-688012'
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def save(n,x):(H/n).write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf-8')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def norm(x):return re.sub(r'\s+','',x)
M=read(E/'manifest_v3.json');O=Path(M['output_root']);D=read(O/'input.json');V2=read(O.parent/'input.json')
intg=[]
for a in M['artifacts']:
 p=Path(a['absolute_path']);intg.append(dict(path=str(p),status='PASS' if p.stat().st_size==a['bytes'] and sha(p)==a['sha256'] else 'FAIL'))
save('v3_artifact_integrity.json',intg)
protect=[]
for a in read(E/'repair_v3.json')['old_v2_protected']:
 p=Path(a['path']);protect.append(dict(a,status='PASS' if p.stat().st_size==a['bytes'] and sha(p)==a['sha256'] else 'FAIL'))
save('v3_v2_protection.json',protect)
triage=read(E/'announcement_triage_v3.json');ap=[];full=[]
for t in triage:
 if not t['body_path']:continue
 doc=fitz.open(t['body_path']);rows=[{'page':i+1,'text':p.get_text()} for i,p in enumerate(doc)]
 ap.append(dict(announcement_id=t['announcement_id'],pages=rows,raw_sha256=sha(t['body_path']),issuer_role=t['issuer_role']))
 full.append('\n===== '+t['announcement_id']+' '+t['title']+' '+t['issuer_role']+' =====\n'+'\n'.join('[PAGE '+str(p['page'])+']\n'+p['text'] for p in rows))
save('v3_announcement_independent_pages.json',ap)
(H/'v3_announcement_independent_full.txt').write_text('\n'.join(full),encoding='utf-8')
pages={D['sources'][0]['source_id']:read(H/'annual2025_independent_pages.json'),D['sources'][1]['source_id']:read(H/'half2026_current_independent_pages.json')}
for a in ap:
 pages['amec_cninfo_'+a['announcement_id']]=a['pages']
IR={x['id']:x['content'] for x in read(H/'independent_ir_identity.json')['selected']}
semi=(O.parent/'semi_web_open_snapshot.json').read_text(encoding='utf-8')
old={c['claim_id']:c for c in V2['evidence_claims']};facts=[];groups=collections.defaultdict(list)
for c in D['evidence_claims']:
 loc=c['locator'];sid=c['source_id']
 if sid in pages:
  match=re.search(r'(?:pages?|PDF\s*p|\bp)\s*(\d+)',loc,re.I);assert match,(c['claim_id'],loc)
  n=int(match.group(1));context=pages[sid][n-1]['text']
  if 'pages176' in loc:context+='\n'+pages[sid][176]['text']
 elif sid=='amec_sse_results_qa_20260910':context=IR[int(re.search(r'id\s*(\d+)',loc).group(1))]
 elif sid=='semi_wfe_20260714':context=semi
 else:raise RuntimeError(sid)
 changed=old.get(c['claim_id'])!=c
 facts.append(dict(claim_id=c['claim_id'],target_type=c['target_type'],target_id=c['target_id'],support_type=c['support_type'],
  locator=loc,source_id=sid,extracted_value=c.get('extracted_value'),unit=c.get('unit'),period=c.get('period'),
  status='PASS' if norm(c['excerpt']) in norm(context) else 'FAIL',excerpt=c['excerpt'],independent_context_sha256=hashlib.sha256(context.encode()).hexdigest(),
  original_content_sha256=c['content_sha256'],changed_or_new=changed,semantic_support='pending_independent_read'))
 if changed:groups[(sid,loc,c['excerpt'])].append(c['claim_id'])
save('v3_all_106_claim_independent_match.json',facts)
lines=[]
for (sid,loc,ex),ids in groups.items():
 lines += ['\n==== '+','.join(ids)+'\n'+sid+' / '+loc+' ====\n'+ex]
(H/'v3_changed_claim_contexts.txt').write_text('\n'.join(lines),encoding='utf-8')
save('v3_parameter_change_matrix.json',[dict(parameter_id=p['parameter_id'],numeric_unchanged=p['value']==next(q['value'] for q in V2['parameters'] if q['parameter_id']==p['parameter_id']),
 kind=p['kind'],value=p['value'],definition=p['definition'],rationale=p['rationale'],claim_ids=p['claim_ids']) for p in D['parameters']])
print(json.dumps({'artifacts':len(intg),'artifact_fail':sum(a['status']=='FAIL' for a in intg),'protected':protect,'claims':len(facts),'claim_match_fail':[f['claim_id'] for f in facts if f['status']=='FAIL'],
 'changed_claims':sum(f['changed_or_new'] for f in facts),'changed_unique_contexts':len(groups),'pdf_documents':len(ap),'pdf_pages':sum(len(a['pages']) for a in ap),
 'full_pdf_chars':sum(len(s) for s in full),'changed_context_chars':sum(len(s) for s in lines)},ensure_ascii=False))
