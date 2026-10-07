# 并行总计划：门禁先行，独立目录施工，MAIN统一打通

**最新G3验收（2026-10-07）：**三个包已接收并补齐MAIN接线，两个本地主线已并入。RF `ab7a7a44`已正常推远端main（107快测绿）；CWP接线代码`b2c9e66`，115责任用例最终绿、1921单元绿，正在正常发布。详情见[g3_main_acceptance](g3_main_acceptance_2026-10-07.md)。G3不再派发；G2-04旧维护退休已完成，R4依据现有注册重复上界决定不做对象化迁移（不是释放空间）。RF真实用户安装未同步；G2-12/其他G2、R2元数据生产应用、R3和R5仍未完成。目标服务保持paused，本次仅执行用户明确要求的G3验收，并未恢复总目标/付费/生产批次。


> **最新（2026-10-07）：**G3三工作树已建立，RF/SOURCE-FACTS已有独立计划，未见交接；不再次派发。当前可新派发的是[G4两张大卡](harness_lanes/g4_parallel_packages_2026-10-07.md)：CWP冻结Pipeline整族退休、SID最新财报发现，各独占`Projects/_g4/`新根，互不影响G3/MAIN。总目标服务实读paused，本次仅编制卡；MAIN恢复后仍负责全部公共接线/生产/安装/合入。下方旧未启动文字是历史。

## 当前新增可分派：G4两条线

| 卡 | 独占目录 | 责任 | 状态 |
|---|---|---|---|
| [G4-CWP-PIPELINE](harness_lanes/g4_cwp_frozen_pipeline_retirement.md) | `Projects/_g4/CWP-PIPELINE/company-wiki` | G2-03旧Gate家族/配置退出、stdlib退休壳、部署报告与责任测试 | ready，可现在开工 |
| [G4-SID-LATEST](harness_lanes/g4_sid_latest_discovery.md) | `Projects/_g4/SID-LATEST/StockInfoDLSimple` | 按as-of有界发现年报/半年报/季报，期间/分页/预算/真实JSON CLI | ready，可现在开工 |

精确代码写集和统一交接见[G4总包](harness_lanes/g4_parallel_packages_2026-10-07.md)。外线不合主线/不写生产；MAIN集中接线与既有G2A/B验收，不增加小节点签收。

> **2026-10-07当前：**目标active，先G2再R2/R3/R4/R5。上一批G2三包全部验收并线；13/01b已发布，MAIN继续12及公共接线。[新G3三卡](harness_lanes/g3_parallel_packages_2026-10-07.md)ready，可同时分派，未启动；独占新工作树和互不重叠写集。MAIN负责总PWF/生产/安装/主线，Dayu/IQS零写。

## 当前可分派：G3三个互不重叠包

单卡各自完整，交给独立harness即可：

| 卡 | 实际独占目录 | 责任 | 状态 |
|---|---|---|---|
| [G3-RF-ASSURANCE](harness_lanes/g3_rf_assurance_and_packaging.md) | `Projects/_g3/RF-ASSURANCE/revenue-forecast` | RF历史质量/manifest时间语义与安装runtime职责，代码+测试 | 工作树/本卡计划已建立，待交接，不重派 |
| [G3-CWP-MAINT](harness_lanes/g3_cwp_maintenance_retirement.md) | `Projects/_g3/CWP-MAINT/company-wiki` | 维护后端退休与只读清单，MAIN再接CLI/工程清单 | 工作树已建立，待交接，不重派 |
| [G3-SOURCE-FACTS](harness_lanes/g3_source_metadata_and_raw_space.md) | `Projects/_g3/SOURCE-FACTS/company-wiki` | R2真实来源metadata/R4内部原件收益只读核实，MAIN再应用生产 | 工作树/本卡计划已建立，待交接，不重派 |

写集/冻结基线/交接/一个集中测试节点见[G3总包](harness_lanes/g3_parallel_packages_2026-10-07.md)。不同工作树之外，源文件范围也不重叠；均不改MAIN获取/CLI/FF/生产/安装。三个包不互相等待。

## 上一批G2：全部完成，禁止重派

完整目录/冻结依赖/共同交接见[G2并行总包](harness_lanes/g2_parallel_packages_2026-10-07.md)。各卡单独交付即可实施，不需要其他卡上下文。

