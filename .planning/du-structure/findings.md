# DU-STRUCTURE 调查发现

## 上游契约（INTERFACES.md 第 2、4 节）

du-input/1：`{schema_version, source_ref{source_id,source_sha256}, metadata{...}, coverage{native_scan, opaque_pages, deferred_pages}, units[]}`
unit：`{unit_id, ordinal, locator, page, text, kind, language, role, layout{bbox,page_width,page_height,column}, hints{heading_level,table_id,row,column,speaker,turn_id,dom_path}}`

du-structure/1 输出：`{schema_version, source_ref, sections, semantic_units, relations, coverage, diagnostics}`

limits 默认：max_units=50000、max_relations=100000、max_group_members=64、max_work_units=2000000。
调用方更低值优先，显式 partial。

## 关键约束（逐字摘自接口）

- 所有 unit 只属于输入的一份 source；ordinal 从 0 递增唯一。
- locator 是 opaque 字符串，模块不能重新编号或解析其中公司/目录。
- text 为内存原语言文本，输出结构默认只保存 unit 引用。
- 无网络/磁盘写入/读取配置/当前时间依赖。相同输入相同输出，排序稳定。
- 不读取公司名/证券代码做特判。
- 不能导入 profiles 包；识别 generic 章节结构。
- relations kind ∈ {continuation, header_for, footnote_for, question_answer, language_parallel, section_cross_reference}
- coverage 不把 complete 映射为全业务召回。
- 避免对全文 units 两两比较；按页/邻接/章节线性或 n log n。

## 现有代码事实

- `NarrativeUnit`（source_catalog/narrative_document.py）字段：unit_id/source_id/parser_name/parser_version/
  coordinates(EvidenceCoordinates)/raw_text/unit_kind/source_role/language/quality_flags/metadata。
  其 `metadata` 常用键：`source_locator`、`bbox`、`pdf_block`、`block_char_start`、`block_char_end`、
  `table_headers`、`row_cells`、`table_index`、`row_index`。
- `EvidenceCoordinates` 有 page_number/paragraph_index/char_start/char_end/table_index/row_index/column_index
  （narrative_project_context 与 narrative_pdf_groups 用法可证）。
- `narrative_context._scan_pages` 每页重置上下文 → 这是设计文档点名的缺陷（跨页丢上下文）。
- `narrative_pdf_groups._visually_continues` 用同一 `pdf_block` 或 bbox 垂直间隙 ≤16 且水平重叠 ≥60%。
- `narrative_pdf_qa.pdf_qa_parts` 识别 `问/问题`/`N、`、`答复|回答|答|回复`，并区分
  investor_question / management / unknown；state 含 question_paired / question_unanswered /
  question_continuation / answer_paired / answer_continuation / before_first_question。
- `narrative_project_context` 用 `_INTRO`（募集资金…投资于以下项目）、`_PURPOSE`（运用方向|投资项目|项目名称…）、
  `_PROJECT`、`_FINANCE_ONLY`（补充流动资金|偿还|合计）判别募投项目行；要求 intro 与行块水平重叠 ≥60%、
  垂直间隙 0..72，且中间块必须是 `单位/币种` caption；歧义表（两个候选间隙差 ≤1）放弃绑定。
- `verify_unit_identity` 绑定 source_id/sha/format/locator/text_sha/kind/role/parser_version。

## 真实样本要点（来自 findings.md / design.md）

- 恒锋 2020 增发 p62：页首承接上页项目表，页中投资/用地，页末建设期续到 p63。物理页切块会断项目语义。
- 名创 2024 港股年报 p12：中英左右栏，同表含 2023/2024、内地/海外、直营/合伙/代理店数 + TOP TOY 表。
- 万润 p3：“不生产 VC”否定与问题中的合作设想相反 → 否定必须保留。
- 中微 2026Q1 p3：同页混薄膜设备开发、EPI 验证、财务增减原因和表头。
- 鼎龙 IPO 确认意见 p1：扫描单页，原生文本为空 → opaque，不能空文本直接 skip。

## C 节点真实观察（2026-10-13，只读三份原件）

工具：`.planning/du-structure/c_node_real_check.py`（调查入口，非产品代码）。
证据：`.planning/du-structure/c-evidence/c_node_evidence.json`；摘录 3216/4321/8147 字节，
均 ≤8KiB/文档。原件未复制、未修改。

