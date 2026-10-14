# 共享引擎＋多份文档阅读策略 — ROOT统一执行PWF

PLAN_ID: document-understanding-2026-10-13
PWF_PLAN_ROOT: C:/Users/郑曾波/Projects/company-wiki/docs/plans
Owner: ROOT
Current Phase: A/B — 生产选择/摘要与缓存恢复已接线，集中工程验收及真实质量继续

## Goal

完成一个共享文档阅读引擎与多份市场/文档/业务策略，并接入正式资料处理、原语言摘要和缓存。与母PWF共用G2/G4/G5真实验证；不另建引擎、任务库、全篇MD副本、权限或人工签收链。原件保留，IO/身份/预算各由负责层执行。

此表是唯一当前执行状态；详细施工见 [completion_implementation.md](completion_implementation.md)。旧DU/DU2接收已关闭，旧卡和阶段文字只供历史/设计参考，不再等待交付或重发同卡。改前先读本表、findings、progress及所做节点细则。

## 已完成基础

- [complete] 20原件调查、设计与DU/1接口、原三包和独立接收整改。三仓本轮架构质量改造已发布。
- [complete] DU2三最新作者＋ROOT整合：一个运行catalog含24文档规格/14业务策略；层级/实际范围、原文闭包、字体/粗几何和有界布局实际消费。
- [complete] 联合1135 PASS，四PDF658原文span验真，真实10-Q六项PASS，独审共同根因关闭；原件/配置/测试环境保持。
- [complete] 源码deb7eb7d并master并推送，CI38476678472 success；正常pre-push4175 PASS/17 SKIP。收尾9e4faf2a已推送，ROOT整合树/临时材料已归档回收，作者bindings保持。

## 剩余阶段（仅三大节点）

### Phase A: 生产选择与唯一材料

**Status:** in_progress

统一ReadingPlan进入既有candidate/finalize/budget流程，业务价值/主题多样性/新信息和完整闭合边际成本共同决定选择。根治旧活跃题材/固定4–9个月优待，不能仅改排序或提高cap。共享上下文唯一材料＋组引用，复用生产eN/gN形式。先写行为RED，集中实现并跑A受影响测试。

责任范围：source_catalog的候选/预算/最终选择；document_understanding的选择桥/摘要组装。旧版本仅供必要回放，新默认在C达标后切换。

### Phase B: 正式摘要、generation与缓存恢复

**Status:** in_progress

同一次parser→DU→正式SelectResult→ModelRequest→NarrativeRef，只有最终实际采用提示进入模型。selection-decision指纹与final-sent-policy指纹分开；未选但参与决策的策略变化也失效，无关策略不全库重建。

采用base归属→正式select一次→final generation CAS→模型任务顺序，复用原AUTO/Store/outbox与计费。production factory/loopback、相关/无关变更0POST、取消/丢ACK/重启、旧ref回放和消费者在一次集中工程E2E节点验收，独立复核后正常发布。不新建canary或人工许可。

### Phase C: 真实质量、泛化、默认切换和清理

**Status:** pending

同原件同范围同预算旧/新比较，精确使用配置的MiMo/DeepSeek/MiniMax和原累计账$20/200万token；与母G2真实摘要、G4原三公司、G5新A/H/US三公司共用一个验证窗口。包含文档类型覆盖、关键业务gold、原文回开、数字/角色/阶段、空间/时间/并发观察。

细分栏/细表不足及缺样诚实记录；关键经营信息漏读不能用partial标签放行。达标后一次切正式默认、清理被替代运行逻辑和自有scratch，保留历史ref回放、原件及必要usage，正常并线/推送/精确CI与技能定点同步。

## Next Step

下一步完成同原件 A/H/US 有界闭包回放及 RF 新 DTO 兼容，然后统一正式配置摘要、缓存恢复与真实质量验收。连续上下文、经营表筛页、英简繁机制已实现：相关257 PASS，原10个独审探针最终全 PASS；真实小PDF经营表与原文回开2 PASS。a117fafc 已正常推送，精确CI38554334091 success。实际CWP→FF→RF离线联调暴露RF消费者仍只识别旧Bundle/claim/versions，须完整保留并验证新 reading_context 与组引用；不删字段伪造通过。三个真实原件回放进行中；默认仍0.8，正式供应商调用尚未开始。三DU3已接收，作者树保留干净，RF仅在独立工作树施工，不触及旧assurance/output。

最新工程节点：[明确范围收据](production-selection-evidence/acceptance.json) / [压缩测试与独审证据](production-selection-evidence/receipts.zip)。真实CLI三载体已强制完整dependency和same/cross-run0POST，集中143PASS；统一A/H封面用途与历史发行信号溯源195PASS。当前质量阻点是PDF跨原生blocks断句/经营表筛页与多语言业务机制，不是再提高预算。正式摘要尚未付费运行，默认0.8保持。各历史FAIL和独立金标字面错误保留。

## 并行施工（现在可独立启动）

[DU3三卡总览与工作目录](parallel/du3-2026-10-14/README.md)。QUALITY仅拥有tools/document_understanding_benchmark；DEPENDENCIES仅拥有新decision_dependencies子包；GEOMETRY仅拥有新layout_snapshots子包，各自另有排他tests/ledger、独立稀疏worktree。ROOT保留source_catalog候选/预算/finalize、DU选择/summary与automation正式接线，三线不写这些共享目录、不重开旧DU/DU2卡。

