# HK 表格期间错配：共享根因与实施细则

Owner: `/root/provider_quality_review`\
Observed: 2026-10-14 23:00 UTC（London 已2026-10-15）\
状态：只读设计；**未实施、未写测试、未运行测试**。

本报告供 ROOT 合入同一 PWF；不自行修改生产计划或源码。只读取既有 HK request/final、独审报告、当前相关源码和 DU3 接口。没有重新打开原件、parse、API、Git 或生产配置操作。原输入 packet 的指纹见 [observations.json](observations.json)；允许其他施工线正常改自己的源码，不对整个 src 施加静止断言。

## 1. 先说清楚已证明什么

实际样本：`live-20261014T224413-922d46`，run `phaseC-090-76236609f71c`。输入 body SHA `0fc9020b40f9c4ecf10cdf231466eaf2887124daa494e160a0280466445cde53`。DeepSeek 已真实1POST，摘要后发生 `LOCATOR_REPLAY_FAILED`；这一旧 packet 没保存 typed SelectResult/完整 generation/native locator map，不能凭现在源码补造历史原件坐标或精确 verifier 失败原因。

### 1.1 实际模型输入中的缺口

| 实际组 | 已送标题 | 已送正文 | 能证明的结论 |
|---|---|---|---|
| g2 / e19–e23 | 2023、2024两个年列，中英各一遍 | 城市层级每行仅一个值：522 /1,617 /1,787 | 不能凭标题把唯一值移到2024；其和3,926与已送2023内地总数一致，强烈指向候选错年 |
| g3 / e31–e35 | 2023、2024两个年列 | 地区每行仅一个值：1,333 /172 /552 /231 /199 | 不能按最新年默认；其和2,487与已送2023海外总数一致 |
| g4 / e37–e41 | six months2023、twelve months2023、fiscal2024三列 | 每个指标只有两值，如GMV6,895 /13,035 | 两个值究竟落哪两列没有精确绑定；13,035不能因为在最右就当2024 |
| g5 / e43–e47 | 同上三个期间 | GMV6,452 /10,989、增长区间等每行两值 | 10,989与2024的关系在 packet 中未被证明 |
| g6 / e50–e54 | 同上三个期间 | TOP TOY GMV445 /814、客单价118.7 /121.3等两值 | 814 /121.3不能被无依据分配给2024；门店GMV也不能换成其他片段的品牌全渠道GMV |

这里的合计只作独立审查中的一致性反证，不用它重建缺失的2024值，也不把运算结果写成原件直接披露的事实。

实际 /2 只送 `evidence[id,raw_text,role,flags]`，`evidence_groups[id,members]` 和 `reading_strategy.groups[id,kind,section_role]`。没有原生列索引、空位、数值单元格对应的表头路径/期间/单位/不确定状态。`operating_table` 标签、闭包包含全部标题和合法 alias 都不能证明数字归属。

### 1.2 不能提前下的结论

- 未证明原件是否缺2024值；也未证明 native extractor、adapter 或 projection 哪一层**首先**丢了该列。
- 文档整体 layout partial/deferred5211 是全局诊断，不能推断这几个具体单元没有细 cells。
- 不把 PDF replay 的语言端口问题与表格期间语义问题混成一个故障。前者修好后，c6/c7错年依然必须独立关闭。
- 新 `reading-model-input/3` 的单一 citation-unit 能修重复引用责任，不能自动证明表格期间。

## 2. 当前代码链的确定性缺口

以下是这次阅读时的源码位置；完整文件 SHA 仅作阅读时记录，不阻挡其他线合法施工。

