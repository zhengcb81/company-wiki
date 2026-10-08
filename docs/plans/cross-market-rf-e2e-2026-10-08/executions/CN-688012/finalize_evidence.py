"""Assemble engineering handoff only; research output remains isolated TEMP."""
from pathlib import Path
import datetime,hashlib,json,os,subprocess,sys
ROOT=Path(__file__).resolve().parent
CWP=ROOT.parents[4]
OUT=Path(os.environ['TEMP'])/'cwp-rf-e2e-20261008'/'CN-688012'
SKILL=Path('C:/Users/郑曾波/.agents/skills/revenue-forecast')
RF=Path('C:/Users/郑曾波/Projects/revenue-forecast')
FF=Path('C:/Users/郑曾波/.agents/skills/filing-fetch')
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf-8')
now=datetime.datetime.now(datetime.timezone.utc).isoformat()
input_data=read(OUT/'input.json');result=read(OUT/'forecast.json');snapshot=read(OUT/'snapshot_v2.json')
verification=read(ROOT/'formal_verification_receipt.json')
assert verification['status'].startswith('PASS') and 'PASS' in verification['snapshot']
for artifact in verification['artifacts']:assert sha(Path(artifact['path']))==artifact['sha256']
assert snapshot['input_document']==input_data and snapshot['forecast_result']==result
index=[json.loads(x) for x in (ROOT/'commands'/'index.jsonl').read_text(encoding='utf-8').splitlines() if x.strip()]
finished=[x for x in index if x['event']=='finish']
def log(label):
 rows=[x for x in finished if x['label']==label]; assert rows,label
 return rows[-1]
