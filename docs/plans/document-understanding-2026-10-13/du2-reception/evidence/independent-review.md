# DU2 非作者独立复核

Reviewer: quality_cwp（本轮 DU2 非作者）。工作树：C:/Users/郑曾波/Projects/_harness_worktrees/document-reading-review-20261013/reception。基线 78fecefa 来自 ROOT 声明；本审查未执行 Git 命令。

## 结论与边界

**本轮冻结的共享 catalog / scoped ReadingPlan / layout bridge / 最终摘要请求，没有尚未关闭的 P1/P2 阻断。** 可进入 ROOT 的大节点接收。这个结论只覆盖候选公开解析与摘要请求组装，不表示生产默认 selector 已替换、真实 LLM 摘要已经验收或 RF 全流程已经完成。

源代码和原始资料只读；仅写本目录审查材料。未改 ROOT PWF、Git、生产配置、作者树或原件；模型调用 0、网络调用 0、费用 $0。代码摘要和行号见 summary.json，仅用于证据定位，不是新许可门。

## 实际覆盖

| 面向职责 | 复核内容与结论 |
|---|---|
| 唯一运行配置 | profiles/registry.py 只在导入时加载 packaged reading_catalog.json；reading_defaults 与 docs 仅由维护 compiler 消费。24 family / 14 facet / 15 legacy binding 是一个资产的兼容投影，未发现第二运行 registry。 |
| 用途与章节 | pipeline 实际调用 resolve_reading_profile，再由 strategy_binding 消费独立 section_rules / heading_path；Part I/II 的同名 Item 不合并。child 只见实际读到范围，外部未读 attachment 不升级为已读。 |
| 配置局部失效 | 采用的 family/共享指令/最终 sent facet 进入内容摘要；不相关 family/facet、未发送 child 不影响当前采用指令。最终摘要顶层指令与采用集合已统一，见 R1。 |
| 业务关注 | facets 只从最终实际送出的原文选择；输出问题、条件槽位、absence、泛化混淆风险和机制阅读提示。没有把机制提示变成 observed_mechanism，也没有生成事实/数量。 |
| 布局与定位 | 字体、bbox、宽高来自同一前端 snapshot；90 度旋转使用 dict 文本坐标框架。只有既有 unit_id/locator；粗块/表区不伪造 cell。原始文字、源 SHA、parser identity 保持。 |
| 预算与恢复 | layout WorkBudget 耗尽中断且 partial；binding 每条计量路径都 charge，完整计算后才提交依赖。summary 用同一 context graph/closure，真正恢复原文成员，完整计字符和额外上下文，超限整包 deferred，最终依赖再验。 |
| 审查/权限 | 新链无人工签收、private/public、许可 JSON 或 canary；source identity/type/schema/资源错误仍由所属层拒绝，不是人为审批。 |
| 数据规格 | 阅读 family 的 proposed/missing/not_integrated 未被自动认证；author 结构/引文 PASS 不等于语义抽取或模型 PASS。真实与 synthetic 样本分开记录。 |

CodeGraph canonical index 用于初始结构查询；新 DU2 代码仍在候选接收树，canonical index 不包含这些变更。因此随后仅对已经明确的文件阅读和 AST 定位，不用旧图推断新代码完成状态。

## 独审发现与已关闭的共用根因

### R1 — 实际顶层指令与局部指纹不一致（P1，已关闭）

初始仅 child 文本送出时，reading_policy_version 只含 child，但顶层 focus / negative_hints 仍来自未采用 parent。改变 parent 后，实际提示改变、digest 不变。ROOT 先 RED，再把 focus / negative_hints / preferred semantic units / priorities 收敛到最终采用 policy，并让 binder 透传实际采用指令。独立反例确认：未用 parent 改动不改整份请求，已用 negative 改动改变 digest，empty 不保留 parent 指令。

### R2 — FACET 混淆风险没有被真正消费（P2，已关闭）

初始 spec.confusions 被全丢，机制列表也从摘要中丢失。“注册海外子公司不等于已有收入”等风险没有进最终请求。ROOT 采用 confusion_checks={risk:why_wrong,required_context_slots}，避免把带合成案例数字的 source_meaning/wrong_assertion 送给模型，同时保留 applicable_mechanisms 作为阅读指令。逐条抽查 14 facet 的 why_wrong 后，这种泛化精简足以覆盖此风险；独立测试验证有风险说明、没有案例事实字段或示例数字。

