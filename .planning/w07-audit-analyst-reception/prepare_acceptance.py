import hashlib
import json
from pathlib import Path
import os
import subprocess
import time
import uuid

ROOT = Path('C:/Users/郑曾波/Projects/_harness_worktrees/w07/root-audit-analyst-reception')
AUTHOR = Path('C:/Users/郑曾波/Projects/_harness_worktrees/w07/audit-analyst-quality')
EVIDENCE = Path(__file__).resolve().parent / 'verification'
assert not EVIDENCE.exists()
EVIDENCE.mkdir()
handoff = json.loads((AUTHOR / 'docs/handoffs/w07-audit-analyst-quality/handoff.json').read_text(encoding='utf-8'))
hashes = []
for item in handoff['changed_files'] + handoff['readonly_inputs']:
    digest = hashlib.sha256((AUTHOR / item['path']).read_bytes()).hexdigest()
    hashes.append({'path': item['path'], 'expected': item['sha256'], 'actual': digest, 'match': digest == item['sha256']})
assert all(row['match'] for row in hashes), [row for row in hashes if not row['match']]
(EVIDENCE / 'author-hash-boundary.json').write_text(json.dumps(hashes, ensure_ascii=False, indent=2), encoding='utf-8')

reference = ROOT / 'skills/revenue-forecast-audit/references/analyst-risk-audit.md'
doc = reference.read_text(encoding='utf-8')
doc = doc.replace('.driver_parameter_ids.revenue', '.driver_parameter_ids (all native model roles)')
doc += '''

## ROOT 接收补充：引用与作用域

OBSERVED只说明当前打开的原生数据中存在可解析、范围匹配的声明，不证明来源真值或经济合理性。
收入路径按分部与情景读取全部native driver roles；校准输入通过已声明的input/output bridge归属路径，不运行公式。
支持cell的校准scope、输出parameter的period/unit和scenario须匹配，未知引用逐项列UNRESOLVED。
Finding的native_evidence_refs含kind/id/resolved；已解析项含input文档pointer，缺项明确保持resolved=false。
独立性metadata按相同target_type/target_id比较，不能由另一组note覆盖；布尔字符串不当作true。
超预期基准日期须可解析且不晚于结果公告，比较parameter期间需一致；引用measure_check_ids时实际索引checks，未测/失败不成为比较依据。
范围来源claim需可解，observed_period不可缺失；无效区间不覆盖支持cell。联合压力索引实际声明的分部、情景和参数路径。
actual_input须有有限数值（0合法，null/NaN/布尔不是实际值）及单位；period-only历史记录不建立actual覆盖。
WAPE只索引具有正observations和sum_absolute_actual的原生1.1历史汇总；历史误差与未来actual覆盖分别报告，缺证据保持null。
新增诊断reason包括driver_parameter_unresolved/driver_segment_path_mismatch/driver_timing_unresolved、
calibration_reference_unresolved/calibration_scope_not_covering/calibration_output_unresolved/conversion_unit_incomparable、
independence_reference_unresolved、beat_comparison_period_unresolved/beat_baseline_after_result/beat_date_unresolved、
measure_reference_unresolved/measure_evidence_unresolved、range_timing_unknown、native_reference_unresolved和error_metric_without_actual_evidence。
这些检查只查已打开JSON的引用和报告范围，不重复原文SHA、身份验证、下载或RF validator，不阻断预测。
'''
reference.write_text(doc, encoding='utf-8', newline='\n')
reviewer = ROOT / 'skills/revenue-forecast-audit/references/review-analyst.md'
doc = reviewer.read_text(encoding='utf-8')
assert 'analyst-risk-audit.md' not in doc
doc += '''

## 模型风险诊断辅助（A02/A05/A06/A08/A10/A13/A17/A18）

使用[模型风险诊断工具](analyst-risk-audit.md)消费本次已经打开的RF input/result和support诊断：

```text
python -B scripts/analyst_risk_audit.py --input ABS_RF_INPUT --forecast ABS_RF_RESULT --support ABS_RF_SUPPORT --out-root ABS_ROLE_ATTEMPTS
```

从已安装技能根目录执行；可用--context提供你自己的基准、联合压力和actual声明，--measure-report引用数字口径诊断。
不为诊断再下载、运行RF或调用LLM。未生成support时如实列未检查，不伪造支持文件。
保存本角色新attempt报告，在analyst.json/.md引用具体finding和native pointer；OBSERVED仅说明声明存在且引用/范围可查。
UNRESOLVED/NOT_CHECKED列入独立判断的证据缺口，不自动变成审批或拒绝预测；来源真值与经济合理性继续由你独立审查。
继续完成A01–A18、关键假设表、cross-check和超预期论据，工具没有覆盖的项目不得略过。
'''
reviewer.write_text(doc, encoding='utf-8', newline='\n')

env = dict(os.environ, PYTEST_DISABLE_PLUGIN_AUTOLOAD='1', PYTHONDONTWRITEBYTECODE='1', PYTHONUTF8='1')
def run(label, args, limit):
    started = time.monotonic()
    p = subprocess.run(args, cwd=ROOT, env=env, capture_output=True, encoding='utf-8', errors='replace', timeout=limit)
    (EVIDENCE / (label + '-stdout.log')).write_text(p.stdout, encoding='utf-8')
    (EVIDENCE / (label + '-stderr.log')).write_text(p.stderr, encoding='utf-8')
    row = {'command': args, 'exit_code': p.returncode, 'wall_seconds': time.monotonic()-started}
    (EVIDENCE / (label + '-execution.json')).write_text(json.dumps(row, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'label': label, **row}, ensure_ascii=False))
    print(p.stdout[-2000:])
    assert p.returncode == 0, p.stderr[-1000:]

run('focused', ['python','-B','-m','pytest','-q','tests/test_root_w07_analyst_scope.py','tests/test_w07_analyst_risk_audit.py','--tb=short','-p','no:cacheprovider'], 30)
scratch = ROOT / '.tmp' / ('root-w07-' + uuid.uuid4().hex[:8])
assert scratch.resolve().is_relative_to(ROOT.resolve()) and not scratch.exists()
run('e2e', ['python','-B','tools/run_analyst_risk_e2e.py','--owned-root',str(scratch),'--out-root',str(EVIDENCE / 'e2e')], 30)
assert not scratch.exists()
run('skill-structure', ['python','-B','C:/Users/郑曾波/.codex/skills/.system/skill-creator/scripts/quick_validate.py',str(ROOT / 'skills/revenue-forecast-audit')], 20)
print('ROOT acceptance verification complete; costs=0; original scratch absent')
