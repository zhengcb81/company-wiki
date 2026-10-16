## ROOT接收更新 — 2026-10-16

ROOT接收组件验收通过，待正常提交/并线/远端；不是生产摘要接线完成。独审6类RED：partial碎片假整体数值、无观察的首格标签导致丢值、耗尽后O(rows*cells)扫描、坏格丢弃仍complete、fine页矛盾、header跨scope。隔离修复后43短测通过；逐row索引一次、排序/复制预付，耗尽尾部扫描由12万/49万/194万line变72/72/72。真实名创年报p12单parse、2表28格16值（12bound/4ambiguous），所有引用核对；2M预算用1,162,753、原件/配置SHAmtime不变，0供应商。集中557PASS/24SKIP/2FAIL均为ROOT稀疏树漏检出旧DU2资产，补既有夹具后原两项2PASS/4.03s，原失败保留，不改旧断言。六个本次作者新测试的错误首格/耗尽假设已保存原zip并纠正，旧binder/layout金标没改。全局e2e runner移入本PWF/e2e避免未来外包冲突。深页223/224因上游64页capture未覆盖，未知merged/空格/行标签及正式selection/summary/RF仍OPEN，由ROOT来源层后续解决。

**Next Step：** 正常提交并主线、可用远端发布和相关技能文件定点同步，由ROOT归总母PWF。

---

# 调查

ROOT已核对真实已提交代码基线。卡内已复现/静态/待验证范围分开；不得把旧stale PWF重派为任务。尚未实施本卡。

## A-1 只读调查事实（真实代码，2026-10-16）

均在本工区源码基线 `04c7f1bc` 内只读核实：

1. **PDF fine 载体（DU3 几何捕获）**：`source_catalog/narrative_pdf_layout.py::PdfLayoutCollector`。
   `capture_table(page, index, table, rows)` 只保留**有值且有 bbox** 的 cell（`text/bbox/native_index/row/column/table_id="p{page}:t{index}"`）；
   空格、缺 bbox 的格与合并跨度信息在上游已丢（卡 §0 属实）。`_binding` 为 `pdf_table_row` 行单元
   计算每个 cell 在行原文（`" | ".join(非空格)`）内的 `char_start/char_end`；QA 碎片单元走 fragment 路径
   （`text=单元原文`、`native_cell_char_start/end`、`partial_cell`）。经
   `layout_snapshots.unit_binding.bind_binding` 投影后成为 `hints["cells"]`（含 `char_alignment`、
   `row/column/table_id`、`page`、`coordinate_frame`），`words`/`font_runs`/`spans` 同理进入
   `hints["words"|"font_runs"|"spans"]`。`observation_adapter._FINE_LAYOUT_FIELDS` 冻结了这些 wire 字段名。
2. **du-input/1 wire 表证据**：`observation_adapter.build_observation` 为表行单元输出
   `hints.table_id="p{page}:t{index}"`、`hints.row`、`hints.column`（行单元为 None；QA 碎片有列）、
   `hints.source_id`（parent）；`kind="table_header"` 只由 `_wire_kind` 依 `row_index == 0` 判定
   （**无条件第 0 行假设**，行 0 为空时真实表头行反而为 `table_row`）。parser 元数据
   `table_headers`（首个非空行）与 `row_cells` **不在 du-input wire 上**（`build_observation` 不投影）。
3. **du2-layout-hints/1 共享关系**：`layout_hints/__init__.py` 产出 `groups`（`table_region`/`table_row`/`caption`/`footnote`，
   `cells[]` 带真实 native row）与 `relations`（`header_for`（basis `header_row|header_block`）、`caption_for`、`footnote_for`、`continuation`）。
   fine cells 在 `fine_geometry.consume_fine_geometry` 中以严格校验拆成视图：`_range` 要求
   int 偏移 + `char_alignment=="exact"` + `text == unit.text[start:end]` 完全相等，`_frame_valid` 要求
   `coordinate_frame in {"dict","page"}` —— 与本卡"回切原text完全相等 / frame已知+exact"要求同源。
