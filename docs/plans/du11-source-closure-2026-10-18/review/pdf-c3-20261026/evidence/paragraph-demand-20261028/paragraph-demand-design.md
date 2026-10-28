# 段落增强需求：窄范围结构根修与 TDD 施工方案

状态：READ_ONLY_DESIGN_READY。基于已发布 SOURCE v6c / ec7c8d84；本轮未改源码、测试或 PWF，未运行原生 PDF、SDK、模型或下载。读取了 PARAGRAPH_DEMAND_ROOT_PLAN 与 paragraph-demand-v1.json，并用 CodeGraph 定位责任层。

## 已证实的问题

`source_catalog/narrative_pdf_paragraphs.py::triage_paragraph_gaps` 已先构建 observation、运行 `build_native_continuity`，排除已闭合的原生边，随后对同页相邻 pdf_text_block 检查几何、尾标点和两个文本启发式。它没有消费表行完整覆盖或已证明 furniture。`_DEPENDENT` 中裸 `其` 从起始位置匹配任意后续字符；`其他` 因而被当成从属尾句。`\d$ + dependent` 又升为 priority3。另一条 `len(left)>=32 + CJK/lowercase right` 会把完整数值行对当成 prose。

现有 triage 快照中 12 条原因可分为：9 条完整“标签＋多数值”行之间的边，2 条报告页脚与“其他資料”之间的边，1 条长披露标题与正文之间的边。前两类不需要业务/财务分类即可解释。最后一条只有文本预览，不能据此证明是标题边界或真正段落断裂，应保留为待物理证明项。快照只收录排名前三页及最多64原因，不能由这12条推断修复后只剩1页；重排后可能出现此前未入选的原因。

## 责任层与最小接口

1. **paragraph owner 决定是否存在未闭合物理边**。改动主文件仅 `source_catalog/narrative_pdf_paragraphs.py`。保留现有 source/page/role/kind/frame/rotation/column/overlap、终止标点、native proven-edge 和 unexamined boundary 约束；在文字启发式之前消费下面两种正向结构证明。不得调用 SOURCE business purpose/support classifier，不变更已审 admission、offer 或 heap。
2. **表行完整覆盖直接复用** `document_normalization/table_shapes.py::observe_value_cells(text)`。现有返回 `ValueCellObservation(unbound_numeric_cells, complete_value_row)`；本节点不需要修改其语法。每个原始 unit 在同一共享 WorkBudget 预收费后仅准备一次、按原 unit_id 本地缓存。仅当 **left 和 right 各自 complete_value_row=True** 才把“完整 row/scalar 对”排除出 prose-gap 候选。不能使用 numeric presence、table_region、财务章节/科目、数字比例或“任一侧是 row”。此证明不赋予数字列、期间或经营意义，也不改变原文/表格可读性。
3. **furniture 仅消费已有正向证明，本节点不扩检测能力**。现有 `document_understanding/structure/layout.py::_running_furniture` / `order_units` 返回的 `Ordering.running_header_ids` 可供已有结构路径复用；其纯页码序列要求打印页码等于物理页码。当前“二零二五 中期報告16”与物理17页不满足该规则，也不属于相同文本重复，不能宣称已证明 furniture。此次最小实现不新增 detector/公开 wrapper，不为获取 furniture 重跑 build_structure/apply_layout_hints。若已有输入确实携带同源可靠家具证据，可保留既有 exclusion；无证据则不排除。实际两条短页脚→其他資料的边将在依存词边界修复后自然失去 dependent 条件，又不满足 left>=32 的 wrapped-prose 条件，无须扩展页脚词表或几何阈值。
4. **词内边界留在 paragraph 的既有 physical-tail grammar**。将从属匹配准备为每个右端一次的观察，复用同一结果决定 reason/priority，避免当前重复 search。修正单字 `其` 与完整词 `其他/其它` 的边界，保留真 `其…`、`其中…`、该/上述、因果连接和金额单位尾句。可以在既有正则中表达这个词内边界，不能靠完整标题/句子 blacklist，也不能借产品词表限制所有可读正文。财务、审计、股份或行业页没有 special case。
5. **recipe/cache 仍由 PDF reading owner 维护**。`ParagraphRuntimeConfig.recipe` 已把 paragraph 文件绑为 alignment_sha256，修改主文件将使本次 recipe 改变。增加 shared table 调用后，须在同一现有 recipe 描述符中绑定实际实现依赖（例如一个有界 `triage_dependencies_sha256`，覆盖实际使用的 table_shapes LF 规范源码；本节点不凭空加入未调用的 furniture helper）。不新建 registry/缓存库，不修改 worker request/schema。沿用 PdfReading 的 frozen-recipe 比对，测试 helper 字节变化能使 recipe 漂移被拒；不能只依赖主文件变化遮盖未来 helper-only 更新。

