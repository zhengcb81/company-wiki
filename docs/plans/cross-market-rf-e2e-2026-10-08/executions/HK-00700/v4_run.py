"""Single classification repair; sealed v3 and all original observations are immutable."""
from pathlib import Path
import copy, datetime as dt, hashlib, json, os, subprocess, sys
HERE=Path(__file__).resolve().parent;PLAN=HERE.parents[1];WIKI=HERE.parents[4]
OLD=Path(json.loads((HERE/'before.json').read_text(encoding='utf-8'))['output_root']);V3=OLD/'v3';OUT=OLD/'v4'
SKILL=Path.home()/'.agents/skills/revenue-forecast'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def write(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
def item(p):return {'path':str(p.resolve()),'bytes':p.stat().st_size,'sha256':sha(p)}
def event(action,paths,details=None,outcome='success'):
 row={'timestamp_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'agent_id':'/root/rf_hk_execution','step':'v4_classification_repair','action':action,'tool':'task-local actual installed runtime subprocess','input_summary':details,'source_url':None,'artifacts':[str(p) for p in paths],'outcome':outcome,'error':None}
 with (HERE/'events.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps(row,ensure_ascii=False)+'\n')
action=sys.argv[1]
if action=='build':
 assert not OUT.exists() and not (HERE/'before_v4.json').exists(),'Never overwrite v4 or its frozen baseline'
 protected=[item(p) for p in OLD.rglob('*') if p.is_file() and 'v4' not in p.relative_to(OLD).parts]
 protected += [item(p) for p in HERE.iterdir() if p.is_file() and not p.name.startswith(('v4_','before_v4','after_v4','repair_v4','manifest_v4','classification_v4')) and p.name!='events.jsonl']
 protected += [item(Path(x['path'])) for x in read(HERE/'before_v3.json')['raw_and_config_baseline']]
 write(HERE/'before_v4.json',{'timestamp_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'protected':protected,'v4_output_root':str(OUT),'v3_output_root':str(V3),'scope':'old TEMP incl every v3 file, old engineering/manifest/receipts, all original raw/config unchanged; only append existing process and command logs'})
 OUT.mkdir(exist_ok=False);d=copy.deepcopy(read(V3/'input.json'));driver=next(x for x in d['growth_driver_tree']['drivers'] if x['driver_id']=='evergreen_and_launch_monetization');node=next(x for x in driver['evidence_nodes'] if x['evidence_id']=='games_independent_peer_context');before=copy.deepcopy(node)
 node['inference_distance']='contrary'
 node['evidence_type']='independent_peer_competition_risk'
 node['conclusion']='NetEase H1 Games-and-related-VAS NET revenue +8.3%, active franchises and international operations indicate an analogical competitive RISK to Tencent paid retention/launch monetization. Classified contrary, not positive support for Tencent evergreen/new-launch revenue growth. Different company, accounting and perimeter; no explicit causal bridge identifying Tencent share, displacement, payer/ARPPU or growth magnitude. This evidence cannot triangulate the positive Tencent mechanism.'
 own_contra=next(x for x in driver['evidence_nodes'] if x['evidence_id']=='evergreen_and_launch_monetization_contrary')
 own_contra['conclusion']=own_contra['conclusion'].replace('NetEase competition is separate one-step context, not measured Tencent displacement.','NetEase competition is separately classified analogical competitive risk/contrary evidence, not positive Tencent growth support or measured displacement.')
 driver['counterevidence_rationale']=own_contra['conclusion']
 d['forecast_version']='2026-10-08-hk-v4'
 d['data_gaps'].append('NetEase peer growth and live franchises are contrary/analogical competitive-risk context, not independent positive evidence for Tencent evergreen/new-launch revenue. Games remains limited, without triangulation credit; all325 claim bytes and53 parameter records unchanged.')
 assert d['parameters']==read(V3/'input.json')['parameters'] and d['evidence_claims']==read(V3/'input.json')['evidence_claims']
 write(OUT/'input.json',d)
 write(HERE/'classification_v4.json',{'issue':'HK-v3-R02 independent-peer competitive risk improperly counted as positive triangulation','reference':'RF references/growth-driver-tree.md lines35-46','before':before,'after':node,'runtime_rule':'research/drivers.py excludes only inference_distance=contrary from supporting evidence; analogical alone still enters supporting types/sources','choice':'contrary encodes direction; narrative discloses analogical peer distance and does not invent Tencent causal bridge','expected_engine_evidence_status':'limited','expected_confidence_limitation':'Growth driver evergreen_and_launch_monetization is not triangulated across two evidence types and sources','no_new_claims':True,'all325_claims_unchanged':True,'all53_parameter_records_unchanged':True,'independent_review':'PENDING'})
 # Reuse an already audited local arithmetic verifier as a NEW file, adapting only owned output paths.
 verify=(HERE/'v3_verify.py').read_text(encoding='utf-8').replace("OUT=OLD/'v3'","OUT=OLD/'v4'").replace("v3_delivery_verification.json","v4_delivery_verification.json")
 verify += '''\n# Classification-only dependency comparison to sealed v3.\nv3i=read(OLD/'v3/input.json');v3f=read(OLD/'v3/forecast.json')\nassert i['parameters']==v3i['parameters'] and i['evidence_claims']==v3i['evidence_claims']\nassert i['sources']==v3i['sources'] and i['management_communication_coverage']==v3i['management_communication_coverage']\nassert i['segments']==v3i['segments']\nassert f['consolidated_forecast']==v3f['consolidated_forecast'] and f['sensitivities']==v3f['sensitivities']\nbefore=next(x for x in v3f['growth_driver_analysis']['top_drivers'] if x['driver_id']=='evergreen_and_launch_monetization')\nafter=next(x for x in f['growth_driver_analysis']['top_drivers'] if x['driver_id']=='evergreen_and_launch_monetization')\nassert before['evidence_status']=='triangulated' and after['evidence_status']=='limited'\nassert f['confidence']['score']==v3f['confidence']['score']==64.0\nlim='Growth driver evergreen_and_launch_monetization is not triangulated across two evidence types and sources'\nassert lim in f['confidence']['limitations'] and lim not in v3f['confidence']['limitations']\nchecks['classification_dependency']={'before':'triangulated','after':'limited','restored_confidence_limitation':lim,'confidence_score_unchanged':64.0,'all325_claims_unchanged':True,'all53_parameter_records_unchanged':True,'all_income_and_sensitivity_results_unchanged':True,'no_new_source_calls':True}\n(HERE/'v4_delivery_verification.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2),encoding='utf-8')\nprint(json.dumps(checks['classification_dependency'],ensure_ascii=False))\n'''
 (HERE/'v4_verify.py').write_text(verify,encoding='utf-8')
 event('freeze_and_reclassify_peer_competition',[HERE/'before_v4.json',HERE/'classification_v4.json',OUT/'input.json'],{'old_protected_count':len(protected),'before':before['inference_distance'],'after':node['inference_distance']})
 print(json.dumps({'output':str(OUT),'old_artifacts_frozen':len(protected),'all325claims':'unchanged','all53parameters':'unchanged','classification':'contrary competitive risk; analogical peer distance disclosed'},ensure_ascii=False));sys.exit(0)
env=dict(os.environ,PYTHONUTF8='1',PYTHONIOENCODING='utf-8',REVENUE_PUBLICATION_REGISTRY=str(OUT/'publications.jsonl'),CWP_AUDIT_PROCESS_DIR=str(HERE/'processes'))
env['PYTHONPATH']=os.pathsep.join([str(PLAN/'process_trace'),env.get('PYTHONPATH','')])
cmds={
 'lint':['lint_input.py',str(OUT/'input.json'),'--check-conclusion-facts','--check-sensitivity-propagation'],
 'hash-check':['fix_hashes.py',str(OUT/'input.json'),'--check'],
 'validate':['revenue_forecast.py',str(OUT/'input.json'),'--validate-only','--verbose'],
 'forecast':['revenue_forecast.py',str(OUT/'input.json'),'--output',str(OUT/'forecast.json'),'--markdown',str(OUT/'forecast.md')],
 'snapshot':['revenue_backtest.py','create',str(OUT/'input.json'),'--version','2026-10-08-hk-v4','--output',str(OUT/'snapshot.json')],
 'audit':['publication_registry.py','audit','--result',str(OUT/'forecast.json')],
 'strong':['__local__',str(HERE/'v4_verify.py')],
}
c=cmds[action];cmd=[sys.executable,'-X','utf8',c[1]] if c[0]=='__local__' else [sys.executable,'-X','utf8',str(SKILL/'scripts'/c[0]),*c[1:]]
print(json.dumps({'actual_command':cmd,'environment_overrides':{k:env[k] for k in ('REVENUE_PUBLICATION_REGISTRY','CWP_AUDIT_PROCESS_DIR','PYTHONPATH')}},ensure_ascii=False),flush=True)
r=subprocess.run(cmd,cwd=str(OUT),env=env,capture_output=True,text=True,encoding='utf-8',timeout=180)
out=HERE/f'v4_{action}.stdout.txt';err=HERE/f'v4_{action}.stderr.txt';out.write_text(r.stdout,encoding='utf-8');err.write_text(r.stderr,encoding='utf-8')
event('actual_'+action,[out,err],{'command':cmd,'returncode':r.returncode},outcome='success' if r.returncode==0 else 'failed')
print(r.stdout);print(r.stderr,file=sys.stderr);sys.exit(r.returncode)
