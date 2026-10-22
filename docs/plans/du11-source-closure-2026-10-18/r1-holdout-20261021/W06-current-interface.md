# W06 当前执行接口：新版研究与真实RF消费

唯一整体入口为上一级`CURRENT_STATUS.md/json`。本卡补充冻结专家W06卡，不改initial FAIL、原scope、639工件及其manifest；不是新审批步骤。

## 当前输入与所有权

- audit run：`revenue-forecast-audit/runs/r1-20261021-cn-wuxi-apptec`；新输出只写`execution_replays/r1-remediation-01/`及分配的executor新日志。
- scope：该attempt的`coordinator-effective-scope-v2.json`；当前操作索引为同目录`native_operation_index.json`。原`roles/executor/native_operation_index.json`已在initial封存，只读。新attempt必须独立保存当前引用，不能追加旧封存后改manifest。
- 原阶段A交接：`research/phase_a_handoff.json`与`phase_a_manifest.json`；10合格来源、8新原件、20事实/6目标，研究尚有明确缺口，不冒充完整窗口。
- W07交接：母仓`.planning/r1-w07-live/20261022-annual-090-reallocated/w06-context-handoff.json`；真实公开RFcontext的SHA/路径、SourceRef、as-of及配置均在其中。已走onePOST的0.9/v5恢复/cache，不再付费重做。
- 当前summary为partial/needs_review；它帮助定位业务，数字回原件。default仍0.8，不因本次显式0.9通过自动切换全局。

## 顺序与产出

1. 读当前已安装RF技能及方法卡，记录每个实际入口的代码/技能版本，不能从旧固定编号推测功能。保持原三年Low/Base/High任务范围。
2. 独立经营桥先于管理目标：基期/最新H1、确认时点、需求/产能/项目进度/价格/FX、取消与共享风险。只给可解释的最少参数；未知实证区间保留conditional，不能编出外部范围、假peer或未来actual。
3. Chemistry的2025基期36465.84688297 CNYmillion；内含TIDES11370，non-TIDES余项25095.84688297。三者不能相加为公司收入。原专家卡的11370/25095.8469解释为互斥子项，不是化学业务合计。
4. 最新H1与H2桥、RPO在手存量与收入确认分别处理；H1无剩余FY2026 cohort节奏不造下半年收入下限。配售/可转债募集资金和未用余额不是营业收入。管理585–605亿元与TIDES45%等只按原文期间/口径作为可比较目标，不倒推独立基准凑指引。
5. `scripts/source_narrative_context.py::consume_narrative_input`为真实函数，没有同名独立CLI。用既有公开reader、真实SourceRef/capture与support span绑定一个或多个确实进入native分部公式的参数；context partition不能变support。保留返回的consumption/citation trace，只有context可读不能写consumed。
6. 完成当前RF15步及coverage、管理目标、因果驱动树、历史/分部核对、参数/证据、native compute/strong validate/render、shared stress、registry/snapshot（按当前runtime真实要求）。每项做/失败/不适用有证据，不偷偷省略。
7. 每次可包装工具先`execution_request.py build`，`audit_run.py capture --freeze-input/--freeze-arg-index`消费该call确切输入副本；原始native exit、stderr和失败保留。错误请求用新v2取代并索引，不覆盖旧bytes。
8. 给出source→fact→parameter→formula→scenario结果索引，区分reported事实、管理目标、独立观察、分析师假设；复算单位/货币、亿/billion、存量/流量、年度/半年度、gross/net及累计/单年。
9. 完成/失败同样交接：真实forecast/report、step ledger、document matrix、事实及目标表、费用/HTTP known/unknown、manifest和trust statement，保留partial/gap。ROOT再安排四个真正独立reviewer，不能执行agent自判通过。

## 当前并发与资源

ROOT先交Bachem单次免费采集时段，已于20:32:40UTC完成并交接；随后为减少往返，将剩余phaseB的catalog唯一写者完整交给executor，直到最终handoff/manifest封存。必要的最新IR/演示/独立来源可沿原scope采集意图、实际字节/时间/$0上限自主采集/注册/read，无需逐URL询问。ROOT不再写该真实湖，审查agent只读；其它工程测试在各自隔离根。资料不再变动时发最终catalog_handoff，不创建逐材料许可。Bachem实际1GET/112259B，合格日期2026-07-30、0LLM；来源登记与HTTP用量分开记录。

本次不自行调用收费模型；确需新摘要交ROOT做现配置预检及原生预算。当前母账1561352tokens/631959microUSD，公司56355/16421；自定公司累计150k/$1、单请求deploy100k、母2M/$20不变。unknown保留，不能另建费用账或重复POST。免费HTTP真实字节/unknown与LLM账分开，不把资料已登记数当下载数。

## 验收节点

只在完整研究/预测大节点封存并四路独审；审查关注资料/虚拟化/切片摘要、FF真实复用与类型路由、RF步骤/数字出处、资深买方模型质量。结构绿不代签经济质量，外部限制单列。根因修复若影响通用机制，先同公司regression复验，再药明合联、Snowflake泛化，旧公司不再称新holdout。
