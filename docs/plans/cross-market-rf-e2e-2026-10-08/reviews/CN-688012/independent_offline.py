import json,hashlib,pathlib,sys,re,math,datetime,collections,os,subprocess
HERE=pathlib.Path(__file__).resolve().parent;PLAN=HERE.parent.parent;EX=PLAN/'executions'/'CN-688012'
M=json.loads((EX/'manifest.json').read_text(encoding='utf-8'));OUT=pathlib.Path(M['output_root'])
D=json.loads((OUT/'input.json').read_text(encoding='utf-8'));R=json.loads((OUT/'forecast.json').read_text(encoding='utf-8'))
def read(p):return json.loads(pathlib.Path(p).read_text(encoding='utf-8'))
def save(n,o): (HERE/n).write_text(json.dumps(o,ensure_ascii=False,indent=2),encoding='utf-8')
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def norm(s):return re.sub(r'\s+','',s)
def eq(a,b): assert math.isclose(a,b,rel_tol=1e-10,abs_tol=1e-8),(a,b)
pages={D['sources'][0]['source_id']:read(HERE/'annual2025_independent_pages.json'),D['sources'][1]['source_id']:read(HERE/'half2026_current_independent_pages.json')}
raw=read(OUT/'roadshow_public_questions.json');records=[x for ds in raw['datas'] for x in ds['records']]
amec=[x for x in records if x.get('guestCompanyName')=='中微公司' and x.get('companyId')==145565 and '688012' in x.get('miniLogoPath','')]
pre=[]
for n in range(1,11):pre += read(OUT/f'roadshow_precollect_questions_page{n}.json')['datas'][0]['records']
pre_amec=[x for x in pre if x.get('companyId')==145565 and x.get('stockCode')=='688012']
save('independent_ir_identity.json',{'total_interactive':len(records),'selected':amec,'excluded':len(records)-len(amec),'total_precollected':len(pre),'selected_precollected':pre_amec,'unique_precollected_ids':len(set(x['id'] for x in pre))})
print('IR all195 / exactAMEC8',len(records),len(amec),'PRE',len(pre),len(pre_amec))
for x in amec:print('IR',x['id'],x['guestName'],x['crtTime'],x['content'])
for x in pre_amec:print('PRE',x['id'],x['question'],x.get('answer'))
semi=(OUT/'semi_web_open_snapshot.json').read_text(encoding='utf-8')
facts=[]
for c in D['evidence_claims']:
 src=c['source_id'];actual='';loc=c['locator'];page=None
 if src in pages:
  page=int(re.search(r'pages?\s*(\d+)',loc,re.I).group(1));actual=pages[src][page-1]['text']
  if 'pages176' in loc:actual+='\n'+pages[src][176]['text']
 elif src=='amec_sse_results_qa_20260910':
  rid=int(re.search(r'id\s*(\d+)',loc).group(1));actual=next(x['content'] for x in amec if x['id']==rid)
 elif src=='semi_wfe_20260714':actual=semi
 hit=norm(c['excerpt']) in norm(actual)
 facts.append({'claim_or_parameter_id':c['claim_id'],'target_type':c['target_type'],'target_id':c['target_id'],'support_type':c['support_type'],'source_locator':loc,'independent_value':c.get('extracted_value'),'unit':c.get('unit'),'period':c.get('period'),'excerpt_found_in_independent_original':hit,'status':'PASS' if hit else 'FAIL','original_context_sha256':hashlib.sha256(actual.encode()).hexdigest(),'evidence':str(HERE/('annual2025_independent_pages.json' if src==D['sources'][0]['source_id'] else 'half2026_current_independent_pages.json')) if src in pages else str(OUT/('roadshow_public_questions.json' if src=='amec_sse_results_qa_20260910' else 'semi_web_open_snapshot.json'))})
save('all_claim_original_match.json',facts);print('CLAIM MATCH',len(facts),sum(x['status']=='FAIL' for x in facts));print([x for x in facts if x['status']=='FAIL'])
ledger=[json.loads(l) for l in pathlib.Path(M['command_index']).read_text(encoding='utf-8').splitlines() if l]
by=collections.defaultdict(list)
for e in ledger:by[e['id']].append(e)
aud=[]
for id,es in by.items():
 issues=[];a=[e for e in es if e['event']=='start'];b=[e for e in es if e['event']=='finish']
 if len(a)!=1 or len(b)!=1:issues.append('start-finish pairing')
 else:
  if a[0]['command']!=b[0]['command'] or a[0]['cwd']!=b[0]['cwd']:issues.append('invocation drift')
  for typ,item in b[0]['outputs'].items():
   p=pathlib.Path(item['path'])
   if not p.exists() or p.stat().st_size!=item['byte_size'] or sha(p)!=item['sha256']:issues.append(typ+' bytes/hash')
 aud.append({'id':id,'label':es[0]['label'],'returncode':b[0]['returncode'] if b else None,'issues':issues,'status':'PASS' if not issues else 'FAIL'})
