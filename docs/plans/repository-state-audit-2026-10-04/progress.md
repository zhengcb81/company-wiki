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