| 卡 | 实际独占目录 | 施工范围 | 当前状态 |
|---|---|---|---|
| [G2-SW-DAILY](harness_lanes/g2_stockwiki_daily_checks.md) | `Projects/_g2/sw/StockWiki` | 单检查入口、日常/集中分离、指标诊断、真实来源消费者回归 | complete，master0b48919本地（无remote） |
| [G2-SQA-CHECKS](harness_lanes/g2_stockqa_engineering_checks.md) | `Projects/_g2/StockQAbyLLM` | sh/bat/CI/hook统一，真实退出码和关联security/release/docs workflow | complete，master0f8fbfa已推/精确CI绿 |
| [G2-RF-TOOLS](harness_lanes/g2_revenue_forecast_optional_tools.md) | `Projects/_g2/revenue-forecast` | 可选发布/覆盖率/会话清单及历史兼容 | complete，main1a2f9428已推/精确CI绿 |

每仓仅自己的计划、源码白名单、测试和交接写入；三根互不包含。StockWiki使用已发布CWP代码临时导出，不能读取MAIN正在变化的代码作为测试依赖。各线一个集中节点，MAIN合入复用责任证据，纳入既有G2B；不追加逐helper签收。交付本仓正常commit，MAIN统一接线；创建card不代表已经启动、交付或并线。

## 以下为历史已交付线

> **最新：N5-RAW-DUP已交付e40b4ec并经MAIN集中修正；51项/9.09秒、两CLI与Ruff绿，已合入master a41244a并推远端、精确CI37523080920/57秒绿。** [验收卡](harness_lanes/n5_raw_duplicate_main_acceptance_2026-10-06.md)；ET已验收，DOCSET交接2c3583e已到待MAIN验收，不重派。下方旧未交付叙述属历史。

> **2026-10-06当前并行状态：**见[N5三包总计划](harness_lanes/n5_parallel_packages_2026-10-06.md)：DOCSET真实文档质量基准、RAW-DUP只读原件重复工具已分派，尚待完整交接；ET-TXT已验收并推本地/远端main `2b9fb84`，92项+10 goldens与43份真实TXT只读audit通过。MAIN真实N4C run10已收口，短摘要保留非穷尽边界。各线写集不重叠，不重派已完成包，不碰IQS/Dayu/RF。下方旧“待验收/待清理”仅为历史，当前动作只取总task_plan。

> **2026-10-06最新覆盖：**P5-FF已验收并入main758e8f4/精确CI37385101051 GREEN；P5-STORAGE已验收e570daf，生产处置与S6收尾均已完成。RF已验收并推main ca67eab7（默认链代码b110502f）；精确CI37391526925一次全绿、job32秒。本地正式revenue-forecast已切main同步，旧rf-impl WIP原样保留在独立分支；三处已安装来源入口SHA与主线一致。不重派或写穿。MAIN运行旧generator已退出安装包b148123，229个不同case分步GREEN、真实PDF/TXT原件/来源事实保持且0新全文派生；CI37388329668已completed/success。质量/正式精选接口已发布绿。下方旧日期仅作追溯，不产生待办或签收。

## P5交付与独占目录（均已完成，不再派发）

| 包 | 独占目录 | 接口与交接 | 何时开工 |
|---|---|---|---|
| [P5-RF](harness_lanes/p5_rf_source_default_migration.md) | `Projects/cwp-lanes-20261005/rf-source-v2` | RF SourceRecord/reuse receipt沿用已发布wire；仅RF默认入口迁移 | 已验收并推main ca67eab7/精确CI绿，本地正式目录同步；不重派 |
| [P5-FF](harness_lanes/p5_ff_runtime_simplification.md) | `Projects/cwp-lanes-20261005/ff-runtime-cleanup` | SourceRef/companion wire不变；共用有界进程、一次请求限额 | 已验收并入本地/远端main758e8f4，精确CI GREEN；不重派 |
| [P5-STORAGE](harness_lanes/p5_storage_retirement_engine.md) | `Projects/cwp-lanes-20261005/cwp-storage-tool` | 新tools/专属tests；四维护操作及`cwp-storage-retirement/1`小报告 | 已验收合入/发布e570daf，53项分步GREEN；生产清理由MAIN在迁caller后做，不重派 |

绝对目录、准备命令、精确写集、测试/清根及统一handoff字段见[P5总包](harness_lanes/p5_parallel_packages_2026-10-05.md)。三卡不再派发，本总表与CWP总PWF只由MAIN改。交付不等于已验收或已并入主线。

## 2026-10-04历史外线状态（不作为当前派发清单）

