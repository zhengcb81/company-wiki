# 多仓库支线与未提交文件只读盘点 — 任务计划

**状态：** 四仓集成已处理：RF、StockInfoDLSimple、filing-fetch 已推送目标主线；Dayu 仅本地快进，远端 push 被 403 拒绝，尚未完成远端并线。StockQAbyLLM 与 MeetingConverter 报告已验收；IQS 由独立项目处理，本线排除。
**基线观察：** 2026-10-04（本机 UTC 16:39 前后；远端 refs 以 `git ls-remote` 实测为准；并线结果另见下方实施记录）
**范围：** 只读审计卡和其后用户明确要求的四仓并线。未授权清理其他仓库；不检查或改动由独立项目负责的 invest-quick-scan。

## 目标

识别哪些仓库确有未并入主线的提交、未提交文件或无法从 Git/PWF 记录解释的工作树；为每个需要盘点的仓库提供一份互不重叠的施工卡，定义同一交接格式，并由总指挥集中接收报告。用户已决定 StockInfoDownloader 不参与主线，CWP 应使用 StockInfoDLSimple；因此不为 StockInfoDownloader 建施工卡，也不把它的支线作为合并候选。

## 阶段

1. [x] 只读盘点本机候选仓库、branch/worktree 状态、tracked/untracked 状态，并用 `git ls-remote` 校验关键远端 refs；未 fetch。
2. [x] 对照 CWP、RF、FF、ET、StockInfoDLSimple、StockWiki、IQS 等仓库的可见 PWF/交接记录，标明完成声明与当前 Git 证据的差异。
3. [x] 按用户最新决定移除 StockInfoDownloader 施工线，查明 CWP 现有 StockInfoDLSimple provider 入口和剩余旧引用；不读写 StockInfoDownloader 工作树。
4. [x] 写总览、统一交接模板和 9 份独立审计卡（CWP 报告通过 harness 回复返回；其他报告写入各自唯一结果文件）。
5. [x] 在 CWP 中以测试先行把下载路径默认改为 StockInfoDLSimple，并更新当前说明；保留被 writer freeze 拦截的历史入口为不执行的兼容记录。
6. [x] 集中核对卡片边界、验收口径、测试和 Git diff；只提交本计划目录与明确授权的 CWP 代码/测试/文档文件，不暂存既有 `config/source_acquisition.yaml` 用户改动。`d8e6054`（provider 对齐/审计包）、`ae2b2b7`（退役旧批量下载旁路）与 `bc5fed9`（PWF 收尾）均已推送 `origin/master`；推送前远端均核验为父提交，pre-commit 与 pre-push 检查通过。ET lane 交接已收录为 [`results/earnings_transcripts.md`](results/earnings_transcripts.md)。

## 固定边界

- 对被审计仓库仅执行读取命令。禁止 `fetch/pull/switch/checkout/restore/reset/stash/clean/merge/rebase/cherry-pick/commit/push`，禁止改任何目标仓库的 Git 配置、分支、索引、工作树或生成文件。
- 审计卡不运行项目测试/构建/下载/LLM；只查现存测试、CI、PWF 收据。运行测试容易写缓存或运行产物，不适合纯盘点。
- 不读取、不复制、不哈希、不输出密钥及本机敏感配置的正文。只记录路径、Git 状态和必要的非敏感元数据。
- 不清理“看起来像临时文件”的路径；通过计划、创建/消费者、时间、哈希/重复性和 Git 历史证据分类后，仍把删除/回滚作为后续单独决定。
- 每个外部 harness 只负责施工卡指定的一个仓库，只能写其唯一交接结果；不能读取其他源仓库，不碰其他 lane 输出。
- Dayu 是外部项目。用户本轮仅明确授权把 opt/cn_score 的一个既有提交快进到本地 main；除该提交外不改其代码/配置/文件。远端 push 因 HTTP 403 未完成。
- StockInfoDownloader 被用户明确排除，不创建其审计卡，不合并其分支。StockInfoDLSimple 是当前和未来优先的 A 股 provider。

## 主要验收点

- 每个卡都有唯一 source repo、base/default-ref 规则、PWF/commit/worktree 检查法、敏感文件纪律、唯一交接目标和禁止操作。
- 结果能区分：已合并/仅落后主线/确有独有提交/patch-equivalent/本地 dirty/未跟踪/忽略生成物/部署分支/无远端无法确认。
- 结果报告不把 PWF checkbox 等同 Git 合并事实，不把文件名或旧计划的“完成”当成删除许可。
- 计划目录以外的目标仓库内容无变化；用户原有 CWP config dirty 改动保留且不暂存。

## 错误与约束记录

| 事项 | 处置 |
|---|---|
| 初次跨仓分支统计脚本把 behind 误标成 diverged | 丢弃该统计；按 `rev-list --left-right --count base...branch` 的第二列重新筛出 branch-only commits。 |
| PowerShell 批次命令输出曾截断/提前结束 | 改为各仓分支/状态的独立并行只读命令，并对关键仓库逐项检查。 |
| 普通沙箱的 Git ownership 与少量文件访问限制 | 使用单次命令级 `safe.directory` 的只读 Git 查询；未写全局配置。 |

## 后续独立交接

本任务已完成审计卡、交接模板和 StockInfoDLSimple provider 对齐；ET lane 已收到并记录。其他 lane 结果到达后，由总指挥按各卡唯一接口与统一模板继续只读验收。该包不授权清理或并线；任何清理/并线另按证据制定施工计划。