### R3 — layout binding 无 required 项时不检查 work ceiling（P1，已关闭）

初始在 group members 遍历中只递增 work，只有进入 required_context 内循环才检查；max_work_units=0 的纯 heading group 仍返回 complete。ROOT/作者复用 WorkBudget，对 known/member/group/依赖遍历逐次预留工作，全部完成后才发布 requirement。我的原零预算反例现返回 partial+明确诊断，源输入不变，没有半成依赖发布。

### R4 — 只“恢复 ID”却没有恢复实际原文材料（P1，已关闭）

初始 layout binder 增加外部 caption/header required IDs；closure 显示 CONTEXT_RESTORED，但 materialise 只读原 members，最终把有原文的 row 误判为 MISSING_REQUIRED_CONTEXT 丢掉。ROOT 修复 shared context graph，selection / materialisation / final verification 复用同图。实际 allowed required 和 transitive 原文在字符/上下文限额内加入。原直接表头反例、两跳 footnote、字符裁切、上下文 0/1 限额均独验通过；未放松最终依赖检查。

## 测试证据

本审查没有重跑全套 CI。所有自跑均为 python -B -X utf8 的进程内聚焦探针；没有 pytest cache 或其他测试写穿。

| 自跑阶段 | 结果 | 证据 |
|---|---:|---|
| catalog/Part绑定/局部指纹/child范围/layout 0、5、40 work/opaque | 18 PASS / 0 FAIL | focused-probes.json |
| R1/R2修后、empty、最终实际 HTML normalize/replay | 8 PASS / 0 FAIL | summary-fixed-probes.json |
| R3/R4修后、直接与两跳上下文、字符/额外 context 限额 | 7 PASS / 0 FAIL | layout-context-fixed-probes.json |
| 最后冻结 bridge：字体原始身份、missing geometry、来源/ID拒绝、Part/display/TOC/Notes、90°框架、字体run索引 | 8 PASS / 0 FAIL | final-bridge-probes.json |

上述是分阶段探针记录，不将其冒充完整 pytest 节点数或全部业务语义验收。最后字体测试第一次直接调用漏传 monkeypatch，是审查脚本调用错误；提供原有 fixture 后通过，没有改代码或断言。一次组合探针的“transitive reason”断言也促成 R4 真实根因检查；修复前错误材料丢弃证据没有抹掉。

合成 PDF/HTML 在内存构建，经真实 public parser/replay 执行；它们不冒充真实公司样本。每项机器证据列出调用的实际测试函数名，可用原 test 文件与相同 fixture 重放。

## 真实 10-Q 证据的独立阅读

ROOT/作者的同一 us-10q 原件 SHA：
5afe631934fce5d3e23b6aa393ec599cd89b290cde1fc1667ebe22025d2479eb。

已逐项读取 real_10q_replay、after1、after2、after3，不把旧失败替换成“始终成功”：

- 原始回放 2274 units、0 scoped 命中；Part 段落和 Item 单行双格未进入正确父子结构。
- after1/after2 仍 mda/controls=false，确认 Notes 等子标题错误打断 Part I；这说明合成章节 PASS 不能代替真实来源回放。
- 最后冻结 adapter 区分普通 p 的文本编号与真实 DOM heading；Notes 相对 Item，后续 Item 返回实际 Part。after3：同 SHA、2274 units、30 sections、5 scoped 命中；mda、controls、legal、risk、mine_not_controls、table_year_address_not_headings 六项全真；MDA priority=1、Controls=3，Mine Safety 未误归为 Controls。receipt 记录 input/SHA/mtime 不变。
- after3 是我独立阅读和检查的作者真实回放收据，**不是我亲自重新跑完整真实 10-Q**。我的独跑对公开 HTML/Notes 和 parser identity 另有决定性探针。

ROOT 还在总体节点集中签收四份真实 PDF 的 public pipeline 回放；其结果不在本审查先行伪报。亲跑真实 LLM 摘要、公司 RF/G2/G4/G5、missing shapes 仍按母计划办理。

## 剩余风险与后续归属（不扩大本次接收）

