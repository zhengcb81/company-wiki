# DU4-TABLE 交接 / du4-handoff/1

- lane：DU4-TABLE；分支 `codex/du4-table-20261015`；基线 `8206e78d4087531b1d7ed57c45a73c942cc702e3`。
- 实施提交：`87c69b92444566e4e3f6011491b36ae93af3b5e5`（本文件在其后单独交接提交中登记，避免递归）。
- 接口版本：`du4-interfaces/1`（INTERFACES.md TABLE 节，未改动）。

## 接口实例

```python
from company_wiki.document_understanding.table_measurements import bind_operating_table
from company_wiki.document_understanding.layout_hints.contract import WorkBudget

result = bind_operating_table(observation, *, work_budget: WorkBudget)
```

- 输入：`schema_version="du4-table-observation/1"`，`scope={parent_id, table_id, page}`，
  `units={id: {text, parent_id, role, kind, locator}}`，
  `cells=[{cell_id,row,column,row_span,column_span,presence,text_refs,header_refs}]`，
  可选 `header_rows`、`provenance`（仅 `native_slot|fine_geometry`）、`truncated`。
  数据格 `text_refs` 是逐值字符引用，`header_refs` 是标注/表头引用；出现在任一 `header_refs`
  的引用视为标签、不产生 measurement。`TextRef={unit_id,char_start,char_end}` 严格落在 unit 原文内。
- 输出：`schema_version="du4-table-bindings/1"`，同 scope，
  `status=complete|partial|unavailable`，`columns`、`measurements`、`unbound_value_refs`、
  `diagnostics`、`work_used`（本次调用 charge 数）。structural 错误（错 schema、重复 cell_id、
  非法索引、越界 ref、非法 provenance）抛 `ValueError`；证据不足逐项 ambiguous/unavailable + 诊断。
- 预算：复用传入的 `layout_hints.contract.WorkBudget`，不新建限额；耗尽保留已确定结果、
  `status=partial` + `work_budget_exhausted`。
- 单位取用为最紧作用域优先（单元格 > 行标签 > 表头路径）：行标签已给单位时不再叠加列头的
  量级标注（如 in millions），接线核对摘要数字时需知悉；原始表头引用始终保留在
  `columns[].header_refs`/`period.raw_label_refs`。

## 未绑定原因（真实保留包）

真实 HK 保留包 5 张表合计 **bound 34 / ambiguous 7 / unavailable 0**
（逐值引用与列/期间见 `results/real-packet-bindings-report.json`）：

- 7 项 ambiguous 全部是左侧大合并格内容（门店数旧值块、`Total 合計` 块、GMV 多行块、TOP TOY 块）：
  合并格覆盖标签列＋旧年列（GMV 表覆盖三列），没有逐值原生定位，按契约明确 ambiguous，
  不右对齐、不按最新年填槽：全部 `period=null` 并记 `multi_column_value`，其中 6 项因跨列
  `column_id` 亦为 null；p20t1 一块因 raw_rows 截断、行槽无格 bbox，按 `no_header_path` 判
  ambiguous，保留其已知原生 `column_id=col-0`。
- 34 项 bound 全部是后续右列行的原生单格值：门店表绑到 as-of 2024-12-31 列，GMV 表绑到
  fiscal 2024（fiscal_label "2024"）列；没有任何值落到 2023 列，六个月/十二个月 2023 与
  fiscal 2024 是三个独立列/期间。

## 真实 / 合成边界

- 真实：`fixtures/hk-table-observation.json.gz`（SHA-256 `6f3ce02a…c1e25571`，与 manifest 一致）的
  字符串去重表、replay units、native slot 栅格与格 bbox；未重开原件。
- 适配器派生（`tests/unit/du4_table_measurements/real_packet.py` 文档头逐条注明）：parent_id/role/kind
  占位、`header_rows=[0..3]`、由保留 bbox 投影的 row/column span 归属（同时写入 provenance）、
  per-table 截断标记。
- 合成：`tests/unit/du4_table_measurements/builders.py` 构造的语义反例与 holdout（test_1..test_4、
  test_6），expected 独立于实现编写，未使用真实公司数值作为代码规则；真实数值只出现在测试
  对照保留包的位置性断言（列归属/期间），不硬编码进实现。

## 验证证据（均本工作树 PYTHONPATH=src）

| 项 | 命令 | 结果 | receipt |
|---|---|---|---|
| RED-1 导入失败 | `python -B -m pytest -q tests/unit/du4_table_measurements` | exit 2 | results/red-1-import-failure.log |
| RED-2 语义失败 | 同上（骨架） | exit 1，31 failed/2 passed | results/red-2-semantic-failure.log |
| 集中单测 | 同上 | exit 0，36 passed | results/pytest-final.log |
| Ruff | `python -m ruff check src/.../table_measurements tests/unit/du4_table_measurements` | exit 0 | results/ruff-final.log |
| mypy | `python -m mypy src/company_wiki/document_understanding/table_measurements` | exit 0 | results/mypy-final.log |
| 真实走通 | `python -B tests/unit/du4_table_measurements/report_real_packet.py` | bound 34/ambiguous 7 | results/real-packet-bindings-report.json |

预算观察（同报告，无毫秒门槛）：cap 0/5/50 → partial + 耗尽诊断、work_used 恰为 cap；
cap 400 → 6/6 保留、work_used 148、无耗尽；同输入两次输出完全一致（含 work_used）。

## ROOT 接线清单（本作者不做）

1. 同次 native parse 采集格槽（row/column/span/presence + 逐值 text refs）→ 构造 observation。
2. adapter/structure 调 `bind_operating_table`，TableDraft/wire 保留 bindings 引用。
3. 解释必需 refs（header/period raw labels、unit、footnote）进现有选择依赖闭包。
4. canonical context/模型投影携带同一绑定；unbound 数字只作定性/明确未知。
5. 真实 HK + 另一公司/格式 holdout 逐 claim 核对。
6. cache 指纹/旧 Ref 恢复与摘要数字审查。

生产写入 0；供应商调用 0；未改主目录、兄弟工作树、CI、hooks。STOP 等 ROOT 接收。
