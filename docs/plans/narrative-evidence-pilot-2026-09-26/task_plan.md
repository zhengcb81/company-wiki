# 公司来源平台：当前总计划

**新增G5独立包（2026-10-07）：**[三卡总包](harness_lanes/g5_parallel_packages_2026-10-07.md)ready，可现在分别交harness；CWP六旧工程/批处理壳退休、SID纯API解耦与身份查询预算、RF定点安装工具/三tmp验收，分别独占`Projects/_g5/cwp|sid|rf`不同项目工作树。当前目录尚未创建，未代用户启动。G3/G4已完成不重派；MAIN保留G2-12/FF/公共CLI/指纹/工程清单、真实安装与生产/总PWF/并线。目标继续paused，本次仅制卡和发布。

**最新G4验收（2026-10-07）：**两包已验收、并入实际执行分支并推远端。CWP `df7d7ba`：冻结Pipeline/Gate0–5整族退休及CN 1.3.0路由配套，211责任用例绿；精确CI37673393822所有步骤绿/74秒。SID `eb8495c`：latest分页矛盾TDD修复，127责任/真实CLI离线联调用例绿，已推`v2-clean-rewrite`；该仓无workflow，不声称远端CI。见[G4正式验收](g4_main_acceptance_2026-10-07.md)。G4不再派发。G2-03完成；完整G2-12 ensure/FF/ET/CWP入库与复用仍未提交，其他G2、R2生产应用/R3/R5未完成。总目标保持paused，本次没有恢复生产或付费批次。

**上一批G3验收（历史记录）：**三个包已接收并补齐MAIN接线，两个本地主线已并入。RF `ab7a7a44`已正常推远端main（107快测绿）；CWP接线代码`b2c9e66`随`4bde75a`已正常推master，115责任用例最终绿、1921单元绿；精确CI37665222739成功84秒，RF精确CI37664909065成功31秒。详情见[g3_main_acceptance](g3_main_acceptance_2026-10-07.md)。G3不再派发；G2-04旧维护退休已完成，R4依据现有注册重复上界决定不做对象化迁移（不是释放空间）。RF真实用户安装未同步；G2-12/其他G2、R2元数据生产应用、R3和R5仍未完成。目标服务保持paused，本次仅执行用户明确要求的G3验收，并未恢复总目标/付费/生产批次。


> **当前并行：**G2/G3/G4已发包均已接收，不重派；G5三卡可新派发，详见页首。恢复总目标后MAIN先收尾G2-12/FF与公共接线，避开G5三线白名单，再R2→R3→R4→R5；保留未提交代码及owner文件。

