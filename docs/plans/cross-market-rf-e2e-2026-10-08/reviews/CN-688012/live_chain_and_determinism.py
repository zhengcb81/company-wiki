import json,pathlib,subprocess,sys,os,hashlib,urllib.request,urllib.parse,time,datetime
H=pathlib.Path(__file__).resolve().parent;P=H.parent.parent;E=P/'executions'/'CN-688012'
M=json.loads((E/'manifest.json').read_text(encoding='utf-8'));O=pathlib.Path(M['output_root']);D=json.loads((O/'input.json').read_text(encoding='utf-8'))
T=O.parent/'CN-688012-review';T.mkdir(exist_ok=True)
S=pathlib.Path('C:/Users/郑曾波/.agents/skills/revenue-forecast');C=pathlib.Path('C:/Users/郑曾波/Projects/company-wiki')
env=dict(os.environ,PYTHONUTF8='1',PYTHONIOENCODING='utf-8',PYTHONDONTWRITEBYTECODE='1',REVENUE_PUBLICATION_REGISTRY=str(T/'publications.jsonl'),CWP_AUDIT_PROCESS_DIR=str(H/'processes'))
env['PYTHONPATH']=str(P/'process_trace')+os.pathsep+env.get('PYTHONPATH','')
def sha(b):return hashlib.sha256(b).hexdigest()
def save(n,x): (H/n).write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf-8')
def run(args,cwd,stdin=None):
 q=subprocess.run(args,cwd=cwd,env=env,input=stdin,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=90)
 print('INVOKE',json.dumps(args,ensure_ascii=False),'RC',q.returncode)
 if q.returncode:print(q.stderr.decode());raise RuntimeError('subprocess failed')
 return q
chain=[]
for label,request_name in [('annual','annual2025.json'),('half','half2026_fetch.json')]:
 req=json.loads((E/'requests'/request_name).read_text(encoding='utf-8'));req['filing_intent']='reuse_only';req.pop('acquisition_limits',None)
 q=run([sys.executable,'-B',str(S/'scripts'/'source_preparation.py'),'--company-wiki-catalog-config',str(C/'config'/'source_catalog.yaml')],S,json.dumps(req).encode())
 p=json.loads(q.stdout);save(label+'_independent_rf_source_preparation.json',p)
 ref=p['company_wiki_trace']['source_ref']
 r=run([sys.executable,'-B','-m','company_wiki.source_catalog.source_reader_cli','--config',str(C/'config'/'source_catalog.yaml'),'--document-id',ref['document_id'],'--source-id',ref['source_id'],'--content-sha256',ref['content_sha256'],'--purpose','filing_reuse'],C)
 receipt=json.loads(r.stderr);assert sha(r.stdout)==ref['content_sha256'] and len(r.stdout)==ref['byte_size'];(T/(label+'.pdf')).write_bytes(r.stdout)
 save(label+'_independent_raw_receipt.json',receipt)
 chain.append({'label':label,'source_ref':ref,'original_raw_sha':sha(r.stdout),'size':len(r.stdout),'resolution_outcome':p['company_wiki_trace'].get('resolution_outcome'),'reuse_receipt':p.get('reuse_receipt'),'manifest':receipt['manifest']})
save('actual_independent_chain.json',chain)
(T/'input.json').write_bytes((O/'input.json').read_bytes())
q=run([sys.executable,'-B',str(S/'scripts'/'revenue_forecast.py'),str(T/'input.json'),'--output',str(T/'forecast.json'),'--markdown',str(T/'forecast.md')],T)
old=json.loads((O/'forecast.json').read_text(encoding='utf-8'));new=json.loads((T/'forecast.json').read_text(encoding='utf-8'))
diff=[k for k in old if old[k]!=new[k]];assert not diff,diff
assert (O/'forecast.md').read_bytes()==(T/'forecast.md').read_bytes()
save('independent_fresh_cli_reproduction.json',{'status':'PASS','whole_json_equal':True,'markdown_bytes_equal':True,'input_sha256':sha((T/'input.json').read_bytes()),'forecast_sha256':sha((T/'forecast.json').read_bytes()),'owned_temp':str(T),'registry_path':str(T/'publications.jsonl')})
# The endpoint/fields are a publicly observed SSE frontend interface; no private API or credentials.
url='https://roadshow.sseinfo.com/base-service/api/pub/v1/question_answer/answer_question_page'
body=urllib.parse.urlencode({'pageNo':1,'pageSize':200,'questionTypeList':[2,3,4],'activityId':40766,'askTypes':[1]},doseq=True).encode()
rq=urllib.request.Request(url,data=body,headers={'Content-Type':'application/x-www-form-urlencoded','User-Agent':'Mozilla/5.0','Referer':'https://roadshow.sseinfo.com/activityDetails/40766'})
with urllib.request.urlopen(rq,timeout=30) as response:
 b=response.read(1048577);assert len(b)<=1048576;status=response.status
j=json.loads(b);assert j['success'];rr=[x for ds in j['datas'] for x in ds['records']];sel=[x for x in rr if x.get('companyId')==145565 and x.get('guestCompanyName')=='中微公司' and '688012' in x.get('miniLogoPath','')]
oldsel=json.loads((H/'independent_ir_identity.json').read_text(encoding='utf-8'))['selected']
assert {x['id']:x['content'] for x in sel}=={x['id']:x['content'] for x in oldsel}
(T/'independent_sse_api.json').write_bytes(b)
save('live_official_ir_check.json',{'status':'PASS','url':url,'http_status':status,'bytes':len(b),'sha256':sha(b),'all_records':len(rr),'selected_exact_company':len(sel),'all_selected_reply_contents_equal':True,'credentials_used':False,'cost_usd':0,'raw_temp':str(T/'independent_sse_api.json'),'captured_at':datetime.datetime.now(datetime.timezone.utc).isoformat()})
print('LIVE CHAIN rawSHA / freshCLI allJSON / SSE live8answers PASS')
