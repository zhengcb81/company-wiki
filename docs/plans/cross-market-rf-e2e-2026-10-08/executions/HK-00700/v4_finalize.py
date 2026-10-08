"""Seal classification repair handoff, without self acceptance or shared writes."""
from pathlib import Path
import datetime as dt, hashlib, json
HERE=Path(__file__).resolve().parent;PLAN=HERE.parents[1];B=json.loads((HERE/'before_v4.json').read_text(encoding='utf-8'));OUT=Path(B['v4_output_root']);V3=Path(B['v3_output_root'])
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
def artifact(p,role):return {'absolute_path':str(p.resolve()),'bytes':p.stat().st_size,'sha256':sha(p),'role':role}
def canonical_sha(v):return hashlib.sha256(json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')).hexdigest()
old=read(V3/'input.json');new=read(OUT/'input.json');f=read(OUT/'forecast.json');v3f=read(V3/'forecast.json');verify=read(HERE/'v4_delivery_verification.json')
unchanged=[]
for row in B['protected']:
 p=Path(row['path']);after={**row,'after_bytes':p.stat().st_size if p.exists() else None,'after_sha256':sha(p) if p.exists() else None};after['unchanged']=after['after_bytes']==row['bytes'] and after['after_sha256']==row['sha256'];unchanged.append(after)
assert all(x['unchanged'] for x in unchanged)
write(HERE/'after_v4_integrity.json',{'timestamp_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'old_all_files_including_sealed_v3':'UNCHANGED','protected_count':len(unchanged),'checks':unchanged,'allowed_append_only_logs':['events.jsonl','commands/index.jsonl','processes/*'],'producer_writes':0})
def diff(a,b,p=''):
 out=[]
 if isinstance(a,dict) and isinstance(b,dict):
  for k in sorted(set(a)|set(b)):
   if k not in a or k not in b:out.append({'path':p+'/'+str(k),'before':a.get(k),'after':b.get(k)})
   else:out+=diff(a[k],b[k],p+'/'+str(k))
 elif isinstance(a,list) and isinstance(b,list):
  for n in range(max(len(a),len(b))):
   if n>=len(a) or n>=len(b):out.append({'path':p+'/'+str(n),'before':a[n] if n<len(a) else None,'after':b[n] if n<len(b) else None})
   else:out+=diff(a[n],b[n],p+'/'+str(n))
 elif a!=b:out.append({'path':p,'before':a,'after':b})
 return out
changes=diff(old,new)
allowed=['/forecast_version','/data_gaps/','/growth_driver_tree/drivers/0/counterevidence_rationale','/growth_driver_tree/drivers/0/evidence_nodes/1/conclusion','/growth_driver_tree/drivers/0/evidence_nodes/2/evidence_type','/growth_driver_tree/drivers/0/evidence_nodes/2/inference_distance','/growth_driver_tree/drivers/0/evidence_nodes/2/conclusion']
assert all(any(x['path']==k or (k.endswith('/') and x['path'].startswith(k)) for k in allowed) for x in changes)
assert len(changes)==7
assert new['data_gaps'][:-1]==old['data_gaps']
classification=read(HERE/'classification_v4.json');classification.update({'actual_input_diff':changes,'actual_engine_evidence_status':'limited','actual_confidence_limitation_restored':verify['classification_dependency']['restored_confidence_limitation'],'confidence_score':64.0,'income_and_sensitivity_results':'UNCHANGED','old_protected_count':len(unchanged),'old_files':'UNCHANGED','independent_review':'PENDING'})
write(HERE/'classification_v4.json',classification)

reg=[json.loads(line) for line in (OUT/'publications.jsonl').read_text(encoding='utf-8').splitlines() if line.strip()];prev=None
for x in reg:
 assert x['prev_line_sha256']==prev and canonical_sha({k:v for k,v in x.items() if k!='line_sha256'})==x['line_sha256'];prev=x['line_sha256']
assert any(x['artifact_type']=='forecast' and x['input_sha256']==f['input_sha256'] and x['result_sha256']==f['result_sha256'] for x in reg)
assert any(x['artifact_type']=='snapshot' and x['input_sha256']==f['input_sha256'] for x in reg)
write(HERE/'v4_registry_integrity.json',{'chain':'PASS','forecast_and_snapshot_anchors':'PASS','registry':artifact(OUT/'publications.jsonl','v4 isolated append-only publication registry'),'entries':reg,'actual_audit_exit':0,'actual_audit_stdout':(HERE/'v4_audit.stdout.txt').read_text(encoding='utf-8'),'scope':'No old v3 or installation registry writes'})
runtime=read(HERE/'v3_runtime_inventory.json')['current_runtime']
for row in runtime:assert sha(Path(row['installed_path']))==row['installed_sha256'] and sha(Path(row['canonical_path']))==row['canonical_sha256']
review=PLAN/'reviews/HK-00700';reviewjson=read(review/'recheck_v3.json')
review_inputs=[artifact(review/name,'sealed independent v3 review') for name in ['recheck_v3.md','recheck_v3.json']]
commands=[json.loads(line) for line in (HERE/'commands/index.jsonl').read_text(encoding='utf-8').splitlines()];cmds=[x for x in commands if x['event']=='finish' and x['label'].startswith('HK-v4-')]
for name in ('lint','hash-check','validate','forecast','snapshot','audit','strong'):assert any(x['label']=='HK-v4-'+name and x['returncode']==0 for x in cmds)
repair={'schema_version':'1.0','company':'TencentHK00700','agent_id':'/root/rf_hk_execution','as_of_date':'2026-10-08','scope':'Only independent-peer competition-risk classification and explanatory dependency closure','independent_finding':'HK-V3-R01 / HK-R02','status':'implemented_pending_independent_review','classification_path':str(HERE/'classification_v4.json'),'before':'NetEase competitor node one_step/non-contrary -> Games triangulated; limitation omitted','after':'contrary competitive-risk node; analogical peer distance disclosed -> Games limited; limitation restored','reference':'RF references/growth-driver-tree.md lines35-46','why_not_analogical_enum_alone':'Current engine counts all non-contrary nodes including analogical as positive triangulation; contrary encodes observed risk direction with analogy limitation in text','claims_unchanged':325,'parameter_records_unchanged':53,'original45_future_rates':'UNCHANGED','all_company_and_segment_revenue_CAGR_and_sensitivities':'UNCHANGED','confidence_score':64.0,'confidence_dependency':verify['classification_dependency'],'runtime_51_files':'UNCHANGED and installed/canonical matching','old_files_unchanged':len(unchanged),'raw_config_and_producer':'No writes; unchanged','actual_commands':[{'label':x['label'],'id':x['id'],'returncode':x['returncode'],'outputs':x['outputs']} for x in cmds],'review_inputs':review_inputs,'remaining_pipeline_limitations':['FY2025 official same-SHA provenance and exact public days unverified','Bounded Dayu missing filing downloaded_new→reuse not demonstrated','Latest ET/call body absent and full announcements interval not opened','HK canonical Worker/narrative consumption not demonstrated','Conditional five-stream direct_growth forecast without causal coefficient/reference-class/future accuracy calibration'],'provider_calls':0,'paid_LLM_calls':0,'cost_usd':0,'independent_review':'REQUIRED; no self acceptance','verification_path':str(HERE/'v4_delivery_verification.json'),'registry_integrity_path':str(HERE/'v4_registry_integrity.json'),'old_byte_integrity_path':str(HERE/'after_v4_integrity.json')}
write(HERE/'repair_v4.json',repair)
text=['# HK00700 v4 竞争证据分类修复交接','', '**实现与执行验证完成，待同一独立 reviewer 复核；完整产品链仍 PARTIAL。**','', '## 修复范围','', '- sealed v3的NetEase同行节点只证明跨公司竞争风险，无Tencent正向增长的明确因果桥，不能算作evergreen/new-launch机制的独立正面支撑。','- `inference_distance`改为`contrary`，evidence_type和结论明确竞争风险、analogical同行距离、NET/perimeter不同以及没有测定Tencent份额或替代。单改`analogical`在当前引擎仍会被计入正面triangulation，因此不采用该枚举单改。','- 正式引擎现将Games恢复为`limited`，confidence恢复“Growth driver evergreen_and_launch_monetization is not triangulated across two evidence types and sources”。分值仍64，是工程/证据质量说明，不是未来成功概率。','', '## 不变及完整验证','', '- 325条claims和53个参数记录全文保持，来源/capture、其余认定及业务模型保持，原45未来增长率未调。全部收入、CAGR、敏感性与sealed v3逐项完全一致。','- 实际lint、只读hash-check、validate-only、engine、same-source强验证/render、所有45曲线/9合计/15敏感性、immutable snapshot、registry audit/chain/anchors全部通过。输入只有7处分类/说明/版本变化，详见classification_v4.json。',f'- {len(unchanged)}项原TEMP及sealed v3全文件、旧工程manifest/receipts、raw/config逐一SHA/bytes保持。51runtime文件与canonical及v3发出时一致；没有producer/source-facts/Dayu/邻仓/配置/安装写操作。','', '## 复查入口','', f'- 新研究四产物和独立registry：`{OUT}`。', '- manifest_v4.json：四主产物真实SHA/bytes、环境、原文件完整性与所有交接路径。','- classification_v4.json：节点前后、7项精确inputdiff、实际输出标签与confidence依赖；repair_v4.json：原审查finding及全部正式命令日志接口。','- v4_delivery_verification.json / v4_registry_integrity.json / after_v4_integrity.json：完整测试和旧文件证据。','- 不运行旧build或v3脚本，不改sealed v3；独立reviewer只审变化依赖闭包。','', '## 保留限制','', '- 年报官方同SHA和确切发布日期未证实；日期仅明确的available-asof上界。','- Dayu有界缺文档下载→复用、ET电话会、全公告区间、HK canonical Worker仍BLOCKED/未证明。','- 五业务仍条件direct_growthfallback，无虚构量价/客户分母、无未来实绩回测，无准确率或预测区间保证。','', '执行者不自行签收。']
(HERE/'repair_v4.md').write_text('\n'.join(text)+'\n',encoding='utf-8')
manifest={'schema_version':'1.0','company':'Tencent Holdings Limited','market':'HK','security_id':'00700','agent_id':'/root/rf_hk_execution','as_of_date':'2026-10-08','status':'partial_pending_independent_review','output_root':str(OUT),'primary_artifacts':[artifact(OUT/name,role) for name,role in [('input.json','single classification repair input'),('forecast.json','formal actual engine output'),('forecast.md','same-source deterministic Markdown'),('snapshot.json','immutable v4 snapshot')]],'registry':artifact(OUT/'publications.jsonl','v4 independent registry'),'classification_path':str(HERE/'classification_v4.json'),'repair_json_path':str(HERE/'repair_v4.json'),'repair_markdown_path':str(HERE/'repair_v4.md'),'strong_verification_path':str(HERE/'v4_delivery_verification.json'),'old_integrity_path':str(HERE/'after_v4_integrity.json'),'old_protected_count':len(unchanged),'runtime_version':f['engine_version'],'runtime_schema':f['schema_version'],'runtime_51':'unchanged installed/canonical SHA','command_index':str(HERE/'commands/index.jsonl'),'process_trace_dir':str(HERE/'processes'),'environment':{'REVENUE_PUBLICATION_REGISTRY':str(OUT/'publications.jsonl'),'CWP_AUDIT_PROCESS_DIR':str(HERE/'processes'),'PYTHONPATH_prefix':str(PLAN/'process_trace')},'sealed_v3_manifest':artifact(HERE/'manifest_v3.json','unchanged sealed v3 manifest'),'review_inputs':review_inputs,'calls_and_cost':{'provider_calls':0,'paid_LLM_calls':0,'cost_usd':0},'remaining_limitations':repair['remaining_pipeline_limitations'],'independent_review':'PENDING; executor not signed','ended_at':dt.datetime.now(dt.timezone.utc).isoformat()}
write(HERE/'manifest_v4.json',manifest)
print(json.dumps({'manifest':str(HERE/'manifest_v4.json'),'classification':str(HERE/'classification_v4.json'),'old_files_unchanged':len(unchanged),'input_diff_count':len(changes),'Games_evidence':'limited','confidence':64.0,'restored_warning':verify['classification_dependency']['restored_confidence_limitation'],'status':'partial_pending_independent_review'},ensure_ascii=False))