4. **du4-table-observation/1 与 binder**：`native_table_bridge._observation` 是现有 HTML 生产投影
   （scope/units/cells/header_rows/provenance(native_slot)/truncated）；`table_measurements.bindings`
   消费该 schema：header_rows 中 present 格的 refs 成为列路径（期间/单位来自 label 扫描）；
   `header_refs` 中出现过的 ref 视为标签、不产生 measurement；`row_label_refs=header_refs-列路径`；
   span=None 按单格处理、`truncated=True` 阻断 complete。`tests/unit/du4_table_measurements/real_packet.py`
   的 `HEADER_ROWS=(0,1,2,3)`、bbox 推 span 是测试样本适配（文档头自述），不是生产依据。
5. **现有缺口（RED 依据）**：`native_table_bridge.bind_native_tables` 只读 `hints.native_tables`
   （来自 `metadata.native_source_view.tables`，仅 HTML parser 产出）；PDF 解析后
   `hints.native_tables` 不存在 → 现行公开链对 PDF 表格产出 0 张表（生产观察缺口）。
   另 `_wire_kind` 把续表（无表头行）的第 0 个数据行也标为 `table_header`（错误 header 假设）。
6. **入口与预算**：`layout_hints.contract.WorkBudget`（charge/used/exhausted）为唯一共享逻辑预算；
   `layout_bridge.apply_layout_hints(observation, work_budget=...) -> (observation, du2-layout-hints/1)`；
   `source_catalog.narrative_evidence.parse_pdf_bytes`（`selector_version="0.9.0"` 启用 PdfLayoutCollector、
   `table_pages=` 指定表页）为真实单次 parse 入口。

## A-2 字段映射表（真实 fine 载体 → du4-table-observation/1）

| contract 字段 | 来源（真实字段） | 规则 |
|---|---|---|
| `scope.parent_id` | `unit.hints.source_id`，缺省 `observation.source_ref.source_id` | 原样搬用，不重算 |
| `scope.table_id` | `unit.hints.table_id`（如 `p12:t0`） | 复用页面原生身份；(parent, table_id, page) 三元组定作用域，跨 source 同编号绝不合并 |
| `scope.page` | `unit.page` | 原样搬用 |
| `units[u].text/parent_id/role/kind/locator` | `unit.text / hints.source_id / unit.role / unit.kind / unit.locator` | 不改字串/ID/locator |
| `cells[].row/column` | fine cell 的 `row/column`（capture_table 原生槽） | 与所属单元 `hints.row` 不一致则弃用并诊断；不按文字顺序/右对齐/年份推列 |
| `cells[].row_span/column_span` | 无观察 | 恒为 `None`（不默认 1、不拆 merged 格） |
| `cells[].presence` | fine cell 观察 | 有值观察=`present`（ref 验证失败仍 present、无 ref、记诊断=定位 unknown）；`empty` 只给实观察空格（PDF 上游不留空格，故本组件不产出 empty）；未观察槽位不产出格、不造 TextRef |
| `cells[].text_refs` | fine cell `char_start/char_end` + `text` | 仅当 `char_alignment=="exact"` 且 `coordinate_frame in {"dict","page"}` 且 `unit.text[s:e] == cell.text` 完全相等才产出；不做字符串全局查找（relocated 不可用） |
| `cells[].header_refs` | ① caption_for/footnote_for 组成员单元全文 ref（context）②同行最小原生列格（行标签）的已验证 refs | 逐 ref 回切完全相等；外 parent/越界 ref 弃用并诊断 |
| `header_rows` | ① `relations.header_for` from 组成员行（共享关系）② `unit.kind=="table_header"`（原生关系）不被共享行组反证时 | 无固定常量；不按第 0 行/最新年一概判定；无证据=不设（binder 报 no_header_path/ambiguous） |
| `provenance[]` | `{"kind":"native_slot", cell_id,row,column,row_span,column_span}` | 每格一条实际 native slot 记录（span 键显式 None=未观察） |
| `truncated` | 行覆盖检查 | 任一 `hints.row` 行无任何可用 fine cell（槽位信息丢失）→ `True`；不为补矩形造格 |

words 载体说明：`pdf_table_row`/QA 碎片单元没有文本块 words（`_binding` 只对 pdf_block 单元收集 words），
且用 words 反查 cell 值属于"依局部 value 字符串全局查找"禁项，故 words 不用于值定位；cell 的精确
scalar offsets 才是值定位依据。fine cell 的 `native_cell_char_start/end`、`partial_cell` 原样保留为
多单元承接同格时的真实片段来源，不伪造连续原文。

## A-3 手工期望（合成小样本，独立于实现编写）

