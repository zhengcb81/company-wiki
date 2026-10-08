# R6-RF-INPUT：单位、管理目标、证据角色与真实输入依赖

## 任务与开工

这是较大的 RF 共用输入改造，可以立即独立启动。工作目录：`C:/Users/郑曾波/Projects/_harness_worktrees/cmrf-20261008/rf-inputs`；分支 `codex/cmrf-input-semantics-20261008`；基线 `72ce94c160bbb5b9399c8716307588b443a72a83`。

MAIN 本阶段不同时改 RF 源码。只在该工作树自己的分支施工；canonical RF 的三项 assurance 日志及 output 属 owner WIP，不修改/恢复。不可写 CWP、FF、StockWiki、IQS、安装技能或原文目录。

读本卡、README/handoff_interface、root_cause_remediation/follow_up_plan，以及 RF SKILL、references/input-construction.md / input-schema.md / management-targets.md。实际实现入口已核实：`scripts/research/targets.py`、`scripts/contracts/evidence.py`、`scripts/analysis/sensitivity.py`、`company_wiki_narrative_reader.py` / contracts、`narrative_source_preparation.py`。不是不存在的 scripts/management_targets.py。结构先 CodeGraph。

## 已证实问题和范围

- US 5pp 被作为 ratio=5.0；按错误输入算术会全绿，不能靠改 clamp 或通用浮点容差修。
- 季度/恒定汇率/定性区间/未定年达产目标，不能直接当年度 reported 数值；没有年度转换依据时仍需完整保留管理原话。
- 合法 claim ID＋真实原文不自动支持未来增长范围；历史基数、会计确认政策、同行竞争曾被错用为未来公司机制支持或 triangulated。
- NarrativeRef文件存在不等于正式RF input消费。必须有可核查的参数/driver依赖；单纯把引用复制到附录不能过关。

责任是构建与验证研究输入，不是来源下载/路径解析。尽量复用现有 evidence_role/inference_distance/目标 ledger/公式及强 validator，避免另建许可、签收或研究数据库。不改变收入之外投资研究边界。

## 可写范围与接口

RF 仓源码、必要测试/说明及 `docs/implementation/cmrf-input-semantics-20261008/`。不改 assurance/runs、output、生产配置/费用账、compatibility/current.json、CI工作流、旧快照和封存第一组产物。现有 golden 只能在独立重现旧行为＋明确升级原因后更新新版本，不能重哈希旧产物。

对 MAIN 至少交付三个可运行公共构建入口（可按仓结构放一个或数个小模块，导入路径在交接固定）：

1. `convert_input_quantity(value, *, input_unit, engine_unit)`：显式人类单位转换；5pp→0.05 ratio、5percent→0.05，ratio=5.0保留真实语义不能自动猜成5%。严格拒 bool、NaN/Inf、未知/不兼容单位，保留原值/单位和 conversion 表达。绝对数量货币不偷偷混 percent；合理范围由对应参数语义判，不所有 ratio 通杀>1。
2. `build_management_target(statement, *, ...)`：保留逐字原话、source/claim、commitment、period/FY/Q、范围/定性标签、CC/reported、gross/net、scope/perimeter、measurement basis；返回现有正式输入可消费的目标/coverage记录及未比较原因。季度/定性/未定年先具名保留，没有显式支持转换时不产生年度比较。若必须扩现有正式合同，说明版本/兼容性并同步 validator/engine/report，不只写旁表文档。
3. `bind_parameter_evidence(parameter, *, evidence_bindings, ...)`：构建 checked fact/history、机制方向、数值范围、反证/peer类比、转换假设的明确依赖，并接入现有正式输入结构。绑定 source_id/span或claim/NarrativeRef content SHA/locator；保留文本/事实与假设区别，peer不能自动公司自身one-step/triangulated。不要给原文无法支持的数值盖“已验证”章。

不要求新增固定 key 满足模板，而是上述能力真实可调用、可被正式入口消费；任何新字段必须有严格解析和旧输入默认策略。缺真实摘要可用既有合法文本证据/小fixture建立机制，MAIN 后续接新格式真实摘要。

## 实施步骤

1. 建本线 PWF，整理原审查 issue→责任机制六字段表。先最小 RED：pp/ratio、季度CC/定性目标被伪年化、peer被升级、EvidenceRef只放附录但未进input。用函数缺失的RED只证明缺API，另补真正语义错误/正例。
2. 实现单位构建并用正式 sensitivity 路径验证 requested/effective shock；处理 clamp 仍透明，不用 clamp 掩盖输入意图。记录 source文字单位与计算单位。
3. 目标表示与兼容：季度真实值/定性labels/区间/无确定年份不漏报；原声明永不被转换覆盖。年度转换必须明确参数/公式/依据并验证年度时间权重、汇率/并表/确认口径。不能季数乘4、造mid-single中点或把capacity plan当revenue promise。
4. 证据绑定使用角色与距离，不靠公司名/NLP关键词自动判断经济真实性。可机器检查类型/身份/角色/数值引用缺失，但保留不确定性，最终语义由 MAIN 的大节点独立review。本公司事实与同行参考不混；parameter hypothesized range需声明是分析假设。
5. 接正式模板/构建入口、lint/strong validator、engine/report。证明新 NarrativeRef→claim/span→parameter/driver 进入实际 input，并影响输入 lineage 或质量/limitations；不得仅声明存在引用。改证据源后实际消费链要变，engine不会旁路成另一路手算。
6. 集中跑责任层＋正式CLI/快照/registry集成，再按同原则复核不同 synthetic 公司形态和第一组真实输入；明确不重建真实研究、不给未来预测造真值。提交本分支交接 MAIN。

## 必需测试包

- 单元：0/5/-5pp、percent/ratio、bool/NaN/Inf、金额/数量单位、非相容转换；基于数学手算 oracle，不复制实现。
- 管理目标：quarter/FY、CC/reported、上下区间、mid-single/high-teens原标签、未定年、run-rate/recognized、部分并表/全年度、gross/net、currency/scale。合法显式转换通过；缺转换、伪季度年化、字面公式常数/无真实依赖的转换拒绝或诚实gap。
- 证据：历史基数仅history、会计政策仅recognition、公司机制与peer竞争不同、方向支持不冒充range支持、反证材料不与同摘录支持混用、source/claim/locator/内容SHA错配、NarrativeRef有文件无消费。
- 集成/E2E：在独立测试根运行真实构建→lint/validator→engine→report→snapshot→registry。无需下载/付费；用现有公开 SourceRef/NarrativeRef协议fixture，核依赖实际进入正式载荷。一个支持源变体/一个peer变体，在收入不变时检查evidence_status/confidence limitation确实变化。
- 兼容：原三公司封存输入/旧快照只读；stable-fsum/1跨seed精确强验证保持；其他既有有效输入继续通过，实质错语义负例拒绝。不得为了把旧错误输入过审而给公司白名单。
- 本线测试建议新 `tests/test_input_quantity_conversion.py`、`test_management_target_semantics.py`、`test_evidence_input_lineage.py`、`test_input_semantics_e2e.py`，并集中运行现有相关 tests（先rg清单选实际文件）。全量/网络不进每次commit门。

## 交付与仍归 MAIN 的事

在本线 docs 交五文件和准确接口样例/版本/运行闭包名单；Git逐提交。保留实际RED/GREEN和异公司变体，不只文档完工。MAIN负责合并/安装、用新canonical摘要跑三公司完整新研究、独立语义审查、换三公司泛化；不在本线提前宣称这些已绿。不买套餐/换模型，默认费用0。
