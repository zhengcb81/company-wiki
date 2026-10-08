"""Finalize the isolated MSFT engineering handoff without modifying frozen research."""
from lane_tools import LANE, OUTPUT, RF, event, write
from pathlib import Path
import argparse, datetime, hashlib, json, os, subprocess, sys

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def load(path):
    return json.loads(path.read_text(encoding='utf-8'))

def checked_commands():
    env=dict(os.environ, PYTHONUTF8='1', PYTHONIOENCODING='utf-8', REVENUE_PUBLICATION_REGISTRY=str(OUTPUT/'publications.jsonl'), CWP_AUDIT_PROCESS_DIR=str(LANE/'processes'))
    env['PYTHONPATH']=str(LANE.parents[1]/'process_trace')+os.pathsep+env.get('PYTHONPATH','')
    before={name:sha(OUTPUT/name) for name in ['input.json','forecast.json','forecast.md','snapshot.json']}
    results=[]
    commands=[('lint', [str(RF/'scripts/lint_input.py'),str(OUTPUT/'input.json')],0), ('hash_check',[str(RF/'scripts/fix_hashes.py'),str(OUTPUT/'input.json'),'--check'],0), ('frozen_validate_only',[str(RF/'scripts/revenue_forecast.py'),str(OUTPUT/'input.json'),'--validate-only','--verbose'],0), ('immutable_duplicate',[str(RF/'scripts/revenue_backtest.py'),'create',str(OUTPUT/'input.json'),'--version','2026-10-08-MSFT-v1','--output',str(OUTPUT/'snapshot.json')],2)]
    for label,args,expected in commands:
        proc=subprocess.run([sys.executable,'-X','utf8',*args],env=env,cwd=RF,capture_output=True,timeout=70)
        (LANE/(label+'_stdout.txt')).write_bytes(proc.stdout)
        (LANE/(label+'_stderr.txt')).write_bytes(proc.stderr)
        ok=proc.returncode==expected if label!='immutable_duplicate' else proc.returncode!=0 and sha(OUTPUT/'snapshot.json')==before['snapshot.json']
        results.append(dict(label=label,command=[sys.executable,'-X','utf8',*args],returncode=proc.returncode,expected_nonzero=label=='immutable_duplicate',passed=ok,stdout=str(LANE/(label+'_stdout.txt')),stderr=str(LANE/(label+'_stderr.txt'))))
        event('11' if label=='immutable_duplicate' else '10',label,tool='installed RF CLI',outcome='PASS' if ok else 'FAIL',returncode=proc.returncode,command=args)
    after={name:sha(OUTPUT/name) for name in before}
    ok=before==after and all(r['passed'] for r in results)
    write(LANE/'preflight_and_immutability.json',dict(results=results,before_sha256=before,after_sha256=after,frozen_artifacts_unchanged=before==after,status='PASS' if ok else 'FAIL'))
    print(json.dumps(dict(status='PASS' if ok else 'FAIL',checks=results),ensure_ascii=False))
    return 0 if ok else 1