| 线 | 状态 | 独占实际工作目录 | 内容/责任 | 独立施工卡 |
|---|---|---|---|---|
| MAIN/root | active | `C:\Users\郑曾波\Projects\company-wiki` 当前根 | 来源核心、共享CLI/Contract、Store/预算、总PWF、配置发布与全部合入 | [G1细则](gate_simplification_closeout_2026-10-04.md)、[总计划](task_plan.md) |
| ET-DEADLINE | complete，已合入main63c4090；不重派 | `C:\Users\郑曾波\Projects\earnings-transcripts-s3-deadline` | 两个正式采集入口硬deadline、进程回收、原协议/语言/hash不变 | [ET独立代码包](harness_lanes/et_retrieval_deadline_closeout.md) |
| ET-LIVE | 完成一次授权尝试；HTTP 402，导入NOT RUN | `C:\Users\郑曾波\Projects\company-wiki-et-live-20261004` | 单次真实ET取数尝试与隔离报告；确定性CWP/FF测试已通过；未改生产仓 | [只读验收报告](C:/Users/郑曾波/Projects/company-wiki-et-live-20261004/report.md) |

这三个实际目录互不包含，也不进入MAIN当前工作树施工。各卡列精确写集。共享Git对象库不等于共享工作目录；各线用自己的index/codex分支，MAIN负责最后合入。Git切主线/合入期间交付线冻结，不并发改同一目标分支。

ET-DEADLINE独占worktree仍未提交。MAIN只读集中责任包91 passed、1 failed；唯一失败测试把API捕获的`RuntimeError`误当成worker异常退出，见task_plan下一步；MAIN未改外线写集。ET-LIVE只读报告已交付：一次FMP GET被HTTP 402拒绝，不重试，临时根已清理。没有交付消息不推测代码线完成；目录已存在先核身份/status，不reset不明工作。

## 已交付，不再重新启动

| 原线 | 当前事实 | 后续归属 |
|---|---|---|
| FF-S3 | `1d0c73c`与SourceRef v2资格收敛`e1eda60`已推远端main；当前FF聚焦回归177 passed / 1 skipped / 39 subtests，正常push gate GREEN | MAIN处理S3 live接口验收与安装/provider可移植配置 |
| ET-S3 | 已合ET main `93fe52c`；现代入口/旧薄batch/默认原语言已收敛 | ET-DEADLINE仅补真实截止缺口，不重做ET-S3 |
| G1-LEGACY | 外包交付 commit `1cf8183` 已并入 CWP `6394271`；handoff已保存；集中回归`170 passed, 1 deselected` | 外线写集关闭；G1全节点已完成，MAIN转入S3真实电话会导入验收 |
| SPACE-S5 | `company-wiki-storage-audit-20261003/results/storage_audit.{json,md}`交付，15项审计工具测试绿；零生产修改 | S5/S6由MAIN执行删除/迁caller，不重派空间审计 |
| StockWiki W01/W04、工程门简化、SourceExport、Identity、G-C消费者 | 各自既有交付/收据保留 | 不以新包重复实现；active owner树只读 |

## MAIN职责与当前施工

1. CWP来源reader/as-of/resolver/gap_plan/canonical_writer与FF SourceRef v2资格门已按TDD收敛；真实SHA、身份/期次/公开日、可回放locator保持自动验证，采集描述缺失仅诊断。
2. G1-LEGACY旧入口退役及46项当前状态分类完成；CloseGapBinding、旧whole-catalog LLM summarizer及archive/prune代码未发现生产caller，不作为用户门，后续若无调用者随S5/S6清理。
3. G1/S3已完成，ET-DEADLINE已集中验收并合入main63c4090。ET-LIVE一次请求被FMP HTTP 402拒绝，尚无live原文导入。N4-T1/T2及MeetingConverter CI均已交付并收口，不重派。2026-10-05 MAIN完成N4C阶段耗时调查与版本修复后按用户要求暂停；当前恢复接口见[收尾收据](harness_lanes/results/n4c_latency_version_closeout_2026-10-05.md)，当前没有新派发包。
4. 接收外线commit与短报告，核diff/接口/相关测试，解决冲突和跨仓接线。MAIN统一发布；外线不自己合main、不写他仓、不安装全局技能。
5. 测试全用独立根，退出恢复原样；不丢原件。不造签名、人工授权文件、每helper审批或固定场景数。

## 交接接口（冻结，避免各线自创合同）

### I1 已有 FF→CWP，复用

SourceRef 2.0、SourceExport v2、现有FF v2 request/result不变。上层传ID/hash/locator，不传存储目录；CWP独占来源DB与原件保存。

