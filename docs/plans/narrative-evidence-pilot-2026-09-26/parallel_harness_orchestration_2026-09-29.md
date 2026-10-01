# 六仓独占施工与总指挥集成计划（2026-09-29）

> **2026-10-01 当前现场状态（后续更新见 Phase 34）：**CWP `master@00af53f` 已包含 E-B merge `9e73eb4`，合并后相关回归 349 passed/2 skipped；StockWiki `master@b4f3846` 已包含 W01/W02/W03、SourceExport reader、W04 和 MIC 补强，`check_all.sh` 686 passed，所有已知来源分支均为 master 祖先。RF `rf-impl main@3e03ce83` 已包含 `fcap@ee0a82bf` 全部已提交历史且干净（ahead origin 4）；revenue-forecast 的 fcap 工作树仍有大量未提交/不可见项，不能按旧审计下界清理或整树并线。FF 当前 `fcap@d35b6f5` 与 `origin/main` 同步，但本地 `main@c9799b7` 落后 39 个提交；SourceRef v2 与 transcript companion 两个干净 WIP worktree 有 4 个核心路径重叠，应由同一 FF owner 合入。ET `main@4924d57` 已推送 origin/main，`/2` producer 已实现；其本地 `.workbuddy-ai/` 与 `eval_results.json` 保留。IQS `master@56ff421` 已提交 owner 盘点；现有 V02/scoring 未跟踪工作由其 owner 管理；provisional G2b 正反 CLI 通过，但 full G2b、QA-04 与 SW-IDENT 仍有 pending。跨仓工作继续按每仓单一 owner，本计划不另开第二写入者。

> **本计划已进入实施；当前提交与测试状态见 [Phase 26–34](task_plan.md) 与 [S0a/S0b 接口表](s0a_observed_interfaces_2026-09-29.md)。** 本任务的主 agent 是唯一总指挥：维护本目录总计划、冻结接口、收各仓提交、处理跨仓不兼容、运行跨仓真实数据 E2E 和发布汇总。各 harness 只写自己独占的项目仓库/隔离工作树；可以只读其它仓及本目录的合同。IQS 当前由既有 owner 维护，不另开同仓写入线。StockWiki reader/W02/W03/W04 均已通过本地单仓集成验收，收据见 [W04 owner-context card](harness_lanes/stockwiki_g2b_owner_context.md)。旧 [跨仓施工图](cross_repo_mainline_and_delivery_plan_2026-09-28.md)保留历史调查和详细试验背景，冲突时以本页、Phase 26–34 与 2026-09-29 清理方案为准。

## 1. 唯一写入者与六份可直接派发的施工卡

| 线 / 独占项目目录 | 可直接交给 harness 的文档 | 输入 | 产出 |
|---|---|---|---|
| CWP / `C:\Users\郑曾波\Projects\company-wiki` 的**专用代码 worktree** | [CWP 施工卡](harness_lanes/company_wiki.md) | 本仓已保存的 2026-09-28 WIP、真实原件只读副本 | 来源读取/导出 golden、简化的精确采集接口、selected bundle 与可靠 Worker |
| ET / `C:\Users\郑曾波\Projects\earnings-transcripts\earnings-transcripts` | [ET 施工卡](harness_lanes/earnings_transcripts.md) | 明确公司和 fiscal FY/Q 请求 | 原语言 TXT 的版本化精确工具结果 |
| FF / `C:\Users\郑曾波\Projects\filing-fetch` | [FF 施工卡](harness_lanes/filing_fetch.md) | CWP SourceRef/operation golden、ET tool golden | v1 兼容和显式 v2 来源/电话会编排 envelope |
| RF / `C:\Users\郑曾波\Projects\revenue-forecast` | [RF 施工卡](harness_lanes/revenue_forecast.md) | FF/CWP 生产者 golden 和来源读取 CLI | 无物理根依赖的来源 adapter；仓内可读证据路径即可闭环，缺 hash 只记 pending，已有 hash 校验格式和实际字节 |
| RF 本地状态只读审计 / RF 只读、CWP 单一报告文件 | [RF 状态审计卡](harness_lanes/revenue_forecast_worktree_audit_2026-10-01.md) | 2026-10-01 审计基线快照：root `fcap@ee0a82bf` 12 tracked 状态/404 untracked；local main `415d8eb3`；reader `3b00b938` | 审计报告已交付在指定结果路径；已提交 fcap 历史在 main，旧 reader 原型需择要评估；报告记录 ACL 不可见目录与未完成的全量归属，不据此清理；RF 全程只读 |
| StockWiki / `C:\Users\郑曾波\Projects\StockWiki` | [W04 实施与验收记录](harness_lanes/stockwiki_g2b_owner_context.md)；已完成并线见[收据](harness_lanes/stockwiki_mainline_integration.md) | 当前本地 `master@b4f3846`；保留源 worktree、分支和 `.claude/` | owner receipt、ISO MIC registry、精确 request export 与关系校验已合入；聚焦 57 项、合并后全门 686 项通过；G2b public CLI 正反例通过；W04 已验收，不再把此卡当作未完成实现任务 |
| IQS / `C:\Users\郑曾波\Projects\invest-quick-scan` | [IQS 施工卡](harness_lanes/invest_quick_scan.md) | canonical golden 已由当前 owner 提供；只读核收尾报告/公开 CLI，不新开写入线 | G2b 当前 owner-context 公共正反例已通过；其它 IQS capability 与其 active PWF 由现有 owner 收尾，不由本线重复实现 |

