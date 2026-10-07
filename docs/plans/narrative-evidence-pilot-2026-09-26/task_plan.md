# 公司来源平台：当前总计划

> 本页是唯一当前施工入口。旧步骤、旧预算答复和已交付卡不产生新的任务或人工签收。历史细节保留在 [收敛前版本](https://github.com/zhengcb81/company-wiki/blob/659bcefc9d49a7e7f7fdc58e9c11d46e45da49ab/docs/plans/narrative-evidence-pilot-2026-09-26/task_plan.md)、findings/progress 和阶段收据中。

## Goal

逐步完成 company-wiki 叙述性证据选择、摘要/检索、Worker 多文档并发、跨项目消费接口和低价值原文/派生处置计划；每阶段先核查 revenue-forecast 当前实施状态，复用其正式合同与组件，避免修改对方文件或重复实现，并保留用户已批准的安全边界。

一个下载请求入口、一套 pathless 来源接口、一套 AUTO 任务系统；按需处理有价值的业务叙述，停止全量永久 PDF→MD 和重复正文。原件及来源/版本事实不丢。company-wiki 只供应资料和可定位证据，投资研究语义属于 StockWiki。

## 当前恢复点（2026-10-07）

- **IR parser0.1.1集中本地验收通过，准备发布。** 旧0.1.0算法与旧final保持；143责任项/1.35秒、45个CI源模块mypy/Ruff绿，真实S07/S08/S09正式Worker→RF/search/exact/resume及旧final9/实际selector与parser升级共12项/52.16秒通过。完整九文档27/33、761定位零失败、精选62953B（原66215B）、IR两条套话clean，optional3/17→2/17的一条泛答提问取舍保留。全Unit首次1688通过/10版本写死失败，相关143复验已绿，远端精确CI待发布；9个自己临时路径恢复absent，原件/用户配置/RF6e6b817a保护保持，0供应商/下载/翻译。详见[IR收据](harness_lanes/results/s7_ir_main_acceptance_2026-10-07.json)。

- **当前施工：S7经营语义集中节点已发布：9bf25a5，精确CI37550268890全部步骤绿/71秒。** 按[后续实施单](s7_followup_quality_implementation_2026-10-07.md)完成具体经营reason、量化行业独立类别和有界未完句合组；selector0.4.1、parser仍0.1.0。293责任项/3.60秒、真实S01/S02/S06正式链路7点/97.74秒及既有节点/旧final/generation11项通过。完整九文档27/33（原21/33），764定位全绿、必需旧full无退步；optional5/17→3/17的两项取舍完整保留，不能宣称所有旧full无回退。精选66215B（原66195B）、重复4（原3）。S04募投上下文与S08数字问答解析仍未施工，S7不complete。详见[s7节点收据](harness_lanes/results/s7_operating_main_acceptance_2026-10-07.json)。

- **N6交付已完成（此前节点证据）。** 三包实际并线/推送，候选merge e8c645e、精确CI37547043642全部步骤成功/job53秒；当时selector0.4.0、269责任项+11真实/兼容/升级通过、九文档21/33。当前质量与剩余项以上方S7节点及下方Next Step为准，不重派已交卡；[N6收据](n6_candidate_main_acceptance_2026-10-07.md)保留历史保护/发布事实。

- DOCSET真实merge `58b74d07dd4f8b589c134ef9060a689864a8c089`已推master，精确CI37528050044一次成功/75秒；43不同责任case和真实9样本已接收，工具完成而质量required12/33仍待改。MAIN先行兼容/业务标准已发布`0947cea63140d515620f563daf2058f4520cd6a3`、精确CI37532408169一次成功/80秒，无运行代码变更。RAW-DUP a41244a/CI57秒、R6 eae2dd4/CI59秒等已完成证据不重跑。
- RF 正式 main `6e6b817a1a6e4567293a4dcb835815f3be508a03`，已有默认 v2 与真实原文读取验收；FF main `758e8f4`，ET 本地/真实远端 main 已快进到 `2b9fb84660f98ce27a05709a7e31342ab044b4d2`，包含 N5-ET-TXT。不要重派已完成交付。
- 当前 RF 正常用户上下文有三份 owner daily/weekly/manifest 日志修改，本线不改；旧 rf-impl WIP 保存在独立分支。本机 CWP `config/source_acquisition.yaml` 是用户改动，SHA `3609e707466eeb3e0f685e14f2637c6afa39ba900edef1be4814433a43300a01`，不暂存、不覆盖。
- S4 修复后真实电话会 run10 已完成：20 条摘要、15 条管理层陈述、46 个定位全部回放，RF 正式读取通过；六类业务主题精选6/6、短摘要5/6，GPU效率未单列，不能声称穷尽。完成审计发现R6具体缺口，现已TDD修复并发布/精确CI绿，S4关闭；其余核心证据不重做。N5-RAW-DUP完整交付已集中修正/51项绿，已合入master a41244a并推远端、精确CI37523080920/57秒绿；DOCSET已接收并推58b74d0/CI75秒绿；初测12/33已被最新S7的27/33覆盖，整体目标active。

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

优先事项G1门禁精简、S3虚拟化已完成，S5/S6生产清理完成。S4真实业务效果已验证，完成审计发现的[R6局部摘要恢复](r6_partial_summary_implementation_2026-10-06.md)已补齐并推/精确CI绿；DOCSET与RAW-DUP并线已发布。N6三卡已由用户分派；MAIN先行历史final兼容9项/4.85秒绿和33点业务解释完成，不新增小节点门。

| 步骤 | 状态 | 范围与证据 |
|---|---|---|
| S0 简化收口 | complete | gold/shadow/Work Unit 人工链退出；commit 无 pytest，config doctor 仅相关改动触发；`ff5396c`/CI 绿 |
| S1 N4A | complete | scope 贯通 Store/Worker/Supervisor/outbox/prepared；空范围零修改，SQL 范围先于 LIMIT；节点 A 绿 |
| S2 N4B | complete | 隔离子进程客户端、真实 HTTP/factory、有限 batch、持久预算、lease/generation/kill/ACK 恢复；节点 A/B 集中验收绿 |
| G1 多余门禁/签收 | complete | 46 项已分类；private/public、prompt 人工复核阻断、签名/TTL、reviewer 必填、双授权及旧审批工具退出；CWP/FF/ET 责任测试绿 |
| S3 来源虚拟化 | complete | SourceRef/SourceExport v2、FF→ET→CWP 正式 CLI 离线链、迁根/只读/去重/SHA/语言/超时清理验收；RF 默认 v2 已发布，StockWiki 现有只读消费者复用 |
| S4 N4C与R6实际效果 | complete | 四类真实final/RF读取与run10业务复核完成；R6 TDD→184责任测试→正式离线E2E/RF→代码eae2dd4/CI59秒绿，保留好claim，坏片段不进入产物，不重跑真实模型 |
| S5 逐 caller 与派生清理 | complete | 旧全文 writer/消费者退出；生产 7104 旧文件、8191 handle 退休；原件与来源事实保持 |
| S6 DB 收缩与收尾 | complete | 1490530 旧 span 删除；DB 3055841280→222408704 B；说明/控制/短 smoke 已发布，精确 CI 绿 |
| S7 N5-DOCSET质量对照与整改 | in_progress | DOCSET和N6三包已并线；0.4.1九样本27/33、764定位全回放、293责任项与真实7业务点通过，2个optional取舍保留。下节点数字IR parser0.1.1及剩余应用/募投联系见[最新实施单](s7_followup_quality_implementation_2026-10-07.md)；不扩预算/改golden凑绿 |
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

MAIN 独占共享接口、总 PWF、生产状态和所有合入；外线独占各自 worktree/测试/计划，不交叉写。RF、StockWiki、IQS owner 工作树不另写；IQS 有独立项目，不盘点、不重新分派。Dayu 为纯外部项目，**零代码修改**；不支持真实硬限额的路由外发前拒绝。CN 使用 StockInfoDLSimple，目标交付 `v2-clean-rewrite@8ed5fdd`，不维护 StockInfoDownloader 主线。

G1-LEGACY、ET-DEADLINE、FF/ET-S3、P5-FF/STORAGE/RF、N4-T1/T2、StockWiki 来源/身份线与 MeetingConverter CI 卡已交付，不重派。相关功能并线不等于每仓所有历史 WIP 都已消失；Dayu 现有提交只有本地集成，远端 push 曾 403，不宣称远端同步。

已分派的 [N5 三包](harness_lanes/n5_parallel_packages_2026-10-06.md)：DOCSET基准已接收，质量整改进入N6；RAW-DUP已完整交付并经MAIN集中修正/51项与CLI绿，已合入master a41244a并推、精确CI57秒绿；ET-TXT已验收并线。卡内有独占目录、写集、接口、测试和交接，不重派、不新增 N4C 屏障。半年报、季报、融资/可转债、招股、IR 等的更广质量实证进入 DOCSET，不以选择器输出自己生成 golden。

2026-10-06 已核对三个独立目录均存在。DOCSET已验收并线58b74d0/精确CI绿；RAW-DUP交付e40b4ec已收到，见[MAIN验收](harness_lanes/n5_raw_duplicate_main_acceptance_2026-10-06.md)。ET 代码`96c9bc8`、交接`2b9fb84`已验收并推 main：MAIN 92项/26.24秒、10 goldens、相关 Ruff 绿，主线真实43份TXT只读 audit/0写收据/原件与配置不变，测试根恢复 absent；[正式验收](harness_lanes/results/n5_et_text_main_acceptance_2026-10-06.json)。不重复外线234项已绿全包，不改公开 wire，也没有新增人工签收。

FMP 真实 HTTP 402 说明套餐能力边界，不冒充 live 下载通过；已有三仓离线链通过。FF 的正美元额度没有实际 FMP 账单计量，不声称已经实测该能力。RF 当前接通来源读取/准备，不冒充已把摘要全部接入预测计算。

## 验收与发布

TDD 框住具体公开行为。只在 N4 A/B/C、存储迁移等大节点集中检查；helper、每份文档、每个删除文件没有人工签收。修复红灯只跑责任包，不重复已绿长测、不扩 coverage/多平台日常矩阵。

正式 E2E 使用独立短根，同 OS 账号创建/执行/finally 清理，测试前后核原件/配置/生产/owner 指纹；新下载或副本原先不存在则结束删除。正常 commit/push；提交不跑 pytest，推送短集合，代码 CI 单 Python 全 Unit + 精选合同；纯文档不要求新 CI。CI 收据必须对应实际代码 SHA，不能拿另一提交或本地集成测试冒充。

## 当前文档导航

- [八束已采纳方案](radical_simplification_proposal_2026-10-03.md)、[G1 实施细则](gate_simplification_closeout_2026-10-04.md)、[46 项历史审计](gate_permission_inventory_2026-10-03.md)
- [N4 实施与真实批次恢复细则](n4_production_batch_implementation.md)、[S5/S6 清理细则](s5_s6_legacy_storage_implementation.md)
- [完成证据](main_completion_evidence_2026-10-06.md)、[并行总计划](parallel_execution_plan_2026-10-03.md)、[N5 三包](harness_lanes/n5_parallel_packages_2026-10-06.md)
- [findings](findings.md)、[progress](progress.md)
- [S7后续质量具体实施单](s7_followup_quality_implementation_2026-10-07.md)

历史卡只解释已做工作，不能将“待测试/待并线/下一步”的旧文字恢复成当前门。

## Next Step

**当前动作：正常提交推送IR0.1.1节点，核精确代码CI；随后只处理S01应用事实的预算优先级与S04募投引导句/项目表的真实联系。** 全九已完成，原golden/33分母及96/160不改；S08两条套话已清理，不重复IR节点或12项已绿长测。六个正式remaining仍保留，其中S06 G03同原件page7完整产能已入选，三项为纯财务/provider边界。下方旧“下一进入IR/未施工”不再是施工步骤。没有新增人工签收或日常长CI。

**S7 selector0.4.1已发布，下一进入IR parser0.1.1节点。** N6三线验收、实际并线和推送已完成，不重派。新S7正式年报/半年报/可转债7业务点及原节点/旧final/升级已验证，完整九样本27/33；两处optional取舍保持可见。发布收据已实读记录代码9bf25a5、精确CI37550268890全部步骤绿/71秒；不重跑已验节点。下一IR版本传播和责任测试包均在[S7细则](s7_followup_quality_implementation_2026-10-07.md)最后一节；修复数字问答混合cell与两条套话，不改原golden。提交不跑长pytest，日常CI没有加入大基准或真实长E2E。

首次组合全表403.731秒实测18/33（旧12/33）、764定位零失败、重复3（旧48）。已保留初次报告；其中年报G04发生回退及EPI正式E2E失败，MAIN按句理由/组、忙页分类offer、完整fact reasons及工程时间表责任修正，最终集中复验已完成：21/33、可选5/17、764定位零失败、重复3、精选66195B、372.044秒，旧required/optional full均无回退。不用手推覆盖或旧CI替代。原golden/86点/33分母、parser0.1.0、原件与96/160限额不变。**N6实现合入与S7全部业务质量完成分别记录。**

S7后续按最终逐点差距处理，不重派已交三包：

**以最新0.4.1结果覆盖下面历史9点清单：** 必需remaining6：G-S01-01（海外批量销售已保留、全球应用前一句未全部选）、G-S04-03（募投引导句/项目表联系）、G-S06-03（page43 oracle miss、同原件page7完整产能已canonical保留）、纯融资金额G-S06-01、正文外provider G-S09-01、纯guidance G-S09-03。业务/项目解释子集26/29，不能替代正式27/33。下一先IR解析噪声，再按实际资料价值处理S01/募投上下文；不强行塞融资总额或guidance凑分。

本项目不把“每个optional旧full必须永久保持”设为自动发布门：本轮G-S02-06静态海外销售主体职责、G-S05-05项目营收/利润测算退步，已查原句并按“业务动态优先、财务工具负责纯数值”明确记录。原标注、全部必需业务断言与定位真实性不变；以后optional退步仍逐项说明，不能用此项泛化为允许丢订单/产能/项目进展。

1. 剩余选择问题只针对S01全球应用前句及S04募投intro/具体项目表联系，按同原件parsed→candidate→selected和PDF视觉位置定位，新增一般性责任反例。S06 G03已canonical保留在同原件page7，不复制page43重复原文以凑golden；正式miss保留。纯财务/provider缺口不扩大正文范围或切片配额。
2. 修IR数字编号问题/多问答混合cell：S08现有0.1.0 parser把“4：/5：”和两条套话留在一个219字orphan_answer单元。先测试数值口径、提问/答复角色、原始cell字符范围、负例和旧final回放；评估最小可回放片段与parser版本传播。不能删整条有价值占比或屏蔽noise/needs_review，不能跨仓改RF合同。
3. 最终针对改变的格式跑责任测试和真实入口大节点；只有具体剩余风险才重跑全九样本，不每个helper重跑。业务覆盖未完成仍列remaining，不拿全定位绿冒充语义完成。

空间cf24f34/CI37542743196全绿68秒，预算3cd4960/CI37543349021全绿72秒均已实际并线/推，不重复验收。最新单根逻辑24,365,900,191 B，raw23,462,933,638 B占96.2941%；tmp+tmp DB候选323,168,254 B仅候选上界，未自动删除/声称物理释放；1007云占位跳过。生产S5/S6净释放5,659,443,210 B沿原收据。

RF main6e6b817a三owner SHA保持；用户source_acquisition.yaml SHA3609e707独立dirty且不stage。Dayu/IQS/StockWiki/ET与外线worktree零写。详细剩余ID、最终实测覆盖、scratch恢复和精确CI发布记录在验收单/收据。不要把历史等待blocked状态当权限门，不增加人工签收。
