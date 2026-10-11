"""Record final OCR quality/resource facts, before normal publication."""
from pathlib import Path

HERE = Path(__file__).resolve().parent
MARKER = '## ROOT 最终资源与真实回放通过 — 2026-10-11'
prefix = f'''{MARKER}

OCR source/resource 大节点已通过：预分配7真实RED→54集中PASS/3.78秒、15旧输出/坐标/原错误完全一致；非作者34纯几何/预算探针PASS/0.383秒。真实初次处理+新进程locator回开总83.006秒，阶段37.706/44.104秒，原85/90上限不变；22旧行EXACT、两定义置信度.98912/.99044及locators同旧PASS，5原件/配置SHA与4产品SHA前后相同，scratch恢复absent，0调用/费用。原85秒native FAIL、旧独审FAIL、预分配7RED全部保留。

Windows native边界最终22项此前通过，当前未再改其源码；184项仅属去掉重复监听之前的组合基线，不能说已按最后源码重跑。最终独审PASS_WITH_SCOPE；POSIX仅静态审查、没有峰值RSS实测，不签研究质量。报告 independent-preallocation/report.md 与 preallocation-real-e2e/ 位于共用W05接收证据。

为避免关键回归未接CI而漏检，ROOT在既有FAST_CONTRACT_CASES登记6个小节点（实际11参数用例），先6登记断言RED，再既有fast入口148PASS/24.45秒；没有新gate，也没有把真实模型/整套normalization纳入每push。正常源码发布时既有完整受影响节点仍会执行。

## Next Step

A/B/C完成；待正常暂存ROOT的两份登记变更、commit/merge/push与精确CI。用户新交付W06-CWP-PORTABILITY当前只读验收发现owned目录清理缺口，FF matrix也发现oracle/隔离缺口；它们单独修复，不改已冻结OCR，不把测试工具的错误称为CWP生产缺陷。母W04/G2/G4/G5尚未完成。

'''
for name in ('task_plan.md', 'findings.md', 'progress.md'):
    path = HERE / name
    old = path.read_bytes()
    assert MARKER.encode('utf-8') not in old
    path.write_bytes(prefix.encode('utf-8') + old)
print('OCR selected plan updated; earlier failures preserved')