> 本页是唯一当前施工入口。旧步骤、旧预算答复和已交付卡不产生新的任务或人工签收。历史细节保留在 [收敛前版本](https://github.com/zhengcb81/company-wiki/blob/659bcefc9d49a7e7f7fdc58e9c11d46e45da49ab/docs/plans/narrative-evidence-pilot-2026-09-26/task_plan.md)、findings/progress 和阶段收据中。

## 当前最高优先级：G2 门禁全面补漏（2026-10-07）

**此前恢复运行时点实读active（本次保持paused）。当前次序为G2/P0→R2生产准备→R3正式运行→R4收益决策→R5收口。** 已审查八仓入口/生产配置/工程检查/两份安装技能；旧canary现场已迁移，默认steady/有效pin/AUTO机器错误/派生质量/版本化终态恢复核心代码93ac5a5已正常推送，精确CI37590638806全部步骤绿90秒。StockWiki/StockQA日常全套、联网hook和隐藏阈值升P0-B，具体工具/默认配置/AGENTS同步写集已加[G2实施单](gate_simplification_reaudit_2026-10-07.md)，仅两个大节点。[原审计收据](harness_lanes/results/g2_gate_reaudit_2026-10-07.json)、[现场迁移](harness_lanes/results/g2_steady_production_migration_2026-10-07.json)和[核心实现验收](harness_lanes/results/g2_core_implementation_acceptance_2026-10-07.json)各自明确证明范围。

**上一批G2施工包分派历史（已验收并线）：**[StockWiki日常检查](harness_lanes/g2_stockwiki_daily_checks.md)、[StockQA工程入口/workflow](harness_lanes/g2_stockqa_engineering_checks.md)、[RF可选工具](harness_lanes/g2_revenue_forecast_optional_tools.md)。[并行总包](harness_lanes/g2_parallel_packages_2026-10-07.md)定义互不包含的工作树、冻结依赖、输出接口与MAIN接线责任。未代用户启动外部harness；MAIN继续G2-13/01b/CWP和FF共享接口，外线不等待MAIN改代码、不写CWP总PWF。StockWiki是新的剩余范围，不重派已完成旧工程卡。StockQA另外三workflow、RF release_checklist和历史读取器同步责任已纳入单卡。

G1历史验收继续有效，但不能宣称全面清理已完成。现场仅小policy变为steady，16有效断言/17事实表/原件/数据库/owner配置不变；S07旧security标签及生产metadata仍待R2。2cad90d/202责任/CI37582474369是此前代码的证据，不能冒充本次新代码已发布。没有新增人工签收，不重复付费模型/已绿大包；Dayu/IQS/原件/owner文件边界保持。

二次追链新增第13组G2-12：exact下载已单请求，latest却只返GAP并分叉到binding/snapshot/hash/expiry旧签收，新steady无snapshot也被旧close-gap拒绝，FF v2无法自动补缺；统一ensure资源事务列P0-B。另G2-01b无关root/DB位置仍令终态批次失效，明确pending。详细单给出完整代码/入口/测试/指导文件写集，保留真SHA/身份/期间/公开日/预算，而非放过坏资料。

最终追链补第14组G2-13/P0：日常AUTO/RunStore构造会做一轮/两轮整库integrity/FK检查，终态读和每worker启动合计三轮；CatalogStore当前schema每次仍全库fingerprint seed。预算同实例按run_id查询没有此问题。先系统拆开结构检查/显式深检并退出日常全库seed，再进入R2；具体写集/SQL trace反例加入G2A，仍仅两个大节点。

## Goal

逐步完成 company-wiki 叙述性证据选择、摘要/检索、Worker 多文档并发、跨项目消费接口和低价值原文/派生处置计划；每阶段先核查 revenue-forecast 当前实施状态，复用其正式合同与组件，避免修改对方文件或重复实现，并保留用户已批准的安全边界。

一个下载请求入口、一套 pathless 来源接口、一套 AUTO 任务系统；按需处理有价值的业务叙述，停止全量永久 PDF→MD 和重复正文。原件及来源/版本事实不丢。company-wiki 只供应资料和可定位证据，投资研究语义属于 StockWiki。

## 上一阶段恢复点（非当前总目标完成声明）

- **原目标16项已在明确范围内验收：**A12/A13最后两处下载日误拒已实际修复并线；其余14项沿用已发布证据，不重复已绿节点。[逐项结论](final_scope_audit_2026-10-07.md)、[实际主线验收](harness_lanes/results/final_asof_implementation_2026-10-07.json)。
- **RF已发布、StockWiki本地主线已合入：**RF e241389/精确CI37574397700全部步骤绿30秒；StockWiki9f552a6无远端，明确只验收本地master。六正式跨仓CLI6pass/29.63秒，晚下载成功、未来公开拒绝，证据逐条一致；两仓责任反例保持。
- **运行节点与范围：**selector0.4.2/parser0.1.1 aa52cbd、deadline7aa88ae及N6三包均已发布，既有精确CI绿。九样本29/33、761定位全回放；四required miss、optional三取舍和重复6仍公开，未降低标准。
- **保护与空间：**生产DB222408704B完整指纹、九原件及六保护文件不变；S5/S6净释放5659443210B/raw删除0。本次新建工作树和测试根全absent，临时清理136471537B另计。未重跑付费模型、九样本或备份恢复。
- **owner边界：**RF三日志dirty、CWP source_acquisition.yaml独立dirty均保留，不stage/覆盖；StockWiki主线clean；Dayu/IQS/quick-scan本轮无写。CWP ee0d1e7已推送，精确CI37575052423全部步骤绿70秒；本轮目标完成，必要施工无剩余。

历史恢复细节见[收口前已提交版本](https://github.com/zhengcb81/company-wiki/blob/1fb3cff6c1e32c01bfa5adbb4365b382a4d40b8b/docs/plans/narrative-evidence-pilot-2026-09-26/task_plan.md)与各节点收据；历史“未提交/待CI”不代表当前状态。

## 已批准预算与配置

当前明确批准的累计上限是 **200000 tokens / $0.12**（用户在本轮对费用提高回复“批准”）。此前60000/160000、$0.10和费用待答记录是历史。P04 招股同一业务片段→DeepSeek 已获批准并在 run08 成功；T01 电话会→DeepSeek 的明确外发授权继续有效。

run10 已执行一次 T01+零模型 policy，实际新增 `9151 tokens / 9853 microUSD`，新 unknown0/unsettled0。累计 `190035 tokens / 100502 microUSD`，历史 unknown7/unsettled0、FX guard `2764 microUSD` 保留；余 `9965 tokens / 16734 microUSD`（含 FX 扣减）。费用是配置价格代理，不能冒充供应商现金账单。没有必要再重复付费；现配置完整请求预留18755 tokens也不符合剩余 token，不自动重试或提高预算。

模型严格经 `Config.load / model_options_from_config`：MiMo `mimo-v2.6-flash`（`https://token-plan-cn.xiaomimimo.com/v1`），DeepSeek `deepseek-flash`（`https://api.deepseek.com`）；输出 8192、温度 1.0，现有 timeout/default thinking 不擅改。不退款旧 unknown、不用临时折价凑预算、不增加第二账本。

零网络准备工具现要求显式传入两项累计上限，避免旧 60000 默认误报；这是资源输入，不是人工许可文件。下列命令只读资料、只导出 RF 已提交六模块、清理临时根；输出路径必须原先不存在：

```powershell
python -B tools/n4c_live_preflight.py --rf-root 'C:/Users/郑曾波/Projects/revenue-forecast' --rf-head 6e6b817a1a6e4567293a4dcb835815f3be508a03 --campaign-token-cap 200000 --campaign-cost-cap-micro-usd 120000 --output '<新的小收据JSON路径>'
```

报告的 `budget_can_reserve_configured_output` 只检查输出 token；不能作为完整请求或费用通过的证明。全部日期真实旧账统一取 `prior_budget()`。当前实读证据：[显式额度离线准备](harness_lanes/results/n4c_explicit_limits_preflight_2026-10-06.json)。

## 实施顺序与当前完成范围

G1门禁精简、S3虚拟化本次最后两消费者公开日期合同已修复并线；S5/S6生产清理完成。S4真实业务效果已验证，完成审计发现的[R6局部摘要恢复](r6_partial_summary_implementation_2026-10-06.md)已补齐并推/精确CI绿；DOCSET与RAW-DUP并线已发布。N6三卡已验收并线/推送；MAIN先行历史final兼容9项/4.85秒绿和33点业务解释完成，不新增小节点门。

| 步骤 | 状态 | 范围与证据 |
|---|---|---|
| S0 简化收口 | complete | gold/shadow/Work Unit 人工链退出；commit 无 pytest，config doctor 仅相关改动触发；`ff5396c`/CI 绿 |
| S1 N4A | complete | scope 贯通 Store/Worker/Supervisor/outbox/prepared；空范围零修改，SQL 范围先于 LIMIT；节点 A 绿 |
| S2 N4B | complete | 隔离子进程客户端、真实 HTTP/factory、有限 batch、持久预算、lease/generation/kill/ACK 恢复；节点 A/B 集中验收绿 |
| G1 多余门禁/签收 | complete（原约定范围）；G2补漏in_progress | 人工审批链/下载日误拒已退出；当前重新核出canary、读取pin、AUTO错误和工程工具遗留，优先按G2清理，保留公开日/SHA/身份/预算等自动正确性 |
| S3 来源虚拟化 | complete（来源供应与消费接口） | SourceRef/SourceExport v2、FF→ET→CWP离线链、迁根/只读/SHA/语言/清理及当前两仓主线六CLI已验收；不等同自动投资研究计算 |
| S4 N4C与R6实际效果 | complete | 四类真实final/RF读取与run10业务复核完成；R6 TDD→184责任测试→正式离线E2E/RF→代码eae2dd4/CI59秒绿，保留好claim，坏片段不进入产物，不重跑真实模型 |
| S5 逐 caller 与派生清理 | complete | 旧全文 writer/消费者退出；生产 7104 旧文件、8191 handle 退休；原件与来源事实保持 |
| S6 DB 收缩与收尾 | complete | 1490530 旧 span 删除；DB 3055841280→222408704 B；说明/控制/短 smoke 已发布，精确 CI 绿 |
| S7 N5-DOCSET质量对照与整改 | complete（有界九样本与正式入口验收，剩余范围公开） | selector0.4.2/parser0.1.1已发布aa52cbd/精确CI81秒绿；九样本29/33、761定位全回放，200责任项与真实链/旧pin/升级11项通过。四个正式miss及canonical另页full、三项optional取舍/重复6保留；原分母/额度不变，不再重做已绿节点 |
| 可选原件 exact-SHA 去重 | 不阻 S0–S6 完成 | 先只读实证收益，保留来源/location 版本；未测重复 raw 不计节省，不自动删原件 |

[完成证据与真实缺口](main_completion_evidence_2026-10-06.md)分别说明 fixture/真实模型/消费者读取的证明范围。生产清理净释放 **5659443210 B**，原件删除 **0**，17 表事实及四份真实 raw 前后读取一致；正式证据：[生产存储收据](harness_lanes/results/s5_production_storage_acceptance_2026-10-06.json)。没有完整恢复 46GB 备份演练。

## 最小自动正确性与各层责任

1. 存储层：immutable raw、实际 open 的 bytes SHA、路径包含与写入归属；上层不重复解释 company-wiki/dayu/Dropbox 目录。
2. 来源层：公司/证券/期间/公开日期、版本/撤回事实；非核心采集字段缺失只诊断，不用 capture_ready/URL/collector 描述阻断真实字节读取。默认公开日期 cutoff，后来下载的旧公开资料可用。
3. 解析/摘要层：精选业务证据、同原语言、parser/prompt/version、全部 locator 回放；引用有依据，partial 不需要人工签收。只产生来源资料，不生成投资结论。
4. 调度层：一套 AUTO 的事务、lease/generation、幂等/outbox；计算锁外，提交复核来源版本；有限批次，不重启旧无限 Worker。
5. 资源层：文件/字节/时间/token/费用上限及未知 usage 预留；不新增角色、人工授权文件或签收服务。

原件一份，最终摘要和精选证据一份，小型事实/usage 记录一份。全文转换是临时材料；active/retry/prepared/未 ACK 恢复材料保留，终态成功后清理重复正文。典型 final 20–100KB 是目标，实测招股 238766 B；单 final 2MiB、批次持久增量 1GiB、scratch 2GiB 为现有限额，不因超限删除 raw。新生产 final 仍为 0，隔离试点全部恢复目录原样。

## 并行所有权与外仓边界

MAIN 独占共享接口、总 PWF、生产状态和所有合入；外线独占各自 worktree/测试/计划，不交叉写。RF、StockWiki、IQS owner 工作树不另写；IQS 有独立项目，不盘点、不重新分派。Dayu 为纯外部项目，**零代码修改**；不支持真实硬限额的路由外发前拒绝。CN 使用 StockInfoDLSimple，当前已发布 `v2-clean-rewrite@eb8495c`，不维护 StockInfoDownloader 主线。

G1-LEGACY、ET-DEADLINE、FF/ET-S3、P5-FF/STORAGE/RF、N4-T1/T2、StockWiki 来源/身份线与 MeetingConverter CI 卡已交付，不重派。相关功能并线不等于每仓所有历史 WIP 都已消失；Dayu 现有提交只有本地集成，远端 push 曾 403，不宣称远端同步。

已分派的 [N5 三包](harness_lanes/n5_parallel_packages_2026-10-06.md)：DOCSET基准已接收，质量整改进入N6；RAW-DUP已完整交付并经MAIN集中修正/51项与CLI绿，已合入master a41244a并推、精确CI57秒绿；ET-TXT已验收并线。卡内有独占目录、写集、接口、测试和交接，不重派、不新增 N4C 屏障。半年报、季报、融资/可转债、招股、IR 等的更广质量实证进入 DOCSET，不以选择器输出自己生成 golden。

2026-10-06 已核对三个独立目录均存在。DOCSET已验收并线58b74d0/精确CI绿；RAW-DUP交付e40b4ec已收到，见[MAIN验收](harness_lanes/n5_raw_duplicate_main_acceptance_2026-10-06.md)。ET 代码`96c9bc8`、交接`2b9fb84`已验收并推 main：MAIN 92项/26.24秒、10 goldens、相关 Ruff 绿，主线真实43份TXT只读 audit/0写收据/原件与配置不变，测试根恢复 absent；[正式验收](harness_lanes/results/n5_et_text_main_acceptance_2026-10-06.json)。不重复外线234项已绿全包，不改公开 wire，也没有新增人工签收。

FMP 真实 HTTP 402 说明套餐能力边界，不冒充 live 下载通过；已有三仓离线链通过。FF 的正美元额度没有实际 FMP 账单计量，不声称已经实测该能力。RF 当前接通来源读取/准备，不冒充已把摘要全部接入预测计算。

## 验收与发布

TDD 框住具体公开行为。只在 N4 A/B/C、存储迁移等大节点集中检查；helper、每份文档、每个删除文件没有人工签收。修复红灯只跑责任包，不重复已绿长测、不扩 coverage/多平台日常矩阵。

正式 E2E 使用独立短根，同 OS 账号创建/执行/finally 清理，测试前后核原件/配置/生产/owner 指纹；新下载或副本原先不存在则结束删除。正常 commit/push；提交不跑 pytest，推送短集合，代码 CI 单 Python 全 Unit + 精选合同；纯文档不要求新 CI。CI 收据必须对应实际代码 SHA，不能拿另一提交或本地集成测试冒充。

## 当前文档导航

- [八束已采纳方案](radical_simplification_proposal_2026-10-03.md)、[G1 实施细则](gate_simplification_closeout_2026-10-04.md)、[46 项历史审计](gate_permission_inventory_2026-10-03.md)
- [G2 当前全面补漏与优先实施](gate_simplification_reaudit_2026-10-07.md)：覆盖历史收口文字，14组结论、两大节点，不增加人工门禁。
- [N4 实施与真实批次恢复细则](n4_production_batch_implementation.md)、[S5/S6 清理细则](s5_s6_legacy_storage_implementation.md)
- [完成证据](main_completion_evidence_2026-10-06.md)、[并行总计划](parallel_execution_plan_2026-10-03.md)、[N5 三包](harness_lanes/n5_parallel_packages_2026-10-06.md)
- [findings](findings.md)、[progress](progress.md)
- [S7后续质量具体实施单](s7_followup_quality_implementation_2026-10-07.md)

历史卡只解释已做工作，不能将“待测试/待并线/下一步”的旧文字恢复成当前门。

## 当前新增目标（2026-10-07；暂停状态见页首）

用户明确要求完成全部PWF计划内容。上一轮S0–S7与日期合同的已发布验收保持，但整个目标仍未完成；此前恢复时目标服务active，当前保持paused。不能把有界试点等同全部计划落地。MAIN先盘点全部引用细则及交付，再按实际剩余步骤实施；不缩范围，不重跑已绿旧节点，不无限扩展初稿。

### R0 完整计划与实际待办核对

**Status:** complete

逐份引用细则、生产状态和消费者入口对账，形成可执行步骤与明确完成条件。重点核查生产final0、原文去重可选实施、召回差距真实原因、RF/StockWiki实际使用链及尚未同步的交付；AGENTS来源供应边界与预算上限保持。

## 新目标实施顺序

[全部PWF实施细则](all_pwf_completion_implementation_2026-10-07.md)为唯一新增施工入口；逐份计划[目录](harness_lanes/results/all_pwf_inventory_2026-10-07.json)与历史收据保留。

| 阶段 | 状态 | 下一责任 |
|---|---|---|
| G2门禁全面补漏/P0 | in_progress；目标服务paused | 核心93ac5a5、13/b202d07、01b/22dcc927已发布/精确CI绿；SW0b48919本地主线，RF1a2f9428及SQA0f8fbfa均并主线/已推/精确CI绿（含SQA文档构建与部署）；MAIN12新13反例绿，但旧测试/CLI/FF/并发联调未完成；P1家族/质量读取器/包装待办，仍只两大节点 |
| R0完整对账 | complete | 已确认真实生产metadata/分类/ET登记缺口；已完成核心不重做 |
| R1融资文档正式分类 | complete | 66ce0467已发布，真实两PDF CLI与分类责任包绿，精确CI37578307854绿 |
| R2真实生产来源/预算准备 | in_progress；生产步骤顺延G2后 | 全库发现/有限登记/AUTO范围代码2cad90d已推且精确CI绿；G2先清旧控制面，再核公开日/retired/ET，不猜metadata |
| R3正式生产与跨仓消费 | pending | 有价值final+零模型skip、真实ref/search/exact/消费者/同run恢复/空间 |
| R4原件去重决策 | pending | 只核CWP内部真实收益，原件不丢、外部根不动 |
| R5PWF与发布收口 | pending | 历史Git、简化当前入口、正常并线/push/精确CI |

## Next Step

当前本次交付是[G4独立包](harness_lanes/g4_parallel_packages_2026-10-07.md)，并修正G3已建立工作树事实。总目标服务实读paused，以下MAIN实施动作是恢复后的待办，不表示本次已执行。G4两条线可由用户现在启动，不等待MAIN；MAIN保留公共接口接线、工程清单、生产和合入职责。

MAIN继续[G2-12实施单](g2_latest_acquisition_implementation_2026-10-07.md)：统一服务、目标锁、预算异常传播、失败清理与共享预算重试的13项新反例已绿1.68秒；尚未发布，先完成旧责任测试合同同步、latest期间语义、可选binding CLI、FF接线和跨进程/真实离线E2E，再集中发布。不把13项试点当whole G2B。旧三外线已验收并线，精确主线CI见[收据](harness_lanes/results/g2_parallel_exact_ci_2026-10-07.json)，不重派。

用户现请求新独立包：[G3总包](harness_lanes/g3_parallel_packages_2026-10-07.md)及三单卡ready，未启动/未创建工作树；RF历史质量/包装、CWP维护后端、来源事实/内部空间只读核实各独占根/写集，均可同时开工。MAIN独占公共CLI/FF/指纹/工程清单/生产/技能安装与合入。G3代码接入既有G2A/B，调查供应R2/R4；不增加小节点门。然后G2A/B→R2/R3/R4/R5。01b旧binding1保留原账，不推导不可逆历史pin、不付费重跑，既有验收继续有效。
