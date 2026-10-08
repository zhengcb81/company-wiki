"""Independent classification-only v4 closure and real deterministic replay."""
import collections,datetime as dt,hashlib,json,os,shutil,subprocess,sys
from pathlib import Path
sys.dont_write_bytecode=True
sys.stdout.reconfigure(encoding='utf-8')
HERE=Path(__file__).resolve().parent;EX=HERE.parents[1]/'executions/HK-00700'
load=lambda p:json.loads(Path(p).read_text(encoding='utf-8'))
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
save=lambda n,v:(HERE/n).write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
m=load(EX/'manifest_v4.json');m3=load(EX/'manifest_v3.json');oldm=load(EX/'manifest.json')
OUT=Path(m['output_root']);V3=Path(m3['output_root']);SKILL=Path(oldm['skill_root'])
i=load(OUT/'input.json');i3=load(V3/'input.json');f=load(OUT/'forecast.json');f3=load(V3/'forecast.json');s=load(OUT/'snapshot.json')
repair=load(EX/'repair_v4.json');classification=load(EX/'classification_v4.json');oldreview=load(HERE/'recheck_v3.json')
def diffs(a,b,path=''):
    if type(a) is not type(b):return [dict(path=path,before=a,after=b)]
    if isinstance(a,dict):
        result=[]
        for k in sorted(set(a)|set(b)):result+=diffs(a.get(k),b.get(k),path+'/'+k)
        return result
    if isinstance(a,list):
        result=[]
        for k in range(max(len(a),len(b))):result+=diffs(a[k] if k<len(a) else None,b[k] if k<len(b) else None,path+'/'+str(k))
        return result
    return [] if a==b else [dict(path=path,before=a,after=b)]
delta=diffs(i3,i)
assert len(delta)==7 and sorted(delta,key=lambda q:q['path'])==sorted(classification['actual_input_diff'],key=lambda q:q['path'])
assert i['evidence_claims']==i3['evidence_claims'] and len(i['evidence_claims'])==325
assert i['parameters']==i3['parameters'] and len(i['parameters'])==53
assert i['sources']==i3['sources'] and i['historical_revenue']==i3['historical_revenue'] and i['segments']==i3['segments']
assert i['management_communication_coverage']==i3['management_communication_coverage'] and i['management_targets']==i3['management_targets']
peer=i['growth_driver_tree']['drivers'][0]['evidence_nodes'][2]
assert peer==classification['after'] and peer['inference_distance']=='contrary'
assert peer['evidence_type']=='independent_peer_competition_risk'
assert all(t in peer['conclusion'] for t in ['analogical','competitive RISK','not positive support','Different company','no explicit causal bridge','cannot triangulate'])
warning='Growth driver evergreen_and_launch_monetization is not triangulated across two evidence types and sources'
game=next(q for q in f['growth_driver_analysis']['drivers'] if q['driver_id']=='evergreen_and_launch_monetization')
top=next(q for q in f['growth_driver_analysis']['top_drivers'] if q['driver_id']=='evergreen_and_launch_monetization')
assert game['evidence_status']==top['evidence_status']=='limited'
assert next(q for q in f3['growth_driver_analysis']['drivers'] if q['driver_id']==game['driver_id'])['evidence_status']=='triangulated'
assert warning in f['confidence']['limitations'] and warning not in f3['confidence']['limitations']
assert f['confidence']['score']==f3['confidence']['score']==64
assert f['confidence']['components']==f3['confidence']['components']
assert set(f['confidence']['limitations'])==set(f3['confidence']['limitations'])|{warning}
for seg in f['segments']:assert seg['scenarios']==next(q for q in f3['segments'] if q['name']==seg['name'])['scenarios']
assert f['consolidated_forecast']==f3['consolidated_forecast'] and f['sensitivities']==f3['sensitivities']
allocation=[]
for section in ['drivers','top_drivers','headwinds']:
    old={q['driver_id']:q for q in f3['growth_driver_analysis'][section]}
    assert set(old)=={q['driver_id'] for q in f['growth_driver_analysis'][section]}
    for row in f['growth_driver_analysis'][section]:
        keys=['estimated_base_terminal_increment','share_of_positive_driver_increment','terminal_increment_by_segment','rank','segment_attribution']
        assert all(row.get(k)==old[row['driver_id']].get(k) for k in keys)
        allocation.append(dict(section=section,driver_id=row['driver_id'],numeric_fields={k:row[k] for k in keys if k in row}))
assert f['growth_driver_analysis']['reconciliation']==f3['growth_driver_analysis']['reconciliation']
protected=[]
oldprotection=load(EX/'after_v4_integrity.json')
for row in oldprotection['checks']:
    p=Path(row['path']);actual=sha(p);size=p.stat().st_size
    assert actual==row['sha256'] and size==row['bytes'],str(p)
    protected.append(dict(path=str(p),sha256=actual,byte_size=size))
assert len(protected)==188
artifacts=[]
for row in m['primary_artifacts']+[m['registry'],m['sealed_v3_manifest']]+m['review_inputs']:
    p=Path(row['absolute_path']);actual=sha(p);size=p.stat().st_size
    assert actual==row['sha256'] and size==row['bytes']
    artifacts.append(dict(path=str(p),sha256=actual,byte_size=size))
runtime=[]
for row in load(EX/'v3_runtime_inventory.json')['current_runtime']:
    a=sha(row['installed_path']);b=sha(row['canonical_path'])
    assert a==row['installed_sha256'] and b==row['canonical_sha256'] and a==b
    runtime.append(dict(installed_path=row['installed_path'],canonical_path=row['canonical_path'],sha256=a))
