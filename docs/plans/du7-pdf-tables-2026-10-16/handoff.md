# DU7-PDF-TABLE 交接 / du7-handoff/1

- lane：DU7-PDF-TABLE；分支 `codex/du7-pdf-tables-20261016`；源码基线 `04c7f1bc93386a5703693f9303c3a59bb7546025`。
- 实施提交：`a8b391da`（组件+测试+e2e+PWF 证据）；本文件所在提交不自列，避免递归。
- 接口版本：施工卡冻结接口（`build_pdf_table_observations`），消费 `du4-interfaces/1` TABLE 契约，未改动任何冻结面。

## 做了什么（根因与产物）

**缺口根因**：PDF 的 DU3 fine 几何（精确 cells/words/char offsets）已在 `du-input/1` wire 上，
但生产表观察只有 HTML 桥（`hints.native_tables` ← `metadata.native_source_view.tables`）；
`bind_native_tables` 对 PDF 产出 0 张表，且 `_wire_kind` 对每张抽取表的第 0 行无条件标 `table_header`
（续表数据行也被当表头）。retained 样本适配 `real_packet.py` 的 `HEADER_ROWS=(0,1,2,3)` 是测试常量，
不能作为生产方案。

**产物**：纯内存适配组件
`src/company_wiki/document_normalization/pdf_table_observations/adapter.py`
（导出 `company_wiki.document_normalization.pdf_table_observations.build_pdf_table_observations`），
把 `du-input/1` 已观察 fine 槽位 + `du2-layout-hints/1` 共享关系投影为严格 `du4-table-observation/1`，
可由 ROOT 直接喂现有 `bind_operating_table`。不重复原 parser 工作、不重解析、不造引用/空格/跨度/表头。

## 接口

```python
from company_wiki.document_normalization.pdf_table_observations import build_pdf_table_observations
from company_wiki.document_understanding.layout_hints.contract import WorkBudget

built = build_pdf_table_observations(observation, layout_hints, *, work_budget: WorkBudget)
# {"status": "complete|partial|unavailable", "tables": [<du4-table-observation/1>, ...],
#  "diagnostics": [...], "work_used": <本调用增量>}
```

- 输入：`du-input/1` observation（units 的 `hints.cells` fine 条目 + `table_id/row/source_id` 槽位）、
  `du2-layout-hints/1`（`relations`: header_for/caption_for/footnote_for；可传 None）。
- 输出：每张表严格 `du4-table-observation/1`（scope/units/cells/header_rows/provenance(native_slot)/truncated）。
- 语义要点（详见 findings.md A-2/A-4）：ref 仅在 `char_alignment=exact` + frame 已知 + 回切完全相等时产出；
  header_rows 取共享 `header_for` 行 ∪ 未被共享数据行组反证的 wire `table_header` 行；
  行标签 = 非表头行最小原生列格；span 恒 None；空位丢失不造格；多单元承接同格只搬真实 refs。
- 计费：单一共享 `WorkBudget`，公式固定于模块 docstring（entry 1、unit 1、fine 格 1、
  切片 (end-start)//64、关系/成员 1、表收尾 1、provenance 1、header_ref 1、unit 物化 1）；
  耗尽保留已闭合表并回 `partial`。

## 如何复现

```powershell
# 组件行为测试（30 项）
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
python -B -m pytest -q tests/unit/pdf_table_observations
# 旧 TABLE/layout 集中回归（516 passed/24 skipped）
python -B -m pytest -q tests/unit/du4_table_measurements tests/unit/document_understanding_root `
  tests/unit/document_normalization_layout_snapshots tests/unit/document_understanding_layout_hints `
  tests/unit/test_shared_reading_pdf_layout.py tests/unit/test_shared_reading_pdf_table_policy.py `
  tests/unit/test_shared_reading_layout_coverage.py
# 真实原件 E2E（原件只读；示例为开发回归样本，路径/哈希来自主 PWF sample_manifest）
python -B e2e/run_e2e.py --manifest docs/plans/document-understanding-2026-10-13/sample_manifest.json `
  --sample hk-annual --pages 12 --language zh --work-dir <你的临时目录> --out <receipt.json>
```

DU3/DU2 旧测试目录的本地 fixtures 不在本 sparse 工作树视图内，已
`git sparse-checkout add tests/fixtures/document_normalization_layout_snapshots tests/fixtures/document_understanding_layout_hints tests/fixtures/document_understanding_structure`
物化（同 commit 只读内容，未改任何文件）后按原样运行。

## 测试结果（receipts/）

| 项 | 命令 | 结果 | receipt |
|---|---|---|---|
| RED-1 首个行为红 | `pytest -q tests/unit/pdf_table_observations`（实现前） | exit 2，组件导入收集失败（6×ModuleNotFoundError，pytest 中断；缺口演示同轮未执行到） | receipts/red-1-pre-implementation.log |
| RED-2 行为红重放 | 同上（隐藏实现、`--continue-on-collection-errors`） | 3 failed + 6 errors（组件缺失）+ **3 passed（公开链缺口/错误假设演示）** | receipts/red-2-behavior-replay.log |
| 组件行为测试 | 同上（实现后） | exit 0，**31 passed** | receipts/component-tests-final.log |
| 旧集中回归 | 见上 | exit 0，**516 passed / 24 skipped / 0 failed** | receipts/old-suite-regression.log |
| Ruff | `python -m ruff check src/.../pdf_table_observations tests/unit/pdf_table_observations` | exit 0 | receipts/ruff-final.log |
| E2E 名创 p12（开发） | `run_e2e.py --sample hk-annual --pages 12` | 2 表，12 bound/4 ambiguous，complete，逐值回切全等 | receipts/e2e-hk-annual-p12.json |
| E2E 恒锋 p61/62（开发） | `--sample cn-equity --pages 61 62` | 4 表，43 bound/2 ambiguous，complete，1×HEADER_EVIDENCE_CONFLICT | receipts/e2e-cn-equity-p61-62.json |
| E2E 金禾 p223/224（**holdout**） | `--sample cn-convertible --pages 223 224` | 0 表/partial：上游 layout 捕获 64 页硬上限，目标页 LAYOUT_CAPTURE_DEFERRED；保守降级不造格 | receipts/e2e-cn-convertible-holdout-p223-224.json |
| E2E 金禾 p25/26（holdout 附注） | `--sample cn-convertible --pages 25 26` | 3 表，17 bound/4 ambiguous，complete（换公司/格式绑定泛化） | receipts/e2e-cn-convertible-addendum-p25-26.json |

