"""Freeze final independent rejection and bounded positive checks."""
import copy
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
result = json.loads((HERE / 'results.json').read_text(encoding='utf-8'))
baseline = json.loads((BASE / 'fix/final-refresh/real-run-report.json').read_text(encoding='utf-8'))
s2index = next(i for i, item in enumerate(baseline['scenarios']) if item['id'] == 'S2')
changes = {
    'new_move_denies_same_root_ids': ('move', 'same_root_ids', False),
    'new_move_denies_same_relative_paths': ('move', 'same_relative_paths', False),
    'new_policy_change_is_auth_gate': ('policy_observation', 'change_is_auth_gate', True),
    'new_old_ref_identity_not_preserved': ('reads_after_move', 'ref_identity_preserved', False),
}
failed = [item for item in result['oracle_cases'] if not item['as_expected']]
assert len(failed) == 4 and {item['name'] for item in failed} == set(changes)
counterexamples = []
for item in failed:
    original = copy.deepcopy(baseline)
    group, key, value = changes[item['name']]
    target = original['scenarios'][s2index]['evidence'][group]
    original_value = target[0][key] if isinstance(target, list) else target[key]
    if isinstance(target, list):
        target[0][key] = value
        suffix = f'/{group}/0/{key}'
    else:
        target[key] = value
        suffix = f'/{group}/{key}'
    canonical = json.dumps(original, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()
    counterexamples.append({
        'name': item['name'],
        'original_value': original_value,
        'json_patch': [{'op': 'replace', 'path': f'/scenarios/{s2index}/evidence'+suffix, 'value': value}],
        'canonical_effective_input_sha256': hashlib.sha256(canonical).hexdigest(),
        'expected_overall': 'FAIL', 'actual_overall': item['actual'],
        'actual_findings': item['findings'],
    })
case_record = {
    'schema_version': 'w06-portability-four-common-classification-counterexamples/1',
    'base_report_ref': '../fix/final-refresh/real-run-report.json',
    'base_report_sha256': result['author_final']['real_report_sha256'],
    'replay': 'probes.py; each JSON patch applied separately to the unchanged base report',
    'canonical_input_encoding': 'UTF-8 JSON sort_keys=true ensure_ascii=false compact separators',
    'counterexamples': counterexamples,
}
(HERE / 'counterexamples.json').write_text(json.dumps(case_record, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
review = {
    'schema_version': 'w06-portability-independent-review/1',
    'verdict': 'FAIL_NEW_ORACLE_EXPECTATION_CLASSIFICATION',
    'blockers': [{
        'id': 'W06-PORT-ORACLE-FINDING-VERDICT', 'priority': 'P1',
        'root_cause': 'Failed hard contract checks emit expectation_unmet, but final verdict/scenario status only escalates false_pass prefix and two named hard-defect codes.',
        'source_locations': ['tools/source_root_portability/oracle.py:389',
                             'tools/source_root_portability/oracle.py:407',
                             'tools/source_root_portability/oracle.py:457',
                             'tools/source_root_portability/oracle.py:847'],
        'demonstrated_vectors': [v['name'] for v in failed],
        'fix_direction': 'A common finding outcome/severity contract must determine both scenario status and overall verdict. Do not fix the four field names separately. Preserve accurate PARTIAL/UNKNOWN and non-blocking diagnostics.',
    }],
    'oracle': {'bounded_cases': 22, 'as_expected': 18, 'false_pass': 4,
               'original_eight_oracle_counterexamples_rejected': True,
               'legitimate_PASS_PARTIAL_UNKNOWN_controls': True},
    'real_child_full_ref': [{'name': v['name'], 'exit_code': v['actual']['exit_code'],
                            'status': v['actual']['probe']['status'], 'reason': v['actual']['probe']['reason']}
                           for v in result['runtime']['actual_complete_ref_child_results']],
    'runtime': {'raw_CLI_failure_unmodified': True, 'old_files_preserved': 7,
                'existing_empty_directories_preserved': 6, 'all_three_overlap_refusals_before_write': True,
                'minimal_environment': True, 'synthetic_home_temp': True,
                'scratch_restored_absent': result['runtime']['scratch_restored_absent']},
    'freeze': {'sha256': result['freeze_sha256'], 'product_file_count': 11,
               'producer_file_count': 8, 'all_frozen_shas_match': result['all_frozen_shas_match'],
               'old_intake_preserved': result['old_intake_preserved']},
    'author_current_evidence': result['author_final'],
    'hygiene': result['hygiene'],
    'scope': result['scope'],
    'seconds': result['seconds'], 'disposition': 'STOP; ROOT common tool verdict fix before publication',
}
(HERE / 'report.json').write_text(json.dumps(review, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
text = '''# W06-CWP-PORTABILITY 最终非作者验收

## 结论

**FAIL_NEW_ORACLE_EXPECTATION_CLASSIFICATION，暂不并线。** 原先工具层的八个证据误判/CRASH 向量已经修复，真实完整引用、CLI 原始证据、目录归属及子进程隔离复验均通过。新增一个共用汇总缺陷仍会将违反硬契约的观测判成 PASS，需要统一修复 finding→场景状态→总 verdict 的映射。

## 已证实的阻断项

本次只读绑定 `8862372f714209cff1b218d77b5c4b8af6bc74dc` 隔离 ROOT 树及作者 `product-freeze.json`（SHA `b1662c806216a8c2e729ae7a48fda6b83a741a552e0e60323b1a662854dd715b`）。对冻结真实七场景报告各自只改一个明确否定值，得到以下结果：

| 单独否定的硬契约 | 预期 | 当前实际 |
|---|---|---|
| S2 `same_root_ids=false` | FAIL | PASS，finding=`expectation_unmet` |
| S2 `same_relative_paths=false` | FAIL | PASS，finding=`expectation_unmet` |
| S2 `change_is_auth_gate=true` | FAIL | PASS，finding=`expectation_unmet` |
| S2 旧引用实读 `ref_identity_preserved=false` | FAIL | PASS，finding=`expectation_unmet` |

原因在 `oracle.py:389/407/457` 产生 finding 后，`:847` 后的汇总只按 `false_pass` 前缀和 `offline_violation`/`code_identity_missing` 升级失败；上面已经检测出来的硬契约违例没有进入该集合。场景状态和 overall 都仍为 PASS。四项属于同一个判定责任缺陷，不是四个需要加特例的字段。

`counterexamples.json` 保存原始报告引用及 SHA、每项精确 JSON patch、原值、独立有效输入规范化 SHA、预期和实际 findings；`probes.py` 可以从未改动的冻结原报告复现。没有拷贝四份大报告或覆盖旧 FAIL。

## 对 finding 类别的静态核对

以下当前 `expectation_unmet` 均是 PASS 声明下的**硬契约/必需证据缺口**，不能仅写诊断后保留 PASS：

- S2 同 root ID/相对路径约束（389；一个分支包含两条件）；配置变化不是许可门（407）；旧完整引用身份保持（457）。
- S3 必须分类重登后的旧引用结果（512）。不要求 `document_id` 永远不变；具名旧位置不可用可以是合法观测，未知身份也可以准确报 UNKNOWN。缺分类仍不能声称该场景已验收。
- S4 删除只限 synthetic 副本（566），缺这个条件不能签测试环境安全 PASS。
- S5 恢复后必须真正重读字节（603）；没有恢复实读就没有完成该检查点。

本轮仅前四项实际新增复现；后三项是相同代码路径的静态风险，不声称已经另跑。少 S2–S7、丢部分 ref、漏最终恢复、替换 raw CLI、receipt 冒充 bytes、错类型等目前已有严格拒绝，见 22 项结果。

普通诊断不应被升级成门禁：真实 ID 关系描述/非永久 ID、配置 SHA 的真实变化本身、blocked socket 观测、测试 warning、当前 host 无法创建 symlink 等。准确的 PARTIAL/UNKNOWN 不是 false PASS；我的两个正控仍分别返回 PARTIAL/UNKNOWN。建议 finding 明确携带共用 outcome/严重程度（或一个集中映射），由汇总统一处理，不再依赖名字前缀，也不把全部诊断无差别变成失败。

## 已完成的有界独立复验

- **22 项 oracle：18 项符合预期，4 项新增误 PASS。** 原 eight 包括七项旧错/漏证据 PASS 及弱类型 CRASH，当前全部拒绝；合法冻结七场景和准确 PARTIAL/UNKNOWN 控制成立。
- 四个真实新进程：合法完整 TXT SourceRef `exit=0/ok`；错 size、错 MIME 均 `exit=2/source_ref_changed`；旧 schema `exit=2/unsupported_version`。未调用 query 来替换收到的 pin；合法读取真正触碰 synthetic raw，并归属 company_wiki。
- 对实际 export 执行面注入空 manifests，原 stdout、stderr、bundle 原样保留；已有 storage facts 未补造成成功。此注入仅验证测试工具记录职责，未 mock 原件/Reader。
- 本次自有短目录的 **7 个既有文件 SHA、6 个空目录**均保持；无归属旧 cleanup 不删，唯一创建 child 清掉，3 种重叠目录关系在写前拒绝，最终整个独立 scratch absent。
- 子进程 env 为最小平台名单、synthetic HOME/TEMP，禁 dotenv；网络/凭证文件 guard 在生产导入前启用。记录一个 blocked socket 类动作，没有 connect/DNS/外部访问；provider/LLM/费用均 0。
- 全 **11 冻结产品文件 + 8 生产模块**前后 SHA 相同；原 intake 文件 SHA 相同。没有产品、共享 PWF、Git、安装副本或真实 raw 写入。
- 独立最终耗时 **4.449 秒**。第一回沙箱 TEMP 最终删除 WinError 5 已留 `initial-runtime-diagnostic.log`；随后精确路径检查 absent。第二回使用本仓 `.tmp` 唯一短子目录、升级工具执行及绝对删除校验，恢复成功；不将这个测试环境故障归为产品缺陷。

## 当前作者证据和范围

核对的是 `fix/final-refresh` 的 **56 PASS / 1 SKIP / 1 warning，10.97 秒**及当前真实 synthetic Reader/CLI **7 场景、4.755 秒**；不是旧 worker 33 PASS。报告有 4 doc_key / 3 distinct 逻辑来源。S2/S6 可以实读四个引用别名，不能据此说四个物理路径均读过；S4 另有删除主副本读取备份的实际证据。58 in-process API calls+4 child invocations=62 API 调用，不等于 62 次成功 bytes read。

本轮没有重跑 3257 全集，也没有真实 OCR/LLM/云、Dayu/Dropbox 项目代码、POSIX 或投资质量认证。工具修复后由 ROOT 在一个大节点验原反例及合法控制，再决定正常提交、并线和推送。当前 STOP，等待 ROOT 处理共用 oracle 汇总。
'''
(HERE / 'report.md').write_text(text, encoding='utf-8')
manifest = {'schema_version': 'w06-portability-independent-manifest/1',
            'verdict': review['verdict'], 'files': []}
for path in sorted(HERE.glob('*')):
    if path.is_file() and path.name != 'manifest.json':
        data = path.read_bytes()
        manifest['files'].append({'path': path.name, 'byte_size': len(data),
                                  'sha256': hashlib.sha256(data).hexdigest()})
(HERE / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print(json.dumps({'verdict': review['verdict'], 'files': len(manifest['files']),
                  'bytes': sum(f['byte_size'] for f in manifest['files']),
                  'scratch_restored': review['runtime']['scratch_restored_absent']}, ensure_ascii=False))