| 层 | 当前行为 | 缺失职责 |
|---|---|---|
| `source_catalog/narrative_evidence.py::_emit_pdf_table`（约1309） | `table.extract()`只调一次；None变空串；保存 normalized_rows并交layout collector | None、真实空格、合并格未提取的区别丢失；需要保留原生格槽状态 |
| 同文件 `::_emit_pdf_row`（约1248） | `raw_text = ' | '.join(nonempty cells)`；row_cells仍保留归一化后位置；普通row只有table/row坐标 | 展示字符串压掉空槽，不足以反推列；普通row没有逐值索引 |
| `narrative_pdf_layout.py::PdfLayoutCollector.capture_table/_binding`（约278/317） | 同次native table可保留真实row/column/bbox及字符区间 | DU3证明真实元数据投影，**没有**承担期间/单位语义；粗整表bbox不能冒充每个值的位置 |
| `document_understanding/observation_adapter.py`（约450/545） | 映射table_id/row/column、可选fine cells；未把row_cells/table_headers作为保空槽的表格载体传递 | 上层不能在没有fine cells时使用已有明确原生格槽；不能从raw_text空格数猜回 |
| `structure/contract.py::ObservationUnit`（约121） | 接收table_id/row/column_index；不保留每行格槽 | 缺一个与格式无关的table observation端口 |
| `structure/tables.py::build_operating_tables/TableDraft`（约128/27） | 收标题/行/脚注；`periods`是去重年份；只检查是否存在年/单位；as_wire没带periods/unit_label | 2023六个月与2023十二个月被年份去重抹平；没有value→column→header-path绑定 |
| `layout_bridge.py::_bind_context`（约195） | 将已有布局组的required_context IDs加进semantic package | 闭包是来源成员关系，不是数值列映射；没有把已证明的cell归属交到table语义 |
| `source_catalog/narrative_reading.py::_context`（约486） | 只保存闭组的kind/section_role/evidence_ids | 语义绑定/逐值不确定无法抵达canonical reading context |
| `automation/narrative_model.py::from_selection/_reading_model_context`（约454/249） | /2仅将raw文字/角色/flags与闭包给模型 | 模型最后必须猜列；全局mixed语言标签也不能证明每条引用的原语言 |

**根因是责任链没有“期间已绑定”的对象。** 简单增加提示、机械补表头、保更多raw字符、提高20/96/48000或再跑一个PDF parser都不能替代它。

## 3. 唯一共享绑定端口

沿现共享引擎增加一个纯内存的表格绑定服务，建议放 `document_understanding/structure/table_bindings.py`。由 `build_operating_tables` 调一次；格式适配器只交真实格槽/位置，不各自写一份期间推断。以下是**建议接口，未冻结为产品schema**，ROOT整合时与 /3 owner 对齐。

```python
def bind_operating_table(
    table_observation: Mapping,
    *,
    original_units: Mapping[str, Mapping],
    layout_table: Mapping | None,
    work_budget,  # 用现共享work budget，不建第二限额系统
) -> dict: ...
```

### 3.1 输入：真实格槽，不是一个重新解析的全文

`table_observation`包含source/table范围、原生行/列槽和原unit文字引用：

- `table_scope`：现source_id + 实际page/table_id；页内相同table index不得跨页自动合并。
- 每格：`row,column`及**实际观察**的row_span/column_span（缺失不猜）、`text_ref={unit_id,char_start,char_end}`、`presence=present|empty|unavailable|merged_unknown`、可选frame/bbox证明。
- `None`若只是提取器没给格，不能无声当真实空格；真实空串也不能被压掉后左移。缺列、重复列、冲突坐标各自明确诊断。
- 原文只保留已有unit一份；细格用原unit内精确范围。禁止重写原text/locator、伪造EvidenceSpan或用整行框复制成多个cell。
- 由已有DU3真实fine cells提供的映射优先复用。若旧native row_cells已有明确原生索引，可无geometry读取格槽；若一格含整个多行body且没有逐值位置，**不得**仅按空白或数值数量拆成“已证明”的列。

建议在既有 `du-input/1.hints`增加一个可选 `table_observation`载体；ObservationUnit只新增这个一般字段，避免塞一串PDF专用变量。通用HTML/DOCX表格原生索引可走同端口，经营策略不认识格式路径。现fine geometry仍由唯一layout引擎判断；没有第二个bbox/column推断器。

### 3.2 输出：绑定与未知逐值并存

输出建议 `du-table-bindings/1`：

```text
table_scope, status=complete|partial|unavailable,
columns[{column_id, header_refs, period, status, diagnostics}],
measurements[{measurement_id, value_ref, row_label_refs,
              column_id, period_ref, unit_refs, qualifier_refs,
              scope_refs, language_lane_refs, binding_status}],
unbound_value_refs, diagnostics
```

`period`至少区分 `as_of / duration / fiscal_year / unspecified`，保留raw label及其真实header refs；end/date、duration只填原文确有的值。**2023六个月、2023十二个月是两个不同期间**；不能只用年份集合。没有明确start就保留null，不为了美观推算开始日或把fiscal year一律写成12个月。

