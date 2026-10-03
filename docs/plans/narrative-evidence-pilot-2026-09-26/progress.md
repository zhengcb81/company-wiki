# Progress：激进简化实施

> 历史Phase 1–64及详细运行记录：https://github.com/zhengcb81/company-wiki/blob/bff81afe7cbb11c895764a94c2eabd121539e248/docs/plans/narrative-evidence-pilot-2026-09-26/progress.md。当前只记录本计划的真实完成项与下一步，不重复旧验收。

## 2026-10-03 — 采纳方案、恢复实施

- 用户明确要求以八束激进方案改整个PWF并继续执行。已将task_plan改为S0–S6当前顺序、具体接口/owner/大节点与原件保护；README统一入口，旧卡的执行要求由当前页覆盖，不复制大体积历史。
- CWP当前bff81af已核clean。正常用户只读外仓：RF main6fb2def7/4 tracked dirty，fcap5319ee26保留；FF c47c397 clean，ET4924d57 clean；StockWiki d4779e6/2 tracked dirty，IQSbfaf04c clean。未覆盖其他owner。
- 并行分工：R1先精确退役清单，N4A先scope接口负例；root拥有PWF/hooks与汇合。写入必须独占文件，shared Store与registry/planner分开。
- goal实读paused；工具只有get/create/update(complete/paused/blocked)，无resume/修改objective；继续已授权本轮工作，不错误mark旧goal complete。
- 初始决定：先保存计划，然后S0 TDD/退休，N4A在独占范围并行（已完成，见下文）。旧Worker仍paused，未调用provider或删除原件。

## 当前步骤

S0/N4A已正常发布且CI绿；S2完整prompt/usage/HTTP节点与持久预算施工，S3–S6 pending。下一次完成节点后及时commit/push及更新本页，不新增每文件review/coverage门。

## S0 / N4A TDD进行中

- root先取得4项确定性RED：commit重复pytest、config always_run、activation CLI无reviewer失败、restore无reviewer失败；实现自动actor记录与静态commit后，36相关测试GREEN/6.62秒，Ruff/mypy3模块通过，测试根finally删除。
- R1 agent先取得11项退休行为RED；整套退出后节点包157通过/3静态失败，真实叙述3个E2E与23个内容质量测试均绿。收敛import层级误判与B10现行metadata handoff，未弱化原件/引用断言。
- N4A agent取得19项scope初测，12项缺scope接口RED；正实施SQL先LIMIT过滤与prepared effect scope，通用状态/Store schema不改。
- root整套删除旧deletion_manifest及仅服务它的Unit/过期ignore；合法ignored凭证的旧rotation门已先RED再改，真实tracked/history泄露检测仍保留。可选prompt签名writer只服务fixture但有多个consumer测试构造，合入S3诊断协议收口，不在本批留下新签收替代物。

## Errors Encountered

- sandbox只读Git提示用户ignore/cache权限；正常用户元数据盘点正常，不修改ACL或reset。工具agent线程上限沿用现有agent，不继续创建新线程。
- 两个猜测测试文件名不存在，改用CodeGraph给出的实际activation/restore文件；rg混合显式文件和目录导致过宽输出，后续只列命中文件/精确片段。pytest插件隔离下asyncio_mode警告不影响结果；测试根已清。施工中另agent文件EOF提示交该owner收尾，不跨线修改。

## S0 / N4A集中验收完成

- root一次集成全Unit及受影响activation/restore/transcript/automation/B10合同：1161 passed /178.40s（Windows）；隔离根finally删除。该大节点不进入每次commit，提交只静态检查，CI继续现有快速组。
- R1首次157绿/3红，根因修复责任包22全绿；11退休RED与4数组元数据RED均转绿。净删约4027行；gold内容质量和三份真实叙述E2E保留绿。
- N4A相关120绿/1新增spawn夹具身份错误，修夹具后该项绿，root集成21scope全部绿。覆盖批外parent只读、空scope零事务、101早prepared及库外ACK不被本批处理。没有schema升级。
- secret ignored-local规则1 RED→9相关GREEN/17.55s；真实tracked/history泄露检测仍在。复杂度冻结及其镜像断言退出，tools/complexity_report.py只报告；不新增数值门。
- root extra mypy发现现有Spec float→Worker int秒注解不一致，统一真实支持的float秒，不截断lease。生产raw/config/control/DB未写，测试不联网、不读实际key。
- goal重新创建尝试被工具拒绝：cannot create a new goal because this thread has an unfinished goal。旧目标尚未完成，不能mark complete绕过；应用卡仍需用户侧resume，执行持续推进。
- 当前准备正常提交推送S0/N4A和PWF；S2新adapter文件若已创建不混入本次阶段提交。

## S0/N4A发布与S2模型接口

- ff5396c3a8766f557c016c30cbbf33571d67b288已正常commit/push；Ruff/mypy/host静态hook通过，pre-push精选通过，无跳过hook。CI37131769647成功，Fast checks job53秒。
- 15项usage字段先RED后GREEN：可选成对token、0有效、bool/负值/部分字段拒绝；4位置参数replay兼容，坏JSON仍可带真实usage。
- 完整schema/同语言wire示例先4 RED，prompt升级1.1.0；41项summarize/model字段包GREEN/1.62s。模型端清楚业务叙述、来源引用、角色/情态和质量诊断；不新增第二轮LLM。
- gh不在PATH/常见安装位置；改用GitHub公开API取得真实CI收据。发布前scope测试多一个EOF空行被diff-check拦住，修空白后正常提交，未绕过检查。测试独立根已finally清除。

## S2/N4节点A：持久预算与生产factory

- AUTO v3只新增run/run_jobs/reservations三表，v1/v2事实与只读classification竞态保留；当前reopen只读，旧v2明确迁移且仅一次小库backup。预算不创建第二CSV/数据库。
- 55项预算/迁移相关契约累计GREEN，含真实双spawn抢最后额度仅一份成功、kill/expired lease后预留保留、异常聚合整数上界仍记账并block。ctor不初始化/迁移生产库。
- HTTP33项真实loopbackGREEN/2.13s，无redirect/retry/fallback；truncate带已知usage、确定零HTTP的credentials具名区分，不保存响应正文或key。
- caller先7 RED，再7绿/1新storage-failure RED，修后8全绿/0.98s；settle-before-decode，未知保占额，确定未调用才0，DB结算失败保预留metrics。handler新增4 RED，45包全绿/1.43s，坏JSON/坏claim不丢已付费metrics，skip0调用。
- 请求16 RED→16绿；round-trip补1 RED修正规范金额后17绿/0.69s。1–100精确refs、折叠重复、路径在composition、integer microUSD，profile/时限/模型/费率/版本共同bind hash，secret值不进入options。
- 正式factory15项已各自GREEN含真实spawn+真实Reader零外网/原件不变；真实Reader的dict返回不协变，用只读Mapping Protocol收敛，无cast/第二Reader。6模块mypy与现行Ruff scope全绿。
- root大节点集中1241项：1238绿/3旧预期红，旧expected error tuple/v2 version+table set；同步真实v3后117责任包GREEN/13.35s。不重跑全部既有1238绿、不放宽注入/版本/lease断言。所有独立根finally清除，生产DB/config/control/raw未写。
- 尚未完成：正式batch coordinator/CLI、terminal降容、完整本地HTTP CLIE2E、真实四样本live与S3–S6。新markets/agreements业务句零召回已记S3质量缺口；不能将factory synthetic成功当真实叙述召回验收。