主 agent 独占当前 `company-wiki/docs/plans/narrative-evidence-pilot-2026-09-26/` 中的总计划、接口表和既有卡；唯一例外是 RF 只读审计卡指定的新报告文件 `harness_lanes/results/revenue_forecast_worktree_audit_2026-10-01.md`，仅该审计 harness 可写，其他 lane 与主 agent不得改它。跨仓 E2E 运行目录仍由总指挥独占。CWP 代码 harness 必须使用独立**物理 worktree 目录与独立分支**，不在主 agent 当前工作树写文件；总指挥先核对当前 WIP、再指定准确 base。RF 审计 harness 对 RF 全程只读；其它仓每仓仍只设一个产品代码写入者，同仓 WIP 收拢由该 owner 完成。外部 `dayu-agent`、`StockInfoDLSimple` 和全局安装的 filing-fetch skill 本波为只读依赖；如确需修改，增开单独目录所有者，不让 FF harness 越界写。

**写入交接**：每仓 owner 独自提交并正常合并该仓代码、报告 HEAD/剩余脏文件，然后停写；总指挥只读核验各仓结果、协调跨仓不兼容并运行独立汇合测试，不进入别人的仓库执行合并。G-D 的 CWP 生产派生清理也由 CWP owner 在总指挥核准精确清单和隔离测试结果后执行；主 agent 核对前后原件/manifest/净空间账。总指挥的计划文档与 CWP 代码 worktree 始终是两个不同的物理目录和不同写入集合，但共享同一 Git 对象库/refs；并行期双方只操作自己的分支，不做共享 `gc/prune`、跨分支 reset 或强推。各线测试根使用该 harness **实际可写**的短临时目录 `<lane>-<nonce>`，汇合根使用总指挥可写的 `gate-<nonce>`；仅在 `C:\cwt` 已明确配置为可写时才选它，运行前须确认目标原本不存在且在专用测试目录内。

使用 PWF 的 harness 把自己的进度记在**自己的仓库/工作树**，其它 harness 可直接使用本页链接的单仓施工卡；不共同编辑本计划目录，也不把其它仓 PWF 当自己的任务状态。总指挥是本目录 `task_plan.md`、接口表和跨仓结果的唯一写入者。各线单独测试通过是本仓交接条件，跨仓能力是否可用由总指挥跑相应 G 节点后标记；没有第二套人工签收文件。

## 2. S0a/S0b：先给共同基线，再冻结正式 producer 合同

1. **S0a 只读盘点**：在具备完整文件权限的环境逐仓记录 live HEAD、上游/merge-base、tracked diff、untracked 路径清单和已有 PWF 关联。CWP 当前未提交简化改动、ET/FF/RF 的 WIP、StockWiki 未跟踪 W01、IQS 大量活动文件均须先归属，不用 `reset --hard`/通配符 clean。派发后各仓 owner 才在独立分支保存自己的有效 WIP 为可恢复提交；总指挥只记录 commit/路径，不复制跨仓文件。
2. **S0a（派发前）**：总指挥只读记录当前 CWP/ET/FF 真实 serializer、CLI 与现存样本的版本/字段/错误码；IQS 则记录现有 2.2 schema/参考校验器和合同夹具，StockWiki 身份库生产入口现状。此时接口表标 `observed` 或 `pending`，只足以让各线写本仓 RED/整理 WIP，**不宣称 frozen**。
3. 固定 P01 年报、P04 招股书、P06 增发、P07 IR、T01/T02 电话会、P09 低价值文档等试点原件的文件身份和只读路径；每个测试复制少量原件到**各线不同**的隔离根。测试结束恢复本次测试目录原状，生产原件、catalog 和 manifest 不写。
4. 总指挥发每条线的独立施工卡和 S0a 表。**S0b（producer owner 完成后）**：CWP owner 从现行或修复后的代码输出 SourceRef/operation/SourceExport v2/verified-open 的正式 golden；ET owner 输出 `/2` 工具 golden；FF owner 输出 v2 envelope golden；StockWiki owner 从自己的身份数据库/serializer 输出 identity snapshot golden，IQS owner 用其 schema/参考校验器验证并交合同反例。总指挥把版本、golden 文件 SHA、字段/错误码、CLI 命令、owner/consumer 与 `frozen` 状态登记。selected package 与尚未定义的 identity mapping DTO 均保持 `pending`，直到各自 owner 给出正式版本。消费者只在对应 producer 冻结后接入；任何字段变化由生产者先更新 golden 和版本，再通知受影响 consumer，只重跑受影响合同与跨仓边。