样本表（行原文 `"项目 | 2025年 | 2024年"`、`"直营门店 | 16 | 16"`、`"单位：人民币万元"` caption）：

1. **双期同数值**：值 `16` 在行原文出现两次，两 ref 分别指向各自偏移（不同 (char_start,char_end)），
   同字符串不合并、不全局查找；经原 binder 后分别绑定 col-1（period end 2025-12-31）与 col-2（2024-12-31）。
2. **行标签**：`直营门店` ref（同行最小原生列格）出现在两值格 `header_refs` → binder
   `row_label_refs` 指向该片段；该 ref 不产生 measurement。
3. **单位**：caption 片段 `单位：人民币万元` 的 ref 进入各格 `header_refs` → binder `unit_refs`
   指向该片段（原词不变更、无万元/亿元换算）。
4. **范围**：行标签含范围词（如 `亚太地区`）时其 ref 经 binder `scan_label` 进入 `scope_refs`，
   指向标签片段本身。
5. **缺失→unknown**：无 header 证据列 → `period=null`、`no_header_path`、值 ambiguous；
   缺 bbox/越界/非 exact 对齐 → 不产出 ref（present 无 ref）；未观察空位 → 无格无 ref；
   span 未知 → None；均不猜。

## A-4 语义决策与反例（组件按保守降级执行）

1. **header 证据**：`header_for` 共享关系 ∪（未被共享行组反证的 `kind=="table_header"` 原生关系）。
   反例（RED 演示）：续表（无表头行）第 0 行是数据行，`_wire_kind` 仍标 `table_header`；
   共享引擎把它分入数据行组且无 header_for → 本组件不判为表头。无 layout_hints/无共享视图时
   原生 kind 是唯一已观察关系，保留旧行为（记录为 limit，ROOT 接线建议见下）。
2. **行标签关系**：数据行（非 header 行）≥2 个已观察格时，同行**最小原生列**格为行标签格，
   其已验证 refs 挂到同行其他格的 `header_refs`（与 DU4 测试 `test_3_headers_units_scope` 的
   label→values 形态一致）；依据是真实 native 槽位序，不是页上文字顺序/右对齐。反例：转置表
   （标签在首行）会误挂 —— 保留为 limit；ROOT 建议补真实 row-label 观察字段（如 HTML `header_scope="row"` 同类）。
3. **表头缺失不硬补**：无 header 证据即 `header_rows=[]`，交 binder 出 `no_header_path`；
   不按"最新年列"判表头、不硬编码 `HEADER_ROWS=[0,1,2,3]`（与 real_packet 测试适配相反）。
4. **多单元承接同格**：同 (row,column) 的多个已验证 ref 全部保留（各自指向本单元真实片段），
   不拼接连续原文、不择一；歧义语义由原 binder 保持。
5. **状态语义**（本调用准备质量）：预算耗尽→`partial`+`WORK_BUDGET_EXCEEDED`（保留已闭合表）；
   无表证据/无表可产出→`unavailable`；任一表截断/跳过/存在 present 无 ref 的值→`partial`；
   否则 `complete`。work_used 为本调用增量，计费公式在实现 docstring 中固定并被测试断言。
6. **ROOT 需要的新源字段（反例+提案，本组件不改冻结面）**：
   a) parser 的真实表头行观察（`table_headers` 首个非空行）应投影到 wire（现 `_wire_kind` 的
      row-0 无条件假设在行 0 为空/续表时错误）；b) 真实 row-label 观察（等价 HTML `scope="row"`）；
   c) 空格/合并 span 的原生观察（现 capture_table 已丢）。本组件对三者缺失一律保守降级为 unknown。

## A-5 RED（首个行为红，见 receipts/）

`tests/unit/pdf_table_observations/` 先行行为测试：除导入失败外，包含**经现行公开适配链的语义缺口演示**
（parse_pdf_bytes→build_observation→bind_native_tables 对 PDF 表产出 0 张表；续表第 0 数据行被标
table_header 的错误假设），并与非 fixture 常量方案（本组件按关系证据得 header_rows）对照断言。

- `receipts/red-1-pre-implementation.log`：首个行为红。该轮 pytest 因组件导入失败的收集错误中断
  （6×ModuleNotFoundError），缺口演示同轮未执行到。