def path(label):return Path(log(label)['outputs']['stdout']['path'])
annual=read(path('annual25-zero-download-repeat'))
half_download=read(path('rf-half2026-fetch-after-sid-fix'))
half=read(path('rf-half2026-reuse-date-corrected'))
assert annual['reuse_receipt']['download_calls']==0
assert half_download['company_wiki_trace']['source_candidate']['resolution_outcome']=='downloaded_new'
assert half['reuse_receipt']['download_calls']==0
assert half_download['source_id']==half['source_id']
assert half['published_date']=='2026-08-20'
assert sha(OUT/'annual2025.pdf')==annual['capture']['snapshot_sha256']
assert sha(OUT/'half2026.pdf')==half['capture']['snapshot_sha256']
assert sha(OUT/'half2026_current.pdf')==half['capture']['snapshot_sha256']
assert read(ROOT/'half2026_current_source_inspection.json')['manifest']['published_date']=='2026-08-20'
def append_event(step,action,tool,summary,artifacts,outcome,source=None,retrospective=False):
 with (ROOT/'events.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps(dict(timestamp_utc=now,agent_id='rf_cn_execution',step=step,action=action,tool=tool,input_summary=summary,source_url=source,artifacts=artifacts,outcome=outcome,error=None,retrospective_record=retrospective,original_exact_tool_timestamp='not available' if retrospective else now),ensure_ascii=False)+'\n')
append_event('1A/1B','Record previously observed non-shell web actions','web.run',dict(open_ids=['turn234view0','turn231view0','turn232view0'],scope='Actual SEMI official release opened and returned parsed tool output saved; official AMEC homepage and SSE IR2 open failures; secondary August IR-DOCX leads were NOT used as facts',limitation='Per-tool original precise timestamps were not persisted; logging time is finalization, prior date is observed information date'),[str(OUT/'semi_web_open_snapshot.json')],'actual observed tool results; retrospective timing disclosed',retrospective=True)
append_event('1A','Record actual temporary roadshow browser interaction and cleanup','cua_repl',dict(url='https://roadshow.sseinfo.com/activityDetails/40766',observed_state='Official roadshow,195 replies and29 pre-collected responses; guestCompanyName=中微公司, companyId145565,688012 logo',observed_public_asset_inventory='9ef2eae4-17c7-4fde-8ced-f581cde4c627'),[str(ROOT/'roadshow_observed_assets_receipt.json'),str(ROOT/'roadshow_public_questions_receipt.json'),str(ROOT/'roadshow_precollect_complete_receipt.json')],'created temporary tab closed; original API responses retained for reviewer',retrospective=True)
runtime_files=['SKILL.md','scripts/revenue_forecast.py','scripts/source_preparation.py','scripts/revenue_core.py','scripts/revenue_report.py','scripts/revenue_backtest.py','scripts/publication_registry.py','scripts/contracts/constants.py','scripts/forecast/segments.py']
runtime=[]
for rel in runtime_files:
 installed=SKILL/rel; canonical=RF/rel
 assert installed.exists(),str(installed)
 row=dict(relative_path=rel,installed_path=str(installed),installed_sha256=sha(installed))
 if canonical.exists():row.update(canonical_path=str(canonical),canonical_sha256=sha(canonical),identical=sha(installed)==sha(canonical))
 runtime.append(row)
assert all(x.get('identical',True) for x in runtime),'Installed/repository drift requires MAIN review'
references=[dict(path=str(p),sha256=sha(p),reading_basis='Required RF reference read during this executor run; SHA inventoried at finalization') for p in sorted((SKILL/'references').glob('*.md')) if p.name in {'input-construction.md','input-schema.md','data-governance.md','compliance-workflow.md','model-library.md','research-methodology.md','management-targets.md','growth-driver-tree.md','revenue-recognition.md','output-specification.md','lifecycle-modeling.md','backtesting.md','buy-side-research.md'}]
baseline=read(ROOT.parents[1]/'baseline.json')
configuration=[]
for row in baseline['config_files']:
 p=Path(row['path']); current=sha(p)
 configuration.append(dict(path=str(p),baseline_sha256=row['sha256'],current_sha256=current,unchanged=current==row['sha256']))
assert all(x['unchanged'] for x in configuration if x['path'].endswith('source_catalog.yaml') or x['path'].endswith('company_wiki.json'))
write(ROOT/'runtime_and_configuration.json',dict(runtime_version=result['engine_version'],schema_version=result['schema_version'],runtime_files=runtime,required_reference_inventory=references,configuration=configuration,actual_environment=dict(TEMP=os.environ['TEMP'],output_root=str(OUT),REVENUE_PUBLICATION_REGISTRY=str(OUT/'publications.jsonl'),CWP_AUDIT_PROCESS_DIR=str(ROOT/'processes'),PYTHONPATH_prefix=str(ROOT.parents[1]/'process_trace')),note='Only non-secret isolation variables inventoried; no signer configured'))
steps=[
 ('0','PASS','Nine dimensions map to actual used drivers with explicit physical-capacity/history/market-share gaps. Runtime completeness is not economic validation.',['input.json','forecast.json']),
 ('1','PASS','688012,CN; as_of2026-10-08;FY2025base;FY2026–28;CNYmillion;12-31yearend. No later disclosures.',['input.json']),
 ('1A','PASS_WITH_GAPS','Six official communication categories;4 checked, telephone TXT/presentation original unavailable. Read all195 interactive replies +29 pre-collected;8 AMEC replies+1 AMEC pre-collected answer filtered. All19 post-H1 announcement titles read, bodies except H1 unavailable.',['communication_coverage.json','roadshow_public_questions_receipt.json','roadshow_precollect_complete_receipt.json','recent_announcements_receipt.json']),
 ('1B','PASS_WITH_LIMITATIONS','Independent SEMI primary WFE reference + China moderation; original client discount/concentration/acquisition risks; explicit alternative conditions/falsifiers. No statistically calibrated AMEC forecasts.',['model_design.md','fact_checks.json','input.json']),
 ('2','PASS','3 historical revenues from actual2025annual comparative table; precise total versus rounded equipment residual reconcile. Full2024annual readonly lookup not_found, never claimed read.',['annual2025_source_inspection.json','fact_checks.json']),
 ('3','PASS','Real RF→FF→CWP annual reuse and SID H1 download; same H1request then0downloads/stableSHA; pathless SourceRef verified original binary reads. Claim/capture hashes bound.',['commands/index.jsonl','half2026_current_raw_receipt.json','input.json']),
 ('4','PASS_WITH_LIMITATIONS','3 mutually exclusive curves: legacy Equipment excluding CMP, legacy composite residual excluding CMP, acquired CMP all100%consolidated income after control. Unknown product/substream bases not invented.',['input.json','model_design.md']),
 ('5','PASS','Equipment acceptance PIT. Mixed spares/services and CMP recognized direct-revenue aggregate, explicit boundaries and complete policy claims, no false progress/lag.',['input.json','fact_checks.json']),
 ('6','PASS_WITH_LIMITATIONS','Three-year low/base/high allnoncrossing, futuredriver amounts classified assumptions, actual H1 not doubled; 2026 CMP annual seller target mismatch;27/28 full-year independent benchmarks.',['input.json','forecast.json']),
 ('6A','PASS','4 causal roots;weights sum to1 bysegment; actual Base parameter IDs, evidence/falsifiers and contrary risk nodes, one explicit analogical outside-industry reference. Weights are analyst allocations.',['input.json','forecast.json']),
 ('7','PASS','All9 scenario-year sums, bridge/increments/CAGR independently recomputed; no company adjustment or constraint invented, no ownership multiplication.',['formal_verification_receipt.json']),
 ('8','PASS','Four terminal driver tests use percent fractions .10/.05/.20/.30; no assumption single shocks sum into joint stress. Strong validator recomputes sensitivity.',['forecast.json','formal_verification_receipt.json']),
 ('9','PASS_WITH_LIMITATIONS','Engine score is workflow/evidence quality only; no immutable realized historical accuracy. Proxy sold-chambers≠provenacceptedrevenue units; mixed fallbacks and target mismatch remain material.',['forecast.json']),
 ('10','PASS','Actual template/lint/hashcheck/validate-only/engine/input-requiredstrong/exactbytesrender; samev2JSONandMD delivered onlyTEMP.',['commands/index.jsonl','formal_verification_receipt.json','forecast.json','forecast.md']),
 ('11','PASS','Write-once v2snapshot matches exact explicit-version input and full formal result, both strongvalidated. v1freeze retained, not modified after new IR facts.',['snapshot_v2.json','formal_verification_receipt.json']),
 ('11-evaluate','NOT_APPLICABLE','FY2026–28 actual complete results unknown at information date; never used scenario projections as actual backtest.',['snapshot_v2.json']),
 ('CWP-worker','NOT_RUN','This run binary-verified raw and deterministically parsed259annual/210H1 pages in TEMP. It did not schedule CWPWorker or publish production narrative derivatives. receipt parser/LLMcounts null remain unknown, not relabeled zero.',['annual2025_source_inspection.json','half2026_current_source_inspection.json'])]
matrix=[]
for step,status,detail,artifacts in steps:
 resolved=[]
 for name in artifacts:
  p=(OUT/name) if (OUT/name).exists() else ROOT/name
  assert p.exists(),str(p);resolved.append(str(p))
 matrix.append(dict(step=step,status=status,detail=detail,artifacts=resolved,independent_review_status='pending'))
write(ROOT/'skill_step_matrix.json',dict(schema_version='1.0',company='CN-688012',skill_root=str(SKILL),engine_version=result['engine_version'],steps=matrix))
append_event('0–11','Assemble v2 execution completion and handoff','finalize_evidence.py',dict(formal_version=result['forecast_version'],status='execution complete; independent review pending',originals='same SHA after standard source-fact metadata corrections'),[str(ROOT/'skill_step_matrix.json'),str(ROOT/'manifest.json')],'Ready for fresh independent reviewer; no self-acceptance')
sources=[]
for label,payload,request in [('annual2025',annual,'annual2025.json'),('half2026',half,'half2026_fetch.json')]:
 ref=payload['company_wiki_trace']['source_ref'];manifest=payload['company_wiki_trace']['source_manifest']
 sources.append(dict(**ref,published_date=payload['published_date'],request_path=str(ROOT/'requests'/request),response_path=str(path('annual25-zero-download-repeat' if label=='annual2025' else 'rf-half2026-reuse-date-corrected')),download_response_path=str(path('rf-half2026-fetch-after-sid-fix')) if label=='half2026' else None,resolution_outcome='reused_existing' if label=='annual2025' else 'downloaded_new then reused_existing',downloads=0 if label=='annual2025' else 1,verification_fetches=1 if label=='annual2025' else 0,provider=manifest.get('provider'),source_manifest=manifest,original_capture_unknown=manifest.get('retrieved_at') is None))
for source in input_data['sources']:
 if source['source_id'] in {annual['source_id'],half['source_id']}:continue
 capture=source['capture'];p=OUT/('semi_web_open_snapshot.json' if source['source_id']=='semi_wfe_20260714' else 'roadshow_public_questions.json')
 sources.append(dict(source_id=source['source_id'],published_date=source['published_date'],url=source['url'],content_sha256=capture['snapshot_sha256'],bytes=p.stat().st_size,response_path=str(p),resolution_outcome='official_primary_web_open' if source['source_id']=='semi_wfe_20260714' else 'official_public_api_read',downloads=0,provider=source['publisher'],capture=capture))
gaps=['No CWPWorker/narrative-production end-to-end run in this company execution; deterministic per-page TEMP extraction only','August2026 investor IR DOCX/presentation official original remains unavailable; network results Q&A independently fully read','Post-H1 all19announcement metadata covered; fund/capex-delay bodies not downloaded, no inferred facts','Rounded equipment base ±0.5million and unproved sold-chamber vsrecognition proxy','No measured SKUprices, fullchamber throughput ceiling, precise spares/service split, customer futurecapex, or product-family base','2026 CMP fullannual seller commitment cannot map to June–December consolidated revenue','Short3annualhistory, no realized future backtests or calibrated probabilities','Original annual retrieval date null preserved; newly verified open capture is not retroactive retrieval']
defects=[dict(id='RF-CN-V2-ENVELOPE',status='MAIN fixed and installed',evidence='Initial failure commands retained; actualannual schema2reuse now succeeds'),dict(id='RF-CN-UNKNOWN-CAPTURE',status='MAIN fixed; unknown original retrieval preserved',evidence=str(path('annual25-zero-download-repeat'))),dict(id='SID-CN-PERIOD-CATEGORY',status='MAIN TDD fixed annual/H1/Q1Q3; ownerWIP kept',evidence='Official category comparison request/response JSON including real Q1/Q3union + trueH1 downloaded_new'),dict(id='SID-CN-PUBLISHED-DATE-CST',status='MAIN TDD fixed; producer standard source-facts corrected current H1 metadata only',evidence=str(ROOT/'requests'/'half2026_published_date_facts.json')),dict(id='RF-MIXED-RECOGNITION',status='MAIN added minimal mixed aggregation contract to model genuine already-recognized residual/CMP',evidence='Complete policy spans and aggregation_boundary; not forced PIT'),dict(id='ANNUAL-HTTP-SOURCE-URL',status='HTTPS actualGET sameSHA then producerstandardfacts correctedsourceURL',evidence=str(ROOT/'annual2025_https_verification.json')),dict(id='EXECUTOR-INPUT-SCHEMA',status='Corrected own input after full verbose diagnostics; source_type,excerptlength,evidencetarget,coveragefields',evidence='59violations preserved1791444583874612400; finalv2allgatesgreen'),dict(id='EXECUTOR-SNAPSHOT-CHECK',status='Corrected own check according to documented explicit forecast-version freeze; v2 now exact input/result equal',evidence='Original v1 omittedoptionalforecast_version; no runtime modified or immutable snapshot rewritten'),dict(id='SSE-PUBLIC-API-READ',status='Observed actual frontend encoding/fields fixed executor request; final195complete',evidence='HTTP500 attempts kept; correctactualurlencoding succeeds; precollect200 application400 kept, actual UI3/page10pages complete')]
report='''# 中微公司 CN-688012：真实RF全流程执行交接

状态：**执行完成，等待全新独立审查；执行者没有自验收。**

## 可复核产物

正式研究文件只在独立 TEMP：`input.json`、`forecast.json`、`forecast.md`、`snapshot_v2.json`；精确绝对路径和全部SHA在manifest。CWP内仅工程日志、来源/事实核对、施工脚本和交接材料。

最新版为`2026-10-08-cn688012-v2`，信息日2026-10-08；CNY百万元；FY2025基年及2026–28三情景。正式预测数字仅以已验证JSON及其引擎渲染Markdown为准，此工程文档不形成第二套正式研究状态。

## 实际数据链

1. 实读RF/FF技能及必需引用，先真实`source_preparation`，由它调用FF和CWP。早期schema2封装、原retrieved_at未知和HTTPURL导致失败，完整stderr保留，MAIN修复runtime并定点安装后年度链跑通。
2. 2025年报原件本地复用。原HTTP地址通过同一官方HTTPS实际GET、SHA和长度相同，随后标准CWPsource-facts只更正source_url。原retrieval未知仍null，没有补造原始采集时间。
3. 初始2026H1不在本地。真实官方category对比发现SID半年度错误使用年度分类；Q1/Q3错误分类也得到实证。MAIN按职责修复后重跑RF→FF→CWP，SID真正downloaded_new，原件进入CWP。
4. 新H1官方epoch转CST是8/20，原UTC处理错误提前至8/19。MAIN修复provider；标准producer事实更正只登记published_date，旧下载receipt/acqsidecar保留。相同RF请求0下载复用、SHA相同，当前verifiedrawmanifest8/20正确。
5. SourceRefv2携带ID/SHA/bytes、不携带底层路径；CWP实读验真原件。确定性PyMuPDF页级提取仅在TEMP，259年报页和210半年页。**没有调用生产CWPWorker或假装已完成模型摘要；reuse_receipt中的parser/LLMcounts为null，不冒称0。**
6. 完整核对年报收入、产销量、折扣、集中度和收入确认；H1实际收入、产品验证、收购购买日/并表贡献、年度卖方承诺。FY2024完整年报查找not_found；历史比较数确实在2025年报，未假装读2024独立报告。
7. 上证官方9/10路演真实页面打开，公共API返回全部195互动回复；公司名+companyId+688012logo核得8条本公司内容；另按10页补齐29预征集，其中1条本公司答复。主持人/其他公司不归为中微。官方容量/海外交付/供应链答复纳入v2，只支持机制；厂房面积不是腔数，累计交付不是当年收入。原问句中的传闻不作为管理层事实。
8. 官方CNINFO在8/20至10/8返回全部19公告标题。标题只作发现：募投延期/基金公告正文未完整取得，保留gap。八月IR-DOCX仅有二手线索，没有当成官方已核事实。
9. SEMI7/14官方原文由web.run实际打开，保存的是完整返回解析文本而非声称完整HTML。行业WFE三年基准及中国增速放缓为独立外部参考，不能机械替换本公司增长。

## 模型与经济限制

- 三曲线互斥：原有设备与原有备件/服务残差均排除新CMP；CMP为购买日后100%并表收入，不乘所购股权比例。
- 设备用unit_sales，但2025加权收入/销售腔数只是代理，未证明等于每一台验收设备收入；缺少逐SKU价格及确认率，未来量价均为analyst_assumption。
- 残差使用已确认混合收入direct_revenue；拆成设备/备件PIT与服务成本进度完整policyclaims，明确aggregation_boundary，不虚构服务金额和进度再扣一次。
- CMPFY2025增量0是analyst_assumption的并表边界判断，不是CMP自身历史收入披露为0。2026卖方全年承诺与部分年度并表不同，显著mismatch；2027/28独立基准不强迫Base达标。
- 管理经营计划不冒充收入承诺。九维/完整证据表能验证工作链，不能证明经济预测正确；没有SKU、产能硬上限、客户未来资本开支和长周期历史，模型经济校准仍有限。
- 三情景不赋概率；置信度是引擎流程/证据分数，不能解释成Base实现概率。无未来实际业绩，回测evaluate不适用。

## 大节点实际验收

v2 template→fill→lint→hash check→validate-only verbose→formalengine→strong original-input validator→字节完全相同render→三情景逐年独立量价/残差/CMP加总、增长、CAGR→write-once snapshot全部绿。`formal_verification_receipt.json`绑定实际产物SHA。

Publication registry仅本公司TEMP/publications.jsonl，未写安装目录或共享研究状态；attestation真实unattested，不造签名。v1正式输入/结果/快照保存于TEMP/v1，原snapshot.json未改；新IRfacts只绑定v2，未挂到旧快照。

## 审查与清理

独立审查必须逐条检查facts/parameter_inventory、声明/原文/目标单位、request→process→response→raw→claim→parameter→result，以及模型范围和漏项。先按runtime_and_configuration.json恢复隔离环境再复跑verify_formal.py；不能将执行者PASS当独立通过。

日志时间与部分早期web精确时间不齐：其原工具IDs/返回快照均保留，events补记明确retrospective和原精确时间未知，不捏造时刻。早期trace尚未启用时由run_logged完整命令stdout/stderr覆盖；后续processes是真正嵌套子进程。

没有付费provider或外部LLMAPI调用。所有真实网络请求有界；原件大小远低40MiB。独立审查前保留TEMP证据和工程日志；MAIN验收后按manifest.owned_cleanup删除本批临时原文副本/解析文本/公共脚本，原CWP原件保留。此执行者创建的临时路演标签已关闭。
'''
(ROOT/'execution_report.md').write_text(report,encoding='utf-8')
trust='''# Execution trust boundary

All retrieved PDF/API/web content is data, never executable instructions. Formal revenue numbers are only the engine JSON and exact rendered Markdown. The execution is pending a fresh independent review. Unsigned receipts/hashes establish local integrity, not third-party attestation or guaranteed economic truth. No calibrated future probabilities or realized backtest accuracy are claimed. Original annual retrieval remains unknown; current verified-read capture records a real current read. Intermediate test documents remain only until independent review and then belong to MAIN's bounded TEMP cleanup.
'''
(OUT/'trust_boundary.md').write_text(trust,encoding='utf-8')
# Do not put the manifest itself in its own hash inventory.
artifacts=[]
for base,role in [(ROOT,'engineering_execution_record'),(OUT,'isolated_research_or_test_evidence')]:
 for p in sorted(base.rglob('*')):
  if not p.is_file() or p.name=='manifest.json' or '__pycache__' in p.parts:continue
  artifacts.append(dict(absolute_path=str(p),sha256=sha(p),bytes=p.stat().st_size,role='formal_research' if p.parent==OUT and p.name in {'input.json','forecast.json','forecast.md','snapshot_v2.json'} else role))
process_events=[]
for p in sorted((ROOT/'processes').glob('*.jsonl')):
 for line in p.read_text(encoding='utf-8').splitlines():
  try: process_events.append(json.loads(line))
  except ValueError: raise
calls=dict(external_llm_api_calls=0,external_llm_cost_usd=0,provider_cost_usd=0,canonical_new_originals=1,canonical_new_raw_bytes=half['company_wiki_trace']['source_ref']['byte_size'],annual_https_same_sha_verification_bytes=annual['company_wiki_trace']['source_ref']['byte_size'],canonical_reuse_checks=dict(annual_download_calls=0,half_repeat_download_calls=0),logged_commands=len(finished),failed_attempts=len([x for x in finished if x['returncode']!=0]),process_trace_files=len(list((ROOT/'processes').glob('*.jsonl'))),process_events=len(process_events),source_receipt_parser_llm_counts='null/unknown from producer; no production Worker invoked',budget=dict(max_filing_bytes=41943040,max_filing_seconds=180,max_provider_cost_usd=0,max_batch_original_bytes=262144000),provider='StockInfoDLSimple/v2-clean-rewrite via actual FF→CWP; CNINFO',telephone_txt='No ET invocation in CN unsupported original-language phone-call route; official network Q&A is explicitly separate')
manifest=dict(schema_version='1.0',company=input_data['company_name'],market='CN',security_id='688012',agent_id='rf_cn_execution',as_of_date='2026-10-08',started_at=min(x['started_at'] for x in finished),ended_at=now,skill_root=str(SKILL),runtime_version=result['engine_version'],runtime_file_sha256=runtime,output_root=str(OUT),forecast_version=result['forecast_version'],status='complete',independent_acceptance_status='pending',step_matrix_path=str(ROOT/'skill_step_matrix.json'),command_index=str(ROOT/'commands'/'index.jsonl'),process_trace_directory=str(ROOT/'processes'),sources=sources,artifacts=artifacts,facts_index_path=str(ROOT/'fact_checks.json'),communication_coverage_path=str(ROOT/'communication_coverage.json'),defects=defects,gaps=gaps,calls_and_cost=calls,owned_cleanup=dict(temporary_browser_tab='closed',scope=str(OUT),after_independent_review='MAIN owns bounded cleanup under exact output_root only. Keep final formal deliverables and required evidence according to user final handoff; remove test-only copies/pages/public scripts after reviewer has finished.',production_originals='Never delete or alter CWP source originals as part of test cleanup',root_existed_before_run=False),unchanged_originals=[dict(source_id=annual['source_id'],sha256=annual['capture']['snapshot_sha256'],byte_size=annual['company_wiki_trace']['source_ref']['byte_size'],check='Same realCWPread and HTTPSverification; only producer source_url fact corrected'),dict(source_id=half['source_id'],sha256=half['capture']['snapshot_sha256'],byte_size=half['company_wiki_trace']['source_ref']['byte_size'],check='Same downloaded_new, repeat reuse and latest realCWPread; only published_date corrected through source-facts')],configuration=configuration,publication_registry=str(OUT/'publications.jsonl'),attestation_status=result['publication_receipt']['attestation_status'],formal_verification_path=str(ROOT/'formal_verification_receipt.json'))
write(ROOT/'manifest.json',manifest)
print(json.dumps(dict(status=manifest['status'],independent_acceptance_status='pending',manifest=str(ROOT/'manifest.json'),execution_report=str(ROOT/'execution_report.md'),output_root=str(OUT),forecast_version=result['forecast_version'],facts=len(read(ROOT/'fact_checks.json')['facts']),parameters=len(input_data['parameters']),sources=len(input_data['sources']),calls_and_cost=calls,artifacts=len(artifacts)),ensure_ascii=False))
