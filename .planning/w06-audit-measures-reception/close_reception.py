"""Record publication once, without altering historical acceptance evidence."""
from pathlib import Path
import hashlib
import json
import subprocess

ROOT = Path(__file__).resolve().parents[2]
PLAN = Path(__file__).resolve().parent
PROJECT = Path('C:/Users/郑曾波/Projects/revenue-forecast-audit')
TREE = Path('C:/Users/郑曾波/Projects/_harness_worktrees/w06/audit-measures-root')
REL = Path('skills/revenue-forecast-audit/scripts/financial_measure_audit.py')
EVIDENCE = ROOT / 'docs/plans/cross-market-rf-e2e-2026-10-08/phase6/w06_parallel_verification_2026-10-11/evidence/root-audit-measures-acceptance'
EXPECTED = '9cd5ff8a2c8f9c1726c4047785164e3263673614'
TARGET = EVIDENCE / 'publication.json'
assert not TARGET.exists(), 'one-shot: publication already recorded'
head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=PROJECT, text=True).strip()
assert head == EXPECTED
status = subprocess.check_output(['git', 'status', '--porcelain'], cwd=PROJECT, text=True)
assert not status.strip(), status
canonical = (PROJECT / REL).read_bytes()
frozen = (TREE / REL).read_bytes()
assert canonical.replace(b'\r\n', b'\n') == frozen.replace(b'\r\n', b'\n')
installation = json.loads((EVIDENCE / 'installation-after.json').read_text(encoding='utf-8'))
assert installation['head'] == head and installation['files_per_copy'] == 26
assert all(item['status'] == 'MATCH' for item in installation['installations'])
report = {
    'schema_version': 'w06-root-publication/1', 'status': 'ACCEPTED_WITH_SCOPE',
    'main_head': head, 'main_worktree_clean': True,
    'remote': None,
    'frozen_product_sha256': hashlib.sha256(frozen).hexdigest(),
    'canonical_product_sha256': hashlib.sha256(canonical).hexdigest(),
    'normalized_source_equal': True,
    'installed_copies': 2, 'files_per_copy': 26, 'changed_files_per_copy': 5,
    'new_llm_calls': 0, 'new_cost_usd': 0,
    'full_engineering_tests_before_output_field_delta': 296,
    'final_financial_tests': 77,
    'independent_review': 'independent/final-review.md',
    'scope': 'Declared typed arithmetic; source truth and economic reasonableness are not certified.',
    'whole_pwf_complete': False,
}
TARGET.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
for name in ('task_plan.md', 'findings.md', 'progress.md'):
    path = PLAN / name
    old = path.read_bytes()
    prefix = ('## ROOT 完成记录 — 2026-10-11\n\n'
              'W06-AUDIT-MEASURES 已接收：正常合并提交及 canonical main 为 '
              '`9cd5ff8a2c8f9c1726c4047785164e3263673614`，主工作树 clean。'
              '独立原19反例、额外8探针和最终4边界检查通过；大节点296项通过，'
              '一字段修正后77项通过，不重复完整包。两份安装各26文件 MATCH，'
              '每份仅5个包文件与manifest更新，配置/output保留。Audit仓无remote，'
              '不宣称已远端推送。原FAIL全部保留，增量调用与费用0。\n\n'
              '验收范围为声明的类型和算术；来源真值、经济含义及买方模型质量仍由'
              '四位审查agent独立检查。下面旧记录为历史，不表示仍待并线。\n\n')
    if name == 'task_plan.md':
        prefix += ('大节点 A/B/C 均完成。\n\n## Next Step\n\n'
                   'W06包已关闭；ROOT继续W05 OCR预分配资源修复与RF时间口径接收，'
                   '随后返回母PWF未完成项。详见publication.json。\n\n')
    path.write_bytes(prefix.encode('utf-8') + old)
print(json.dumps(report, ensure_ascii=False))
