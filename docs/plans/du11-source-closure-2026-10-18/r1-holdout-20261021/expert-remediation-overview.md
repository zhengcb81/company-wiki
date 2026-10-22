# R1 药明康德专家共因方案与施工入口

状态：**独立诊断与可执行PWF已封存，产品修复/真实复验待ROOT立即按包施工。** 本页只引用独立run主包；全局当前状态仍以[CURRENT_STATUS](../CURRENT_STATUS.md)为准，未改写它或四路封存报告。

运行：[r1-20261021-cn-wuxi-apptec](C:/Users/郑曾波/Projects/revenue-forecast-audit/runs/r1-20261021-cn-wuxi-apptec)。initial manifest `ee08753799d7d2a849dd3fd9c811e7c0e83d20d7538f978218245fdf98dca458`。四路26issue（storage7/fetch8/process6/analyst5；15P1/11P2）已全映射11根因和7包；RC11是携带DU11-R2，不多算一个本轮reviewer缺陷。COORD-OBS-001记录locator/工具限额，126机器MISMATCH不是126事实错误。

主入口：[task_plan](C:/Users/郑曾波/Projects/revenue-forecast-audit/runs/r1-20261021-cn-wuxi-apptec/remediation/task_plan.md)、[findings](C:/Users/郑曾波/Projects/revenue-forecast-audit/runs/r1-20261021-cn-wuxi-apptec/remediation/findings.md)、[progress](C:/Users/郑曾波/Projects/revenue-forecast-audit/runs/r1-20261021-cn-wuxi-apptec/remediation/progress.md)、[共用合同](C:/Users/郑曾波/Projects/revenue-forecast-audit/runs/r1-20261021-cn-wuxi-apptec/remediation/shared_contract.md)。机器映射：[root_causes](C:/Users/郑曾波/Projects/revenue-forecast-audit/runs/r1-20261021-cn-wuxi-apptec/diagnosis/root_causes.json)、[coverage](C:/Users/郑曾波/Projects/revenue-forecast-audit/runs/r1-20261021-cn-wuxi-apptec/diagnosis/coverage.json)、[安装旧SHA基线](C:/Users/郑曾波/Projects/revenue-forecast-audit/runs/r1-20261021-cn-wuxi-apptec/diagnosis/baseline_files.json)。

|包|Owner/范围|依赖|
|---|---|---|
|W01|CWP source/catalog：request-aware有界增量发现、availability与最少来源资格|ROOT接口一次接收|
|W02|FF与RF边界：有效nonzero业务JSON、closed DTO、独立companion结果|接W01 DTO；可并行|
|W04|CWP automation：移除新增实验coverage付费补写，恢复旧mergedfinal/费用|可与W01/02/05并行|
|W05|RF targets：dimensionless ratio与有限segment_group统一原生比较|与RF边界文件分开|
|W03|CWP reading：现成0.9+/5真实上下文、业务/claim语义|W04先合入，避免automation冲突|
|W06|RF新attempt：Q1/H1最新目标、最小经营/RPO/确认/联合压力桥|有效来源/合同/target组合|
|W07|ROOT：定点安装、一次真实0.9 paid-resume/cache/消费大节点、四审与泛化|整合前述包|

每包完整文件在run/remediation/work_packages/Wxx.md，包含可写/禁写、固定DTO、RED→GREEN反例、幂等/费用/空间/失败清理、真实大节点/独审、定点同步oldSHA与handoff。ROOT source lane与既有runtime worktree automation lane分开；RF边界和targets分文件，W04后W03串行。

关键决策：最新H1最后原因是第17个无关历史候选触16限额，不能沿旧publicationunknown或无限扩限。复用可靠availability；真实source-owner本次verifiedopen最小receipt只证明当日及以后，不能改publication/旧asof，若不干净可后续而不扩建。0.9/RFcontext已有实现，真实initial0.8不能验收共享路径。生产default仅在真实语义/消费/普通恢复大节点通过后由ROOT决定。

R2允许修复或移除，本方案选择退役新增付费补写，并保留旧partial/merged输出/费用与确定finalowner恢复；不放宽immutableoutput0、不建multi-operation框架。普通singleoperation paid后激活前恢复仍必验，缓存命中不能代替。旧原AUTO缺失与多pin未知保留具名，不声称所有历史路径已支持。

研究缺口独立处理：97/105参数与1276比较零算术错保留；45未来条件率、H1信息、RPO与交付取消stress需来源反证和更正模型对照，不机械抬到guidance。比例rawmetadata用既有dimensionless，canonicalcurrency=null，与金额/背景币种分清。

专家未付费、下载、改产品/配置/安装或提交。R5已完成不重做。预算母1544023tokens/625258microUSD、公司39026/9720含unknown仅为观察，实际call前重计，MiMo401unknown不盲重发/reset。旧NVDA14根因/7包、原八家公司后续目标、药明合联→Snowflake顺序全部保留。

**下一动作：ROOT一次接受共用接口与RED后，立即并行W01/W02/W04/W05，再按依赖施工、原公司新attempt复验。**