save('command_integrity.json',aud);print('COMMANDS',len(aud),'FAIL',sum(bool(x['issues']) for x in aud),'nonzero',sum(x['returncode']!=0 for x in aud))
params={p['parameter_id']:p for p in D['parameters']};segs={s['name']:s for s in R['segments']};calcs=[]
for sc in ['low','base','high']:
 prev=R['base_revenue']
 for y in [2026,2027,2028]:
  vals={'Equipment':params[f'equipment_units_{sc}_{y}']['value']*params[f'equipment_unit_revenue_{sc}_{y}']['value'],'Aftermarket':params[f'aftermarket_revenue_{sc}_{y}']['value'],'CMP':params[f'cmp_revenue_{sc}_{y}']['value']}
  for n,v in vals.items():
   eq(v,segs[n]['scenarios'][sc]['recognized_revenue'][str(y)]);eq(v,segs[n]['scenarios'][sc]['effective_revenue'][str(y)])
  total=sum(vals.values());path=R['consolidated_forecast'][sc];eq(total,path['annual_revenue'][str(y)]);eq(total/prev-1,path['annual_growth'][str(y)])
  calcs.append({'scenario':sc,'year':y,'segments':vals,'total':total,'annual_growth':total/prev-1,'status':'PASS'});prev=total
 eq((prev/R['base_revenue'])**(1/3)-1,path['cagr']);eq(prev-R['base_revenue'],path['incremental_revenue'])
sens=[];base=R['consolidated_forecast']['base']['terminal_revenue']
for t in R['sensitivities']:
 v=params[t['parameter_id']]['value'];shock=t['shock_value'];assert t['shock_type']=='percent'
 multiplier=params['equipment_unit_revenue_base_2028']['value'] if t['parameter_id']=='equipment_units_base_2028' else params['equipment_units_base_2028']['value'] if t['parameter_id']=='equipment_unit_revenue_base_2028' else 1
 down=base-v*shock*multiplier;up=base+v*shock*multiplier
 eq(down,t['down_terminal_revenue']);eq(up,t['up_terminal_revenue']);eq(v*(1-shock),t['requested_values']['down']);eq(v*(1+shock),t['requested_values']['up'])
 sens.append({'parameter_id':t['parameter_id'],'down':down,'up':up,'status':'PASS'})
drv=[]
for d in D['growth_driver_tree']['drivers']:
 inc=sum((segs[a['segment_name']]['scenarios']['base']['effective_revenue']['2028']-segs[a['segment_name']]['base_revenue'])*a['weight'] for a in d['segment_attribution'])
 out=next(x for x in R['growth_driver_analysis']['top_drivers'] if x['driver_id']==d['driver_id']);eq(inc,out['estimated_base_terminal_increment']);drv.append({'driver_id':d['driver_id'],'increment':inc,'status':'PASS'})
eq(sum(x['increment'] for x in drv),R['consolidated_forecast']['base']['incremental_revenue'])
save('independent_calculations.json',{'year_rows':calcs,'segment_year_scenario_count':27,'sensitivity_tests':sens,'driver_allocations':drv,'all_status':'PASS'})
sys.path.insert(0,'C:/Users/郑曾波/.agents/skills/revenue-forecast/scripts')
from revenue_report import validate_published_forecast,render_markdown
from revenue_backtest import validate_snapshot
validate_published_forecast(R,D);assert (OUT/'forecast.md').read_bytes()==render_markdown(R).encode();snapshot=read(OUT/'snapshot_v2.json');validate_snapshot(snapshot);assert snapshot['input_document']==D;validate_published_forecast(snapshot['forecast_result'],D)
for k,v in R.items():
 if k not in {'publication_receipt','result_sha256'}:assert snapshot['forecast_result'][k]==v,k
save('formal_independent_checks.json',{'strong_original_input':'PASS','exact_markdown':'PASS','immutable_snapshot_v2':'PASS','same_snapshot_input':'PASS','all_economic_payload':'PASS','confidence_component_sum_matches':math.isclose(sum(R['confidence']['components'].values()),R['confidence']['score']),'actual_score':R['confidence']['score'],'historical_accuracy_observations':R['confidence']['historical_accuracy']['observations']})
print('ARITHMETIC strong validator exactrender snapshot PASS')
for label,pp in [('ANNUAL',pages[D['sources'][0]['source_id']]),('H1',pages[D['sources'][1]['source_id']])]:
 for p in pp:
  if re.search(r'39\.99|22\.15|备[品件]|业绩承诺|营业收入.*(?:目标|计划)|募投项目.*延期',p['text']):print('SEARCH',label,p['page'],p['text'][:4500])