- `receipts/red-2-behavior-replay.log`：隐藏实现复现缺组件状态的完整行为红
  （3 failed + 6 collection errors 为组件缺失；**3 passed 为经现行公开适配链的缺口/错误假设演示**，
  即"接口未导入不是全部RED"）。中间另有一轮缺口演示复跑曾因本 lane 测试夹具的重复传参 TypeError 失败，
  夹具当场修正且该轮输出未单独留档，事实以上述两份留档收据为准。
  实现提交后行为套件 31/31 全绿（`receipts/component-tests-final.log`）。

## B-1 实施结果

组件 `src/company_wiki/document_normalization/pdf_table_observations/`（`build_pdf_table_observations`），
行为测试 `tests/unit/pdf_table_observations/` 31 项（B-1..B-6 覆盖清单 + 真实管线 capstone + RED 演示）。
计费公式固定在模块 docstring 并被测试断言（合并调用=单表调用之和-1 的单次索引性质）。
旧 TABLE/layout 相关测试集中回归：**516 passed / 24 skipped / 0 failed**
（`receipts/old-suite-regression.log`；du4_table_measurements、document_understanding_root、
document_normalization_layout_snapshots、document_understanding_layout_hints、
test_shared_reading_pdf_*；其中 DU3/DU2 测试目录的本地 fixtures 不在 sparse 视图内，
已 `git sparse-checkout add tests/fixtures/{document_normalization_layout_snapshots,
document_understanding_layout_hints,document_understanding_structure}` 物化后原样运行，未改旧断言/金样）。
Ruff 通过（`receipts/ruff-final.log`）。

## C-1 真实原件 E2E（receipts/e2e-*.json；原件只读、SHA 前后逐字节一致）

| 样本 | 结果 | 说明 |
|---|---|---|
| 名创双语年报 p12（开发回归） | 2 表 / 28 格 / 12 bound + 4 ambiguous / component complete | header_rows=[0,1,2,3] 由共享 header_for 关系证据得出（非 HEADER_ROWS 常量）；ambiguous 全部是左侧合并大格/`Total 合計` 合并格，同 DU4 保留包现象 |
| 恒锋增发 p61/62（开发回归） | 4 表 / 75 格 / 43 bound + 2 ambiguous / complete | 一表 header_rows=[]（无表头证据→unknown）；1×HEADER_EVIDENCE_CONFLICT：真实数据上反证 row-0 表头假设 |
| 金禾可转债 p223/224（**真实 holdout**） | 0 表 / partial / 逐值回切空集通过 | **上游限制**：`PdfLayoutCollector`/`resolve_limits` 硬上限 `max_pages=64`（只可收紧不可放宽），p223/224 在捕获窗口外 → LAYOUT_CAPTURE_DEFERRED、fine cells 0；组件按卡保守降级（TABLE_ROW_SLOTS_UNAVAILABLE/TABLE_CELLS_UNAVAILABLE），不造格不造引用 |
| 金禾可转债 p25/26（holdout 附注，同公司同格式、捕获窗口内） | 3 表 / 17 bound + 4 ambiguous / complete | 绑定路径对未见公司/格式泛化（真实数值 800/30/60…、字符串 "T-2 日" 原样）；组件在 holdout 观察后未再改动 |

全部 4 次运行：`all_slices_match_original=true`（每个 measurement 的 value_ref 对解析原文逐一回切完全相等并记录 SHA-256）、
parse_count=1、原件 SHA 前后一致、临时目录全部删除（`receipts/cleanup-c.json`）。
未定位例子：4 次运行 CELL_TEXT_UNLOCATABLE 均为 0（真实运行中 fine 偏移全部精确）；
unknown 演示由单元测试覆盖（test_3）并在 holdout 以整表 unknown 呈现。

## C-2 真实未覆盖项（交 ROOT）

1. **深页表格无 fine 几何**：layout 捕获文档级硬上限 64 页（`layout_snapshots.identity.DEFAULT_LIMITS`，
   `resolve_limits` 只可收紧），283 页文档的 p223/224 被 LAYOUT_CAPTURE_DEFERRED。ROOT 接线需决定
   捕获策略（按目标表页定向捕获或调整上限），本组件对缺失输入已保守降级。
2. wire `table_headers`（parser 真实表头行观察）与真实 row-label 关系、空格/合并 span 观察仍缺（见 A-4-6）。
3. holdout p223/224 的绑定质量验收受 1 阻塞；绑定泛化证据见 p25/26 附注与 test_6/test_7。