实际下载限额已经进入CWP→CNINFO bounded provider；配置与请求取更严格值，共享bytes/deadline/cost，不靠JSON校验冒称执行限额。latest_as_of的metadata查询预算沿用现有合同；reuse和是否补采分别控制。BYD FY2024下载10,092,140 B、raw和SourceRef SHA/size相符，latest_as_of只读复用及legacy精确复用没有新增文件。Dayu不改，不能执行所需硬上限则外发前具名失败。

### I2 已有 FF→ET→CWP电话会，协议不变

FF工具位置取 `EARNINGS_TRANSCRIPTS_TOOL`，调用 `--request-stdin --include-source-payload`。request `/1`、现有payload result `/2`、CWP import request `/2`与response `/3`不变；精确市场/证券/FY/Q，不从年报猜Q4、不翻译。ET不直接写CWP；CWP importer保存原件。

ET-DEADLINE只改变内部执行边界。ET-LIVE只证明真实ET工具→临时CWP导入段，FF companion确定性路由另记；如果确实经正式FF入口完成一次live才可以声明完整FF live链。工具不可用时NOT RUN，不用mock伪造真实权益。

### I3 G1-LEGACY→MAIN

**已完成并入。**保留 `enforce_direct_cli`、`legacy_script_execution_allowed`、`is_legacy_script_cli`的现有签名，environment薄兼容但不作为人工许可。支持来源/维护入口可以执行；永久退休研究writer仍退出78；删已完成一次性工具，不动历史事实文件。接收偏差及主线补测记录见G1 handoff。

### I4 ET-DEADLINE→MAIN

正式tool/batch统一内部supervisor；内部operation/request/剩余额度→原wire result+内部usage。内部usage不塞进外部协议。原始语言、期间、payload/hash/size与golden不变。硬限制范围是provider采集，显式旧翻译不冒称受该deadline约束。

超时按一个有限清理宽限回收自建worker；未知usage不当0且停批。原件保存仍由parent完成，已完成文件不回滚。交接提供真实subprocess elapsed/退出/共享deadline测试，不拿最终异常当及时停止。

### I5 只读验收/空间审计→MAIN

ET-LIVE独占报告已交：工具调用1次、FMP GET 1次、HTTP 402（由`provider_entitlement_required`映射；公共结果未返回status字段）、FY2026 Q3、原语言请求、10秒/1MB、没有重试；未取得正文，故未运行导入/SourceRef。确定性测试分别CWP 7 passed、FF 17 passed；临时根清理且CWP生产配置指纹未变。详情见独占目录`report.md`；这份报告完成验收记录，但不代表live source链通过。

SPACE-S5既有 `storage-audit/1`报告是施工输入。MAIN已完成[首批138,648,023 B/923文件清理](harness_lanes/results/s5_first_cache_cleanup_2026-10-04.md)，保护快照和四份原件正式CLI前后实读均通过，不重派不重复计算收益。derived 2,826,010,634 B仍有RF旧默认读取、CWP section入口及8,191条artifact引用；按[实施细则](s5_s6_legacy_storage_implementation.md)先迁caller。DB单独VACUUM不能释放旧全量span占用；原件不进删除候选。

## 依赖图与合入顺序

```mermaid
flowchart LR
    LEGACY[G1-LEGACY 独立代码包] --> G1[MAIN G1 门禁收口]
    CORE[MAIN 来源资格/采集日期阻断清理] --> G1
    G1 --> S3[MAIN S3 虚拟化联调]
    DEADLINE[ET-DEADLINE 独立代码包] --> S3
    LIVE[ET-LIVE 可选真实段验收] --> S3
    S3 --> N4C[N4C 四类文档/1、2、4并行/空间实测]
    N4C --> CLEAN[S5/S6 迁caller/清派生/DB收缩]
    SPACE[SPACE-S5 已交付报告] --> CLEAN
```

没有“所有外线交完才开始MAIN”的屏障。MAIN可先做G1核心、先合已绿G1包；ET代码交付暂存到S3。live不可用不阻G1，但S3不能虚报真实段成功。

## 当前外仓owner边界

正常用户只读Git快照2026-10-04：CWP master `376ed90`仅本机provider配置dirty；RF rf-impl main `6fb2def7`有242项owner记录，RF fcap `5319ee26`只有2项assurance文件变化；FF fcap `1d0c73c`只有未跟踪key；ET main `93fe52c`只有2项旧工具未跟踪记录。RF两个树不要混计。

