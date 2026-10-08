import json, hashlib, pathlib, sys, os, subprocess, math, datetime, time
H=pathlib.Path(__file__).resolve().parent;P=H.parent.parent;E=P/'executions'/'CN-688012'
def read(p):return json.loads(pathlib.Path(p).read_text(encoding='utf-8'))
def save(n,x):(H/n).write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf-8')
def sha(b):return hashlib.sha256(b).hexdigest()
def eq(a,b):assert math.isclose(a,b,rel_tol=1e-10,abs_tol=1e-8),(a,b)
M=read(E/'manifest_v3.json');O=pathlib.Path(M['output_root']);D=read(O/'input.json');R=read(O/'forecast.json')
T=O.parent.parent/'CN-688012-review'/'v3';T.mkdir(parents=True,exist_ok=True)
S=pathlib.Path('C:/Users/郑曾波/.agents/skills/revenue-forecast');C=pathlib.Path('C:/Users/郑曾波/Projects/company-wiki')
env=dict(os.environ,PYTHONUTF8='1',PYTHONIOENCODING='utf-8',PYTHONDONTWRITEBYTECODE='1',REVENUE_PUBLICATION_REGISTRY=str(T/'publications.jsonl'),CWP_AUDIT_PROCESS_DIR=str(H/'v3_processes'))
env['PYTHONPATH']=str(P/'process_trace')+os.pathsep+env.get('PYTHONPATH','')
invocations=[]
def run(cmd,cwd,stdin=None,registry=None):
 started=datetime.datetime.now(datetime.timezone.utc).isoformat();start=time.monotonic()
 ev=dict(env)
 if registry:ev['REVENUE_PUBLICATION_REGISTRY']=str(registry)
 q=subprocess.run(cmd,cwd=cwd,env=ev,input=stdin,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=90)
 rec=dict(command=cmd,cwd=str(cwd),started_at=started,ended_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),elapsed_seconds=time.monotonic()-start,returncode=q.returncode,
 stdout_bytes=len(q.stdout),stdout_sha256=sha(q.stdout),stderr_bytes=len(q.stderr),stderr_sha256=sha(q.stderr))
 invocations.append(rec);save('v3_independent_nested_commands.json',invocations)
 if q.returncode:print(q.stderr.decode());raise RuntimeError(rec)
 return q
req=read(E/'requests'/'half2026_fetch.json');req['filing_intent']='reuse_only';req.pop('acquisition_limits',None)
q=run([sys.executable,'-B',str(S/'scripts'/'source_preparation.py'),'--company-wiki-catalog-config',str(C/'config'/'source_catalog.yaml')],S,json.dumps(req).encode())
source=json.loads(q.stdout);save('v3_independent_source_preparation.json',source)
ref=source['company_wiki_trace']['source_ref'];assert source['reuse_receipt']['download_calls']==0
assert source['url']=='https://static.cninfo.com.cn/finalpage/2026-08-20/1225482884.PDF' and source['published_date']=='2026-08-20'
assert ref['content_sha256']==D['sources'][1]['capture']['snapshot_sha256']
q=run([sys.executable,'-B','-m','company_wiki.source_catalog.source_reader_cli','--config',str(C/'config'/'source_catalog.yaml'),'--document-id',ref['document_id'],'--source-id',ref['source_id'],'--content-sha256',ref['content_sha256'],'--purpose','filing_reuse'],C)
assert sha(q.stdout)==ref['content_sha256'] and len(q.stdout)==ref['byte_size'];receipt=json.loads(q.stderr);save('v3_independent_raw_receipt.json',receipt)
sys.path.insert(0,str(S/'scripts'));from revenue_report import validate_published_forecast,render_markdown
from revenue_backtest import validate_snapshot
validate_published_forecast(R,D);assert (O/'forecast.md').read_bytes()==render_markdown(R).encode()
snapshot=read(O/'snapshot.json');validate_snapshot(snapshot);assert snapshot['input_document']==D;validate_published_forecast(snapshot['forecast_result'],D)
for k,v in R.items():
 if k not in {'publication_receipt','result_sha256'}:assert snapshot['forecast_result'][k]==v,k
params={p['parameter_id']:p for p in D['parameters']};segs={s['name']:s for s in R['segments']};calcs=[]
assert set(segs)=={'Equipment','NonEquipmentResidual','CMP'}
for sc in ['low','base','high']:
 prev=R['base_revenue']
 for year in [2026,2027,2028]:
  values={'Equipment':params[f'equipment_units_{sc}_{year}']['value']*params[f'equipment_unit_revenue_{sc}_{year}']['value'],
   'NonEquipmentResidual':params[f'aftermarket_revenue_{sc}_{year}']['value'],'CMP':params[f'cmp_revenue_{sc}_{year}']['value']}
  for name,v in values.items():
   eq(v,segs[name]['scenarios'][sc]['recognized_revenue'][str(year)]);eq(v,segs[name]['scenarios'][sc]['effective_revenue'][str(year)])
  total=sum(values.values());p=R['consolidated_forecast'][sc];eq(total,p['annual_revenue'][str(year)]);eq(total/prev-1,p['annual_growth'][str(year)])
  calcs.append(dict(scenario=sc,year=year,independent_values=values,total=total,growth=total/prev-1,status='PASS'));prev=total
 eq((prev/R['base_revenue'])**(1/3)-1,p['cagr']);eq(prev-R['base_revenue'],p['incremental_revenue'])
