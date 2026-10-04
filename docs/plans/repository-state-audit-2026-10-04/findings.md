# 发现记录

## 审计方法与时间

- 本轮本机观测时间：2026-10-04 16:39 UTC 左右；远端分支 SHA 通过 `git ls-remote --heads origin` 实时读取，不写 `FETCH_HEAD`。
- Git 分支差异按 `git rev-list --left-right --count <base>...<branch>` 解释：左数是 base 独有，右数是 branch 独有；只把右数大于 0 的 branch 当作含待判断提交。
- 对 linked worktree 分别读取 `git status --short --branch`；PWF 声明与 ancestry、提交内容、handoff/测试收据交叉核对。
- 仅本地 PWF/Git 快照不能证明内容已 push；远端 refs 只在 `ls-remote` 成功且 ref 精确匹配时确认。

## 当前候选盘点

| 仓库 | 主线外提交或未提交状态（本轮观测） | PWF/历史解释 | 处理 |
|---|---|---|---|
| `StockInfoDownloader` | `改版新下载器` 对 `origin/main` 有 38 个独有提交，`origin/v2-clean-rewrite` 43 个；`feature/local-changes` 本地 4 个、远端 3 个独有提交；根工作树的 `.claude/settings.local.json`、`config.json` 有改动。 | 用户 2026-10-04 明确说明不再把该仓并主线，改用 StockInfoDLSimple。 | **排除**：不给它外包卡、不再评估合并。CWP 只登记该架构决策并核查活动入口不再依赖它；不触碰该仓状态。 |
| `StockInfoDLSimple` | 默认/当前 `v2-clean-rewrite@1693045`：多个已暂存、未暂存及 untracked 源码/测试；`codex/cninfo-bounded-budget@8ed5fdd` 相对基线有 2 个独有提交。 | CWP PWF 记有 budget provider 集成、62 项测试和 BYD 真实 CNINFO E2E；此仓本地没有找到根级 `task_plan.md`，需要核对其他计划/交接和 commit 对应关系。 | 发只读卡；要逐项说明 staged/unstaged、哪些代码由 CWP 实际引用，不可回滚。 |
| `revenue-forecast` | `fcap@5319ee26` 与 live `origin/fcap` 相同；相对 live `origin/main@6fb2def7` 为 **4 ahead / 14 behind**。另 `codex/revenue-source-reader` 有 1 个本地独有原型提交。根工作树有 `assurance/runs/weekly_alert.jsonl`、`weekly_manifest.json` 两项 tracked 修改。 | 四个独有提交是 DWA-04R A–D 批，末项记录 360 条路径、8 个 execution-run carriers；RF `audit_review/README.md` 与机器状态记录 plan completed/CA-201（日期 8-31），和较新的 fcap 提交并存，需审查它们是否是后续范围、历史证据还是需并线工作。 | 发只读卡，最高优先；**不**凭 4 个提交数量或旧“completed”文字直接合并/丢弃。 |
| `company-wiki` | `master@0c259cce` 与 live `origin/master` 相同。`codex/g1-legacy-entry-retirement` 有 2 个独有提交且仅见进度/交接文档差异；`codex/rf-state-audit` 本地有 2 个独有提交、一份 RF 审计报告；两个 FC-802 history branch 各有 1 个独有审查记录。主工作树的 `config/source_acquisition.yaml` 被用户修改。 | CWP narrative PWF 明确保留该配置作为本机 provider 集成配置；G1 与 RF 审计文档的主线落点/重复性需核对。 | 发只读卡；卡的报告由 harness 回复返回，不落入目标仓，避免把 CWP 新增计划文件误计为被审计 dirty。当前配置不暂存、不改写。 |
| `filing-fetch` | `fcap@e1eda607` 与 live `origin/main` 相同；`codex/transcript-companion@29085f7` 对主线有 1 个独有 WIP 提交，差异包括 transcript adapter/CLI。根工作树有未跟踪 `config/FMP_API_KEY.txt`。S3 limits checkout 比其远端支线多 2 个提交，但其变更是否已在主线需按 patch/ancestry验证。 | CWP PWF 记有 FF-S3 已 push/main、SourceRef v2 和 transcript companion 组合测试等不同阶段；本地当前 transcript-companion branch 与主线不同。 | 发只读卡；API key 不读不哈希不输出。明确区分已进 main 的 FF-S3 与唯一 WIP 的 companion。 |
| `earnings-transcripts` | `main@93fe52c`；`codex/et-s3-deadline@0017f24` 对 main 有 1 个独有提交且与 live 远端分支一致；根工作树有 `.workbuddy-ai/`、`eval_results.json` 未跟踪。Bounded runtime 已 merge。 | deadline PWF 写“commit/push 待办”，但对应提交已经存在远端，说明 PWF 收尾文本落后于 Git；需核实 handoff、提交测试收据和 main 合入意图。 | 发只读卡。确认它是已交付支线还是待合并功能；不操作远端。 |
| `dayu-agent` | `main` 与 live `origin/main` 相同；live `origin/opt/cn_score` 有 1 个独有提交；根目录有未跟踪 `docs/architecture_report.html`。 | 未找到常规 PWF 三件套；需从 `docs/`、提交、PR/CI 记录查原因。 | 发只读卡，但显著置顶用户禁令：**不改 Dayu 任意代码/配置/分支/文件**。 |
| `invest-quick-scan` | `master@a193821` 与 live `origin/master` 相同，无开发分支独有提交；`nul`、`opencode.json` 未跟踪。 | PWF 最新进度写到 Phase 71，StockWiki G2b-C 已有提交，IQS 仍有草案/owner 签收等状态；需解释这两个未跟踪项是否配置/运行产物。 | 发只读卡，只清点文件元数据、ignore/consumer/PWF 证据，不读取可能有敏感值的 `opencode.json`。 |
| `StockQAbyLLM` | `master@5fdcc2c` 与 live `origin/master` 相同；`gh-pages` 相对 master 有 2 个独有提交（部署分支，不应默认当开发分支）；未跟踪 `.codegraph/`、`.workbuddy-ai/`、`nul`、两个 `pilot_runs/` 目录及 `progress_update.txt`。 | 关联 IQS Phase 68–71 的记录提及运行数据/隔离回执；根级 task_plan/progress 可能是旧计划，需逐项核对作者、阶段、消费者、可再生性和是否唯一证据。 | 发只读卡；不读取/输出 LLM key、来源正文或未提交回执全文。 |
| `MeetingConverter` | `master@3c0b053` 与 live `origin/master` 相同；tracked `.coverage` 修改（53,248 B，文件时间 2026-07-09）；没有发现主线外开发提交。 | progress 记 P0–P8 曾完成；根 task_plan 又把 P0、Phase10–15 保留为 pending，状态彼此过期/冲突。 | 发只读卡核对 `.coverage` 是否受跟踪、生成/消费关系及 PWF 历史；不删除。 |
| `StockWiki` | 本地 `master@b25a34e` 工作树及 7 个 feature worktree 均干净；所有可见 feature tip 对本地 master 无 branch-only commit。**没有配置 Git remote。** | IQS progress 记 G2b-C 已提交到该 master；W01/W02/W03、SourceExport、W04 等支线看起来已集成。 | 不发问题施工卡；本轮本地证据未发现未并入提交或 dirty 文件。没有 remote，故不声称已推送/远端一致。 |
| `StockQAbyLLM` 部署分支、`industry-research`、`QAbyLLM`、`analyze-theme-value-chain`、`invest-skills`、`local-skills`、`MeetingConverter` 之外其余已枚举仓库 | 初轮状态未发现需要并线的开发分支/dirty 文件（MeetingConverter 已单独列出）。 | 以本地 refs 与当前 git status 为界；不保证未配置远端的仓库已推送。 | 不发卡，除非后续 harness 报告提供反证。 |

