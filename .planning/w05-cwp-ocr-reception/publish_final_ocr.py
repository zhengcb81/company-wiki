"""Publish accepted OCR and immutable receipts through normal hooks."""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
PHASE = ROOT / 'docs/plans/cross-market-rf-e2e-2026-10-08/phase6'
directories = [ROOT / 'docs/plans/cross-market-rf-e2e-2026-10-08',
               ROOT / 'docs/plans/narrative-evidence-pilot-2026-09-26',
               PHASE / 'w05_parallel_common_roots_2026-10-11',
               PHASE / 'w06_parallel_verification_2026-10-11']
marker = '## ROOT 当前状态 — OCR 已本地并线 / 两张 W06 接收修复 — 2026-10-11'
prefix = f'''{marker}

- **W05-CWP-OCR：资源与来源大节点验收通过，已正常并入本地主线 ae0ca0d3。** ROI 先计算整数几何、预扣预算，再分配图像和推理；原生进程统一截止与清理。最终54项集中、34项非作者探针、现有快测148项通过；同一微软原件真实两阶段83.006秒（37.706/44.104，原85/90秒限额），22旧行完全一致，两条定义恢复，fresh locator 回开通过。原85秒FAIL、后续88.83秒PASS均保留。POSIX仅静态审查，未测峰值RSS，不能宣称全部OCR召回或研究质量已验收。此次提交后正常推送；精确远端/CI记录另行写入 publication.json。
- **W06-AUDIT-MEASURES：已完成。** Audit main9cd5ff8a，296项大节点、最终77项及独立反例通过；两份技能各26文件MATCH，原件/配置/输出未动。Audit仓无remote。算术检查不认证来源真值。
- **W05-RF-FLOW：最终 typed ancestry 修复已冻结，待非作者复核。** 原标签洗成年度收入的stock/rate/scalar问题按共用数学类型与时间阶数修复；现有唯一工程节点376+36 subtests通过，两个native冻结输入的5份产物完整字节一致。尚未主线并入或安装；他人assurance/output WIP保留。
- **W06-FF-MATRIX：已交付，接收发现工具误判与隔离问题，正在独立ROOT树修复。** 旧12项绿不覆盖错误季度、重复下载、未知用量、SourceRef缺失、环境/清理归属及绝对截止；11项非作者探针10FAIL。测试工具问题不冒充生产缺陷。
- **W06-CWP-PORTABILITY：已交付，非作者接收中。** 当前真实Reader合成移根/原字节/篡改/版本回开等流程通过；工具会清理已有固定目录、改写export证据、刷新输入ref等问题仍需修复，不能据原worker全绿并线。仅修本卡工具与测试，不扩展生产权限或许可。

本批次未调用provider/LLM、无新费用，原件与生产配置未变。母PWF的W04、G2、G4、G5仍开放。下一步先完成RF/W06各自大节点验收与正常并线，再返回统一候选覆盖及真实公司重跑。下面旧记录是历史，不作当前完成声明。

'''
paths = ['.planning/w05-cwp-ocr-reception',
         str((PHASE / 'w05_parallel_common_roots_2026-10-11/evidence/root-cwp-ocr-acceptance').relative_to(ROOT))]
for directory in directories:
    for name in ('task_plan.md', 'findings.md', 'progress.md'):
        path = directory / name
        old = path.read_bytes()
        assert marker.encode('utf-8') not in old, str(path)
        path.write_bytes(prefix.encode('utf-8') + old)
        paths.append(str(path.relative_to(ROOT)))

def run(*args):
    return subprocess.run(args, cwd=ROOT, check=True)

assert not subprocess.check_output(['git', 'diff', '--cached', '--name-only'], cwd=ROOT).strip()
run('git', 'add', '--', *paths)
run('git', 'diff', '--cached', '--stat')
run('git', 'commit', '-m', 'docs(ocr): publish final source replay and independent resource acceptance')
run('git', 'push', 'origin', 'master')
run('git', 'rev-parse', 'HEAD')
run('git', 'ls-remote', 'origin', 'refs/heads/master')
