# OCR empty selection：只读根因与拟 TDD

结论：**需要修复通用 selector 的语义类别及 OCR 视觉分组；此 deck 不应成功 skip。完整度门应保留。** 当前真实大节点仍 FAILED，不能恢复旧 frozen jobs/request 来冒充新版本的选择结果。

诊断 HEAD：`a40eb065da1bb21d231d2644449e2ecd8a2f98d6`。实际失败 run `mocr-20261009T045902-933be853-first`；原 AUTO `C:/Users/郑曾波/AppData/Local/Temp/mOCR-srw9_9oe/auto/first.sqlite3` 保留。证据：既有 [真实失败 receipt](../ocr_major_node/runs/mocr-20261009T045902-933be853/acceptance.json)、本次 [只读 primary/AUTO](primary_evidence.json)、[离线因果结果](offline_selector_probe.json)。

## 真实失败与正确的门

select attempt：`04:59:17Z → 05:01:23Z`，`PARSER_INCOMPLETE` / `empty selection does not have complete coverage`；summary/verify 因 dependency terminal 而 dead_letter。只读当前 AUTO 再证：3 jobs 都 terminal、active attempts=0、reservations=[]、tokens/cost/unknown/unsettled=0，DB SHA/mtime 前后相同。reuse AUTO 未创建；没有付费模型结果。

`NarrativeSelectHandler._select_normalized` → normalization → `language_structure` → `_run_selector` → `_require_usable_selection`。门检查 empty + coverage=false，阻止成功 skip，符合源质量契约。允许非空可信选择返回 `partial` 的现有接线和脚本状态检查不是本次失败原因。

已交付全篇 parser 报告是 22 media / 1067 detected lines / coverage=false；该报告不是此次 failed attempt 的逐行 trace。失败没有保存完整 OCR 文本，本次也未重跑它。离线结果只使用报告中原样保存的有限真 OCR previews，不把这些投影冒充新 OCR 或 provider 回执。

## 根因链

| 检查点 | 实际行为 | 结论 |
|---|---|---|
| role | `document_normalization.units.SOURCE_ROLE=company_filing`；excluded roles 不含此项 | 不是 image_text role 被排除 |
| length/financial | 页7九条已保存 preview 全部 >12；离线 dropped_financial=0；OCR line 不走 `_financial_table` 的 PDF/table-cell 分支 | minlen 和财务表过滤不能解释这些经营口径行的全零 |
| semantics | `_candidate_rules` / `assess_unit` 的动作、progress、operating-fact 类不识别业务归属/报告范围变化及 metric membership 变化 | 即使同句离线拼接，真实 definition 文本仍零候选 |
| grouping | `_pdf_context_groups` → `narrative_pdf_groups._page_units` 仅接 `pdf_text_block`；neighbor lookup 同样仅 PDF | `pptx_image_ocr_line` 的短句/主体/续行不进入已有视觉句子完成逻辑 |
| coordinates | OCR metadata 是 `ocr_box`、image_pixels，现 PDF enrichment 还有 y<60/y>750 正文边界 | 不可仅把 OCR unit_kind 改成 PDF 或机械复制 bbox；会错误排除实际图中 y804/y1264 的正文 |
| budget/finalization | 九条真 preview：candidate=0、selected=0、omitted=0、financial=0、status=needs_review | 不是 selection limit、category fairness 或 dedup 把候选挤掉 |

通用语义缺口是这份材料的直接原因；格式分组缺口是独立共因，会继续影响原本已支持的业务动作被 OCR 拆成多行的材料。新业务词“new product”出现在页7标题并不足以形成一个真实业务动作；不能把标题选中来凑非空。

## 原件业务意义，不强选财务数字

封存 deck SHA `c02f4ea1a2719b74d5752559ad7b907d89dd4b47d292424ade8988396fb2dcd4`，4,016,522 B。本次只按 OOXML display ordinal 7 抽取一个原图并查看，media SHA 与已交付 parser locator 精确相同，没有 normalize/OCR。

第7页原图明确说明 FY27 向两个 reporting segments 过渡，给出各自业务范围，并说明后续 SEC filings 使用更新的产品/服务报告定义；下方包含云产品、developer/security offerings、行业解决方案等归属移动以及服务业务重命名且 otherwise unchanged。这是收入预测口径对齐所需的经营范围/分类说明，不能当作新收入、增长承诺或已经完成的经营扩张。

本次同时通过 `ReadOnlyCatalogReader` 按真实 SourceRef/注册 location 读取已有 SEC FY2025 10-K、验证 SHA `99d693f6c1544144ebeee92954f151a85bc62111837530a42855953bc01d0bbe`。其原文是三分部基线，说明 reportable scope 用于管理与资源分配。它只作 FY2025 基线背景，**不证明 FY27 已实际提交新 SEC 报表**；后者仅是 deck 中的公司声明/未来报告安排。

已有真 OCR 的页7 line20 完整保留了服务业务“previously reported as…otherwise unchanged”的句子；现 selector 仍拒绝。line11 的“now excludes…has moved…”是一条完整检测行，但原图显示同一 bullet 尚有下一行，不能把 line11 独自称为完整语义证据。页18 preview 有 metric 归属变化 footnote，存在 LinkedIn 字形/空格误识且上下文不全，适合作语义回归输入；不能未经精确回放就发布正式摘要。