## 关键架构结论：StockInfoDownloader 与 StockInfoDLSimple

- 当前 canonical source-catalog acquisition provider 配置读取 `config/source_acquisition.yaml`；本机文件（用户已有 dirty 改动）明确指向 `../StockInfoDLSimple/cwp-cninfo-bounded-budget`、provider `stockinfo-cninfo` 1.2.0 并启用 budget capability。该本地配置不能被本轮或 harness 覆盖。
- `scripts/run_downloader.py` 的真实 CLI 已调用 `StockInfoDLSimple`，而且搜索到的 CWP 实际 bounded CNINFO 实测记录也指向它。
- 旧 `scripts/collect_reports.py` 和 `scripts/config.py` 留有 StockInfoDownloader 字样/默认路径；`collect_reports.py` 在 `writer_policy` 下属于被冻结的 legacy mixed entry，不能为了“切换 provider”而重新启用它的 legacy wiki writer。后续代码收敛应把活动默认/说明改到 StockInfoDLSimple，并将该冻结入口明确标记为非 canonical/不可执行，不要调用 StockInfoDownloader，也不要造一套新的下载链。
- 该审计仅更新 CWP 内适配路径默认/说明和测试；不会改 StockInfoDLSimple 源码、不会改其 WIP 工作树，也不会改用户的 source acquisition 配置。

