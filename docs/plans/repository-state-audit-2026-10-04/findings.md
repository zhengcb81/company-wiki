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
- 旧 `scripts/collect_reports.py`、`scripts/batch_download.sh` 和 `scripts/config.py` 留有 StockInfoDownloader 字样/默认路径；`collect_reports.py` 在 `writer_policy` 下属于被冻结的 legacy mixed entry，不能为了“切换 provider”而重新启用它的 legacy wiki writer。`batch_download.sh` 原先仍会直写公司目录、绕过 Source Catalog，已改为 fail-closed 退役提示；不调用 StockInfoDownloader，也不造一套新的下载链。
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

## 四条 lane 接收结论（2026-10-04）

| lane | 验收状态 | 可确认结论 | 需保留/待决事项 |
|---|---|---|---|
| Revenue Forecast | 报告完整，按只读卡验收 | `fcap@5319ee26` 有 4 个 branch-only DWA-04R 提交；batch-A 的 360 路径是该提交文件数（355 carrier + 5 台账修改），不是产品代码量。`codex/revenue-source-reader` 另有 1 个原型提交；其余列出的分支已在 main。 | fcap 的 UC 门补丁与 main 语义分叉，应只迁移仍有价值的证据载体/账本，不整组合并旧实现；先找回 `rf-impl` 唯一 §四十四 owner 裁定。保留两份真实运行周账本、rfv2-tdd WIP；不 prune 掏空的 `rf-merge-review`。1,985 untracked 的提交自述与实测 0 未解释，权限受限目录保持 unknown。T3 连续周运行记录为失败，根因不在本只读审计中验证。
| StockInfoDLSimple | 审计正文完整；附记是审计后的独立工作树实施记录 | 报告时支线 `codex/cninfo-bounded-budget@8ed5fdd` 有 2 个独有提交，包含 1.2.0 bounded provider。审计后附记记录用显式路径把对应 13 个文件放入主 checkout index，并保留 1.1.0 原工作副本备份；单测记录 188 passed/0 failed。当前复核确认 `HEAD@1693045` 未改变，13 个新文件仍 staged、11 个原有文件仍 modified、另有 3 个未跟踪项，分支/远端未合并或提交。 | 本 lane 原定只读，因此将附记作为授权后的实施记录单独对待。继续实施前要核对备份可恢复性、CWP 适配器实际消费的 JSON/预算契约，并补充绑定提交内容的离线集成/E2E 收据；现有 188 项单测不等同跨仓 E2E。不得覆盖或清理另外 11 项 WIP。远端 main 和其它 live heads 本卡未 fetch/评估。 |
| filing-fetch | 报告完整；另做只读当前 SHA 复核 | 报告时 `origin/main@e1eda607` 已含 FF-S3 与 SourceRef v2 companion 实现；当前本地 `origin/main@eb0af134` 又多一个 transcript bridge deadline/exchange 修复。重算后 `codex/transcript-companion` 仍是 1 个 branch-only 原型提交，主线落后数从报告时 19 增至 20。 | 原型与已交付 v2 契约不同，不整笔并入；可留作历史证据。FF-S3 的“未 push/未并线”计划文字已过期，应在后续 PWF 收尾时修正。`config/FMP_API_KEY.txt` 未读未碰。跨仓 FF→ET→CWP 已交付内容以当前主线为准。 |
| Dayu agent | 报告完整，按只读卡验收 | `main@2115c86d` 与 live 主线相同；远端 `opt/cn_score@76037b2` 有 1 个独有提交，且 `refs/pull/159/head` 同 SHA。 | PR #159 开/关/合状态 unknown；遵照“Dayu 为纯外部项目”的用户边界，不操作该仓、远端分支或 PR。来源不明的 `docs/architecture_report.html` 只登记并保留。 |

### 接收边界