`measurement`保留精确值原字符串，不主动换币/换单位或算缺项。单位按实际row/cell/table层级绑定：RMB millions、RMB per transaction、transactions millions、百分比区间、store count、Retail Partner count不同，不能给整张表套一个单位。品牌/地区/门店或全渠道/存量或增量等scope由原标题/行标签/脚注引用限定，不从文件名和公司year常识补。

`binding_status=bound|ambiguous|unavailable`逐值给出。无某列只影响该列/行，不拒绝整份有用业务资料；已经确切绑定的其他经营数字继续可用。原字串与未知数字继续保存在canonical证据/检索层，不删除经营数字来“修复”质量。

### 3.3 唯一解析规则与优先级

1. 同一source/table的实际native格槽/跨度，或唯一layout引擎已证明的细格/表头覆盖关系，才可绑定。
2. 多层表头按真实column覆盖路径组合duration + year + unit；同年不同duration不合并。
3. 只有geometry时复用已有layout的same-frame/column-span结果；整块/整表bbox不足，冲突留ambiguous。
4. English/中文平行标题只有在同一实际列/范围且语义一致时作同一期间的两种标签；不能因全局mixed把两行变成两套列，或把冲突标题任选其一。
5. 遇到“三header、两值”、未知槽、合并格关系不明、跨页关系未证明时，不右对齐、不按最新年填槽、不复制上一行/另一语言车道的值。
6. 普通叙述本来直接说明“as of2024…503/2615”的，仍走其已可靠的叙述事实，不要求它先被表格绑定器重解析。

## 4. 如何接正式选择和 /3，保证不把未知变成确定

1. `TableDraft`保留binding结果引用；结构wire/reading_context保留同一个source-owned对象。**现`automation/narrative_contracts.py::_reading_context`对`du-production-reading/1`及每个group都是_exact字段集合，不能向旧schema随手塞字段。** ROOT须先冻结一个有限版本分派：旧/1字段与bytes不变，`next supported reading-context version（待 inventory 后确定）`明确table_bindings字段及大小/来源refs校验，由未来显式支持该版本的model入口消费；不把语义数据塞进layout_coverage或quality_flags躲合同。当前model/3并不等于已支持table bindings。选中闭包里只能引用实际被保留的原unit；受预算影响缺成员时，对应绑定降为unknown，而非继续把完整table的结论挂到残片。
2. 选择仍由现candidate/finalize/统一预算负责。重要经营指标不会因数字密集整体过滤；可优先选一条完整、可靠的measurement闭包，不能选便宜但丢期间的半条。
3. /3单一citation unit必须携带它的**已证明语义能力**：`period_binding/measurement_binding`。合法citation ID只是来源归属，不能认证年月/金额蕴含。
4. 新摘要的确定性表格数字应由source-owned bound measurement生成/渲染期间、值、单位和scope；模型可做同语言的业务解释，不重新发明这些字段。若模型仍自由输出数值/期间文字，必须承认仅靠合法ID不能保证无错年，不能宣布“期间修复完成”。不要增加一套靠公司名/年份正则扫描自然语言的伪验真器。
5. 只含unbound数字的单元不应进入“可直接断言某年数值”的能力集合；它仍是可检索的原文证据，可输出定性描述/明确未知。其不确定是资料质量，不是等待人工授权。不要让模型把unknown标志加一句needs_review后仍肯定写2024。
6. 精确语言来自实际引用lane的原文字串或已有native provenance，不由全局mixed许可翻译每一条。全English citation保持English；确有中文原lane可以中文摘要；平行重复不是两条独立事实。脚本简繁差异与整条英译中分开诊断。
7. 旧None/v1与已发布/2的body/decoder/ref行为保持；只有新run选新绑定能力和新因果版本。缓存指纹包括真实采用的binder算法/输入绑定材料（现decision_dependencies/generation服务）；无关catalog不全库失效，不新建签收、canary或重复身份校验。

## 5. 最小真实观测：下一次同源initial parse顺手留证

ROOT/table已计划对真实HK**最多一次initial parse＋正常final verify**。本设计不另外开原件。观测插在现单次调用里，before/after每层只保存以下小数据：

