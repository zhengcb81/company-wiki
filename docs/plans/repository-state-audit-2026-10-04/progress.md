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
- `config/source_acquisition.yaml` 仍为用户已有改动，尚未触碰或暂存。最后一阶段只剩 staged-path 核对与计划文件检查。

### 本轮错误及处理

| 错误 | 处理 |
|---|---|
| 初次脚本将 behind 分支也输出为 diverged | 复算并只将 branch-only 提交识别为未并入内容。 |
| 大范围 PWF 文本搜索输出截断 | 对 RF/CWP 等改成指定权威状态文件和 bounded 输出；后续 harness 卡统一提供具体检查顺序。 |
| CodeGraph 首次 context 命中与下载 provider 无关的 `DownloaderConfig` 周边符号 | 改用精确符号与 impact；再用 literal search 核查硬编码的 provider 字符串。 |

## 下一步

补齐总览/交接模板/独立 lane cards，然后按 TDD 更新 CWP 仍指向 StockInfoDownloader 的活动默认路径与当前说明；定向验证后核对新目录和用户配置未混入暂存集。