StockWiki/IQS仍有owner工作；IQS明确只把CWP作为可选只读深研链接，不自动镜像/下载文档。RF/StockWiki已有pathless消费者，不再另开消费者代码包。Dayu纯外部，零修改。

CWP机器特定 `config/source_acquisition.yaml` 指向StockInfo隔离bounded provider工作树，未发布；可移植安装由MAIN收口，不让外线从该dirty配置开始。原StockInfo owner工作树保留，不并行跨仓修改。

## 验收和发布节奏

每个代码包只有三个自然阶段：读基线/目标RED→实现/责任包GREEN→本线commit/push+短handoff。所有局部PWF、测试和报告只在本线目录。交付包含base/head、改动路径、接口/golden、命令/结果、测试目录恢复、未完成事实；不交大执行日志、完整资料副本、key或备份。

MAIN只在G1、S3、N4 B/C、S5/S6几个大节点复核。无逐helper/逐文档/逐删除文件审查。已有轻量Git/CI照常；纯文档本轮不重跑业务测试。复杂度/全coverage是按需诊断，不成为交接资格门。


## 2026-10-04 派发与实际目录复核

用户确认两个代码包已发出：G1-LEGACY、ET-DEADLINE写集归外线，MAIN不抢改。Git实读ET三个worktree：正式main在 `earnings-transcripts/earnings-transcripts@93fe52c`；旧ET-S3 runtime为 `53e1e60`且已合main；新deadline为 `codex/et-s3-deadline@93fe52c`，由本次外包使用。外层earnings-transcripts是容器目录，没有自身.git。

这些worktree共享Git历史，不复制生产CWP资料库；工作目录各自包含代码与已跟踪样本，所以样本文件可能有副本。只读核查旧runtime：跟踪文件干净、无未跟踪文件，53e1e60已在正式main历史中；有130个已跟踪transcripts文件、ignored本地config.json与缓存。旧runtime可在保留本机配置后收尾，本轮不删除。新deadline保留到外包交付/合入结束。目录存在只证明工作树已创建，不代表worker/process仍在运行。


## 2026-10-04 跨仓写集复核

RF `fcap@5319ee26`相对merge-base `ee0a82bfd1eec935cf4e567eb42f0ef79efa0226`没有SourceRef v2消费者代码提交；当前main `6fb2def7`后加的pathless消费者尚未进入fcap。CWP本轮不写RF；合支线时保留main新增的verified-open链路。

FF `codex/transcript-companion@29085f7`现存工作树改动`fetch_filing.py`/`filing_contracts.py`，与SourceRef v2 capture资格入口重叠。MAIN本轮仅核实，不在正式checkout或companion目录改这两个文件；先读清其提交意图，再决定接续或合流。FF root的API key未读未改。

## 2026-10-04 新增三张互斥施工卡

以下三卡均已交付：N4-T1已集成MAIN、MeetingConverter已合master且主线CI绿，N4-T2已差异对账并选择性集成`0657579d`，主线CI绿。以下写集为原卡接口，不重派已完成任务。与之前已验收的StockQAbyLLM、MeetingConverter只读盘点卡区分：这里的MeetingConverter是后续CI零任务根因与快速门施工；若远端最新CI已正常运行测试，卡片要求只交现状证据，不制造无必要改动。

| 卡 | 仓库 | 独占目录与文件写集 | 依赖 / 主线合入 |
|---|---|---|---|
| [N4-T1](harness_lanes/n4_model_transport_diagnostics.md) | company-wiki | 独立worktree；automation/narrative_http_model.py、narrative_model_caller.py及需要时的summarize传递层；三个对应unit测试 | 不依赖N4-T2；不能碰source_catalog、Worker/AUTO、配置、生产数据或总PWF。主线收到后与T2联合验收 |
| [N4-T2](harness_lanes/n4_selective_narrative_coverage.md) | company-wiki | 独立worktree；source_catalog候选、路由、finalize与对应选择/handler测试 | 不依赖N4-T1；不能碰automation模型、Worker/AUTO、配置、生产数据或总PWF。主线收到后与T1联合验收 |
| [MeetingConverter CI快速门](harness_lanes/meetingconverter_ci_fast_gate.md) | MeetingConverter | 独立仓库worktree；限定CI workflow、可选的专用workflow合同测试与独立handoff | 与CWP及N4C无依赖，不进主线关键路径；最新CI若已修复则只报告，不改代码 |