接口表每行固定为 `producer repo+commit | schema/version | serializer/CLI 命令 | golden 正例/畸形反例路径与 SHA | 身份/时间/SHA/locator 语义 | 错误码/退出码 | consumer repo+版本 | 状态 observed/pending/frozen`。正式正例由生产代码序列化，畸形反例可人工构造；接口表是技术事实记录，不是多方签收。

总指挥随 S0a 向每线交一份**只读测试输入清单**：`sample_id | 原件绝对路径 | 原件 SHA/字节数 | 文档类型/期次 | 此线所需 locator oracle | 复制到本线隔离根的规则 | 预期生成文件 | 清理后根状态`。按需求分发 P/T 子集，绝不把生产原文提交进其它仓。各仓自己维护 fake HTTP/坏合同 fixture；真样本只复制到本仓专用可写临时根。G 门使用另一套总指挥专用短根，同一原件在测试前后重算 SHA，DB/WAL/cache/下载等本次生成物全部移除并核根恢复。现有正式测试文件若只在 WIP worktree，先由 owner 保存并导入可恢复提交；测试包不得引用一个尚不存在的路径却记为通过。

## 3. 交接接口：生产者负责事实，消费者只持逻辑 ID

| 生产者 → 消费者 | 已知版本/最小语义 | 冻结物与失败规则 | 汇合测试 |
|---|---|---|---|
| CWP → FF/RF 的 SourceRef/verified read | 现行 `SourceRef` schema `2.0` 含 `document_id, source_id, content_sha256, byte_size, mime_type`；verify/open 返回实际全字节 SHA 验证结果，不返回永久物理路径。外部 envelope 的精确字段以 CWP serializer golden 为准。 | 同 ID 错 SHA、未知版本、撤回、as-of 后、仅元数据未验 bytes 不可当可用原文；同 SHA 多根迁移不得改变逻辑身份。 | G-0、G-A |
| CWP → StockWiki 的 SourceExport v2 | `SourceExportBundleV2` schema `2.0.0`，manifest/evidence span、export ID、bundle SHA、locator；`SourceExport` 是来源快照，不携带投资结论。 | CWP 真实 producer golden；StockWiki 不使用 `companies/`、dayu、Dropbox 的路径或旧 path hash 作 source ID。 | G-B；full sync/weekly 到 G-D |
| ET → FF 的 transcript tool | 现行 opt-in `/2` 请求必须同时提供公司/交易所、FY **及** Q；结果有 `provider_payload_sha256`、抽取文本 `content_bytes`/hash、来源 URL/时间，**没有原始 payload 长度字段**。工具失败和未找到分开。 | ET 真 serializer golden；CWP importer 对 `/2` exact-key 校验。若要 FY-only 或新增 payload 长度，先定义新版本并同步 FF/CWP golden；FF 不把全年报告猜成 Q4，不翻译。 | G-A 中 FF→ET→CWP |
| FF → RF 的 filing/source envelope | FF v1 默认 JSON/退出码继续；显式 v2 SourceRef envelope 将 filing 与 companion 的状态分开。最终 wire 版本由 FF producer golden 固定，旧计划所写 `1.3` 不是允许猜字段的依据。 | 缺 review receipt 不阻断；已有复用须 0 下载，未知/歧义期次 0 网络，错误来源和损坏 payload 具名失败。 | G-A 中正式 FF CLI→CWP→RF |
| IQS 合同 → StockWiki；StockWiki → 下游 identity snapshot | IQS 契约包 `2.2.0`，Entity `2.1.0`、AnalysisSubject `1.0.0`；W02/W03 provisional identity/mapping DTO 与 golden 已交付。 | 精确五态、as-of、issuer/security/listing 与来源绑定复用现有正式 schema/serializer；W04 owner-context/MIC 已验收。full G2b 仍缺 verified、多挂牌、AnalysisSubject、历史区间等真实生产路径证据，不再声称 DTO 不存在。 | basic G-B 已通过；full G2b partial，由 IQS owner 跟踪 |
| CWP → RF/StockWiki 的 selected evidence | narrative event/select/summary/bundle 试点 schema `/2.0`；持久 selected package 和正式消费尚待 CWP/消费者实现。 | CWP 先出含 source ID、locator、raw SHA、同语种摘要、skip/partial/needs_review 理由和撤回/as-of 的正式 package/golden；RF 与 StockWiki 各自实现本仓 reader/adapter 并回源核验，不可直接用试点 DTO 假充已发布合同。 | G-C |