## 直接实施顺序

先在现有 `test_pdf_paragraph_alignment.py` 或同层新 test_pdf_paragraph_demand.py 加中性 in-memory NarrativeUnit/layout 反例，记录实际 RED；随后只接通上述结构观察并修 physical-prefix。triage 内原始 unit 顺序和邻接关系不动，预收费/一次准备后 pair loop 只查 cached facts。不生成“整页无业务/完整读取”的结论，也不承诺0 SDK。保持 max_pages/原因条数、runtime 时间/内存/输出、single converter、offline 和原生 fallback 原样。

随后补 recipe 依赖绑定及真实 no-gap→runner0 次的纯 runner-spy 接线。已有 alignment/原始字符/strict member/checkpoint 契约不重新实现。若既有测试因新共享准备耗费 WorkBudget 而暴露过小局部测试夹具，先核真实工作和边界，不抬生产额度或删预算断言。

## TDD 矩阵（以下均为待实施预期，未运行）

| 边界 | 中性输入/结构 | 预期 |
|---|---|---|
| 两完整行 | `Active customers\n125\n160` → `Other\n23\n–`；CJK 与括号/currency/脚注格式同族 | 无 prose demand；不推断 financial/经营表列 |
| 两纯 scalars | 分隔数字值/破折号，完整覆盖两端 | 无 prose demand |
| 混合 prose | 同一 unit 中既有 prose 与 row；前/后、两文本头组合 | complete_value_row=False，不因存在数列而排除；原 gap 条件满足时仍 demand |
| 只有一侧 row | row → 真说明正文；正文 → row | 不凭 row 排除另一侧未解释正文 |
| 金额尾句 | 现有 `… revenue of 12.4` → `million dollars; rollout is not yet approved.`，CJK `百萬/億元` 同族 | 真 amount tail 仍入选，source/否定原文不改 |
| 真实从属 | 未终止正文 → `which…` / `because…` / `其交付计划仍未获批准。` / `其中…` | 原几何合法且 native 未闭合时仍可增强 |
| 词内其 | 完整独立行/标题 `其他資料`、`其它事项` 与其真从属对照 | 不能以裸其判 dependent；其他条件独立满足时仍可保守 demand，不整词封禁正文 |
| 已证明 furniture | 同源重复 page-edge 文本/现有已证实数字计数序列 → 标题或真 dependent 文本 | 不产生正文续句需求；保留 raw ID/locator |
| 未证明 furniture | body 内重复文本、孤立 edge 数字、不同 source/页码不符、缺几何/计数冲突 | 不授予 furniture 证明；不因“像页脚”排除候选 |
| 真经营表说明 | 表附近产品/客户说明发生实际金额/从属断裂 | 原 gap 条件满足则保留，不按整页/table_region ban |
| 原生已闭合/屏障 | 现有 closed edge、source/role/page/column/frame 差异 | 保留现有约束，不重复昂贵增强或越界拼接 |
| 工作与缓存 | 小 budget、n/2n 单元代理计数、同一右端重复邻接查询 | 不假报完整；shape/marker 每 unit 至多一次，实际计费，无上限提升 |
| 接线与版本 | runner-spy no-gap；真 gap；dependency-byte mutation；旧 recipe | no-gap 0 子进程，真 gap 保留一次调用；实际依赖变动使旧 recipe 失效 |

必要短包：新增 demand 控制、既有 test_pdf_paragraph_alignment、runtime runner/fallback/recipe 用例、page_counter_furniture，以及不启动真SDK的已有 native-continuity/reading integration 对应节点。无需重跑 SOURCE 全域；不把使用 synthetic PDF 的单元测试误称真实原件复验。

## 一次真实复验与结果边界

ROOT 完成测试和独审后，在同一原件/SHA、原资源和现有共享预算下，执行**一次 native read＋triage 观察**；不启动 Docling。复用原观察脚本的 unit ID/text/layout，逐条记录新旧 gap reason、排除依据（两端完整覆盖/已证 furniture/词内边界）和实际 work，检查新浮出的排序原因，不能只比较页数。冻结源 SHA、全部 units 数、source-byte unchanged、pages/reasons、原始范围和耗时。对剩余每个 demand 判明“物理未闭合且值得增强”或“证据不足保留”，不能为了零页数修掉真实断裂。

然后沿 ROOT 已配置的一次 source selection/五金标与全views检查原有业务、未来/否定、未知数列和 required-context 未退化。native 诊断不等于 configured SDK 成功，也不等于新摘要通过。若仍有真 demand，再进入既定 isolated SDK 有界启动与正式供应商摘要节点；本方案不调整120秒/4GiB/3页/2MiB或规避离线配置。
