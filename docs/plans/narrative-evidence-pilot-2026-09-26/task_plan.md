# 公司来源平台：当前总计划

> 本页是唯一当前施工入口。旧步骤、旧预算答复和已交付卡不产生新的任务或人工签收。历史细节保留在 [收敛前版本](https://github.com/zhengcb81/company-wiki/blob/659bcefc9d49a7e7f7fdc58e9c11d46e45da49ab/docs/plans/narrative-evidence-pilot-2026-09-26/task_plan.md)、findings/progress 和阶段收据中。

## Goal

逐步完成 company-wiki 叙述性证据选择、摘要/检索、Worker 多文档并发、跨项目消费接口和低价值原文/派生处置计划；每阶段先核查 revenue-forecast 当前实施状态，复用其正式合同与组件，避免修改对方文件或重复实现，并保留用户已批准的安全边界。

一个下载请求入口、一套 pathless 来源接口、一套 AUTO 任务系统；按需处理有价值的业务叙述，停止全量永久 PDF→MD 和重复正文。原件及来源/版本事实不丢。company-wiki 只供应资料和可定位证据，投资研究语义属于 StockWiki。

## 当前恢复点（2026-10-06）

- DOCSET真实merge `58b74d07dd4f8b589c134ef9060a689864a8c089`已推master，精确CI37528050044一次成功/75秒；43不同责任case和真实9样本已接收，工具完成而质量required12/33仍待改。MAIN先行兼容/业务标准已发布`0947cea63140d515620f563daf2058f4520cd6a3`、精确CI37532408169一次成功/80秒，无运行代码变更。RAW-DUP a41244a/CI57秒、R6 eae2dd4/CI59秒等已完成证据不重跑。
- RF 正式 main `6e6b817a1a6e4567293a4dcb835815f3be508a03`，已有默认 v2 与真实原文读取验收；FF main `758e8f4`，ET 本地/真实远端 main 已快进到 `2b9fb84660f98ce27a05709a7e31342ab044b4d2`，包含 N5-ET-TXT。不要重派已完成交付。
- 当前 RF 正常用户上下文只有两份 owner weekly 日志修改，本线不改；旧 rf-impl WIP 保存在独立分支。本机 CWP `config/source_acquisition.yaml` 是用户改动，SHA `3609e707466eeb3e0f685e14f2637c6afa39ba900edef1be4814433a43300a01`，不暂存、不覆盖。
- S4 修复后真实电话会 run10 已完成：20 条摘要、15 条管理层陈述、46 个定位全部回放，RF 正式读取通过；六类业务主题精选6/6、短摘要5/6，GPU效率未单列，不能声称穷尽。完成审计发现R6具体缺口，现已TDD修复并发布/精确CI绿，S4关闭；其余核心证据不重做。N5-RAW-DUP完整交付已集中修正/51项绿，已合入master a41244a并推远端、精确CI37523080920/57秒绿；DOCSET已接收并推58b74d0/CI75秒绿，当前required12/33按S7/N6整改，整体目标active。

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
| S7 N5-DOCSET质量对照与整改 | in_progress | 工具已集中修正/43不同case通过；当前0.3.2真实9样本required12/33、744定位全回放，不能认为语义完成。[S7细则](s7_document_quality_implementation_2026-10-06.md)按候选完整上下文→固定预算去重/排序→一次质量节点执行，不扩预算/改golden凑绿 |
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

历史卡只解释已做工作，不能将“待测试/待并线/下一步”的旧文字恢复成当前门。

## Next Step

**按[N6并行总包](harness_lanes/n6_parallel_packages_2026-10-06.md)接收已分派三线。** 候选/上下文与固定预算/去重各独占4/2源文件，空间只读工具独占新目录，MAIN不抢外线写集。MAIN先行[0.3.2冻结兼容包](n6_main_compatibility_implementation.md)9项/4.85秒绿，[33点业务解释](n6_main_business_expectations_2026-10-06.md)已写；[业务E2E施工框架](n6_main_business_e2e_implementation.md)已用三类合成原件验证，最终1项/27.65秒绿，正式configured Worker→RF→search/exact→恢复及TXT字节映射均走通，真实质量节点明确未运行。当前RF6e6b817a有daily/weekly/manifest三份owner日志改动，全部只读保护，不恢复。下一收到完整质量交接后实际merge、按main_wiring组合规则/更新selector版本，再一次真实9样本/正式Worker-RF E2E和冻结兼容测试。空间工具可独立接收不阻质量。DOCSET已并线58b74d0/精确CI75秒绿，43不同case通过；当前required12/33、744定位合法不等于语义已达标，不重派旧N5或重复付费。

run10与ET-TXT已完成并推adc9d6b；保留真实结果、旧失败与非穷尽边界。RAW-DUP已有完整交接，MAIN发现并修复输出/预算/分配量/云属性/报告/ACL测试缺口，51责任项/9.09秒与两CLI联调绿，原件删除0；[验收卡](harness_lanes/n5_raw_duplicate_main_acceptance_2026-10-06.md)。历史7.27GiB为跨根候选上界，仅3组151MiB实读，不计释放、不自动迁移；DOCSET已交9份真实资料/86标注点与完整报告；报告基于旧selector0.3.1，required11/33，不能当当前0.3.2结论。下一步按N6候选/预算独立卡并行整改，MAIN接线后集中质量验收。不凭目录文件或日志声称有确认live进程，不自动删原件/hydrate。

N5外线独立实施，MAIN只在完整交付后验收；最终完成以本页每项责任和实际收据审计，不将当前证据缩成更容易通过的目标。

MAIN先行[执行升级隔离](n6_main_upgrade_execution_implementation.md)已本地16.33秒绿：正式旧run/新run任务与artifact版本分离，旧run拒绝误复用、旧reference仍可读取、新run恢复幂等，纯流程PDF零模型。模拟版本传播只证明AUTO身份和传播；实际两线合入后仍用当前真实版本执行大节点。最后质量节点同时跑此case、冻结兼容9项与正式业务E2E，不加逐helper门。