总指挥负责**接口表的登记/冻结、核对各 owner 的真实 producer golden 与跨仓测试**；golden 由生产者 owner 的代码生成。每条线保留内部自由度；不共享数据库、物理根路径、临时文件或 Python 内部类型。若 producer 改了字段且未更新版本/golden，集成失败即由 producer 修复；若 consumer 硬编码路径或擅自放宽 hash，由 consumer 修复。旧兼容只为实存持久数据和既有用户 CLI 保留。

## 4. 可执行的并行波次与关键依赖

```text
S0a 只读盘点 → 六仓各自整理 WIP / 写 RED / 独立测试
CWP P0 修复 → G-0 → CWP S0b golden ─┬→ FF v2 → FF envelope → RF reader → G-A
                                    └→ StockWiki v2 reader → G-B
ET 精确工具 → ET S0b golden → FF companion → G-A
StockWiki W04 owner receipt + ISO MIC registry + exact request export → 只读 IQS CLI 交叉校验 → G2b
CWP 持久 selected package → RF + StockWiki 各自 selected adapter → G-C
G-D：逐批按实际消费者引用选择已通过的 G-A/G-B/G2b/G-C；无全局 G2b 前置
```

- **第一波可同时启动**：ET、IQS、CWP P0 RED/修复/G-0、StockWiki W01/身份 serializer、RF registry hash/无 review 阻断测试、FF v1 基线/SourceRef 合同准备。每线只改自己的仓。FF 最终 v2 消费等 CWP golden；RF 最终 reader 等 FF envelope；StockWiki reader 最终消费等 CWP export golden。StockWiki 身份 producer 可与 IQS 在不同仓并行；IQS 的 G2b 交叉校验等 StockWiki 真实身份 golden 和 IQS 稳定 CLI 都具备后运行。ET 可独立完成工具测试。
- **当前可并行工作**：E-B/W04 均已完成本地主线验收，不重复派发。恢复后 CWP 先完成 G-0/G-A 与 NarrativeBundle transport；RF/StockWiki 在正式接口冻结后可各自实现薄 consumer adapter。FF SourceRef 与 companion 两条支线由单 owner 整合；IQS 继续现有 owner 工作。本次收尾后暂停，不新启写入线。
- **第二波在同仓内顺序**：FF 的 SourceRef v2 与 companion 由同一 owner 顺序合入，先对齐当前 CWP CLI 和 ET JSON/日期语义。StockWiki reader、engineering gate、W02/W03/W04 单仓卡已验收；IQS full G2b 的生产入口/真实样本缺口另由现有 owner 跟踪。CWP 不开第二个并行 writer；selected/full sync 等正式持久包和相关 G-D 条件。
- **汇合可并行**：G-A 和 G-B 在 G-0 通过后可在不同隔离测试根运行；G-C 的 CWP 内部 E5/E6 可与它们推进，但正式 RF/StockWiki selected 消费须等各自 reader 与持久 package。G-D 逐批检查待清派生的实际消费者：只要求与该批相关的已通过读/消费门和无引用证明；G2b 只限制身份功能发布或被身份功能引用的派生，不挡无关清理。
- **共享机器负载**：各仓小测试可并行，429 页 PDF、Windows 1/2/4 进程与空间清理 E2E 由总指挥排班，避免内存/磁盘竞争影响性能结论。任何生产 Worker 在 E-B/G-C 通过前保持 paused。

## 5. 每条线的独立测试包与总指挥验收