N4-T1与N4-T2目录和测试文件互斥。并行时使用两个worktree，从同一提交基线开始；串行时可共用一个专用worktree，T1测试结束并提交后T2接续，以T1交付HEAD为T2的base，分别报告各自的commit范围。无需额外人工签收才能接续T2，但不得共用MAIN活动checkout或同时在一个目录施工。任何共享接口需求写入交接说明，由MAIN处理，worker不得扩写写集或私自合main。独立提交后，MAIN依次集成、运行两卡聚焦包、跨层Worker/本地模型端到端测试；离线合同和真实样本来源校验通过后开始新的有限真实运行。两条代码线不自行调用付费模型或写生产数据。

MeetingConverter使用独立Git仓库，不改变CWP、StockQAbyLLM、IQS或转录资料，因此可和N4-T1/T2同时施工。IQS不在本批可派发工作中，保持用户已明确的排除边界。

## 2026-10-04 G1-LEGACY 接收与主线收口

外包分支 `codex/g1-legacy-entry-retirement@1cf8183` 基于 `1cfec10`，handoff 已复制到 `harness_lanes/results/g1_legacy_entry_retirement_handoff_2026-10-04.md`。代码退役六个一次性 archive/retirement 工具及其专属测试，保留来源/维护 CLI 兼容入口。主线另修复 handoff 漏测的 `source_catalog_pilot_check.py`：它此前只导入 `enforce_direct_cli`，没有实际调用；同时清掉 clean-env 与 deployment 中已废弃的双环境许可残项，并更新旧共享行为测试。

集中主线回归：相关入口/兼容测试 **170 passed, 1 deselected**；单独针对新增行为的组 **27 passed**；Ruff 与 staged/unstaged `git diff --check` 通过。唯一 deselect 是包内全仓 Git 写集断言：外包原隔离工作树已通过，合入主仓后该断言会把本次有意的主线改动也算成包越界。外包 handoff 的该处收据与主线实际回归均保留。机器专用 `config/source_acquisition.yaml` 未纳入合并。

G1-LEGACY 写集已关闭；G1 总阶段仍因 FF SourceRef v2 资格门而保持进行中。ET-DEADLINE 继续在独立 worktree 施工，不合并到本次范围。

## 2026-10-04 外线交付状态

- N4-T1：4a53080 → MAIN 5de9154，跨层114+1项通过；[收据](harness_lanes/results/n4t1_model_transport_acceptance_2026-10-04.md)。不改外线worktree；T2若以4a53080为base，MAIN只集成之后的T2提交。
- MeetingConverter：master/origin/master同为8a33a7f，PR1已merged，新主线CI真实job成功22秒；[收据](harness_lanes/results/meetingconverter_ci_acceptance_2026-10-04.md)。独立卡收尾，不进N4C关键路径。
- N4-T2已交付并验收；N4C真实provider/消费者/总空间大节点仍待验收。S5首批缓存和旧section公开入口退出已完成，不重复施工。

## 2026-10-05 MAIN/外线当前接口状态

- N4-T1 已集成并推送（`5de9154`，包含于 MAIN `66808ee`；最终文档收据`e6b884a`），主线run37241977614 success。N4-T2已收口，见[验收收据](harness_lanes/results/n4t2_selector_acceptance_2026-10-05.md)；不得重复合入T1或T2。
- MeetingConverter施工卡已快进并推送master@`8a33a7f`，CI run37241709261 success；该线关闭。
- MAIN独占的S5旧整库Worker/阶段策略已退役，保留按需normalized读写直到RF与CWP locator消费者迁移；worker状态/停止清理命令继续保留。细节见S5/S6主计划及旧Worker集成测试收据（本轮记录在progress/findings）。
- RF复核仍以远端main `8a153f3387ae75fb172e70f8ab63ffd38100779a`为准；fcap仅weekly assurance两处owner改动未触碰。

## 2026-10-06 MAIN汇总更新

P5三包均已收口且已发布，不再派发。MAIN共享路径修复96f44a1/精确CI37394193179全绿，生产旧派生7104文件、8191 handle和1490530旧span处置完成；DB3055841280→222408704 B，整个旧派生+DB净减5659443210 B，原件/17表来源事实保持。正式小收据见harness_lanes/results/s5_production_storage_acceptance_2026-10-06.json；恢复点和一次性操作目录已删除。S6 docs/hook/控制文件已收尾并发布e481578，精确CI37399248994一次全绿。下一MAIN独占N4C，累计token cap答复仍待；外线不重复删库/重跑inventory、不处理owner WIP、不修改Dayu。
