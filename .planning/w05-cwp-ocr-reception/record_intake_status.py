"""Record this ROOT intake snapshot without rewriting historical PWF bytes."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FAMILY = ROOT / 'docs/plans/cross-market-rf-e2e-2026-10-08/phase6'
MARKER = '## ROOT 接收状态：三交付已盘点、隔离修复中（2026-10-11）'
HEADER = '''## ROOT 接收状态：三交付已盘点、隔离修复中（2026-10-11）

W05-AUDIT-LOOP 已并 main321d4c1、两技能同步，旧结论保持。新三交付均已核 Git/manifest；“worker 完成”仍需 ROOT 验证事实范围，不扩展人工许可。

| 线 | 已核事实 | 当前动作 |
|---|---|---|
| W05-CWP-OCR | 32项SHA/字节匹配；最终184PASS/66.32s、ruff绿、原6反例及有效50ms startup截止绿；真实PPTX首次原图推理85.047s触deadline FAIL | 保留 original-fail 日志/result/receipt；先定位隔离 native 初始化/推理性能根因，不加85/90s上限；未发布 |
| W05-RF-FLOW | 87项匹配、120 tests+33 subtests绿；3个期间语义P1穿透强输出读者；C1 CNY/USD标签、8 ignored产物须纠正；compatibility实为已tracked稀疏排除 | 独立 rf-flow-root 接原提交，正式RED→共用期间语义/依赖顺序修复，未并线或安装 |
| W06-AUDIT-MEASURES | 23项匹配、40+7绿；19冻结反例11假PASS/5结构异常，真实CLI复现 | 独立 audit-measures-root 基于已接W05 main321d，正式RED→typed操作/未知传播/容差/输入边界修复，未并线或安装 |

原交付树不改；ROOT在三个排他树整合，最终集中测试/独审后正常提交并线。只读原件/生产配置SHA保持；测试scratch恢复；本轮0 HTTP/provider/LLM/token/费用。累计413778 tokens /334463µUSD +FX2764 hold保持。Dayu/IQS、其他owner WIP不动。W04阶段/预算召回缺口及G2/G4/G5真实公司质量尚未完成；不能以本次工程绿签收经济结论。

## Next Step

OCR先分段查 native 性能，不凭重跑或提高预算换绿；RF/Audit共因修复在独立树并行，正式失败证据不删除，ROOT负责最终接线、发布、技能定点同步。W06另两卡保留原owner，未交付不重新派工。选定接收计划为 .planning/w05-cwp-ocr-reception、.planning/w05-rf-flow-reception、.planning/w06-audit-measures-reception；母PWF沿用本文状态，历史字节如下保留。

'''

paths = []
for directory in (
    ROOT / 'docs/plans/cross-market-rf-e2e-2026-10-08',
    ROOT / 'docs/plans/narrative-evidence-pilot-2026-09-26',
    FAMILY / 'w05_parallel_common_roots_2026-10-11',
    FAMILY / 'w06_parallel_verification_2026-10-11',
):
    paths.extend(directory / name for name in ('task_plan.md', 'findings.md', 'progress.md'))
for path in paths:
    old = path.read_bytes()
    assert MARKER.encode() not in old, f'one-shot snapshot already present: {path}'
    newline = '\r\n' if b'\r\n' in old else '\n'
    prefix = HEADER.replace('\n', newline).encode('utf-8')
    path.write_bytes(prefix + old)
    assert path.read_bytes().endswith(old)
print(f'{len(paths)} PWF snapshots recorded; historical bytes preserved')
