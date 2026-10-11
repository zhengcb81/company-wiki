"""Prepend one current shared status; preserve every prior PWF byte."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SHARED = [ROOT / 'docs/plans/cross-market-rf-e2e-2026-10-08',
          ROOT / 'docs/plans/narrative-evidence-pilot-2026-09-26']
PHASE = SHARED[0] / 'phase6'
SHARED += [PHASE / 'w05_parallel_common_roots_2026-10-11',
           PHASE / 'w06_parallel_verification_2026-10-11']
MARKER = '## ROOT 当前状态 — W06 accepted / W05 resource finalization — 2026-10-11'
PREFIX = f'''{MARKER}

- **W06-AUDIT-MEASURES：完成。** 原交付6a50d7e在最新W05 audit main上整合并修复共因；main正常合并至9cd5ff8a2c8f9c1726c4047785164e3263673614，clean。296项大节点测试、最终77项及独立19+8+4探针通过；两份技能各26文件MATCH，仅5个包文件/份及manifest更新。Audit无remote。验收限声明的类型与算术，不能替代来源真值与经济模型审查。
- **W05-CWP-OCR：最终资源收尾中，尚未并线。** 原85秒失败来自重复stdin监听与Windows CRT锁互阻，保留原FAIL；去掉冗余监听后22项集中通过、有效50ms产品硬截止通过；同一微软原件真实初次处理及独立回开总88.83秒（阶段各在原85/90秒上限），两定义恢复、22旧行完全一致。独审另发现ROI在PIL放大/拼接后才验像素，ROOT正在统一整数几何预检和预扣，禁止把native推理前已计预算误说成分配前也已计。
- **W05-RF-FLOW：修复集中工程节点通过，尚待最终独审与并线。** 唯一现有pre-push节点356+36 subtests通过（33.20秒），可移植兼容/3.9节点52+7通过，隔离native CLI和三仓显式根集成通过。原FAIL与他人assurance/output WIP保留；不凭解释文字放宽时间窗口或重复贡献，不新增许可门。

本批次没有供应商/LLM调用或新费用，原件与生产配置未改。下面旧状态只作历史；母PWF的W04、G2、G4、G5仍未全部完成，不能写整体完工。下一步：OCR分配前硬预算修复集中测试及真实E2E，RF非作者复核；达标后正常commit/merge/install/push，再返回母计划。

W06精确证据：phase6/w06_parallel_verification_2026-10-11/evidence/root-audit-measures-acceptance/publication.json 与 independent/final-review.md；隔离ROOT接收计划为 .planning/w06-audit-measures-reception/。

'''
for directory in SHARED:
    for name in ('task_plan.md', 'findings.md', 'progress.md'):
        path = directory / name
        old = path.read_bytes()
        assert MARKER.encode('utf-8') not in old, f'already recorded: {path}'
        path.write_bytes(PREFIX.encode('utf-8') + old)
print('12 shared PWF files updated; historical bytes preserved')