四次 e2e：parse_count=1、`all_slices_match_original=true`（每个 measurement 的 value_ref 逐一回切解析原文
并记 SHA-256/source/page/table/offset）、原件 SHA 前后逐字节一致、Temp/sentinel 全部回收（receipts/cleanup-c.json）。
手工期望（findings.md A-3）在 test_2 落地：双期同数值两 ref 各归其列、行标签/单位/范围指向各自原片段、缺失→unknown。

## 局限（known_limits）

1. **深页表格无 fine 几何（真实 holdout 暴露）**：`layout_snapshots.identity.DEFAULT_LIMITS["max_pages"]=64`
   且 `resolve_limits` 只可收紧，`PdfLayoutCollector` 捕获窗口外的页（金禾 p223/224）没有 cells；
   组件按契约回 unknown/partial。绑定质量在深页 holdout 上未验收（见 not_run）。
2. 上游 `capture_table` 只留有值且有 bbox 的格：空位与合并跨度丢失 → `presence=empty/merged_unknown`
   不会由本组件产出，span 恒 None；缺 bbox 的值不造槽位。
3. 行标签=非表头行最小原生列格（≥2 格时）；转置表会误挂（反例见 findings A-4-2）。
4. wire `kind=table_header` 是 row-0 无条件声明；共享引擎无该表视图时它仍是唯一表头证据（保守保留旧行为），
   有反证时按共享行组否决（恒锋真实数据上已发生 1 次）。
5. words 载体不用于值定位（禁止按 value 字符串全局查找）；NFC 非严格相等的引用一律不产出（真实运行 0 例）。
6. 结构合法≠经营/期间解释正确：period/unit/scope 解释由原 binder/下游负责。

## not_run

- holdout 金禾 p223/224 的**绑定质量验收**：被上游 64 页捕获硬上限阻塞（运行已执行并诚实记录 0 表/partial，
  不伪称通过）；换公司/格式的绑定泛化由 p25/26 附注 + test_6/test_7 覆盖。
- 名创 p12/恒锋 p61-62 之外的主 PWF 样本页（cn-h1/cn-ipo/...）不在本卡范围，未运行。

## ROOT 接线步骤（本作者不做）

1. 生产组合（`pipeline.understand_units` TABLE lane 或 `native_table_bridge` 旁）在
   `apply_layout_hints` 之后调用 `build_pdf_table_observations(observation, layout_hints, work_budget=shared)`，
   对每张表以**同一 WorkBudget 实例**调 `bind_operating_table`；一处调用点即可，依赖闭包=本包+现有两包。
2. 解释必需 refs（header/period raw labels、unit/scope/qualifier）进入现有选择依赖闭包
   （du4_production_integration.md §4 第 3 步）。
3. 决定深页 layout 捕获策略：按目标表页定向捕获或调整 `PdfLayoutCollector` 捕获上限
   （`resolve_limits` 现在只可收紧；属 ROOT 冻结面）。
4. 源增强提案（有反例，见 findings A-4-6）：wire 投影 parser `table_headers` 真实表头行观察、
   真实 row-label 观察（等价 HTML `header_scope="row"`）、capture_table 保留空位/合并 span。
5. 真实 HK 保留包 + 未见公司/格式 holdout 的逐 claim 核对在 ROOT/母 PWF 验收节点执行；
   组件 C 不算正式摘要验收。

供应商调用 0；生产写入 0；未改主目录、兄弟工作树、CI、hooks、旧断言/金样。交付后 owned 源码冻结，STOP 等 ROOT 接收。

## 独立审查（第二轮）

独立 agent 逐条核对施工卡/INTERFACES 全部接收要求（含实跑 pytest/ruff 复核）：**无必须修复项**。
其 6 条建议中已落实 4 条：① red-1 收据描述改为与留档日志逐字一致（原措辞提到未留档的中间轮 TypeError，
已更正并注明事实以留档收据为准）；② test_2 补"亿元/US$千元/人民币元/复合单位"显式用例（31 项）；
③ e2e 收据分母增加 `wire_table_claims`（wire 表声明数）并把 `table_claims` 更名 `tables_built`
（holdout 的 3 个声明现直接可见）；④ 逐值记录 `source_id` 改用规范 urn（`source_id_for_sha256`）。
未落实并保留：pytest 收据日志内的工区绝对路径（本机路径属日志固有内容，原件机器路径从未提交；
如 ROOT 要求脱敏可后处理）；`e2e/` 位于仓库根（与施工卡 §5 "提供自有 e2e/run_e2e.py" 的字面一致，
请 ROOT 合并时确认归属）。审查后 e2e 四份收据由最终脚本重新生成，组件实现自 holdout 观察后未再改动。