def handoff():
    data=load(OUTPUT/'input.json');result=load(OUTPUT/'forecast.json')
    sources={s['source_id']:s for s in data['sources']}
    claims={c['claim_id']:c for c in data['evidence_claims']}
    factdoc=load(LANE/'fact_checks.json')
    facts=factdoc['parameters'] if isinstance(factdoc,dict) else factdoc
    for row in facts:
        claim=claims[row['claim_id']];source=sources[claim['source_id']]
        row.update(excerpt=claim['excerpt'],excerpt_sha256=claim['excerpt_sha256'],source_sha256=claim['content_sha256'],published_date=source['published_date'],verified_date=claim['verified_date'],source_url=source['url'],source_artifact=source['capture']['tool_call_id'],target_type=claim['target_type'],support_type=claim['support_type'],verification_scope='Executor checked direction/context or table cell; independent reviewer must reopen every claim. A supported analyst assumption is never a reported forecast.')
        row['excerpt_form']='normalized_visual_table_row_and_annual_cell' if claim['source_id']=='src_presentation' else 'checked_text_excerpt'
    existing={r['claim_id'] for r in facts}
    for cid,claim in claims.items():
        if cid in existing:continue
        source=sources[claim['source_id']]
        facts.append(dict(claim_id=cid,target_id=claim['target_id'],target_type=claim['target_type'],support_type=claim['support_type'],value=claim.get('extracted_value'),unit=claim.get('unit'),period=claim.get('period'),source_id=claim['source_id'],source_url=source['url'],source_artifact=source['capture']['tool_call_id'],source_sha256=claim['content_sha256'],locator=claim['locator'],excerpt=claim['excerpt'],excerpt_sha256=claim['excerpt_sha256'],published_date=source['published_date'],verified_date=claim['verified_date'],status='executor_checked_context_independent_review_pending'))
    for row in facts:
        source=sources[row['source_id']]
        row['source_bytes_path']=str(OUTPUT/'fy2025_verified_raw.html') if row['source_id'].startswith('urn:company-wiki:') else source['capture']['tool_call_id']
        row['checked_excerpt_is_contiguous_quote']=False if row['source_id']=='src_presentation' else None
    write(LANE/'fact_checks.json',facts)

    call_lines=(OUTPUT/'call.txt').read_text(encoding='utf-8').splitlines()
    qualitative=[]
    # Retain complete original lines. Never turn linguistic growth ranges into invented point estimates.
    target_lines=[108,205,255,256,257,258,264,268,269,270,271,272,274,275,278,279]
    for line in target_lines:
        text=call_lines[line-1]
        qualitative.append(dict(source_id='src_call',source_sha256=sources['src_call']['capture']['snapshot_sha256'],source_url=sources['src_call']['url'],published_date='2026-07-29',locator=f'Complete official call, call.txt line {line}',exact_wording=text,period='FY2027Q1' if line>=264 else 'FY2027' if line!=108 else 'two years (exact terminal date not stated)',treatment='qualitative_context_or_explicit_data_gap',normalization='No invented numeric midpoint. Quarterly/as-reported guidance must be reconciled to September2 restatement.',formal_numeric_ledger_coverage='partial: numeric-only schema cannot represent all qualitative statements honestly'))
    qualitative.append(dict(source_id='src_presentation',source_sha256=sources['src_presentation']['capture']['snapshot_sha256'],locator='slides20-21/image20.png and image21.png',published_date='2026-09-02',period='FY2027Q1',exact_wording='Latest restated quarter outlook: licensing low-single decline; industry solutions cloud high-single growth; search exTAC mid-to-high-single growth; Xbox content/services mid-single decline and hardware decline; Windows OEM/devices low20s decline.',excerpt_form='visual transcription/normalized summary; reopen original slide for exact wording',treatment='Reclassification updates supersede old-quarter perimeter; not an annual extrapolation.'))
    coverage=dict(schema_version='1.0',as_of_date='2026-10-08',formal_categories=data['official_communication_coverage'] if 'official_communication_coverage' in data else data.get('management_communication_coverage'),latest_filing_semantics='FY2026 annual filing exists in official SEC listing. not_available in input means bounded acquisition failed, NOT unpublished or nonexistent.',all_presentation_slides_read=dict(method='view_image by execution agent',slide_count=22,source_sha256=sources['src_presentation']['capture']['snapshot_sha256'],images=[str(OUTPUT/'ppt_images'/f'image{i}.png') for i in range(1,23)],ocr_performed=False,text_extraction_empty=True,critical_slides=[4,5,7,8,9,11,13,15,16,17,18,20,21]),complete_call_read=dict(text=str(OUTPUT/'call.txt'),source=str(OUTPUT/'call.html'),sha256=sources['src_call']['capture']['snapshot_sha256'],includes='CEO, CFO full-year/quarter guidance and all Q&A through final IR close'),numeric_targets=data['management_targets'],qualitative_targets=qualitative,future_excluded=dict(event='FY2027Q1 earnings October28 2026',reason='After as_of October8; only guidance available'),semantic_status='PARTIAL: material qualitative targets visible here but not fully expressible in formal numeric target ledger')
    write(LANE/'communication_coverage.json',coverage)
    (LANE/'communication_coverage.md').write_text('''# MSFT 官方沟通覆盖与口径边界

正式 input 的六类沟通覆盖必须结合 communication_coverage.json 阅读。

- FY2026 年报已在官方 SEC filing listing 出现；实际 FF→CWP ensure 下载失败。`not_available` 表示本次未取得，不能解释成公司没有发布。
- 七月29日官方业绩新闻、完整电话会和Q&A已读取，原语言留档。官方网页不是 ET 抓取成功的替代证明。
- 九月2日 FY27 presentation 共22张全部用 view_image 读取；都是嵌入图片，XML提取为空，没有声称OCR成功。关键数据见15–18页，季度调整口径20–21页。
- FY27改为 Agents and Infra、Devices and Consumer 两大板块；八条互斥产品收入用于经济模型，同时映射到这两大披露板块。旧三个分部不得与新口径混加。
- 正式数值目标11项；定性及旧季度口径全部在 JSON 旁表逐段记录。季度数据不乘4；constant currency不视为reported growth；double-digit只是语言下界，不是精确管理层点估计。
- 没有声称管理目标语义完整闭环；numeric-only运行时限制须由独立审查与MAIN裁定。Windows/Xbox等路径是独立分析假设，不能假称管理层承诺。
- Microsoft Cloud收入覆盖多个产品；RPO是存量；paid seats是期末量；AWS run-rate不是年度确认收入，均不另加到收入总额。
- 九月25/28及十月1战略、产品、领导层变化已真实打开。预览、用户量、TAM不能直接换算签约收入。十月28日结果在as-of之后，明确排除。
''',encoding='utf-8')

    # Exact operating observations and accounting pitfalls, separate from parameters.
    operation_lines=[101,102,103,108,230,231,236,243,247,248,264,274]
    ops=[]
    for line in operation_lines:
        ops.append(dict(source_id='src_call',source_sha256=sources['src_call']['capture']['snapshot_sha256'],locator=f'call.txt line {line}',exact_wording=call_lines[line-1],unit_and_date='Use original statement units; annual/quarter/period-end scope is explicit in surrounding call.',check='Direct official text retained; not an additive revenue input',publication_date='2026-07-29'))
    write(LANE/'operating_fact_checks.json',dict(observations=ops,boundaries=['Cloud overlaps Azure/M365; not a fourth stream','RPO678B stock and 2.3-year duration are not annual recognized revenue','Over30million paid Copilot seats are period-end, not annual average','Old Azure annual100B is actual annual revenue, not run-rate; use new restated101938','AWS annualized169B is a peer run-rate; not a Microsoft input','Preview launches and unmonetized developer/user counts are not sales'],independent_review_pending=True))

    trust='''# Trust boundary — MSFT as of 2026-10-08

The installed RF strong input-required validator, same-JSON renderer, independent per-stream arithmetic and snapshot fingerprint checks passed. These establish structural contracts, local bytes/hashes and deterministic input-output reproduction. They do not establish economic accuracy or complete management-target semantics.

No host signer was configured. Publication attestation remains `unattested`; local source host receipts are unsigned. No signer was invented. Actual command/process logs and retained web-tool responses are available for independent review, but no cryptographic host attestation proves URLs, search exhaustiveness or the agent's reading judgments.

The FY2025 CWP SourceRef v2 read verifies original bytes and preserves unknown original retrieved_at/provenance. Auxiliary official HTML/PPT captures live in isolated TEMP; retained multi-view blog response hashes bind the tool output, not separately downloaded blog HTML. PPT row/cell excerpts are visual table transcriptions, not contiguous prose quotations.

Formal v1 is technically emitted and frozen, but the overall acceptance remains PARTIAL: latest FY2026 regulated filing acquisition failed, production CWP selective narrative processing of SEC HTML did not run, ET free FMP entitlement prevented a fetched transcript, and qualitative/quarterly targets lack complete formal schema representation. Do not certify those missing links from green model tests.

All growth scenarios are analyst assumptions with direct_growth fallback and limited independent triangulation. Confidence is workflow/evidence quality, never outcome probability. No future actuals or historical out-of-sample accuracy was fabricated. Independent reviewer acceptance is pending.
'''
    (OUTPUT/'TRUST_BOUNDARY.md').write_text(trust,encoding='utf-8')

    entries=[
      ('0','complete','Nine dimensions; eight modeled and policy gap','input.json:research_coverage'),
      ('1','complete','Identity/date/currency/FY/version frozen; sources after October8 excluded','input.json; snapshot.json'),
      ('1A','partial','Full call, release,22-slide presentation and recent strategy; latest annual download failed and qualitative target runtime gap','communication_coverage.json'),
      ('1B','partial','AWS directional independent reference, company counterevidence; non-cloud roots have limited triangulation','input.json:growth_driver_tree; aws.html'),
      ('2','complete','FY24/25/26 annual total and FY25/26 restated eight-stream history reconciled','input.json:historical_revenue; image15/16/17.png'),
      ('3','partial','RF→FF→CWP existingFY24/25 reuse and actual raw read succeed; newFY26 ensure and ET fail; HTML canonical narrative not run','request_*response/stderr; fy2025_source_read_receipt.json; html_temporary_parse_receipt.json; et_*response.json'),
      ('4','complete_with_fallback','Eight mutually exclusive economic streams map to two FY27 reporting groups; all direct_growth openly fallback','input.json:segments; reporting_groups.json'),
      ('5','partial','Recognized annual aggregate; honest mixed boundaries, no RPO acceleration; FY25 policy may be superseded by unavailable FY26 filing','input.json:recognition; fy2025_consumer_temporary_text.txt'),
      ('6','complete_with_assumptions','Three annual paths perstream; all future rates explicit conditional analyst assumptions, no probabilities','input.json:parameters; fact_checks.json'),
      ('6A','complete_with_limitations','Four roots/leading indicators/falsifiers/counterevidence; attribution allocation, not proved causality','input.json:growth_driver_tree'),
      ('7','complete','Perstream then two reporting groups then company; no duplicated cloud or RPO; signed company adjustment zero','independent_arithmetic_and_groups.json'),
      ('8','complete_with_limitations','Eight unique firstyear base growth shocks; later years not comprehensively shocked; theme analysis not requested','input.json:sensitivity_tests; forecast.json'),
      ('9','complete','Low evidence/workflow score; explicit model and historical accuracy credit zero; not probability','forecast.json:confidence'),
      ('10','complete_technical','Actual template/lint/hashcheck/validate-only/formal/strong/render and independent arithmetic; semantic acceptance separate','formal_validation.json; preflight_and_immutability.json; commands/index.jsonl'),
      ('11','complete','Actual immutable v1 snapshot before FY27+actuals; duplicate-write rejected; future actual evaluate N/A','snapshot.json; preflight_and_immutability.json')]
    write(LANE/'skill_step_matrix.json',dict(schema_version='1.0',status='partial',steps=[dict(step=s,status=status,performed=desc,evidence=ev) for s,status,desc,ev in entries],never_performed=['Successful downloaded_new/repeat newfiling zero-download','CWP canonical selective narrative for SEC HTML','Successful FF→ET fetched TXT/import','Future actual backtest evaluation'],independent_review='pending'))

    finalhash={}
    for rel in ['SKILL.md','scripts/revenue_core.py','scripts/revenue_forecast.py','scripts/source_preparation.py','scripts/company_wiki_source.py','scripts/company_wiki_source_v2.py','scripts/company_wiki_source_reader_v2.py','scripts/contracts/constants.py','scripts/forecast/segments.py','scripts/revenue_backtest.py','scripts/revenue_report.py']:
        ins=RF/rel;repo=Path('C:/Users/郑曾波/Projects/revenue-forecast')/rel
        finalhash[rel]=dict(installed_sha256=sha(ins),repo_sha256=sha(repo) if repo.exists() else None,same=repo.exists() and ins.read_bytes()==repo.read_bytes())
    write(LANE/'runtime_hashes_final.json',finalhash)
    defects=[dict(id='US-FY26-ENSURE',status='unresolved',impact='No downloaded_new; original missing latest filing; repeat newfile test unavailable',evidence=str(LANE/'request_fy2026_fetch_legacy_stderr.txt')),dict(id='US-HTML-NARRATIVE',status='unresolved',impact='CWP canonical selective parser did not process text/html; BS4 temporary parse is not narrative Worker'),dict(id='US-ET-FMP',status='entitlement_required',impact='FMP metadata discovery unsupported and exact fetch entitlement denied; no translated or imported TXT'),dict(id='US-QUALITATIVE-TARGETS',status='semantic_gap',impact='11 numeric targets do not fully represent material qualitative targets; sidecar is explicit, not a formal gate waiver'),dict(id='RF-V2-ENVELOPE-RAW-TIMESTAMPS',status='fixed_by_MAIN',impact='True schema2 reuse now succeeds; unknown original retrieved_at preserved'),dict(id='RF-MIXED-AGGREGATE',status='fixed_by_MAIN',impact='Mixed recognized annual direct fallback supported; prevents fabricated OT/gross split')]
    (LANE/'execution_report.md').write_text('''# US-MSFT 执行交接

## 状态：PARTIAL；正式模型技术校验通过，供应链端到端未闭环

唯一研究目录见 manifest.output_root。v1 input、正式forecast JSON、同源MD、immutable snapshot已冻结；不写 CWP canonical研究state，不改共享代码/配置/Git，不改Dayu。独立审查尚未开始。

## 实际完成

- 按安装RF技能调用source_preparation，经过FF/CWP复用FY2024和FY2025；SourceRef v2实读FY2025 SEC HTML的8158067字节并SHA匹配。原manifest未知值保留，read_at是真正读时。
- MAIN修复schema2包络、旧retrieved_at校验及mixed年收入合同后重跑成功。初始失败原日志留存。最终运行文件SHA见runtime_hashes_final.json。
- 真实打开官方完整电话会、最新release、metrics、22张FY27重分类presentation、战略和重大公告、AWS独立category benchmark。最新新口径和旧季度口径有逐项说明，不把旧三个segment与新两组混用。
- 八条官方重述收入流核对两年；公司总额三年。运行三年三情景、九维、四因果根及反证、八敏感性、低置信度；所有增长是明确analyst assumption。
- 真正运行template builder、lint、hash --check、validate-only、forecast、strong input-required、同JSON render、独立算术、snapshot及拒绝重复覆盖。无未来actuals可回测，无伪造实绩。

## 未完成且不能冒称成功

1. FY2026已发布原年报真实经FF→CWP ensure下载失败，尚无downloaded_new receipt。失败stderr见manifest.defects；不能以官网辅助capture代替这条链。重复新下载零下载测试因此未完成。
2. FF companion不能声称已调度成功。独立ET exact FMP discovery不支持、fetch返回套餐权限限制。电话会HTML是官方阅读来源，不是ET原语言TXT集成成功。
3. CWP生产叙述链未处理SEC HTML；临时BS4文件明确temporary_only，未称Worker摘要/切片已跑。
4. 数值target ledger结构green，但完整定性管理目标在旁表；季度/constant currency不能强行年化。最新年报not_available实际是acquisition_failed，不能解读成未发布。独立审查应单列这些语义差距。

## 复核入口

从manifest→skill_step_matrix→commands/index.jsonl/processes→facts/communication→TEMP frozen inputs/outputs依次复核。formal_validation只证明结构/哈希/重算，TRUST_BOUNDARY明确无host signer、经济假设和来源搜索仍需独立审核。不要因模型green把供应链或目标语义标PASS。

## 费用、配置、清理

无外部LLM调用、无翻译、无付费升级。FMP密钥仅从既有配置继承，不记录值。下载预算40MiB/180s/$0未放宽。REVENUE_PUBLICATION_REGISTRY仅本进程指向独立TEMP，ET工具同样仅请求进程绑定。未清理审查所需TEMP；待MAIN验收后再按精确owned清单清理，不触碰原件。
''',encoding='utf-8')
    event('handoff','write complete executor handoff; independent acceptance pending',outcome='partial',artifacts=[str(LANE/'execution_report.md'),str(LANE/'skill_step_matrix.json'),str(LANE/'communication_coverage.json'),str(OUTPUT/'TRUST_BOUNDARY.md')])
    commandrows=[json.loads(x) for x in (LANE/'commands/index.jsonl').read_text(encoding='utf-8').splitlines()]
    events=[json.loads(x) for x in (LANE/'events.jsonl').read_text(encoding='utf-8').splitlines()]
    processfiles=list((LANE/'processes').glob('*.jsonl'))
    artifactfiles=[p for p in LANE.iterdir() if p.is_file() and p.name!='manifest.json']+list(OUTPUT.glob('*'))
    artifacts=[dict(absolute_path=str(p.resolve()),sha256=sha(p),bytes=p.stat().st_size,role='isolated_research' if p.parent==OUTPUT else 'engineering_execution') for p in artifactfiles if p.is_file()]
    sourced=[]
    for year in [2024,2025]:
        path=LANE/f'request_fy{year}_reuse_response.json';resp=load(path);trace=resp['company_wiki_trace'];manifest=trace['source_manifest'];ref=trace['source_ref']
        sourced.append(dict(source_id=ref['source_id'],document_id=ref['document_id'],sha256=ref['content_sha256'],bytes=ref['byte_size'],published_date=resp['published_date'],request_path=str(LANE/f'request_fy{year}_reuse.json'),response_path=str(path),resolution_outcome='reused_existing',downloads=0,provider=manifest.get('provider'),mime_type=ref['mime_type'],original_retrieved_at=manifest.get('retrieved_at'),read_at=trace['read_receipt']['read_at'],provenance_unknowns=[k for k,v in manifest.items() if v is None]))
    for s in data['sources'][1:]:
        sourced.append(dict(source_id=s['source_id'],sha256=s['capture']['snapshot_sha256'],bytes=Path(s['capture']['tool_call_id']).stat().st_size,published_date=s['published_date'],request_path=None,response_path=s['capture']['tool_call_id'],resolution_outcome='ancillary_official_source_capture_not_regulatory_acquisition',downloads=None,provider=s['publisher'],url=s['url']))
    initial=load(LANE/'initial_context.json')
    manifest=dict(schema_version='1.0',company='Microsoft',market='US',security_id='MSFT',agent_id='/root/rf_us_execution',as_of_date='2026-10-08',started_at=initial['started_at'],ended_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),skill_root=str(RF),runtime_version='4.1.0',runtime_file_sha256=finalhash,output_root=str(OUTPUT),status='partial',formal_technical_status='PASS',independent_review_status='pending',step_matrix_path=str(LANE/'skill_step_matrix.json'),command_index=str(LANE/'commands/index.jsonl'),process_trace_dir=str(LANE/'processes'),command_finish_count=sum(r['event']=='finish' for r in commandrows),command_failure_count=sum(r['event']=='finish' and r.get('returncode')!=0 for r in commandrows),process_trace_file_count=len(processfiles),event_count=len(events),sources=sourced,artifacts=artifacts,facts_index_path=str(LANE/'fact_checks.json'),communication_coverage_path=str(LANE/'communication_coverage.json'),operating_facts_path=str(LANE/'operating_fact_checks.json'),defects=defects,gaps=data['data_gaps'],calls_and_cost=dict(external_llm_calls=0,external_llm_tokens=0,external_llm_cost_usd=0,provider_paid_upgrade=False,et_component_discover_attempts=1,et_component_fetch_attempts=1,et_provider_http_count=None,et_note='Discovery unsupported; exact standalone fetch mapped to FMP entitlement error. No HTTP instrumentation; do not infer total provider API usage from process count.',successful_regulatory_downloads=0,known_reuse_downloads=0,parser_calls_from_reuse_receipt=None,llm_calls_from_reuse_receipt=None,ancillary_captures='Captured HTML/PPT and web.run views counted by artifact receipts, not passed off as filings.'),owned_cleanup=dict(retained_for_independent_review=True,allowed_after_MAIN_acceptance=[str(OUTPUT)],production_cleanup_performed=False),unchanged_originals=dict(actions='read-only SourceRef raw read; no writes to original/CWP canonical directories',fy2025_actual_raw_sha256=sha(OUTPUT/'fy2025_verified_raw.html'),matches_producer=True,global_filesystem_unchanged_claim=False,inventory_verification='MAIN owns baseline/end inventory; executor does not infer all-store unchanged from single receipt'),configuration=dict(REVENUE_PUBLICATION_REGISTRY=str(OUTPUT/'publications.jsonl'),EARNINGS_TRANSCRIPTS_TOOL='C:/Users/郑曾波/Projects/earnings-transcripts/earnings-transcripts/transcript_tool.py',scope='task subprocess only; global environment/config unchanged'))
    write(LANE/'manifest.json',manifest)
    print(json.dumps(dict(status=manifest['status'],manifest=str(LANE/'manifest.json'),facts=len(facts),claims=len(claims),runtime_all_same=all(x['same'] for x in finalhash.values()),formal_input_sha256=sha(OUTPUT/'input.json')),ensure_ascii=False))
    return 0

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('action',choices=['checks','handoff']);args=ap.parse_args()
    sys.exit(checked_commands() if args.action=='checks' else handoff())