assert len(runtime)==51
pairs=collections.defaultdict(list)
for line in Path(m['command_index']).read_text(encoding='utf-8').splitlines():
    row=json.loads(line)
    if 'v4' in row.get('label','').lower():pairs[row['id']].append(row)
commands=[]
for key,rows in pairs.items():
    assert len(rows)==2 and [q['event'] for q in rows]==['start','finish'],key
    end=rows[-1]
    for row in end['outputs'].values():assert sha(row['path'])==row['sha256'] and Path(row['path']).stat().st_size==row['byte_size']
    commands.append(dict(id=key,**{k:end[k] for k in ['label','command','started_at','ended_at','returncode','outputs']}))
traces={}
for p in Path(m['process_trace_dir']).glob('*.jsonl'):
    rows=[json.loads(line) for line in p.read_text(encoding='utf-8').splitlines()]
    if any('v4' in json.dumps(row,ensure_ascii=False) for row in rows):traces[p.name]=rows
REPLAY=OUT.parent/'review-HK-00700-rf_hk_independent_review-v4';REPLAY.mkdir(exist_ok=True)
os.environ['REVENUE_PUBLICATION_REGISTRY']=str(REPLAY/'publications.jsonl')
sys.path.insert(0,str(SKILL/'scripts'))
from revenue_report import validate_published_forecast,render_markdown
from revenue_backtest import validate_snapshot
validate_published_forecast(f,i);validate_snapshot(s)
assert render_markdown(f)==(OUT/'forecast.md').read_text(encoding='utf-8')
markdown=(OUT/'forecast.md').read_text(encoding='utf-8')
assert '- 证据状态：limited' in markdown
assert '[independent_peer_competition_risk/contrary]' in markdown
assert 'Games remains limited, without triangulation credit' in markdown
shutil.copyfile(OUT/'input.json',REPLAY/'input.json')
cmd=[sys.executable,'-B',str(SKILL/'scripts/revenue_forecast.py'),str(REPLAY/'input.json'),'--output',str(REPLAY/'forecast.json'),'--markdown',str(REPLAY/'forecast.md')]
ran=subprocess.run(cmd,capture_output=True,text=True,encoding='utf-8')
(REPLAY/'cli.stdout.txt').write_text(ran.stdout,encoding='utf-8');(REPLAY/'cli.stderr.txt').write_text(ran.stderr,encoding='utf-8')
assert ran.returncode==0,(ran.returncode,ran.stderr)
fresh=load(REPLAY/'forecast.json');validate_published_forecast(fresh,i)
def scrub(v):
    if isinstance(v,dict):return {k:scrub(x) for k,x in v.items() if k not in ['publication_receipt','result_sha256','generated_at','created_at','timestamp','receipt_sha256']}
    if isinstance(v,list):return [scrub(x) for x in v]
    return v
assert scrub(fresh)==scrub(f)
os.environ['REVENUE_PUBLICATION_REGISTRY']=str(OUT/'publications.jsonl')
import publication_registry as reg
entries=reg._read_entries()
assert any(q['artifact_type']=='forecast' and q['input_sha256']==f['input_sha256'] and q['result_sha256']==f['result_sha256'] for q in entries)
assert any(q['artifact_type']=='snapshot' and q['input_sha256']==s['input_sha256'] and q['artifact_id']==s['snapshot_id'] and q['result_sha256']==s['forecast_result_sha256'] for q in entries)
audit_cmd=[sys.executable,'-B',str(SKILL/'scripts/publication_registry.py'),'audit','--result',str(OUT/'forecast.json')]
audit=subprocess.run(audit_cmd,capture_output=True,text=True,encoding='utf-8');assert audit.returncode==0,(audit.returncode,audit.stderr)
for row in m['primary_artifacts']+[m['registry']]:assert sha(row['absolute_path'])==row['sha256']
assert all(sha(q['path'])==q['sha256'] for q in protected)
support=dict(timestamp=dt.datetime.now(dt.timezone.utc).isoformat(),scope='v4 classification dependency only',manifest_sha256=sha(EX/'manifest_v4.json'),repair_read_sha256=sha(EX/'repair_v4.json'),classification_read_sha256=sha(EX/'classification_v4.json'),actual_input_diff=delta,unchanged325_claims=True,unchanged53_parameter_records=True,unchanged_source_date_history_and_segment_contracts=True,peer_before=classification['before'],peer_after=peer,actual_games_evidence_status=game['evidence_status'],restored_confidence_warning=warning,score=64,numerics_equal_v3=dict(all45_curves=True,all9_company_rows_CAGR_increment=True,all15_sensitivities=True,driver_allocations=allocation),protected188=protected,artifacts=artifacts,runtime51=runtime,commands=commands,process_traces=traces,strong_input_required='PASS',same_render='PASS',snapshot='PASS',real_independent_replay=dict(command=cmd,returncode=ran.returncode,root=str(REPLAY),deterministic_match=True),registry=dict(entries=entries,audit_command=audit_cmd,returncode=audit.returncode,stdout=audit.stdout,stderr=audit.stderr,sha256=sha(OUT/'publications.jsonl')),remaining_limitations=m['remaining_limitations'])
save('recheck_v4_support.json',support)
print(json.dumps(dict(input_diff=len(delta),claims_identical=325,parameters_identical=53,protected188='PASS',runtime51='PASS',Games='limited',warning_restored=True,score=64,strong='PASS',render='PASS',snapshot='PASS',real_replay='PASS',registry=audit.returncode,commands=len(commands),traces=len(traces)),ensure_ascii=False))
