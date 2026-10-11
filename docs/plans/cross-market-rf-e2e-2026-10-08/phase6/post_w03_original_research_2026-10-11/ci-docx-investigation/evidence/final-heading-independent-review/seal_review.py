"""Seal read-only review of already-completed tests; no test execution."""
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent
BASE = OUT.parent.parent
TREE = BASE.parents[5]

def digest(path):
    return sha256(path.read_bytes()).hexdigest()

def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))

probe = read(OUT/'probe-results.json')
impl = BASE/'evidence/docx-heading-implementation'
manifest = read(impl/'handoff-manifest.json')
integrity = []
for name, expected in manifest['source_files'].items():
    actual = digest(TREE/name)
    integrity.append({'path': str(TREE/name), 'expected': expected, 'actual': actual, 'status': 'PASS' if expected==actual else 'FAIL'})
for name, expected in manifest['evidence_files'].items():
    actual = digest(impl/name)
    integrity.append({'path': str(impl/name), 'expected': expected, 'actual': actual, 'status': 'PASS' if expected==actual else 'FAIL'})
public = BASE/'evidence/root-final-node'
old_receipt = read(public/'native-public-attempt1.json')
new_receipt = read(public/'docx-public-attempt2.json')
for name, receipt in [('native-public-attempt1',old_receipt), ('docx-public-attempt2',new_receipt)]:
    actual = digest(public/(name+'.log'))
    integrity.append({'path': str(public/(name+'.log')), 'expected': receipt['log_sha256'], 'actual': actual,
                     'status': 'PASS' if receipt['log_sha256']==actual else 'FAIL'})
log = (public/'docx-public-attempt2.log').read_text(encoding='utf-8-sig')
proof = json.loads(next(line.partition('DOCX-PUBLIC-HISTORY ')[2] for line in log.splitlines() if 'DOCX-PUBLIC-HISTORY ' in line))
source_after = {p:digest(TREE/p) for p in probe['source_after']}
test_path = TREE/'tests/integration/test_docx_parser_public_history.py'
checks = list(probe['checks'])
def check(name, condition, basis):
    checks.append({'id':name, 'status':'PASS' if condition else 'FAIL', 'basis':basis})
check('implementation_and_actual_log_integrity', all(row['status']=='PASS' for row in integrity), 'Recomputed source/evidence/log SHA256 against frozen implementation manifest and both ROOT receipts.')
check('review_source_matches_public_frozen_snapshot', source_after == probe['source_before'] == probe['source_after']
      and all(source_after[p]==h for p,h in new_receipt['source_before'].items())
      and new_receipt['source_before']==new_receipt['source_after'], 'All seven final runtime sources match ROOT public attempt2 before/after; replay.py and production catalog config unchanged independently.')
check('public_real_old_parser_and_new_parser', proof['old_parser']=='1.0.0' and proof['new_parser']=='1.1.0'
      and new_receipt['exit_code']==0 and '1 passed in 21.68s' in log,
      'Actual passing finite Worker/public read test checks each bundle parser_version, each EvidenceSpan parser_version and frozen generation_manifest parser component; old producer only selects runtime before processing.')
check('public_old_history_sql_manifest_budget_unchanged', proof['old_budget']=={'estimated_micro_usd':111,'tokens':92,'unknown_reservations':0,'unsettled_reservations':0},
      'Reviewed executed assertions: current resume has identical old items/budget/artifact reference/binding; both read-only SQLite iterdump tuples equal before resume. Source: test_docx_parser_public_history.py:118-126. Original saved artifacts/rows are never edited.')
check('public_two_actual_loopback_posts', proof['loopback_posts']==2 and all(x['exit_code']==0 for x in proof['actual_cli_calls'])
      and [x['run_id'] for x in proof['actual_cli_calls']]==['docx-old','docx-old','docx-current','docx-reuse'],
      'ThreadingHTTPServer listens at 127.0.0.1; do_POST records actual production Worker requests after real prompt checks, not fabricated HandlerResult. New run contributes second POST, old resume/reuse add none.')
check('public_new_generation_does_not_hit_old_cache', proof['old_reference']['artifact_version_id'] != proof['new_reference']['artifact_version_id']
      and proof['old_reference']['source_ref']==proof['new_reference']['source_ref'],
      'Same immutable source_ref, distinct old/new artifact version IDs; current bundle heading spans remain standalone, original locator replay verified through real public read.')
check('public_same_generation_reuse_zero_increment', proof['reuse_budget']=={'estimated_micro_usd':0,'tokens':0,'unknown_reservations':0,'unsettled_reservations':0}
      and proof['new_budget']['tokens']==92,
      'Executed reuse assertions retain exact new reference and count of two POSTs; zero incremental reuse tokens and synthetic charge. External provider/model fee is zero; two loopback runs record synthetic 111 micro-USD each.')