页7首段首行真实 OCR 已漏识，不能靠原图人工补词伪装成 OCR 结果来宣称“两分部”被选中。源 partial、原语言、缺字/漏行限制继续保留。数值表、页码、metric 名称单行、标题、无动作的业务名仍应排除或留 needs_review，不为工程 PASS 硬选。

## 本次离线反例与结果

`python -B docs/plans/cross-market-rf-e2e-2026-10-08/phase6/ocr_selection_diagnosis/offline_selector_probe.py`

- 九条真页7 preview 的 transient structure 投影：0 candidate / 0 selected / 0 financial dropped。role 反事实改 management 或 image_text 后仍0。
- 真实 definition 行1–3仅为分类拼接：仍0；单条真实 line20 重命名/unchanged：仍0。不是简单“合句就修好”。
- 明确 synthetic 的既有动作控制：`We launched` + `a new product for overseas customers.`，OCR分行0 → 合句1 → 现PDF视觉组2。隔离 format-specific grouping 效果，保留原两条成员 locator 的形式仅是测试结构，不是 deck 真证据。
- 六组标题/数字/metric label/finance-only 增长 negative 均0；synthetic 完整 PDF 财务 row 被财务过滤并合法 skip。普通经营事件识别与财务排除保持各自语义。

实际 probe 先有 setup semver 错误、后有 synthetic PDF bbox 放入页顶导致断言失败；这是诊断夹具错误，未算 product RED。修正诊断夹具语义版本及 PDF 正文坐标后实际 exit0，10项因果断言通过，0 network/OCR/provider/AUTO mutation。没有重跑主套件。

## 拟 owner TDD（尚未实施）

1. **经营范围/报告定义变化的类别**：在候选/OperatingFact 层增加通用、受限的 source-only 事实识别。要求具体业务/产品/服务/分部/metric 对象与包含、排除、移入/移出、原报告为、改名/口径更新等关系，保留时点、will/planned、否定、otherwise unchanged。可归既有 core_business topic并给独立理由；不能把财务数字/纯 label 视为动作，不放宽原有财务增长事件 regex，不公司白名单或降低全局阈值。真实 line20、完整 definition 段及通用双语同类样本先 RED；“headline only / numerical metric / boilerplate definition”负例同组。
2. **格式中立的 transient 视觉上下文**：增加 OCR 图片行的 bounded 句子/列表成员分组，维持现有 PDF 行为。同 source、page、media SHA、shape、role、language、parser/config；用显式 image_pixels/dimensions 和相对行高/重叠判邻接，不套 PDF points 页边界。限制8成员及现字符窗；不跨双栏、跨图片、页、标题/段界；低置信行被移除后不可桥接有 index gap 的句子。分类可以看 group，输出继续保留原逐行 text/box/locator/hash，不创建虚构合并段或 financial cell。
3. **集中责任 RED/GREEN**：同一个经营句分别单行、两行OCR、两块PDF、HTML paragraph；新范围变更类别的 rename/unchanged、include/exclude/from-to 和 future modality；同页双栏/两个media/跨页/低置信/gap/无关系词负例；partial来源中可靠小组应产出 nonempty partial且每条可 replay，empty opaque 仍 PARSER_INCOMPLETE；已知纯财务 complete合法skip仍 PASS。无需全22页或付费文本模型来验证这些通用规则。
4. **版本与恢复**：selector/version/generation identity 必须显式变化；旧 failed input_hash `7ed75daab656b24663959524e1458bfe03a6e32e085c5153be3bcb776726cea7`、三条 frozen jobs/request/0账均保留。已 terminal 不盲 resume，不重签旧 run 或改其 handler version。MAIN 可以依据本次 terminal/零账证明为修复后版本建立明确的新 generation/run，并保留两个报告的关联。

建议 owner 定位：`source_catalog/narrative_candidates.py`、`n6_candidate_operating_facts.py`、`narrative_evidence.py`、`narrative_pdf_groups.py`/新的格式中立 group port、`narrative_group_candidates.py`、`narrative_neighbors.py`、`n6_candidate_completion.py`；worker/预算/完整度门不应作为修复点。

诊断无需追加真实 OCR。施工后若 MAIN 需要一个真实小样本，只需**第7页单media**：检验 rename/unchanged line20 是否产生正确原因、server-products bullet 两行是否按实际 boxes 完成，首行漏识仍partial；然后仅该media一次selected replay核原locators。建议60秒外层限额，至多1 initial+1 replay、0 supplier。先由 MAIN 安排，不自行重跑整22页。

## 恢复与边界

single-image TEMP `mSel-9rcj3glu` 已检查绝对路径/marker/仅两文件/无链接后清理；origin `mOCR-srw9_9oe` 继续存在。deck、SEC原件、origin DB 的 SHA/size/mtime 前后相等。本 agent 只写本诊断子目录，没有改代码、PWF、验收脚本、配置、安装、旧 AUTO/request，没有供应商请求。CodeGraph 已首先查询，但当前 merged selector/context 索引没有结果；使用已知文件的实际 source 继续定位，未擅自重建索引。