| 样本 | 页 | units | sections | relations | 结果 |
|---|---|---|---|---|---|
| 名创优品 2024 港股年报 | 12 | 49 | 5 | continuation, language_parallel | 观察到双栏对齐 |
| 恒锋工具 2020 增发 | 62–63 | 77 | 16 | continuation, footnote_for | project 跨页包 |
| 万润股份 IR 记录表 | 2–3 | 109 | 5 | continuation, question_answer | QA 否定保留 |

### 关键真实发现

1. **真实 parser 的 `language` 字段不可用**：名创 p12 英文栏单元 `language` 也是 `zh`。
   改用文本自身的书写系统（CJK vs Latin）+ 真实并排几何作为 lane 证据。
   这是设计文档没写到的；已在 `layout.script_of` / `side_by_side` 落地并加测试。
2. **真实 parser 不输出 `column`**：`narrative_evidence._emit_pdf_text_units` 只写
   `bbox/pdf_block/block_char_*`，没有列号。几何并排推断是当前唯一可用证据路径。
3. **真实 parser 不输出 `heading_level`**：全部 `pdf_text_block`。
   三份样本都出 `NO_HEADING_EVIDENCE`；章节完全依赖编号正则（第X节 / 一、 / （一））。
   → 需要 ROOT 在 du-input 适配层补 heading_level，否则 confidence 上限为 medium。
4. **QA 页被 parser 输出两次**：万润 p2–3 同时有 `investor_question`/`management` 角色单元
   和 `qa_text_shadow` 单元，unit_id 不同（不同 SHA-256）。两个 QA 包内容近似但成员不同。
   本 lane 不去重 —— 删除任一侧即违反「不得删 source unit」。
   → ROOT 合并层需决定保留哪一套角色，这属于 adapter/选择职责。
5. **恒锋跨页项目**：真实数据产出 4 个 project 包，其中一个 9 成员带
   `CROSS_PAGE_CONTINUATION`，说明 p62→63 的建设期延续被保留。
6. **万润否定**：QA 包 `m2` 完整包含「公司现无生产 VC（碳酸亚乙烯酯）的情况」，
   与其提问「VC 的带量采购」同包，completeness=complete，否定未被丢弃或改写。

### 未证明的部分

- 名创 p12 的 `operating_table` 未产出：真实表格被 parser 输出为单个 `pdf_table_row`，
  没有 `table_header`/`table_caption` 兄弟单元，因此本 lane 无法建立表头依赖。
  → ROOT 需要在适配层补齐 header/caption 分区，或由 parser 提供 table 结构。
- 三份样本均 `native_scan=partial`（只解析了指定页），因此 `coverage.complete`
  的语义在 C 节点无法全文档证明；报告按 partial 陈述，未标 PASS。
- 未做：真实 LLM、完整召回率、跨文档变化、生产接线。


1. 纯 JSON Mapping 入出，内部 dataclass；不 import profiles；不新增依赖。
2. 章节构建以「扫描序 + heading 证据 + 布局/分栏」为据；页眉/页脚/TOC 由重复文本与页码模式识别，
   转成 diagnostics/relations，不产生新正文 section。
3. 跨页延续靠 section 栈 + 有限窗口；遇新同级 heading 停止；换页不清空项目上下文。
4. semantic unit 六类：paragraph_event / qa_exchange / project / operating_table / risk / background。
5. 预算：max_group_members 与 max_work_units 双限；超限出 partial + deferred。
6. 关系图用显式 kind 白名单 + 环检测（DFS），禁止无限展开。
7. 语言 lane：仅当 layout.column 或 DOM/文本对应证据存在时输出 language_parallel；
   对齐只做引用，不翻译、不删除任何 unit。

## 设计决策（本 lane）补充

8. lane 证据分级：(a) 显式 `layout.column`；(b) 同页不重叠 bbox + 垂直对齐 + 书写系统不同。
   两者都不满足则不输出 `language_parallel`。
9. 章节 confidence：`layout_inconsistent`（bbox x1<=x0、超出页宽、列号与 x 位置矛盾）时强制 low。
10. 依赖环判定方向：新增 from->to 成环 ⟺ to 已可达 from（不是 from 可达 to）。
11. 性能：单次 `by_id` 索引 + 按页预索引；log-log 斜率 1.14。