1. **B8 优先：存量 flat selector 仍有固定题材/数字排序。** narrative_evidence.py 的 _DOWNSTREAM_CENTER_CERTIFICATION_TIMELINE 固定“集成中心+4–9个月”，传给 GroupCandidateRules 后在 narrative_group_candidates._add_timeline_window 有真实 +2 boost 效应。应按共享 facet/主题预算整体迁移，不再补更多公司/项目 regex；不能说全项目硬编码已清空。本轮 font metadata 不重写它。
2. orchestration.max_members 是保留必需上下文的软截断：required/anchors 本身超限可多于 requested members（已用2→5反例确认）。最终摘要 char/context cap 仍有效；该旧语义留 B8 统一整理，本轮不牺牲完整必要上下文换 PASS。
3. PDF coarse block/row/table_region 不是细胞格几何；NEEDS_UPSTREAM_GRANULARITY / partial 要保留。没有真实 50k original 全上限、全并发 RSS/完整 CPU 指令计量证明。
4. proposed/missing market/form/attachment/company-purpose 样本不能靠 synthetic 或结构 PASS 补成真实认证。FACETS 支持集/引文源修复证据可支持原文真实性，但语义 claim 质量和模型数字错误仍需母计划真实大节点。
5. 新 public pipeline 是候选接收能力；生产默认 selector/模型、旧 MSFT 4/8 问题、RF 和完整公司审查 loop 还需按 B8/B10–11/C12–15 接线与验收。

没有新增人工门、第二任务库或逐材料授权建议。建议 ROOT 用既定大节点完成整体真实回放后正常提交/并线，继续生产迁移计划。

## 联合节点五条旧断言收尾复核

ROOT 联合日志 joint.stdout.txt 的实际结果为 1130 PASS、5 FAIL、24 deselected；本补注不把尚未由 ROOT 更新并重跑的联合 suite 写成全绿。本次只核对这五个失败，源码/Git仍未改。

**结论：五项均未显示实现违反终态契约，应更新测试 oracle，保留或增强安全与预算不变量。**

| 旧失败 | 独立判断与建议 |
|---|---|
| test_output_is_du_layout_hints_wire exact WIRE_KEYS | 输出只增加合法算法 feature_version=1.1.0，用于新 pipeline/summary 的版本追踪。精确 key 集合仅加入此字段并验证常量/版本；不要改为接受任意未知字段。source_ref和每个unit字段仍严格。 |
| annual risk > generic risk | 当前真实 configured risk priority=2，对应score2，generic也是2；旧断言把早期配置值误当永恒语义。逐配置行断言score=4-priority，并使用独立可变profile证明真实排序随配置改变且原文membership不变。我已验证 risk priority3→1：business/risk→risk/business。不能为了旧测试把真实risk配置硬改成3分。 |
| max_packages=1跨a→b→c强求empty | 两种selection都实际发送单个p1，a/b/c原文与locator齐全，精确30chars，p2按PACKAGE_BUDGET deferred。必要上下文恢复进同一包是正确行为。新断言应严格验证单包、三单位、原文绑定、30chars和依赖闭合；并保留实际context/char不足时empty的反例。 |
| max_chars=20强求empty | p1需30所以明确CHAR_BUDGET deferred；p2的b+c完整20合法，未发送a、不构造a。chars19/0时全部empty。新断言应覆盖20边界可读闭合子包、19边界不可读、字符实际计数、成员/text/locator、p1裁切原因，而非强求一切都空。 |
| negation contextcap1只允MISSING_TRANSITIVE_CONTEXT | 仍empty，明确MISSING_REQUIRED_CONTEXT缺c；closure记录CONTEXT_BUDGET_EXCEEDED。比最终验证更早拒绝不是放松依赖。cap2恢复a/b/c，c保留原始“does not produce yet”与loc-c，精确40chars。允许实际安全拒绝阶段理由，同时断言缺少否定绝不能发送、cap正反例和原文保持。 |

独跑收据：five-assertions-probes.json、wire-priority-probes.json。探针验证任何最终输出包都依赖闭合、每个unit来自输入原文且text/locator不变、chars_used等于实际成员字符和、不超过char/package上限。未修改任何business gold、测试、配置或源码，也未删除测试。ROOT可在同一大节点更新上述旧assert并集中重跑，无需新审查节点。