三卡已由用户分发，接口冻结DU3/1，ROOT不写作者工作目录。2026-10-14最新盘点三树干净：GEOMETRY接收为7e023a15/c6224a1a/ef69957a（ROOT89PASS/13SKIP）；QUALITY接收为016e3b4a/9f1a27bd/a8686990/804dfbb7（ROOT217PASS/7SKIP）；DEPENDENCIES接收完整六commit为c79e0c13/e5ad62af/f86aea25/7fd2f117/8a4e4cc4/d6e91356，含两轮独审根因修复。ROOT完整trace/current重建、实际0POST缓存与恢复仍须验证；这些组件PASS不代替生产PASS。A/B/C只作三个大节点，真实模型与跨仓共用母窗口。

## 完成标准与注意事项

- A/B/C全部有真实证据，正式默认启用且发布后才关闭共享阅读升级。母研究循环按原计划继续，不将模块PASS当经济研究PASS。
- 旧微软关键业务baseline4/8 FAIL保持；真实/合成/不可评分别报告，不降gold或删失败收据。
- 生产HTTP原已unique evidence rows；重复正文在DU中间package视图。接线复用既有传输，不能误修正确的HTTP机制。
- 原件与生产配置不写穿；测试独立tmp/sentinel/owned清单，成功/失败都恢复。Dayu/IQS和他人WIP不动。
- ROOT统一共有接口/状态/Git。旧DU/DU2作者卡已完成，不自动重派；DU3按上节最新状态接收，未来分包需排他目录与冻结接口。
- 既有静态/快速hooks正常执行；只在A/B/C大节点做集中复核，不新增小节点门禁。

## 依据和历史

[已发布DU2验收](du2-reception/acceptance.md)、[发布收据](du2-reception/evidence/publication.json)、[旧DU验收](reception/acceptance.md)、[设计](design.md)、[接口](INTERFACES.md)、[旧细则](review/root_implementation.md)、[母跨市场PWF](../cross-market-rf-e2e-2026-10-08/task_plan.md)。原ROOT阶段表保留在Git 9e4faf2a；本表已合并其完成事实与全部剩余任务，历史不再作为当前指令。

## Phase A预算组件节点

纯planner104集中PASS/38独立probe PASS，mypy/ruff通过；原RED、环境失败、测试fixture纠正及独审中间失败留证：[小归档](phase-a-budget-evidence/receipts.zip)/[组件收据](phase-a-budget-evidence/acceptance.json)。只签纯planner，生产ReadingPlan/候选/最终模型输入仍待接线；旧默认与原件/配置保持，0付费。

## 当前 ROOT 实施记录 — 2026-10-14

- 0.9.0新路径实际运行共享understand_units→候选/闭包→既有reading_plan/1→canonical EvidenceSpan。旧题材/4–9月规则只留历史版本。明确anchor身份、被拒包deferred、结构工作停止已修；21边界反例通过（另20K效率反例正在修）。不同原件同locator+同文本保留各自source身份，结构按parent隔离、全局共同竞争预算。
- 正式SelectResult→ModelRequest→Bundle保留紧凑策略；真实48K共享上下文只发一次且双组独立。30新传输测试/246相关集中通过；后续ROOT加bounded deferred全count、选择诊断与可选decision依赖，需统一复验。
- AUTO schema6只增既有run_jobs的nullable final_generation_json；select成功与final CAS同lease事务。实际model有效配置核对、reservation前final-ready、动态runtime resolver已接。143 Store/migration/factory相关通过。
- 新HTML/PDF/TXT正式CLI+子进程E2E和付费后待activation恢复4PASS/65.91s；loopback0真实供应商调用，原件/config/临时目录恢复。same-run0POST，缺完整decision trace跨run不能冒充缓存命中。
- 独审发现20K候选扫描耗尽预算、deferred逾1MiB，及真实HK多行经营表漏读；分别改planner索引/工作计费/有限样本＋全量计数与通用多行header结构。旧失败收据保留，不提高限额或降低gold。真实供应商/质量泛化/default切换未完成。
- 三DU3工作树只读核对仍在195aba20基线，无新commit；ROOT未修改它们owned路径。当前ROOT可选dependency hook缺模块会明确诊断，允许摘要但不允许新缓存有效复用，不重写外包freezer。

## 2026-10-14 生产接线工程节点

实现d3c57b31和夹具修复fc2a4513已正常推master；正常pre-push4379PASS/17SKIP/381.75s，精确[CI38540579403](https://github.com/zhengcb81/company-wiki/actions/runs/38540579403) success。[发布收据](production-wiring-evidence/publication.json)。原3个旧schema夹具失败保留在[修复记录](production-wiring-evidence/push-repair.json)，未跳hooks。

[节点收据](production-wiring-evidence/acceptance.json) / [紧凑原始证据](production-wiring-evidence/receipts.zip)。正式public request显式0.9、唯一原文/策略摘要、same-run/outbox/真实v5升级、原件篡改拒绝已验。集中1149 PASS/17 SKIP/3旧factory失败后，只复跑受影响51（50PASS/1新test参数失配）及最后18PASS；全部已知工程失败关闭，原FAIL保留。新7E2E：集中6PASS，1计数观察点过时，改为统一真实byte owner后1PASS；旧11E2E全PASS。没有反复重跑千项套件或降低断言。

**A/B/C仍未全部完成：** 真实跨run缓存等待DU3依赖组件；同原件旧/新三市场native回放更快但不是摘要质量通过。实际微软8条required_business仅1/8在新选择中保留（旧4/8），三层共因已实证，不是拆句误报。新默认不能启用；下一批先通用RED再修，不在生产加公司词/样本特判。unknown语言准备仍有一次重复读，作为同责任层性能收尾，不新增审批。