| 位置 | 最小字段 | 用来区分什么 |
|---|---|---|
| raw `table.extract()`唯一返回点 | 目标表raw行长度、None/空串状态、native row/column/count和真实cell bbox；有格但未提取也记状态 | 原生提取是否已少列；不要先normalize压掉差异 |
| 已有TextPage/snapshot | 落在目标table和缺列邻域的已读words/span引用、bbox/frame/char range；若未捕获，记未捕获原因 | 缺的2024列是否在同次text carrier中，只是table extractor没组合好 |
| parser units → DU observation | target unit/span↔page/table/row/column、row_cells槽与fine cells是否到达；具体unit diagnostics | 区分adapter丢槽与原生未捕到；不拿全局layout partial替代 |
| structure/binding | header refs/path、每value column→period/unit/status、unbound原因 | 区分“全标题已进组”和“数字确切已对齐” |
| final select → model | canonical闭包/native IDs、实际 /3 citation unit的binding摘要/能力、实际sent原lane | 防止下一层又只剩raw_text，或省预算时丢掉关键period |

只围绕g2–g6对应的实际单元/页；建议观测包最多5组、256细格、64逻辑数据行、256KiB压缩前JSON，超过就注明截断/未观测，不改变生产caps。字段原文保留一次，其他层用引用；不存整页图片/完整PDF/全文MD/第二AUTO库。若这些诊断点当前拿不到，在owner现代码已经持有对象时补有界observer，不能为观测重跑第二parser或额外`get_text`。

这份小packet加initial parse/normal verify各自实际参数与调用数、最终失败链和typed select+summary+generation即可。原件/配置/sentinel保持、独立Temp finally恢复沿现测试机制执行；无需完整恢复备份演练或逐小节点人工签收。

## 6. TDD与大节点验收

详细用例见 [tdd-cases.json](tdd-cases.json)。以下均为**待写/待跑**：

### A — 纯契约与行为RED

先在新pure binder写表形、空槽、多层期间、单位、source/frame、歧义/预算/输入不变测试。使用synthetic原unit+native indices，不用真实公司名/金标数值充当代码规则。按实际列期望结果，不能只断言有diagnostic。零文件、模型、parse调用。核心反例：2023/2024标题＋只在2023列的522不得变2024；2023六个月/2023十二个月/2024财年＋前两列6895/13035不得把13035贴2024。

### B — 一次集中接线验收

用受影响adapter→layout→structure→selection→新model projection做集成。假native table对象证明同一extract返回复用、普通row的原始槽位/字符refs不丢；不是另写parser。新 /3确定性数字只能来自bound measurement；unknown不被升级；旧None/v1/2黄金body和public ref保持。relevant binding变化失效、无关变化same、same/cross cache0POST沿现AUTO恢复测试。只在这个大节点做Ruff/mypy/受影响集成与独立review，不给每一小步加签收。

### C — 真实一次initial parse/正常verify＋实际摘要

用上述小packet证明源列到最终数字的完整链。先零重付费重放保存终文，保留旧错年与FAIL；不能用重写的旧packet伪装已修。等binding、角色/阶段、语言/引用共同根因修好后再按真实配置支付一轮，逐claim验证所有实际经营数字，不只盯7gold。换一个不同市场/不同稀疏列形的文档验泛化。真实未读/缺列诚实计入，不缩gold、加cap或删经营指标凑绿。

## 7. 排他施工与顺序

当前本agent只交设计，**不占任何源码写权**。建议 ROOT 在现model/PDF语言两线SOURCE STOP并接收后，再拆端口：

1. **格式端口 owner（PDF线）**：`source_catalog/narrative_evidence.py/narrative_pdf_layout.py`及其专属tests，保原槽状态/索引与同次snapshot。DU3 layout_snapshots模块继续只做实际投影，不写期间策略。
2. **共享绑定 owner（单独线）**：`document_understanding/structure/table_bindings.py/tables.py/contract.py`及专属tests；只消费冻结的内存端口，不碰format/model/ROOT PWF。
3. **ROOT最后接线**：`observation_adapter.py/layout_bridge.py/source_catalog/narrative_reading.py`、当前canonical contract与model /3消费。先冻结两端再动这些桥，不与正在写narrative_model的line重叠。

可先独立写pure binder的A测试/实现，但前端尚无数据时只能标工程能力，不能签生产表格期间已修。每线只做A/B/C大节点；ROOT归总测试/真实观察/版本/并线与远端CI。接口若需调整由ROOT一次记录，不让各层各加猜测或身份门禁。

## 8. 当前结论与Next Step

闭包完整性、表格值期间绑定、模型语义忠实度必须分别负责；本次问题需要这一条共同源端口。先在 ROOT 已有那次HK initial parse中获取最小分层观测，确定缺列最早发生处；随后以纯binder反例TDD约束共享实现，再一次接线。默认0.8、真实三家质量未通过等当前PWF事实不由本设计改变。