- 这些结论是各自审计时间点的快照，不代表所有远端 ref 在此后都未移动。FF 的主线已在本次验收中用本地 `origin/main` 再核对；RF、Dayu 等待任何后续施工前应按其独立计划复核最新 head。
- 四个 lane 报告自身都未执行合并、清理或提交目标仓库。StockInfoDLSimple 的附记例外于“卡片只读范围”，记载的 staging 和 188 项测试发生在审计正文结束后，并声明有单独用户指令；当前只登记该状态，不继续改外部仓库。
- 本次没有运行产品测试；验收对象是报告证据与状态分类。下一阶段清理/并线需基于独立施工计划，保留 owner WIP 和唯一证据。

## RF 并线前模拟（2026-10-04）

- 再次 `git ls-remote` 确认 RF live heads 未变：`main@6fb2def7`、`fcap@5319ee26`。
- 对 batch-A 的 355 个新增 blob 做 Git 对象大小统计：合计 **15,527,787 bytes（约 14.8 MiB）**，远低于完整 0.807 GiB main tracked tree；不需要恢复/复制完整备份。`origin/main` tracked tree 实测 48,771 blob、865,981,987 bytes（约 0.807 GiB），因此后续必须用稀疏 worktree，避免额外复制整棵树。
- `git merge-tree origin/main fcap` 的合并模拟发现 **50 个冲突：45 个 add/add（execution-run 同路径不同内容）和 5 个文本冲突**（`OWNER_DECISIONS.md`、`REMEDIATION_REGISTER.md`、`progress.md`、`test_scenarios.py`、`uc/scenarios.py`）。这证实不能机械 merge。策略：同路径证据默认保留较新的 main 版本；f​​cap 版本仍由 merge parent 历史保存；文本按当前主线与用户 §四十四裁定做语义合并；代码保留 main 当前“缺 hash 仅诊断、有效路径可闭环”的用户决定。
- `rf-impl` index 中查到 §四十四原文：它明确覆盖 §四十三的缺 hash 阻断规则、有效路径无 hash 可闭环、不得伪造 hash，并保留提供 hash 时的字节 SHA 验证。该内容将安全并入 main 计划记录，不会用过时的 fcap 文本覆盖。
- 受限沙箱中的首次 Git merge-tree 因 `.git/objects` 写入权限失败；改用用户授权的非沙箱只读模拟得到冲突报告，没有移动分支或改变任何 worktree。一次 PowerShell 管道把 `rev-parse --stdin` 当作对象解析器而失败，改用 `cat-file --batch-check` 后完成统计；没有源文件变化。
- 当前策略不是把 45 个同路径冲突的旧证据副本加倍复制进 main。合并提交会保留 fcap 父提交及其原始证据历史，工作树使用主线已存在的对应版本，新增且无冲突的 carrier 和账本再带入主线。

## 2026-10-04 四仓并线及外包卡验收结论

- RF `8a153f3` 已推送 main，UC 聚焦测试 29 passed；稀疏 worktree 缺少 pre-push gate 脚本，钩子跳过，不记为完整门通过。
- StockInfoDLSimple 的 `codex/cninfo-bounded-budget` 已推送到 `v2-clean-rewrite@8ed5fdd`；provider 171 passed、CWP contract/E2E 20 passed。owner WIP 和 CWP 用户配置保留。
- FF 代码功能已在 main；只推送 PWF 收尾提交 `d4d2fac`，旧 companion 原型不并入，精选 push gates 通过。
- Dayu `opt/cn_score@76037b2` 已快进到本地 main，测试 87 passed；远端 push 被 HTTP 403 拒绝，停止重试。
- StockQAbyLLM、MeetingConverter 两份交接已验收。StockQA 运行资料、MeetingConverter `.coverage` 均保留；疑似密钥文件未读。
- IQS 由用户指定的独立项目处理，本线不检查、不修改、不重复派发。company-wiki lane 如有独立报告仍按原交接接口接收。
