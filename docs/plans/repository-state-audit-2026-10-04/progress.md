# 进度日志

## 2026-10-04 — 建立只读盘点施工包

- 恢复并读取既有 active PWF `.planning/g1-legacy-entry-retirement-20261004/{task_plan,progress,findings}.md`；该计划继续保留原 pointer，不覆盖、不改写。
- 首轮识别多仓 branch/worktree/dirty 状态；修正一次 PowerShell 计数脚本把 behind 误解释为 ahead 的错误，后续按 `rev-list --left-right --count` 右列计算。
- 实时 `git ls-remote --heads` 检查主要 remote refs，未 fetch；没有改任何外部仓库或 Git 配置。
- 读取 CWP/RF/FF/ET/StockInfoDLSimple/StockWiki/IQS/Dayu/StockQA/MeetingConverter 可见计划、进度或交接记录。已记录 RF 顶层控制状态与 fcap 后续提交并存、ET deadline PWF 与远端提交不一致等需要 harness 追溯的情况。
- 用户补充决策：StockInfoDownloader 不参与主线，直接使用 StockInfoDLSimple。CodeGraph + literal search 确认 CWP 当前 SourceCatalog provider 及 bulk entry 已使用 StockInfoDLSimple；只剩冻结 legacy collector/config defaults 和说明残留。该决策写入总计划，移除 StockInfoDownloader 卡。
- 完成总览、统一交接接口和 9 张独立 lane 卡。CWP lane 明确要求报告只由 harness 回复返回，不写入被审计工作树；各外部仓报告各有唯一 `results/*.md`。
- 代码对齐：`scripts/config.py` 的默认 downloader paths 从 StockInfoDownloader 改为 StockInfoDLSimple；同步更新 README、ARCHITECTURE 与 TROUBLESHOOTING。旧 `collect_reports.py` 保持 freeze，没有启用或重接它。
- TDD：新增路径默认测试先 RED（1 failed，确实得到旧路径），实现后 GREEN；`tests/unit/test_config.py` 9 passed，ruff 两文件通过，`git diff --check` 通过。
- `config/source_acquisition.yaml` 仍为用户已有改动，尚未触碰或暂存；后续各次提交均只暂存明确路径。

### 本轮错误及处理

| 错误 | 处理 |
|---|---|
| 初次脚本将 behind 分支也输出为 diverged | 复算并只将 branch-only 提交识别为未并入内容。 |
| 大范围 PWF 文本搜索输出截断 | 对 RF/CWP 等改成指定权威状态文件和 bounded 输出；后续 harness 卡统一提供具体检查顺序。 |
| CodeGraph 首次 context 命中与下载 provider 无关的 `DownloaderConfig` 周边符号 | 改用精确符号与 impact；再用 literal search 核查硬编码的 provider 字符串。 |

最终交付：`scripts/config.py` 的 downloader 默认目录切换到 StockInfoDLSimple；旧 `collect_reports.py` 继续被 legacy writer freeze 拦截，不重接 StockInfoDownloader。目标配置 `config/source_acquisition.yaml` 未暂存、未改动。定向配置测试 9 项通过，Ruff 与 diff check 通过；commit `d8e6054` 已推送 `origin/master`，pre-commit 和 pre-push fast contract smoke 均为 GREEN。当前仅剩用户原有 `config/source_acquisition.yaml` 未提交修改。

后续扫描发现旧 `scripts/batch_download.sh` 没有 writer freeze，会直接调用 StockInfoDownloader 并绕过 Source Catalog 写入公司目录；已将其改为 fail-closed 退役提示，并更新架构/排错说明。shell 试运行确认脚本打印退役指引并非零退出，未触碰文件。修复提交 `ae2b2b7` 已推送 `origin/master`，pre-commit 与 pre-push fast contract smoke 通过。

## ET lane 接收 — 2026-10-04

- 收到并只读核验 ET-DEADLINE：`codex/et-s3-deadline@0017f24a999c5ecb224b646f47ebc8804769be73` 与 live 远端一致，相对 `origin/main@93fe52c` 有 1 个独有提交；implementation PWF 的 commit/push 待办已过期，但 branch 尚未并 main。
- 交接记录有 92 项责任包测试、全量 172 passed、10 goldens、ruff 与离线 CLI smoke 收据；本审计未重跑测试。建议分类为 `merge_candidate`，并线前做一次 FF→ET→CWP 离线契约联调。
- 按 lane 唯一接口补写 [`results/earnings_transcripts.md`](results/earnings_transcripts.md)。ET 的 bounded-runtime branch 已在 main 历史中；主仓 untracked `.workbuddy-ai/` 与 `eval_results.json` 保留、不读正文、不清理。
- 全部 PWF/计划卡和 provider 对齐改动已推送，最终 CWP `origin/master` 为 `bc5fed9b508bb168d4bf48ed23fc4c67cf5ec459`。尚有其他仓库 lane 等待独立 harness 交接；收到后按同一模板验收。