各线施工卡列自己的单元/合同/本仓 E2E 文件和正反例；owner 先写或修有意义的失败测试，再实现。开发时跑受影响测试，交接前跑该线测试包；总指挥只在 G-0/G-A/G-B/G-C/G-D 跑一次跨仓真样本 E2E，不要求每个小提交重复全量套件或独立 reviewer。

| 集成点 | 总指挥负责的真入口与通过条件 | 失败时继续的范围 |
|---|---|---|
| G-0 CWP reader | 四根和 company/dayu/Dropbox 原生位置、同 SHA 搬根、同尺寸篡改、旧引用、真实 locator、429 页资源；测试根恢复 | ET/IQS/FF/StockWiki/RF 可继续本仓 TDD，消费者不切默认 |
| G-A 采集/预测 | FF→CWP→RF、FF→ET→CWP 正式 CLI/工具；0 意外网络、一次精确下载、无 review receipt、仓内可读证据路径、缺 hash 只作 pending，已有 hash 校验实际字节、原文与来源不变 | 只关闭失败的 FF/RF/ET 新路由 |
| G-B 来源消费与 G2b 身份 | basic G-B 已通过；W04/MIC 已合入，IQS public CLI 正反例通过，整仓 686 passed。full G2b 的生产 preview/verified、多挂牌/AnalysisSubject/历史区间等证据另行汇合。 | 不重做 W04；full G2b partial 不影响无关原文读取或 CWP 叙述工作 |
| G-C 叙述/Worker | 年报、招股、IR、TXT 的 selected/skip/locator 真回放；RF 与 StockWiki 从各自正式 adapter 实读 selected package 并核撤回/as-of/原文 SHA；1/2/4 文档、kill/retry/lease/outbox、资源/空间上限 | Worker 保持 paused；若仅 CWP 内部包绿而消费者失败，只记内部 E5/E6 通过，G-C 不通过 |
| G-D 派生清理/发布 | 每批 scratch 删除重建、实际消费者引用与对应已通过门、精确生产派生清单、同卷净字节、原件/manifest 前后相同；StockWiki full sync/weekly 仅在相关 G-B/G2b/G-C 已通过后单独 canary | 不可解释的派生批次跳过；无关批次和已验能力继续 |

每个 harness 交接只需一页：`repo/base HEAD/branch/commit`、改动路径、生产接口版本与真实 golden 路径/hash、测试命令/退出和隔离根恢复、已知 hold。该页是技术交接，**不是授权签收**。同仓 owner 按依赖顺序正常合并自己的代码并停写；总指挥只读核实实际仓库状态、协调跨仓字段冲突与最终路线，不 force push。用户无需为已授权范围内的每个文件、job、PR 或节点再签字。

## 6. 当前派发条件与风险

本节实际进度以 [Phase 26–34](task_plan.md) 和本轮新增交叉审计记录为准。CWP E-B 与 StockWiki W04 已在本地主线，不能重复派发。RF 已提交 fcap 历史已进入 `rf-impl main@3e03ce83`；dirty fcap 的 404 项是旧视图下界且有不可见目录，因此不得清理、全量 reset 或按旧摘要合并。FF 只有一个集成 owner：当前 fcap 与远端 main 一致，本地 main ref 落后 39，两个 WIP worktree 有文件重叠；先在 owner worktree 对齐 live main 并整合 SourceRef v2 与 companion。ET `/2` 工具已实现，等待 FF 消费者汇合；ET 本地未跟踪评测/工具记忆保留。IQS 当前 owner 正更新其计划，full G2b 和 QA-04/SW-IDENT 收尾继续由现有 owner 负责。缺 hash 的 RF closure 规则按用户最新裁定：仓内可读真实文件路径必需，缺失/空白 hash 只作 pending，已提供 hash 必须匹配真实 SHA。CWP 总指挥下一步完成 G-0/G-A 剩余真实 E2E，然后冻结独立 `NarrativeBundle /2.0` pathless read/export contract，推进 G-C；G-D 只在消费门通过后按精确派生批次做。FMP 此前真实请求返回 402；fake-provider E2E 不代表已付费 API 可用。

## 7. 收尾暂停（2026-10-01）

以 [跨线收尾报告](harness_lanes/results/cross_line_closeout_2026-10-01.md) 和 Phase 34 为最新状态。用户要求完成提交/远端发布后暂停；ET 已推送，CWP/RF 发布结果见 progress.md。恢复后保持 G-0/G-A→G-C→G-D 顺序；FMP JSON、unknown publication 与原始字节 locator 是明确缺口，不追加无价值 provider 或重复验收。
