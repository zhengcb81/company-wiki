# 仓内PWF与ROOT协调（解耦前暂不派发）

最新用户决定覆盖原先并行建议：先按[DECOUPLING_FIRST](DECOUPLING_FIRST.md)集中完成解耦与D3验收，RF/AUDIT业务卡暂不派发。当前ROOT可实施必要跨仓边界改造；下列每仓writer安排只在D3通过并重新校准卡片后生效。跨仓部署、真实paid和组合验收归ROOT。

| 线 | 工作仓 | 唯一计划入口 | 启动条件 |
|---|---|---|---|
| ROOT-CWP | C:/Users/郑曾波/Projects/company-wiki | docs/plans/du11-source-closure-2026-10-18/task_plan.md | 总控主线 |
| ROOT-FF | C:/Users/郑曾波/Projects/filing-fetch | docs/plans/import-budget-closure-20261102/task_plan.md | 与CWP同一入库链，ROOT处理 |
| RF | C:/Users/郑曾波/Projects/revenue-forecast | docs/plans/r4-owner-closure-20261102/task_plan.md | DEFERRED_UNTIL_DECOUPLING |
| AUDIT | C:/Users/郑曾波/Projects/revenue-forecast-audit | docs/plans/r4-owner-closure-20261102/task_plan.md | DEFERRED_UNTIL_DECOUPLING |

RF已有4个assurance/runs外来tracked改动，必须保留；建议从包含计划的main建立codex/独立worktree。AUDIT无remote，不虚构推送。新worktree选同PLAN_ID/PWF_PLAN_ROOT，不新建竞争根计划。无工作冲突才能在原目录做，禁止reset/clean或覆盖旧runs。

## 固定接口责任

- SourceRef/SourceExport v2：source ID/hash/byte_size、逻辑身份/期间/availability、locator归CWP；物理存储路径不变成研究逻辑。
- Narrative：现有Ref/bundle、完整原话、support/context和quality状态。改写不替换原文，semantic_not_evaluated不冒已验证。新增字段先放便携新旧fixture，不只改producer让consumer猜。
- Acquisition：公司/文种/期间请求、实际预算/剩余deadline、命名结果和真实usage；CWP实读入库，但不另设16MiB许可。
- RF：kind/source/claim/单位/日期和计算血缘归RF；显式关系可加，不从公司名、ID、rationale猜可比性。
- AUDIT：attempt/run/实际消费输入/输出引用、native状态、观察完整性、四路质量结论分别表达。可选记录失败不重POST，缺记录不能冒PASS。

版本与字段以当前公开代码/fixture为准，不复制巨大schema、不造授权JSON。兼容变更普通commit协调，核心未知状态诚实unsupported；不一律忽略未知语义。

## 组合验收端点

| 流程 | 真实终点 |
|---|---|
| 已有资料 | 公开SourceRef正确复用，provider调用0 |
| 缺电话会 | FF→ET真实CLI/supervisor+假HTTP→CWP import/writer→verified-open；请求22MiB、合法17MiB FMP原始JSON（symbol/period/year/date/content）、再次复用0下载；保存/读取原始JSON字节与SHA一致，TXT仅为提取结果；错hash/身份/真实超额反控 |
| 来源忠实 | normalize/select→实际模型输入→decode，父链与限定正反例；单真实H1 |
| 新摘要/恢复/采用 | 同新artifact→prepared恢复→同/跨run0重复POST→RF实际parameter/formula/report/snapshot |
| RF本仓 | 期间补集、单位/血缘→compute/report/snapshot；无CWP内部DB依赖 |
| AUDIT本仓 | fake native成功+optional observer失败保业务结果；新attempt绑定；四审未知不冒PASS，最终绑定ROOT新真实run |

## 交付与签收

各线TDD、受影响域测试；交付前由未实施该代码的独立agent全面检查任务完整度/质量/泛化/边界。发现问题修好后才交付。只有仓内交付、ROOT来源大节点和真实链大节点审查，不按helper增加签收。

一份handoff.md即可，包含：基线/交付commit与修改范围；原issue逐项处置；接口变化/兼容；实际测试命令结果与独审链接；费用/临时目录恢复/剩余风险；ROOT一次重放所需fixture或artifact引用。现有机器结果可链接，不强制重复一套JSON/逐文件签名。Git负责代码版本，原件/paid artifact hash仍沿用。

有remote正常推支线，无remote如实本地交付。ROOT读差异/独审，跑必要消费者契约及组合E2E，正常并线/发布/定点安装，只把commit与结论引用写回主CURRENT_STATUS。组合版本表是事实记录，不是运行许可。

解耦阶段接口变更由ROOT集中完成并实测，业务线不提前施工。D3后由各仓提交确切接口变更供ROOT组合协调。并行不能消除新真实摘要→实际RF采用的因果依赖。
