"""Record the newly proven P1; do not rewrite earlier green-node receipts."""
from pathlib import Path

HERE = Path(__file__).resolve().parent
MARKER = '## 最终独审新增 P1 — annual typed ancestry — 2026-10-11'
prefix = f'''{MARKER}

原3个期间P1已拒绝，29项冻结SHA全MATCH，356+36及52+7工程节点仍是真实历史GREEN。但独审新增输入证明：point_in_time monetary_balance=20 经 derived_fact formula=x0、time_basis=annual、dimension=revenue、无dated ancestor，可穿过validate_document/run_forecast及两个强reader，使FY2026 low150→170。换成period_flow会拒绝，说明annual无dated祖先早退及annual consumer早退是共用类型追溯缺口。已用独立隔离publication registry重放确认，不把最初沙箱外部registry写失败当正确拒绝。

原FAIL存 independent-final/original-and-independent-probes.json 的 independent_point_stock_cannot_be_annual_revenue_alias；ROOT已要求原作者正式RED→共用typed ancestry触发覆盖，保留annual-only legacy草稿、真实stock×有据rate/price等合法原生公式，不按公司打补丁、不增加身份许可。之前的冻结/工程GREEN不得覆写为最终验收。

## Next Step

完成这项系统修复和集中既有工程节点，再由非作者重放原P1及合法正控；通过后才正常提交/并线/定点安装/推送。当前尚未合并或安装，0供应商/LLM/费用；canonical assurance/output WIP不动。

'''
for name in ('task_plan.md', 'findings.md', 'progress.md'):
    path = HERE / name
    old = path.read_bytes()
    assert MARKER.encode('utf-8') not in old
    path.write_bytes(prefix.encode('utf-8') + old)
print('selected RF plan updated; all prior receipts preserved')
