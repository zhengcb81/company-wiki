# DU-ROOT 调查发现

ROOT 集成期间实测得到的事实。每条都注明来源，未测的写明未测。

## 一、生产解析链的真实形状

- **PDF units 不带 `source_locator`**。`narrative_evidence._emit_pdf_text_units` 只写
  `bbox / pdf_block / block_char_start / block_char_end / block_sha256`。
  规范 locator 由坐标派生：`EvidenceCoordinates.locator()` → `loc:v1/page:62/paragraph:3`
  （表格行：`loc:v1/page:10/table:0/row:1`）。`EvidenceSpan` 会校验
  `locator == coordinates.locator()`，所以派生值才是可回放的引用。
  → 早期 adapter 用 unit_id（内容哈希）冒充 locator，**引用无法回放**；已修。
- **HTML/PPTX/DOCX** 走 `document_normalization`，locator 在 `metadata['source_locator']`。
- **表格行**：`pdf_table_row` 的 row 0 就是表头，且每行都带 `table_headers`/`row_cells`，
  所以表头/caption/table_id 可从既有证据派生，不需要猜。
- **QA 页输出两套单元**：`investor_question`/`management`（结构化角色）与
  `qa_text_shadow`（文本层副本），unit_id 不同。真实万润 IR 302 units 中 219 是 shadow。
  `narrative_candidates._EXCLUDED_ROLES` 已把 `qa_text_shadow` 排除在选择之外，
  所以 shadow 副本**不是可选取证据**；但结构层仍需要两份来配对问答。
  → 结论：shadow 既不能删（结构需要），也不能送（重复计费与重复事实），
  只能「不新增、不发送、但报告」。

## 二、章节角色的失败模式

- `_SECTION_ROLE_HINTS` 只能匹配含主题词的标题。子标题如 `（一）项目基本情况`、
  `（四）项目建设周期` 自身不含主题词 → 角色全为 `unknown`。
- **`unknown` 在所有已知角色之后**。恒锋增发 96 页 / 3224 units / 1514 包中，
  19 个 project 包角色全是 `unknown`，被 1000+ 篇散文包挤在 160-unit 预算之外，
  「建设期」整段读不到。
- 修复：子章节继承父章节角色（`basis` 记 `role_inherited`），已正面匹配的不覆盖。
  继承后父章节 `第三节 …募集资金使用的可行性分析` 的角色是 `fundraising`，
  子章节随之进入最高优先级 band。

## 三、排序与预算的真实缺陷

- **包 ID 曾按 `unit_id`（sha256 字符串）排序** → 等于哈希序，与随机无异，
  所有基于 ID 的次序都是任意的。现改为按首个成员的输入 `ordinal`。
- **`max_packages` 默认 400 静默截断尾部** → 尾部就是文档后段，
  发行说明书的募投项目包整段丢失。现默认不截断，显式截断报 `PACKAGE_LIMIT_REACHED`。
- **`section_priorities` 在 profile 上，不在 route 上**。只传 route 会让每份文档
  静默退化到同一套通用顺序，而且看起来是对的。现 `build_dependency_packages`
  接受 profile 并优先使用。
- 列号推断曾按页面中点切分，页眉在右半页时会把左右栏判反。现按窄块左边缘聚类，
  跨栏块（整表）给 `None` 而非猜一侧。

## 四、名创 p12 的真实结论（更正计划原文）

`design.md` 写「中英双栏 / 中英左右栏」。实测：**左栏是英文，右栏是中文**，
两栏各自语言统一，**跨栏不存在同位中英对**。
真实中英并排对（`As of December 31,` / `截至12月31日`）在**同一栏内**相邻。
因此跨栏不产生 `language_parallel` 是正确行为，不是缺陷。

**门店表读不到的确切原因**：真实 parser 把该双语表抽成**退化的单格行**
（`'1,093'`、`'3,536'`、`'Total 合計'`），而不是 `项目 | 投资额 | 建设期` 那样的
规整多列行。即使 `full_table_scan=True`（1283 个 `pdf_table_row`）也**产不出任何
`operating_table` 包**。恒锋的募投表是规整多列行，所以 project 路径可用。
→ 恢复它需要表格几何重建（行列由 bbox 反推），属 parser/表格模型工作，不是排序能解决的。

## 五、基准对照的公平性核对

- 基线 observer（`observer.observe_native`）**同样**输出 `selected_locators` 与
  `selected_text`，本层也输出这两项，因此召回是在同一机制上比较，**没有多选提分**。
- 预算对齐：普通文档 96 units、发行类 160 units，与既有 router 的
  `DEFAULT_SELECTION_LIMIT` / `PROSPECTUS_SELECTION_LIMIT` 一致。
- 结论：development 0.220 → 0.384；holdout 0.000 → 0.350。
  恒锋 0.000 → 0.857；万润 0.143 → 1.000。
  三份回退（cn-h1、cn-q-business、us-nvidia）如实报告，未针对金标调参。

## 六、审计本轮自身发现的问题

| 问题 | 性质 | 状态 |
|---|---|---|
| locator 用 unit_id 冒充 | 引用无法回放 | 已修（改用坐标派生） |
| selectability 只声明未消费 | 同一答案可能送两次、否定被重复加回 | 已修（两个消费者都落地） |
| 包 ID 哈希序 | 次序任意 | 已修 |
| `max_packages` 静默截断 | 后段证据静默丢失 | 已修 |
| 子章节角色不继承 | 目标事实读不到 | 已修 |
| 测试夹具名 `fixtures` 与仓库 `tests/fixtures` 冲突 | 一起跑时收集失败 | 已修（改名 `du_structure_fixtures`） |

## 七、未测 / 未证明

- 真实模型摘要与语义蕴含审查：**未跑**（`paid_path=not_run`），付费路径没有任何证据。
- `context_completeness` / `role_modality_quantity`：基准报 `NOT_EVALUATED`。
- 未做：跨文档变化、本层峰值 RSS、生产接线。
- 20 份调查样本是开发集；US holdout 由 bench 补了两份真实 10-K，非合成顶替。
- 名创门店表与阿里年报（18038 units 对 96 预算）仍为 0.000，原因已定位，未解决。