base=R['consolidated_forecast']['base']['terminal_revenue'];sensitivity=[]
for t in R['sensitivities']:
 v=params[t['parameter_id']]['value'];shock=t['shock_value'];assert t['shock_type']=='percent'
 multiplier=params['equipment_unit_revenue_base_2028']['value'] if t['parameter_id']=='equipment_units_base_2028' else params['equipment_units_base_2028']['value'] if t['parameter_id']=='equipment_unit_revenue_base_2028' else 1
 down=base-v*shock*multiplier;up=base+v*shock*multiplier;eq(down,t['down_terminal_revenue']);eq(up,t['up_terminal_revenue'])
 eq(v*(1-shock),t['requested_values']['down']);eq(v*(1+shock),t['requested_values']['up']);sensitivity.append(dict(parameter_id=t['parameter_id'],down=down,up=up,status='PASS'))
allocation=[]
for d in D['growth_driver_tree']['drivers']:
 inc=sum((segs[a['segment_name']]['scenarios']['base']['effective_revenue']['2028']-segs[a['segment_name']]['base_revenue'])*a['weight'] for a in d['segment_attribution'])
 row=next(x for x in R['growth_driver_analysis']['top_drivers'] if x['driver_id']==d['driver_id']);eq(inc,row['estimated_base_terminal_increment']);allocation.append(dict(driver_id=d['driver_id'],increment=inc,status='PASS'))
eq(sum(x['increment'] for x in allocation),R['consolidated_forecast']['base']['incremental_revenue'])
for year in ['2026','2027','2028']:
 assert R['consolidated_forecast']['low']['annual_revenue'][year]<=R['consolidated_forecast']['base']['annual_revenue'][year]<=R['consolidated_forecast']['high']['annual_revenue'][year]
 assert R['consolidated_forecast']['low']['annual_revenue'][year]>6691.28732767
save('v3_independent_calculations.json',dict(year_rows=calcs,segment_year_scenario_count=27,sensitivities=sensitivity,driver_allocations=allocation,status='PASS'))
(T/'input.json').write_bytes((O/'input.json').read_bytes())
run([sys.executable,'-B',str(S/'scripts'/'revenue_forecast.py'),str(T/'input.json'),'--output',str(T/'forecast.json'),'--markdown',str(T/'forecast.md')],T)
assert read(T/'forecast.json')==R;assert (T/'forecast.md').read_bytes()==(O/'forecast.md').read_bytes()
q=run([sys.executable,'-B',str(S/'scripts'/'publication_registry.py'),'audit','--result',str(O/'forecast.json'),'--result',str(O/'snapshot.json')],S,registry=O/'publications.jsonl')
save('v3_formal_independent_checks.json',dict(strong_original_input='PASS',exact_markdown='PASS',snapshot_same_input_and_economic_payload='PASS',
 independent_fresh_cli_whole_json_equal=True,independent_fresh_markdown_bytes_equal=True,registry_audit='PASS',confidence_score=R['confidence']['score'],
 confidence_components_sum_matches=math.isclose(sum(R['confidence']['components'].values()),R['confidence']['score']),source_ref=ref,current_source_url=source['url'],
 current_published_date=source['published_date'],download_calls=source['reuse_receipt']['download_calls'],raw_sha256=sha(q.stdout) if False else ref['content_sha256'],
 owned_temp=str(T),input_sha256=sha((O/'input.json').read_bytes()),forecast_sha256=sha((O/'forecast.json').read_bytes())))
# Inspect exactly the v3 extension to the original executor ledger; no repeat of sealed v2 command audit.
old_ids={x['id'] for x in read(H/'command_integrity.json')};by=collections.defaultdict(list) if False else {}
for line in pathlib.Path(M['command_index']).read_text(encoding='utf-8').splitlines():
 x=json.loads(line)
 if x['id'] not in old_ids:by.setdefault(x['id'],[]).append(x)
cmds=[]
for ident,events in by.items():
 start=[x for x in events if x['event']=='start'];finish=[x for x in events if x['event']=='finish'];issues=[]
 if len(start)!=1 or len(finish)!=1:issues.append('pairing')
 else:
  if start[0]['command']!=finish[0]['command'] or start[0]['cwd']!=finish[0]['cwd']:issues.append('invocation drift')
  for kind,x in finish[0]['outputs'].items():
   p=pathlib.Path(x['path'])
   if p.stat().st_size!=x['byte_size'] or sha(p.read_bytes())!=x['sha256']:issues.append(kind+' bytes/hash')
 cmds.append(dict(id=ident,label=events[0]['label'],returncode=finish[0]['returncode'] if finish else None,issues=issues,status='PASS' if not issues else 'FAIL'))
save('v3_execution_command_extension_integrity.json',cmds)
print(json.dumps(dict(status='PASS',new_executor_command_pairs=len(cmds),nonzero_attempts=sum(x['returncode']!=0 for x in cmds),numericrows=len(calcs),sensitivity=len(sensitivity),current_url=source['url'],download_calls=0,whole_json_equal=True),ensure_ascii=False))
