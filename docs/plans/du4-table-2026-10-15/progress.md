# 进度

2026-10-15 ROOT 已创建独立稀疏工作树、复制施工卡/接口/真实观察。READY，未实施、未运行本卡测试；不继承主线工程通过结论。

2026-10-15 DU4-TABLE 作者实施完成 A/B/C 三个大节点。以下为实际命令与证据（均在
`C:/Users/郑曾波/Projects/company-wiki-du4-table` 执行，`PYTHONPATH` 指向本工作树 `src`）。

## A：独立 expected 语义反例与 RED

- 确认 import 指向本工作树：`python -B -c "import company_wiki; print(list(company_wiki.__path__))"`
  → `['C:\\...\\company-wiki-du4-table\\src\\company_wiki']`（results/import-check.log）。
- 新建 `tests/unit/du4_table_measurements/`（conftest、builders、real_packet 投影适配器、
  test_1..test_5 语义反例，expected 独立于实现编写）。
- RED-1（新模块导入失败）：`python -B -m pytest -q tests/unit/du4_table_measurements`
  → exit 2，`ModuleNotFoundError: table_measurements`（results/red-1-import-failure.log）。
- 实现 API 骨架（仅 schema/输出形状）后重跑：exit 1，31 failed / 2 passed，
  失败均为真正语义断言（如 `AssertionError: no measurement for value_ref ...`、列/期间期望不符），
  无导入错误（results/red-2-semantic-failure.log）。未改任何 expected 迁就输出；
  仅修正两处测试自身笔误（test_1 取 values[3] 而非不存在的 values[2]；test_3 的
  "7 个单位集合互异" 与同一测试内 "计数行无单位" 期望自相矛盾，改为 "单位引用不跨行混用"）。

## B：实现与集中验证

- 实现 `src/company_wiki/document_understanding/table_measurements/`
  （`__init__.py` 导出 `bind_operating_table`；`bindings.py` 主绑定；`_periods.py` 期间解析；
  `_labels.py` 单位/范围/脚注 span 检测）。纯内存、只用标准库 + 既有 `WorkBudget`，
  不调 LLM/供应商、不读写生产资料。
- 集中单测：`python -B -m pytest -q tests/unit/du4_table_measurements` → **35 passed**，
  exit 0（results/pytest-final.log）。含真实 HK packet（test_5）与合成多表/重复年 holdout（test_6）。
- 真实 packet 走通报告：`python -B tests/unit/du4_table_measurements/report_real_packet.py`
  → results/real-packet-bindings-report.json。真实计数：**bound 34 / ambiguous 7 / unavailable 0**
  （5 张保留表合计；逐表逐值引用、列/期间、诊断码、work_used 与耗时观察见报告；
  未绑定 7 项均为左侧大合并格内容，无逐值原生定位，明确 ambiguous，未被 2023/2024 吸收）。
- 预算观察（同报告 budget_observations，无毫秒门槛）：cap 0/5/50 → partial + `work_budget_exhausted`，
  work_used 恰为 cap；cap 400 → 6/6 测量保留、work_used 148、无耗尽。

## C：静态检查与交接

- `python -m ruff check src/company_wiki/document_understanding/table_measurements tests/unit/du4_table_measurements`
  → All checks passed（results/ruff-final.log）。
- `python -m mypy src/company_wiki/document_understanding/table_measurements`（沿仓库当前 mypy 设置）
  → success: no issues（results/mypy-final.log）。
- 交接：`handoff.md` / `handoff.json`（du4-handoff/1）。未做生产接线、未改主目录/兄弟工作树/CI/hooks；
  supplier_calls=0、production_writes=0。STOP 等 ROOT 接收。