### 已完成的 CWP provider 对齐

- `scripts/config.py` 的 `PathsConfig.downloader_dir` 与 `windows_downloads` 之前仍默认到 `~/StockInfoDownloader`；`Config._build_config` 也再次硬编码旧路径。已统一默认到 `~/Projects/StockInfoDLSimple/v2-clean-rewrite` 及其 `downloads/`。
- `tests/unit/test_config.py` 新增测试同时锁定 dataclass 默认和 `_build_config` 加载默认。RED 复现旧目录，代码改动后 GREEN。
- README、架构图和下载故障说明已声明 StockInfoDLSimple 是 A 股 provider，并把 Source Catalog 的 staging/SHA/manifest 定为正式入库流；旧 `collect_reports.py` 明确继续受 writer freeze 拦截，没有重接旧下载链。
- 未改 `config/source_acquisition.yaml`（用户已有未提交的 1.2.0 provider worktree 路径），未改 StockInfoDLSimple/Dayu/StockInfoDownloader 项目内容。
- 验证：定向 RED 1 failed（期望 DLSimple，实际旧路径）；随后定向单测 **1 passed**，`tests/unit/test_config.py` **9 passed**；`ruff check scripts/config.py tests/unit/test_config.py` 通过；`git diff --check` 通过。第一次 pytest 在沙箱被 TEMP/.pytest_cache 写权限拒绝，没有进入测试；正常权限重跑后使用 pytest 插件隔离并清理了专属 TEMP 目录。

## 已验证远端 heads（`git ls-remote`，非 fetch）

- CWP: `master=0c259cce…`；`codex/g1-legacy-entry-retirement=c3209eee…`；另远端 `fcap=8665c8c…`。
- RF: `main=6fb2def7…`、`fcap=5319ee26…`。
- FF: `main=e1eda607…`、`codex/ff-s3-single-request-limits=5b9a8c19…`。
- ET: `main=93fe52c4…`、`codex/et-s3-deadline=0017f24a…`、bounded runtime `53e1e606…`。
- StockInfoDownloader: `main=6df45a1…`、`v2-clean-rewrite=1693045…`、`改版新下载器=064a837…`、`feature/local-changes=3b6b6a6…`。仅作排除范围佐证，不派施工卡。
- Dayu: `main=2115c86d…`、`opt/cn_score=76037b2…`。
- IQS/StockQA: live `master` 分别为 `a1938213…` / `5fdcc2c5…`。

这些 SHA 是 2026-10-04 的快照，独立审计 harness 必须在执行时重查；不得 fetch 来刷新本地仓库。