## 报告接收与汇总阶段（2026-10-04）

7. [x] 接收并复核 Revenue Forecast、StockInfoDLSimple、filing-fetch、dayu-agent 四份报告；分别记录审计快照边界、关键未决项和后续处置建议。StockInfoDLSimple 报告另含审计后的 1.2.0 血统工作树改造，单独标记为实施附记，不把它误认成只读审计内容。
8. [ ] 按用户 2026-10-04 最新指令推进四仓并线。RF、StockInfoDLSimple、filing-fetch 已推送；Dayu 本地快进及测试完成，但远端拒绝 403，仍待有权限的 owner 推送该已有提交。
9. [ ] 收尾尚未闭合的接收项：company-wiki lane 报告若通过 harness 回复到达则记录；StockQAbyLLM 与 MeetingConverter 已收到并验收。invest-quick-scan 按用户明确要求由另一独立项目负责，本线不检查、不修改、不重复发卡。该项不授权清理目标仓文件。

### 四仓并线施工顺序与验收口径

1. **RF（已完成）**：DWA-04R 有价值载体/账本以稀疏集成树并入，UC 保留 main 的 §四十四 hash-pending 语义；merge commit `8a153f3` 已推送 `origin/main`，UC 聚焦测试 29 passed。缺失 `tools/pre_push_gate.py` 的钩子跳过，未宣称完整 pre-push gate 通过。
2. **StockInfoDLSimple（已完成）**：目标为 CWP 使用的 `v2-clean-rewrite`。`codex/cninfo-bounded-budget` 已快进并推送到 `8ed5fdd`；provider 单测 171 passed，CWP 离线 provider contract/E2E 20 passed。owner checkout 其余 11 项修改、3 项 untracked 和仓外备份保留。
3. **filing-fetch（已完成）**：FF-S3 与 FF→ET→CWP companion 已在 main；旧 schema 原型不整笔并入。PWF 收尾提交 `d4d2fac` 已推送；plan-claims 与精选 pre-push 检查通过。
4. **Dayu（本地完成、远端待 owner）**：只把 `opt/cn_score@76037b2` 这个已有提交快进到本地 main；focused tests 87 passed。推送遭 GitHub HTTP 403 拒绝，停止重试。该授权不延伸到其他 Dayu 工作树/文件，也不包括改 PR。
5. **阶段验证**：RF 29、StockInfoDLSimple 171 + CWP contract/E2E 20、FF 计划声明及精选 push checks、Dayu 87 项均有各自收据。CWP 侧预算/provider E2E 和 FF→ET→CWP 离线合同链已分别验证；没有另造一个把无直接运行依赖的 RF、Dayu 串起来的四仓 smoke。每个小文件/子步骤不增加单独门禁。

### 本轮授权范围

原始审计卡只读边界保持为历史事实。用户随后明确要求推进上述四仓并入主线，因此本阶段获准对四个具名目标做必要的隔离集成、测试、提交和远端推送；范围仅限上述候选。对 Dayu 的新授权只覆盖 `opt/cn_score` 这一个提交，其他 Dayu 内容仍不碰。Dayu 远端 push 已因 403 停止，不尝试权限绕行。

### 2026-10-04 并线实施结果与交接收据

- **Revenue Forecast**：fcap 的有价值 DWA-04R 载体/账本已在稀疏树并入，保留 main 的 UC 语义和 §四十四 hash-pending 决定。集成提交 `8a153f3387ae75fb172e70f8ab63ffd38100779a` 已推送 `origin/main`；UC 测试 29 passed。稀疏工作树缺少 `tools/pre_push_gate.py`，该钩子明确跳过，未记为完整 pre-push gate 通过。
- **StockInfoDLSimple**：`codex/cninfo-bounded-budget` 快进到目标 `v2-clean-rewrite@8ed5fdd` 并已推送；单测 171 passed，CWP provider contract/E2E 集 20 passed。保留 owner checkout 里其他 11 个 tracked 修改和 3 个 untracked 文件；CWP 本机 `config/source_acquisition.yaml` 未改。
- **filing-fetch**：旧 `codex/transcript-companion` 原型未整笔并入；FF-S3/SourceRef v2 companion 已在 main。只更新并推送 PWF 状态提交 `d4d2fac4c690bfb8b1368d2ca140fd75150fd288`；plan-claims verifier 与精选 pre-push gates 全绿。
- **Dayu**：`opt/cn_score@76037b2` 已快进到本地 `main`；两组相关测试 87 passed。推送 `origin/main` 收到 HTTP 403，停止重试；远端仍未确认包含该提交。既有 `docs/architecture_report.html` 保留。
- **外包卡收据**：StockQAbyLLM 与 MeetingConverter 报告已复核。StockQAbyLLM 的 pilot 运行资料（审计时仍在增长）与敏感配置副本原样保留；MeetingConverter 的 `.coverage` 和 ignored `output/` 均保留。invest-quick-scan 由用户指定的独立项目处理，本线完全不检查其仓库。
- **余项**：company-wiki lane 的审计报告仍按原接口等待 harness 回复；这不阻塞已完成的四仓并线。本计划不授权删除外仓文件。

### Next Step

完成本计划收据提交与推送；其后主项目按 narrative-evidence-pilot 的当前 Next Step 进入 N4C 真实文档资格与小批次验收。Dayu 的 403 需由有权限的仓库 owner 处理，不在本地反复推送。
