"""ROOT one-shot narrow skill wiring; preserve existing workflow and EOL."""
from pathlib import Path

SKILL = Path('C:/Users/郑曾波/Projects/_harness_worktrees/w06/audit-measures-root/skills/revenue-forecast-audit')
updates = {
    'SKILL.md': (
        '## 长期约束',
        '对执行包的金额、比例、存量/流量和派生关系，三号审查读取[数字口径工具](references/financial-measure-audit.md)，复用已有数字表映射显式 typed ledger，在本 attempt 新目录运行 `financial_measure_audit.py`。四号可对同一执行数字表独立复算；两位初稿仍互不读取。该工具核声明口径与算式，不读原件、不验证来源真值或预测经济合理性，不成为许可或发布门；未知字段保留诊断，不猜身份/期间/汇率填 PASS。\n\n',
    ),
    'references/review-process.md': (
        '## 报告',
        '### 显式数字口径诊断\n\n'
        '读[financial-measure-audit 合同](financial-measure-audit.md)，将执行包已有数字表及算式映射为 ledger，记录映射到原数字/来源引用的对应关系；公司身份沿用已解析引用，不重建身份库或重新采集。金额保留原币种/scale，比例保留 percent/decimal/percentage_points，期间按真实日期、kind 与定义表达；缺字段列 unknown，不从标签猜全年或把研究假设升级 actual。\n\n'
        '运行 `python <SKILL_DIR>/scripts/financial_measure_audit.py --ledger <本attempt的typed-ledger.json> --out-root <本attempt新诊断目录>`；目录由审查者独占，旧报告不可覆盖。保留实际 exit/report，区分 arithmetic、typed compatibility、UNRESOLVED 与 INVALID；“能算出数”不等于口径已核。原文真实性/每条数字出处仍实读；工具没有覆盖的数字、关系和缺上下文单列，不以其 PASS 代替全量审查。future guidance/assumption 可以有未来 target window，但来源可用日及角色须如实，不能冒 actual。\n\n',
    ),
    'references/review-analyst.md': (
        'reports/analyst.json+.md 必须包括：',
        '金额与比例的 cross-check 可独立使用[数字口径工具](financial-measure-audit.md)，复用同一执行数字表，在自己的 attempt 子目录写新报告。算式/口径 PASS 只作技术事实；source_truth_verified=false、economic_reasonableness=not_evaluated 不会因算式正确变成通过。继续独立核需求、供给、确认节奏、重叠贡献、基准和假设证据；不读取三号初稿来替代判断。\n\n',
    ),
}
for name, (marker, insertion) in updates.items():
    path = SKILL / name
    original = path.read_bytes()
    newline = '\r\n' if b'\r\n' in original else '\n'
    needle = marker.encode('utf-8')
    assert original.count(needle) == 1, f'unique marker required: {name}'
    added = insertion.replace('\n', newline).encode('utf-8')
    assert added not in original, f'already applied: {name}'
    path.write_bytes(original.replace(needle, added + needle, 1))
print('Wired 3 instruction files; existing bytes and metadata preserved')
