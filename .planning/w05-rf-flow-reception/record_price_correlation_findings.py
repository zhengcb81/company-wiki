"""Preserve frozen RF failure and record current blocking common cause."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
prefix = '''## ROOT 最新独审 — 价格期间解释相关性 P1，尚未验收 — 2026-10-11

376+36集中绿及旧stock/日期/重复贡献修复均保留，但非作者新24案/58边界复核发现3个同根因失败：存量×(annual_price/同源annual_price)、派生price比值、两个等价年价格比值仍被四个实际入口认作年度income，FY2026 low由150错增到170。30文件SHA未变，合法ARPU/turnover/fee/yield与CLI冻结产物通过，不是环境或证据换版本造成。

共因是annual_price的多种期间解释独立做笛卡尔组合，丢失同源/同单位/同期间的解释约束。直接或alias消去同一单位价格不能提供年度时间维度；比值只能缩放已有flow，不能使stock成为flow。不得 blanket reject price；统一符号/period约束及少量恒等式业务测试保留合法quantity×price、pointquantity×annualARPU与真实flow/stock周转。

当前B重新开放，C并线/安装未执行。作者仅在原ROOT隔离写集TDD修共享类型；新证据fix/price-correlation/，原independent-typed-final/与之前所有FAIL保留。无新schema、权限、身份或许可门；canonical的assurance/output WIP保持原样。最终集中工程节点和非作者反例复查后才正常commit/merge/install/push。

Next Step：完成共享关联语义修复，冻结产品SHA/17文件定点安装只读plan，再独立复核。母W04/G2/G4/G5仍开放。下面旧冻结和绿色仅作历史，不能当当前签收。

'''
for name in ('task_plan.md', 'findings.md', 'progress.md'):
    p = ROOT / '.planning/w05-rf-flow-reception' / name
    old = p.read_bytes()
    assert prefix.encode('utf-8') not in old
    p.write_bytes(prefix.encode('utf-8') + old)
print('RF price-correlation current state recorded, original bytes retained')