## 四条 lane 报告接收与复核 — 2026-10-04

- 收到并逐项复核 Revenue Forecast、StockInfoDLSimple、filing-fetch、dayu-agent 的报告；四份都明确覆盖各自审计范围与只读方法。RF、FF、Dayu 审计期间没有改源仓、没有运行测试；StockInfoDLSimple 的审计正文也报告只读，但其后附记记录了单独执行的 1.2.0 血统工作树改造与 188 项单测。
- RF：`fcap@5319ee26` 的 4 个 DWA-04R 提交仍未并入 `origin/main@6fb2def7`；UC closure 补丁与 main 现行实现语义分叉，不能整组直接合并。保留 dirty 周账本、`rf-impl` 唯一 §四十四裁定、`rfv2-tdd` WIP；`rf-merge-review` 47,173 个缺失 tracked 文件不做 prune。批 D 所称 1,985 untracked 与审计时 0 的差异保持 unknown。
- StockInfoDLSimple：只读报告快照为旧的 4 staged/1.1.0 血统；附记随后记录按单独用户指令备份并换成 `codex/cninfo-bounded-budget@8ed5fdd` 的 13 文件/3,206 行版本，执行 `tests/unit` 得 188 passed。当前只读复核确认 `HEAD@1693045` 和 refs 未变，工作树现为 13 个 staged additions、11 个 tracked modifications、3 个 untracked（`companies.txt`、`a_share_companies.txt`、`scripts/`）；尚无 commit/并线。外部备份在仓库外 `lineage-cleanup-backup-20261004`。该测试数字未见绑定 SHA 的独立报告，不能当作 E2E/CI 证明。
- filing-fetch：报告快照的主线为 `e1eda607`；当前只读复核看到 `origin/main@eb0af134`，相较报告时多了 `fix: align transcript bridge exchange and deadlines`。重新计算 `origin/main...codex/transcript-companion` 得 base-only 20 / branch-only 1：唯一原型提交仍未并入，但已交付的 SourceRef v2 companion 在主线；不应把原型整笔合并。FF-S3 已进入主线，相关未 push/未合并 PWF 语句属过期记录。未读 FMP key。
- Dayu：主线 `2115c86d` 干净；`opt/cn_score` 有 1 个远端独有提交并关联 PR #159，但 PR 状态无法从本地证据确认。依据用户“Dayu 为纯外部项目、不作任何代码变更”的明确边界，分类只记录、不合并、不清理、不改 PR；未知来源的 `docs/architecture_report.html` 保留。
- 四份结果文件已置于 `results/`。这次只改 CWP 本计划文档；保留 `config/source_acquisition.yaml` 原有用户改动。剩余 company-wiki、StockQAbyLLM、invest-quick-scan、MeetingConverter 四条报告待接收。

## 四仓并线与剩余卡片收尾（2026-10-04）

- RF：合入并推送 merge commit `8a153f3387ae75fb172e70f8ab63ffd38100779a`；UC 29 passed。稀疏树缺失 pre-push gate 文件，明确记录为 skipped。
- StockInfoDLSimple：`v2-clean-rewrite` 推进到 `8ed5fdd` 并推远端；provider 171 passed，CWP 集成 20 passed。第一轮 CWP pytest 因全局 langsmith/Pydantic DLL 导入失败，关闭 pytest plugin autoload 后通过；保留外部 owner WIP。
- filing-fetch：确认功能已在 main，旧 transcript 原型不并；只提交并推送 PWF 收尾 commit `d4d2fac4c690bfb8b1368d2ca140fd75150fd288`，plan claims 和精选 push gates 通过。
- Dayu：`opt/cn_score@76037b2` 快进到本地 main，87 项 focused tests 通过；远端返回 403，停止重试，未更改 PR 或其他文件。
- 收到并验收 StockQAbyLLM、MeetingConverter 两报告；保留 StockQA pilot 运行资料和 MeetingConverter `.coverage`/ignored output。
- 按用户要求不处理 invest-quick-scan；由独立项目负责。本轮未读取或改动 IQS 仓库。
- 准备提交的 CWP 变更严格限于计划、进度和结果报告；`config/source_acquisition.yaml` 用户改动未暂存。
