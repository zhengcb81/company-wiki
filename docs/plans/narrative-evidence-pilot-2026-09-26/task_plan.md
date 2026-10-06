# 公司来源平台：当前总计划

> 本页是唯一当前施工入口。旧步骤、旧预算答复和已交付卡不产生新的任务或人工签收。历史细节保留在 [收敛前版本](https://github.com/zhengcb81/company-wiki/blob/659bcefc9d49a7e7f7fdc58e9c11d46e45da49ab/docs/plans/narrative-evidence-pilot-2026-09-26/task_plan.md)、findings/progress 和阶段收据中。

## Goal

逐步完成 company-wiki 叙述性证据选择、摘要/检索、Worker 多文档并发、跨项目消费接口和低价值原文/派生处置计划；每阶段先核查 revenue-forecast 当前实施状态，复用其正式合同与组件，避免修改对方文件或重复实现，并保留用户已批准的安全边界。

一个下载请求入口、一套 pathless 来源接口、一套 AUTO 任务系统；按需处理有价值的业务叙述，停止全量永久 PDF→MD 和重复正文。原件及来源/版本事实不丢。company-wiki 只供应资料和可定位证据，投资研究语义属于 StockWiki。

## 当前恢复点（2026-10-06）

- CWP 当前代码 `4826ad9c67bce3d3e2b977173d283341d18bc141` 已发布；显式预算修复的 [CI37514053091](harness_lanes/results/n4c_explicit_limits_ci_2026-10-06.json)一次全绿/52秒。短摘要代码 `4d019b5` 和历史长草案兼容测试 `86c8793` 已发布，精确代码 CI 分别一次通过，76/75秒。
- RF 正式 main `6e6b817a1a6e4567293a4dcb835815f3be508a03`，已有默认 v2 与真实原文读取验收；FF main `758e8f4`，ET main `63c4090`。不要重派 P5 已完成交付。
- 当前 RF 正常用户上下文只有两份 owner weekly 日志修改，本线不改；旧 rf-impl WIP 保存在独立分支。本机 CWP `config/source_acquisition.yaml` 是用户改动，SHA `3609e707466eeb3e0f685e14f2637c6afa39ba900edef1be4814433a43300a01`，不暂存、不覆盖。
- 当前核心缺口只有 S4 的修复后真实电话会业务摘要验收；没有 live 模型任务，run10 尚未启动。目标未完成。

## 已批准预算与配置

当前明确批准的累计上限是 **200000 tokens / $0.10**。此前 60000/160000 与待提高 token 的记录是历史。P04 招股同一业务片段→DeepSeek 已获批准并在 run08 成功；T01 电话会→DeepSeek 的明确外发授权继续有效。

累计使用 `180884 tokens / 90649 microUSD`，unknown 7、unsettled 0；历史 FX guard `2764 microUSD` 保留。余 `19116 tokens / 6587 microUSD`。新 T01 请求预留 `18755 tokens / 14445 microUSD`：token 足够，费用不足。**$0.12 费用上限仍待用户答复，不得据此 POST。**

模型严格经 `Config.load / model_options_from_config`：MiMo `mimo-v2.6-flash`（`https://token-plan-cn.xiaomimimo.com/v1`），DeepSeek `deepseek-flash`（`https://api.deepseek.com`）；输出 8192、温度 1.0，现有 timeout/default thinking 不擅改。不退款旧 unknown、不用临时折价凑预算、不增加第二账本。

零网络准备工具现要求显式传入两项累计上限，避免旧 60000 默认误报；这是资源输入，不是人工许可文件。下列命令只读资料、只导出 RF 已提交六模块、清理临时根；输出路径必须原先不存在：

```powershell
python -B tools/n4c_live_preflight.py --rf-root 'C:/Users/郑曾波/Projects/revenue-forecast' --rf-head 6e6b817a1a6e4567293a4dcb835815f3be508a03 --campaign-token-cap 200000 --campaign-cost-cap-micro-usd 100000 --output '<新的小收据JSON路径>'
```

报告的 `budget_can_reserve_configured_output` 只检查输出 token；不能作为完整请求或费用通过的证明。全部日期真实旧账统一取 `prior_budget()`。当前实读证据：[显式额度离线准备](harness_lanes/results/n4c_explicit_limits_preflight_2026-10-06.json)。

## 实施顺序与当前完成范围

优先事项 G1 门禁精简、S3 虚拟化已经完成；不再串行重做。当前执行 S4，S5/S6 已利用外发等待完成。

| 步骤 | 状态 | 范围与证据 |
|---|---|---|
| S0 简化收口 | complete | gold/shadow/Work Unit 人工链退出；commit 无 pytest，config doctor 仅相关改动触发；`ff5396c`/CI 绿 |
| S1 N4A | complete | scope 贯通 Store/Worker/Supervisor/outbox/prepared；空范围零修改，SQL 范围先于 LIMIT；节点 A 绿 |
| S2 N4B | complete | 隔离子进程客户端、真实 HTTP/factory、有限 batch、持久预算、lease/generation/kill/ACK 恢复；节点 A/B 集中验收绿 |
| G1 多余门禁/签收 | complete | 46 项已分类；private/public、prompt 人工复核阻断、签名/TTL、reviewer 必填、双授权及旧审批工具退出；CWP/FF/ET 责任测试绿 |
| S3 来源虚拟化 | complete | SourceRef/SourceExport v2、FF→ET→CWP 正式 CLI 离线链、迁根/只读/去重/SHA/语言/超时清理验收；RF 默认 v2 已发布，StockWiki 现有只读消费者复用 |
| S4 N4C 真实业务效果 | **in_progress，MAIN 独占** | 年报、招股、IR、旧电话会有真实 final/RF 读取；电话会漏选已修，run09 截断未发布；prompt1.5 修复/CI 绿，但新真实效果待验收 |
| S5 逐 caller 与派生清理 | complete | 旧全文 writer/消费者退出；生产 7104 旧文件、8191 handle 退休；原件与来源事实保持 |
| S6 DB 收缩与收尾 | complete | 1490530 旧 span 删除；DB 3055841280→222408704 B；说明/控制/短 smoke 已发布，精确 CI 绿 |
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

当前可独立启动的 [N5 三包](harness_lanes/n5_parallel_packages_2026-10-06.md)：DOCSET 多类型真实质量基准、RAW-DUP 只读重复原件工具、ET-TXT 本地复用验真。卡内有独占目录、写集、接口、测试和交接；未收到交付，不宣称完成，不新增 N4C 屏障。半年报、季报、融资/可转债、招股、IR 等的更广质量实证进入 DOCSET，不以选择器输出自己生成 golden。

2026-10-06已核对三个独立目录均存在、各有本线施工材料；ET代码已提交`96c9bc8`，但三者完整交接文件均未出现。保留外线写集，不重派、不提前合入。核心S4收尾等待费用答复；主线blocked不暂停外线独立工作，交付或费用答复到达后恢复对应验收。

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

**待用户明确提高累计费用上限至 $0.12 后，MAIN 才做同一 T01→DeepSeek 一次修复后真实验收。**当前仍按 200000/$0.10；不得 POST，不重跑已绿长包，不把离线或 Replay 当真实质量通过。

若批准：只把 campaign cost cap 明确设 `120000 microUSD`；所有旧 charges/unknown/FX 保持，模型配置不动。先核 RF 当前主线与 owner 指纹、预算和新 run10/root/receipt 原先不存在，再执行 T01+policy 一次；逐条核具体管理层经营进展、角色、全部 locator、RF 正式读取、原语言、费用、空间及测试目录恢复。失败照实记终态，不自动多次重试或再次提高预算。

若未批准：保留 S4 真实缺口，不标整体完成，不制造新权限、重复测试或另一账本。N5 外线可独立实施；MAIN 在交付后统一验收。最终完成以本页每项责任和实际收据审计，不能把当前证据缩成更容易通过的目标。