check('public_preserved_material_red_then_targeted_green', old_receipt['exit_code']==1 and new_receipt['exit_code']==0,
      'Original native-public attempt1 keeps 14 PASS/1 FAIL for actual bundle1.1 vs frozen1.0 mismatch; only failed public responsibility rerun after sole _normalization_parsers fix. No assertion weakening.')
check('source_native_worker_map_common_cause_fixed', source_after['src/company_wiki/automation/narrative_batch.py']=='a483d786d99a7bef8f4420ada7770260b147c8048a9c1dceb4813d2f7d880df9',
      'Read exact git diff: only _normalization_parsers expands its normalized MIME enumeration to existing shared NORMALIZED_MIME_TYPES including DOCX; recorded manifest.version and legacy fallback1.0 are preserved. Runtime passes this map to owning worker.')
check('public_owned_config_original_cleanup', new_receipt['basetemp_removed'] is True and '"removed": true' in log,
      'Executed fixture finally assertions compare all original bytes and tmp config before/after, closes catalog, removes owned temporary tree; actual CW-BASETEMP-CLEANUP confirms relocation cleanup. Production config independently SHA sealed.')
accepted = all(c['status']=='PASS' for c in checks)
files = [
    BASE/'task_plan.md', BASE/'DOCX_HEADING_CONTINUATION.md',
    BASE/'evidence/independent-review/review.json', BASE/'evidence/independent-review/review.md',
    impl/'IMPLEMENTATION.md', impl/'handoff-manifest.json',
    impl/'before.json', impl/'after.json',
    public/'native-public-attempt1.json', public/'native-public-attempt1.log',
    public/'docx-public-attempt2.json', public/'docx-public-attempt2.log',
    test_path, TREE/'tests/support/official_json_batch_fixture.py',
    TREE/'src/company_wiki/automation/narrative_formats.py',
    OUT/'probe.py', OUT/'probe-first.py', OUT/'probe-first-run.json', OUT/'probe-results.json',
    OUT/'own-noneligible-cell.docx', OUT/'own-inheritance-outline.docx',
]
report = {
    'schema_version':'independent-final-docx-heading-review/1',
    'observed_at':datetime.now(timezone.utc).isoformat(),
    'reviewer':'fresh independent child ci_docx_heading_final_review',
    'recommendation':'accepted_for_reviewed_scope' if accepted else 'changes_required',
    'scope':'Final targeted DOCX heading normalization/default1.1, legacy1.0 identity/replay, strict0.7.1 heading barrier, finite real public history/generation/worker-map proof. Previously accepted unrelated native/CI responsibilities are not reexecuted.',
    'source_tree':str(TREE), 'source_before':probe['source_before'], 'source_after':source_after,
    'source_unchanged':probe['source_before']==source_after,
    'codegraph_usage':'Canonical codegraph_context consulted first. Current native normalization symbols absent from old canonical index; inspected known source files directly. No init/reindex.',
    'checks':checks, 'material_findings':[] if accepted else [c for c in checks if c['status']=='FAIL'],
    'closed_prior_finding':'NATIVE-DOCX-HEADING-01: original c29c7c0d… now actual docx_heading/Heading1/level1 at original p=1 and no longer generic context.',
    'public_proof':proof, 'integrity':integrity,
    'read_materials':[{'path':str(p),'sha256':digest(p)} for p in files],
    'harness_history':[
        'Initial self probe attempted changing EvidenceSpan structured_value without updating its own canonical output/span IDs; constructor rejected before source replay. Self harness changed to recompute both identities so source metadata replay is actually tested. No source/saved artifact edit.',
        'Second self harness run hit Windows filename path length262 at creating independent-inheritance-outline-controls.docx; renamed new self fixture to own-inheritance-outline.docx. Existing c29c original bytes never rewritten.',
        'First completed probe had28 PASS/1 FAIL: generic New products received repeat customer orders. cell is not eligible under existing initial business policy; read-only comparison of frozen parser1.0 with selector0.7/0.7.1 both gives no selected cell. Original self input/probe/result preserved in own-noneligible-cell.docx/probe-first.py/probe-first-run.json. Self positive cell changed to established explicitly eligible operating-event wording; final29 PASS, no source behavior changed.',
    ],
    'operations':{'provider_calls':0,'external_model_calls':0,'new_external_fee':0,'source_edits':0,
      'production_config_edits':0,'saved_artifact_edits':0,'writes_limited_to':str(OUT),
      'sealed_execution_packages_run':False,'dayu_run':False,'commit_or_push':False},
    'limits':[
        'Did not rerun104/112 concentrated units, prior4 public cases or unrelated previously accepted native/CI responsibilities.',
        'Public evidence was independently read and SHA checked; the reviewer did not rerun E2E. SQL/binding equality basis is actual passing assertions in retained test/log; owned temporary SQL/database files were removed by the test fixture.',
        'New code HEAD is not yet published; no new-HEAD remote CI certification. Normal release/exact HEAD CI remains ROOT gate.',
    ],
}
(OUT/'review.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
md = f'''# 独立最终 DOCX 标题定点审查：{report['recommendation']}

审查时间：{report['observed_at']}。本次无 material 发现，关闭旧 NATIVE-DOCX-HEADING-01；接受所审解析、strict selector 和真实公共旧历史/新 generation 责任。新 HEAD 远端 CI 尚未执行，本报告不代签该发布门槛。

最小原件 SHA `c29c7c0d1a40da78cdf6215bb9675f27773b461af49d71f8e1877136d944702c` 原封读取。实际默认 DOCX `1.1.0` 将 Heading1 解析为 `docx_heading`，level1，原定位 `cwp-docx-body/1|p=1`；strict `0.7.1` 仅选择后续 qualifier，跨 heading context 未加入。旧1.0/新1.1 unit IDs 分离，原 locator 相同，全 units 和实际选中 spans 均 exact replay。

独立新 OOXML 原件 `own-inheritance-outline.docx` SHA `{probe['own_original']['sha256']}` 覆盖三层 basedOn 继承、paragraph outline9 覆盖、style outline9 覆盖、direct outline2 覆盖 body style；继承 heading 和 direct heading 阻断上下文，outline9 正文 pair 成完整同组。真实业务 cell 保持 `docx_table_cell` 独立选中；同段正文正控保持原文整体选中。最终29个最小定点检查 PASS，全部源/生产配置审查前后 SHA 未变。

实施原 `legacy-original.docx` SHA `d428ad041147fb650671ee805c38a03539b4f28529a5516bce325cc3a8541761` 的完整单位字段、metadata、kind、角色、identity、coordinates/locator 与文档 metadata/errors，经我重新 normalize 后严格等于保存 before 和 after 记录，指纹仍为 `a6580fca5dcd6c063e2447bf5cf489aaabd8f61c52856646db744cb68d0031e4`，6个旧units全 replay，saved old pin 仍1.0。旧unit增加伪造 heading metadata、新unit改变 heading_level、新EvidenceSpan经重新计算自洽hash后改变 outline_level，均由实际 replay 拒绝；未改任何 saved artifact。

ROOT首公共 attempt保留14 PASS/1 FAIL：旧producer的 manifest1.0与实际 worker/bundle1.1 不符。读取唯一精确 diff，`narrative_batch._normalization_parsers` 使用共享 `NORMALIZED_MIME_TYPES` 补上DOCX，原 manifest.version及旧fallback1.0保留，未放宽测试。最终 batch SHA `a483d786d99a7bef8f4420ada7770260b147c8048a9c1dceb4813d2f7d880df9`。

第二次只该公共责任实际1 PASS/21.68s，日志SHA `6288936168769b74376770e11ad348054e2822979a2a9f0135164bb830bc8045` 已独立核对。四次CLI均exit0；old producer1.0、current resume旧reference/binding/items/budget与AUTO/source只读SQL dump完全一致由真实已执行断言检查；new default1.1与旧source_ref一致但artifact version ID分离，标题spans保持独立，公共read原locator verified；同generation reuse与new reference相同且0新增tokens/费用。实际ThreadingHTTPServer的do_POST记录仅2次127.0.0.1请求，分别92 synthetic tokens/111 micro-USD测试计量，无外部供应商费用。原件/临时配置保护断言和真实temporary cleanup成功。

实施manifest全部源码/证据hash、两次ROOT receipt/log hash均与当前实际字节一致。7个最终源码与公共before/after SHA相同；原 replay.py 和生产 `config/source_catalog.yaml` 独立前后不变。CodeGraph先查canonical旧索引，缺当前native模块后阅读已定位源码，没有初始化索引。

自有harness早期构造伪造span未重算内部ID被构造器拒绝，随后修正为hash自洽后检查源replay；新fixture首长文件名触及Windows262字符限制，缩短自有文件名。首个完成probe的generic cell文案不满足既有eligible规则，旧0.7和新0.7.1均不选；原输入/脚本/28 PASS1 FAIL结果已留存，以明确eligible业务文案补正控后29 PASS。这些不形成源码问题，不放宽测试，不覆盖旧原件。

本审查0 provider、0外部model/新费、0源码/配置/saved artifact编辑，无commit/push，仅写自有final-heading-independent-review。没有重复104/112单元或既有4公共包。公共SQL/binding验收依据是保留日志与已执行的真实相等断言；测试已清理临时数据库。正常发布和精确新HEAD CI由ROOT完成。
'''
(OUT/'review.md').write_text(md,encoding='utf-8')
print(json.dumps({'recommendation':report['recommendation'],'checks':len(checks), 'integrity_records':len(integrity),
    'material_findings':report['material_findings'],'review_json_sha256':digest(OUT/'review.json'),
    'review_md_sha256':digest(OUT/'review.md'), 'source_unchanged':report['source_unchanged']},ensure_ascii=False,indent=2))
raise SystemExit(0 if accepted else 1)
