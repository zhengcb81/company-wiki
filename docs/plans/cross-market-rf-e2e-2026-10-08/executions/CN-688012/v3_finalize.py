"""Engineering-only handoff; formal research remains isolated in TEMP."""
from pathlib import Path
import copy,datetime,hashlib,json,sys
ROOT=Path(__file__).resolve().parent
OLD=Path('C:/Users/郑曾波/AppData/Local/Temp/cwp-rf-e2e-20261008/CN-688012');OUT=OLD/'v3'
SKILL=Path('C:/Users/郑曾波/.agents/skills/revenue-forecast');REPO=Path('C:/Users/郑曾波/Projects/revenue-forecast')
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def dump(p,v):Path(p).write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
def sh(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
now=datetime.datetime.now(datetime.timezone.utc).isoformat();d=read(OUT/'input.json');r=read(OUT/'forecast.json')
verify=read(ROOT/'formal_verification_v3.json');repairs=read(ROOT/'v3_input_repair_receipt.json')
ann=read(ROOT/'announcements_v3_receipts.json');triage=read(ROOT/'announcement_triage_v3.json')
source={s['source_id']:s for s in d['sources']};params={p['parameter_id']:p for p in d['parameters']}
commands=[read(p) for p in (ROOT/'commands').glob('*v3-*.finish.json')]
# run_logged uses index.jsonl as its authoritative finish-event list.
index=[json.loads(line) for line in (ROOT/'commands/index.jsonl').read_text(encoding='utf-8').splitlines() if line.strip()]
commands=[x for x in index if x.get('event')=='finish' and x.get('label','').startswith('v3-')]
formal_labels=['v3-validate-final','v3-formal-engine-markdown','v3-immutable-snapshot','v3-strong-render-calc-snapshot-protection','v3-publication-registry-audit','v3-lint-final','v3-hashcheck-final']
for label in formal_labels:assert any(x.get('label')==label and x.get('returncode')==0 for x in commands),label
snap=read(OUT/'snapshot.json');assert snap['input_document']==d
for p in read(ROOT/'v3_protected_v2.json')['protected']:assert sh(p['path'])==p['sha256'],p
asset={d['sources'][0]['source_id']:str(OLD/'annual2025.pdf'),d['sources'][1]['source_id']:str(OLD/'half2026.pdf'),'semi_wfe_20260714':str(OLD/'semi_web_open_snapshot.json'),'amec_sse_results_qa_20260910':str(OLD/'roadshow_public_questions.json')}
asset.update({'amec_cninfo_'+x['announcement_id']:x['path'] for x in ann})
facts=[]
for c in d['evidence_claims']:
    p=params.get(c['target_id']);s=source[c['source_id']]
    facts.append(dict(claim_id=c['claim_id'],source_id=c['source_id'],source_url=s['url'],source_published_date=s['published_date'],source_artifact=asset[c['source_id']],source_snapshot_sha256=c['content_sha256'],capture_receipt_sha256=c['capture_receipt_sha256'],locator=c['locator'],excerpt=c['excerpt'],excerpt_sha256=c['excerpt_sha256'],target_type=c['target_type'],target_id=c['target_id'],support_type=c['support_type'],parameter_kind=p['kind'] if p else None,parameter_value=p['value'] if p else None,parameter_definition=p.get('definition') if p else None,parameter_rationale=p.get('rationale') if p else None,extracted_value=c.get('extracted_value'),unit=c.get('unit'),period=c.get('period'),verified_date=c['verified_date'],status='PASS exact original normalized substring and hash binding; semantic interpretation awaits independent reviewer',rationale_limit='Source context does not state future assumption numeric value' if c['support_type']=='rationale_support' else 'Original value/period/perimeter stated; compare according to target semantics',full_checked_context=repairs['full_context'].get(c['claim_id'],{}).get('full_checked_context',c['excerpt'])))
dump(ROOT/'fact_checks_v3.json',facts)
dump(ROOT/'communication_coverage_v3.json',dict(records=d['management_communication_coverage'],targets=d['management_targets'],announcement_triage_path=str(ROOT/'announcement_triage_v3.json'),remaining_gaps=verify['gaps']))
matrix=copy.deepcopy(read(ROOT/'skill_step_matrix.json'))
matrix.update(forecast_version=d['forecast_version'],output_root=str(OUT),status='PARTIAL: formal forecast complete; end-to-end Worker/IR gaps remain',independent_review_status='pending v3 closure review')
for step in matrix['steps']:
    step['artifacts']=[str(OUT/Path(p).name) if Path(p).name in ['input.json','forecast.json','forecast.md'] else p for p in step.get('artifacts',[])]
    step['artifacts']+= [str(ROOT/'repair_v3.json'),str(ROOT/'formal_verification_v3.json')]
    step['independent_review_status']='v2 reviewed PARTIAL; newv3 closure pending independent reviewer'
    if step['step']=='1A':step.update(status='PARTIAL',detail='Nine material original PDFs fully opened (eightcompany +onebroker), all19records honestlytriaged. Newlocal300000万元 maturitytarget enteredambiguous/mismatchgap. Exactincentivegrowth schedule remains unfetched; telephoneTXT/presentationoriginal unavailable. Checked categories do not prove no undiscovered target.')
    if step['step'] in ['0','4','6A']:step['detail']='v3 narrows residual to unsplit non-equipment fallback with unknown composition/calibration; explicit assumptions and allocations, no all-aftermarket or fake repeat-purchase mechanism. SEMI fullperiod/China contrary, customer39.99/22.15, TSV and correctrisk branches bound.'
    if step['step']=='3':step['detail']='Original v2 RF→FF→CWP H1 realdownload andzero-downloadreuse remainevidence. v3 standardappend-only URLfact then realRF→FF→CWPcorrectedURL zero-downloadreuse/newverifiedcapture. NineauxiliarySIDPDFs are notFFpipelineingestion orWorker.'
    if step['step']=='10':step.update(status='PASS',detail='Finalactual lint/hashcheck/validate-only/formalengine/stronginput-required/render/106claim originalchecks/9 arithmeticrows/registryauditallgreen. These are execution checks, independentacceptancepending.')
    if step['step']=='11':step.update(status='PASS_FROZEN_FUTURE',detail='Newv3 immutable snapshot created once, validated againstexactinput/economicresult. Registryisolated. Oldv2bytesunchanged. Forecastfutureactuals unavailable, evaluateN/A; attestationrealunattested.')
matrix['upstream_processing_status']={'CWPWorker':'BLOCKED/not_run; deterministic isolatedPDF text is not canonicalWorker narrative','IR_original_DOCX':'BLOCKED/not_obtained; networkQ&A registered separately','ET_CN_telephone_TXT':'not_available/not_obtained; no fake ET acquisition success'}
dump(ROOT/'skill_step_matrix_v3.json',matrix)
findings=[
dict(id='CN01',status='REPAIRED_PENDING_INDEPENDENT_REVIEW',changes='Aftermarket renamedNonEquipmentResidual; 9futureparameter claims+root reboundactualannual53 withadditional48/65,H1p19/p23 businesscontext. Policyretained onlyrecognition. Residualcomposition/renewalunknown; direct_revenue fallback, uncertainpersistence, suitablefalsifiers, nine-dimensionnarrowing. Numerics transparentlyretained.',artifacts=['v3_build_input.py','fact_checks_v3.json','v3_input_repair_receipt.json']),
dict(id='CN02',status='REPAIRED_PENDING_INDEPENDENT_REVIEW',changes='CustomerA39.99/22.15 completeannualp219boundall9futureunit assumptions. SEMI2027/28 completeclaim+China2026moderationcontrarybothEquipmentroots. FullTSVH1p16packagingclaim supplementsfilm. Fourrisknodes reboundactualH1p32supply/p33tech+merger withspecificscope; HQdelaycompany4additionalcontrary. No quantifiedclientcapexclaim.',artifacts=['fact_checks_v3.json','formal_verification_v3.json']),
dict(id='CN03',status='REPAIRED_WITH_VISIBLE_GAPS_PENDING_INDEPENDENT_REVIEW',changes='All19entries individualtriage. 9originalPDFs actualexistingSIDfreeboundedfetch; full8company+onebrokerreview. Company1225482911distinguishedbroker1225482916; fund/loancash neverrevenue. Discovered1225482894local-salesmaturity300000万元targetregisteredcapacity_plan/ambiguous/mismatch/unmodeled. HQfulluse2027-12 updates9unitrationales+2contrarynodes. 1225482917expectedrelatedsalesauthorization not guaranteed recognizedtarget/internalelimination. 2880incentivegrowthconditionsmention remainsgapasnumeric/year scheduleunobtained.',artifacts=['announcement_triage_v3.json','announcements_v3_receipts.json','communication_coverage_v3.json']),
dict(id='CN04',status='REPAIRED_PENDING_INDEPENDENT_REVIEW',changes='IndependentactualHTTPsameSHAPDFreceipt usedstandardCWPsource-facts append-onlysource_url correctionto8/20statictransport; subsequent realRF/FF/CWP verifiedrawreuse returnedcorrectpubdate/URL,newcapture,sameSHA,0download. Raw,oldsidecar,oldacquisitionreceipt andv2protectedbytespreserved.',artifacts=['requests/v3_half_source_url_fact.json','commands/1791448083706980100-v3-half-append-only-url-source-facts.stdout.txt','commands/1791448098298712100-v3-half2026-corrected-url-reuse.stdout.txt'])]
repair=dict(schema_version='1.0',company='CN-688012',agent_id='rf_cn_execution',timestamp_utc=now,status='PARTIAL',scope='One bounded v3 closure repair of independentCN01-04; not independent acceptance',findings=findings,remaining_gaps=verify['gaps'],formal_check_labels=formal_labels,claims_checked=verify['claims_count'],announcement_originals=9,announcement_response_bytes=sum(x['usage']['response_bytes'] for x in ann),provider_cost_usd='0',external_llm_calls=0,output_root=str(OUT),old_v2_protected=read(ROOT/'v3_protected_v2.json')['protected'],shared_mutation='Only authorized standardappend-only CWPsource_urlfact; no sharedcode/config/install/Git/Dayu changes',future_backtest='NOT_APPLICABLE: futureactualsunknown',publication_attestation='unattested',publication_registry=str(OUT/'publications.jsonl'))
dump(ROOT/'repair_v3.json',repair)
(ROOT/'repair_v3.md').write_text('''# CN-688012 v3 修复交接

状态：**PARTIAL，正式预测已完成，等待原独立审查者复查 CN01–04 变更闭包**。

## 修复范围

- CN01：把全部残差称为售后的错误解释取消。正式分段改为 NonEquipmentResidual，1857.63826811m 只是集团总收入减去四舍五入的专用设备收入。九个未来金额仍为分析者假设；年度48/53/65及半年19/23真实业务上下文已绑定，收入确认政策只支持会计时点。没有编造设备存量、续约率或量价机制。
- CN02：客户A 39.99%/22.15%来自年报219完整原文，绑定九个未来验收腔假设；SEMI2027/28 21.8%/14.1%与中国2026增长放缓分别绑定。TSV先进封装原文补齐。四个风险节点各用真实适用风险，不再把半年33泛指客户资本开支或全部交期。
- CN03：全部19条公告分别写明重要性和原文是否打开。通过现有SID工具实际获取9份全文，八份公司公告、一份保荐人意见；并不冒充FF→CWP入库。资金/借款/资本开支不等同营业收入。1225482911公司正文确认总部研发完整投用延到2027年12月，九个验收腔假设及设备反证明确采用该约束背景。1225482894新发现达产后属地销售300000万元计划，因年期、年度/累计和集团外部收入边界不明登记为capacity_plan+ambiguous+mismatch+unmodeled_data_gap，未硬加收入。1225482917关联销售预计额度是交易授权，客户2/3是董事任职的外部关联法人，并不默认集团内收入抵销。1225482880提到激励计划收入增长考核，数字/期间原激励表未取得，明确保留缺口。
- CN04：用独立审查者真实重取同SHA的8月20日官方PDF收据，调用标准append-only source-facts改transport source_url。随后真实RF→FF→CWP再复用：日期8/20、URL8/20、原件SHA相同、零下载，新capture进入v3。没有直接写数据库、改原raw/旧sidecar/旧acquisition receipt。

## 正式检验

最终lint、hashcheck、validate-only、engine/Markdown、强input-required验证、逐条106个claim原文匹配、9行独立公式/增长率/CAGR/增量、非交叉/H1下限、immutable snapshot与registry audit全绿。新文件均在独立TEMP/CN-688012/v3。原v2 input/forecast/md/snapshot_v2与原manifest全部SHA及字节数不变。原命令日志继续追加，旧manifest封存时的日志前缀不被重写；不要把新增日志误算旧主产物变动。

## 真实未完成项

CWP Worker没有运行（仍BLOCKED/not_run），孤立PDF解析不算canonical narrative处理；IR原DOCX/投资者PPT、A股电话会TXT未取得。未拆分残差的数量校准未知。二期销售计划年期/口径不明。股权激励增长考核原schedule未取得。模型绿色不能把上述项改成端到端PASS。未来实际业绩未知，backtest evaluate不适用；真实签名状态仍unattested。

## 审查入口

先读repair_v3.json与manifest_v3.json，再查fact_checks_v3.json、announcement_triage_v3.json、formal_verification_v3.json及commands实际收据；只复查本次变更及其依赖闭包，保留v2独立原审查。正式研究文件在manifest_v3指向的TEMP路径；共享PWF/其他公司目录/Dayu保持。
''',encoding='utf-8')
runtimefiles=['scripts/revenue_forecast.py','scripts/revenue_core.py','scripts/revenue_report.py','scripts/revenue_backtest.py','scripts/revenue_engine.py','scripts/revenue_constants.py','scripts/revenue_segments.py','scripts/revenue_sources.py','scripts/revenue_parameters.py','scripts/revenue_growth_drivers.py','scripts/source_preparation.py','scripts/company_wiki_source_v2.py','scripts/publication_registry.py','scripts/lint_input.py','scripts/fix_hashes.py']
runtime=[]
for rel in runtimefiles:
    path=SKILL/rel
    if path.exists():runtime.append(dict(path=str(path),sha256=sh(path),repo_path=str(REPO/rel),repo_sha256=sh(REPO/rel) if (REPO/rel).exists() else None,installed_repo_equal=(sh(path)==sh(REPO/rel)) if (REPO/rel).exists() else None))
dump(ROOT/'runtime_v3.json',dict(skill_root=str(SKILL),engine_version=r['engine_version'],runtime_files=runtime,environment={'REVENUE_PUBLICATION_REGISTRY':str(OUT/'publications.jsonl'),'CWP_AUDIT_PROCESS_DIR':str(ROOT/'processes'),'PYTHONPATH_prepend':str(ROOT.parents[1]/'process_trace')},configuration_changes='None; subprocessonlyenvironment'))
dump(ROOT/'manifest_v3_unsealed.json',dict(schema_version='1.0',company='中微公司',market='CN',security_id='688012',agent_id='rf_cn_execution',as_of_date='2026-10-08',ended_at=now,skill_root=str(SKILL),runtime_version=r['engine_version'],runtime_file_sha256=runtime,output_root=str(OUT),status='partial',formal_forecast_status='complete and execution validated; independent closure pending',step_matrix_path=str(ROOT/'skill_step_matrix_v3.json'),command_index=str(ROOT/'commands/index.jsonl'),sources=[dict(s,original_artifact=asset[s['source_id']]) for s in d['sources']],artifacts=[],facts_index_path=str(ROOT/'fact_checks_v3.json'),communication_coverage_path=str(ROOT/'communication_coverage_v3.json'),repair_path=str(ROOT/'repair_v3.json'),gaps=verify['gaps'],calls_and_cost={'v3_auxiliary_sid_download_calls':9,'v3_provider_response_bytes':repair['announcement_response_bytes'],'v3_provider_cost_usd':'0','v3_external_llm_calls':0,'v3_ff_cwp_half_reuse_download_calls':0,'parser':'actualdeterministicfitzoriginalPDF; noWorker','limits':{'each_download_bytes':41943040,'each_download_seconds':180,'provider_cost':'0','all_raw_bytes':262144000}},owned_cleanup='No test downloads removed yet: isolated original PDFs are audit evidence; never canonically ingested by this auxiliary research. They may be cleaned after review per MAIN preserving engineering SHA receipts. No shared-temp deletion.',unchanged_originals=verify['old_v2_artifacts_protected'],frozen_v2_manifest_sha256=sh(ROOT/'manifest.json'),remaining_review='OriginalCNindependentreviewer: CN01-04 closure only'))
event=dict(timestamp_utc=now,agent_id='rf_cn_execution',step='v3_handoff',action='Close boundedrepair batch and prepare independent closure review',tool='v3_finalize.py',input_summary='CN01-04 original review findings; no sharedcode changes',artifacts=[str(ROOT/'repair_v3.json'),str(ROOT/'manifest_v3_unsealed.json')],outcome='formalworkflowgreen; truthful end-to-end PARTIAL',error=None)
with (ROOT/'events.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps(event,ensure_ascii=False)+'\n')
print(json.dumps({'status':'PARTIAL','claims':len(facts),'targets':len(d['management_targets']),'pdf_originals':len(ann),'bytes':repair['announcement_response_bytes'],'formal_checks':'green','old_v2_unchanged':True,'artifacts':str(ROOT)},ensure_ascii=False))
