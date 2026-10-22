# W07 固化联合验收控制器：独立测试实现卡

ROOT，2026-10-22。只实现可复用测试控制器与离线真实链路；真实付费执行由ROOT后续按预算统一启动。它与W03-A两线、母仓当前发布不重叠。

## 责任范围

- 工区：`C:/Users/郑曾波/Projects/company-wiki-r1-holdout-controller`，分支`codex/r1-holdout-controller`，基线`c3b4ebf1`，稀疏源码/测试目录；不复制完整运行湖。
- 可改：一个独立测试工具模块族 `tools/document_understanding_benchmark/holdout_acceptance*.py`；快速单测`tests/unit/test_holdout_acceptance_controller.py`、大节点多进程端到端`tests/integration/test_holdout_acceptance_controller_e2e.py`及确需的测试support；自有PWF `docs/plans/r1-w07-controller-20261022/`。恢复/缓存多进程套件显式在大节点运行，不加入每次提交的快速CI，不改CI或新增许可flag。
- 不改：生产`src/`、模型/来源配置、budget/native数据库实现、FF/RF/ET、母仓PWF、安装副本、旧phase-C代码/旧run/旧gold、0.8默认。发现生产缺口给ROOT证据和RED，不自行扩大改动。
- **不调用外部/收费API、不读真实key、不下载真实资料。** 测试只用isolated loopback HTTP/fake key，但必须走现有configured batch入口、真实Catalog/AUTO/worker/HTTP adapter/paid pin/outbox/cache。

## 共用输入与输出

控制器接收显式参数：公司/run/attempt标识、现有project-root/catalog/AUTO路径、完整SourceRef、固定as-of、当前LLM配置路径/provider、明确token/费用/时间/空间上限、receipt输出目录；不得在代码硬编码药明康德或三个development sample ID，不引入第二账或任务库。

请求固定selector0.9.0、reading-model-input/5；model/options由既有Config加载。**v5使用原文source cards+模型排序决策，实际模型wire是/6；不能要求旧自由摘要JSON。** 保留source cards/headings/support/context和实际generation绑定；不把availability读取metadata或reviewer gold注入模型输入/cache key。

预检复用正式入口的公开builder、selector和adapter，用显式内存preview context计算实际request_bytes及`len(body)+128+配置max_output_tokens`；标为preview，不造native执行/lease/摘要收据。它不建立AUTO run、generation locator或reservation，catalog和原件不变，自有scratch清理。正式configured调用在预算预留与POST前核对预检完整body SHA/bytes/输出上限；不一致明确失败。早先将preview做成故障native run的两次失败保留，不能删locator或改SQLite使之“恢复”；真正同run恢复仍是下一节paid-response后路径。

分段执行、可重入并记录阶段收据；每次新阶段读取原生真状态，不靠手写PASS。输出至少：请求/source/config非密钥fingerprint、native run/reservation/paid operation/pin/文档generation、POST计数、恢复/缓存前后费用与reservation差、原件SHA/临时根清理、阶段状态与具体失败原因。不得收集HTTP认证headers/环境变量值。

## 离线必须跑通的正向生命周期

1. 用真实configured batch CLI/入口和loopback OpenAI兼容响应，执行真实0.9/v5路径；provider只根据收到的真实卡片构造合法排名，无审查gold/指定公司事实。
2. 第一次HTTP成功、paid response与usage已原生持久化后，在summary终态提交前制造受控失败。优先复用现有 `test_narrative_legacy_final_output::test_ordinary_single_paid_operation_recovers_then_activates_with_no_new_reservation` 的 **RETRYABLE** 恢复路径和已有公开batch恢复能力；不能凭猜想改为会阻断恢复的terminal返回。
3. 新进程/新合法lease恢复**同audit attempt+batch run+paid operation**，原生`BudgetedNarrativeCaller._recover`和真实`replay_response`实际执行；不要求保留旧worker lease/runtime fence。HTTP层观测0新增POST、0新增reservation；费用/未知预留不释放。
4. 恢复继续到outbox，第二处在测试wrapper的`NarrativeArtifactStore.activate`中暂时拒绝，实际得到activation_pending；解除后同run激活完成，最终artifact可见。不要给生产增加故障flag。
5. 新batch run_id/空workdir，其它有效输入相同，真正跨run cache复用同artifact；0 POST、0 reservation、0 token变化。cache不能代签第3步paid replay。

**POST控制点必须在实际HTTP request层。** 旧phase-C observer在caller.generate前forbid_post会误杀合法replay，不能复用该错误。故障仅作用于本次owned测试进程/fixture，不终止其它agent，也不直改SQLite伪造状态。

如公开batch恢复接口客观不能完成某一步，保留真实RED和最小根因定位，先报ROOT；不得用手工造结果/直接调用私有store完成后声称公开生产全链通过。

## 负向与关键验证

- 本地测试缺pin、篡改pin/请求、旧lease/current parent失效，不得再次POST或清掉未知费用；不为负例额外调用供应商。
- 一次POST约束跨阶段/子进程真实计数；记录每个CLI native exit及stderr，不把生成读取失败一律换成transport故障。
- 保持旧0.8 generation/请求字节和已冻旧run不改；控制器不切生产默认。
- 脚本能在边界失败后安全重入，不产生第二个费用账/隐藏下载。目录初始状态→结束状态一致，清理由测试拥有的明确根完成；无完整恢复备份演练。
- RF实际`consume_narrative_input`绑定used parameter/formula是ROOT后续跨仓步骤；本工具可留明确版本化结果/路径交接接口，不写RF或伪称`context可读`已消费。

## 后续真实执行（本施工禁止运行）

ROOT将复用R1既有scoped wiki，年报原件SHA`7f1431d66eae399d4b35639bb650e23287c7f52dacbb47b4b4a197fb5026d6a2`、1,608,226B；不重init/复制整湖/重新下载。先母账与公司native索引重计，当前母余455,977tokens/$19.374742，公司余60,974tokens/$0.990280；实际调用前以更小实时值为准。旧MiMo UNKNOWN无pin不能重发、旧DS0.8无pin不能代演练新paid replay。

真实payload的保守预算沿用原生`len(body)+128+max_output_tokens`，不能按字符猜更小；超公司余量先报告实际字节/原生bound，不擅自缩小用户配置输出或释放旧预留。阶段原生费用汇入现有`append_native`/`mother_totals`，无第二收费账。

## 交接

先RED再GREEN，相关loopback完整E2E、工具静态检查/项目mypy、normal commit；所有临时目录恢复原样。提交`handoff.md/json`含产品commit+逐文件SHA、真实命令/阶段/POST及费用差/skip、初始和结束temp清理、未完成的真实API/RF消费边界。ROOT安排非作者独立审查并修清所有材料性问题后接收；分线不能自行push/合并主线或调用供应商。
