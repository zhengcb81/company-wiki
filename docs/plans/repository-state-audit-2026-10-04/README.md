# 仓库状态只读审计施工包

## 给独立 harness 的用法

每个 harness 只拿本目录中的**一张 lane 卡**和 [`handoff_template.md`](handoff_template.md)。卡内列出唯一目标仓、允许读取的范围和唯一结果路径。不同仓库可并行；同一个仓库只能有一个 harness。所有审计只读，报告以 Git/PWF/已有测试证据为依据。总指挥负责接收、去重和下一步决策。

报告需严格遵守统一模板，不能把推测写成事实。目标仓库远端不可达、无 remote、PWF 状态互相冲突、文件疑似含密钥/来源原文时，标明 `unknown` 并解释，不猜。

## 审计线清单

| 优先 | 仓库 | 首轮问题 | Lane 卡 | 结果交接 |
|---|---|---|---|---|
| P1 | Revenue Forecast | fcap 4 个独有提交、360 路径证据记录、2 个 tracked dirty JSON；PWF 完成标志早于当前提交 | [revenue_forecast.md](lanes/revenue_forecast.md) | `results/revenue_forecast.md` |
| P1 | StockInfoDLSimple | 当前 owner checkout 多个 staged/unstaged/untracked 改动，另有 2 commit bounded-budget worktree | [stock_info_dl_simple.md](lanes/stock_info_dl_simple.md) | `results/stock_info_dl_simple.md` |
| P2 | filing-fetch | 主线已含 FF-S3，但 transcript companion 有 1 个独有 WIP commit；未跟踪 FMP key | [filing_fetch.md](lanes/filing_fetch.md) | `results/filing_fetch.md` |
| P2 | earnings-transcripts | ET-DEADLINE 1 个远端独有 commit；PWF “待 commit/push”已过期；根目录有未跟踪运行/工具资料 | [earnings_transcripts.md](lanes/earnings_transcripts.md) | `results/earnings_transcripts.md` |
| P2 | company-wiki | 本机 provider 配置 dirty；G1、RF-state、FC-802 历史文档分支有少量独有提交/报告 | [company_wiki.md](lanes/company_wiki.md) | Harness 在回复中返回完整报告；不要写目标仓 |
| P2 | dayu-agent | opt/cn_score 有 1 个远端独有提交；architecture_report 未跟踪 | [dayu_agent.md](lanes/dayu_agent.md) | `results/dayu_agent.md` |
| P3 | StockQAbyLLM | 多个未跟踪 pilot/工具/报告目录；gh-pages 为部署分支 | [stock_qa_by_llm.md](lanes/stock_qa_by_llm.md) | `results/stock_qa_by_llm.md` |
| P3 | invest-quick-scan | `nul`、`opencode.json` 未跟踪，当前开发分支无独有提交 | [invest_quick_scan.md](lanes/invest_quick_scan.md) | `results/invest_quick_scan.md` |
| P3 | MeetingConverter | tracked `.coverage` 改动，计划状态互相过期 | [meeting_converter.md](lanes/meeting_converter.md) | `results/meeting_converter.md` |

## 用户已裁定：StockInfoDownloader 不并线

StockInfoDownloader 仓库的 `改版新下载器` 相对 `origin/main` 有 38 个独有提交，`origin/v2-clean-rewrite` 有 43 个；不过用户已明确不把它作为主线，直接使用简易版 StockInfoDLSimple。因此：

- 不把 StockInfoDownloader 发给 harness，不审核它的支线做 merge 候选，也不清理其工作树。
- 不因旧计划/旧脚本引用 StockInfoDownloader 而重接它。
- 只由 StockInfoDLSimple lane 盘点当前被 CWP 实际引用的 provider 代码和未提交状态。
- 总指挥只更新 CWP 的活动路径默认/说明，并把旧入口保持冻结。将来要归档/删除 StockInfoDownloader 本地分支或文件时另行做有证据的操作计划，不包含在只读包中。

## 当前无需发卡的仓库

- **StockWiki**：本机 master `b25a34e` 干净，7 个 linked feature worktree 干净；当前能看到的 feature tips 均无相对本地 master 的独有提交。该仓库没有配置 Git remote，所以只能确认本地集成，不能声称已推送。
- QAbyLLM、industry-research、analyze-theme-value-chain、invest-skills、local-skills：首轮没有发现主线外开发提交或需要审计的 dirty 状态。后续若收到新 Git/PWF 证据再增卡。

## 总指挥接收规则

1. 先检查报告 `audit_status` 是否 `complete`；若 partial/blocked，先接收已确认事实和缺口，不要求 harness冒险写目标仓。
2. 根据 branch-only SHA 和 `git ls-remote` 当前 head 重算合并候选；不把 `ahead` 相对旧 tracking ref 误当成相对主线未并入。
3. 把代码、测试/收据、PWF 交接、tracked dirty、untracked 和 ignored 文件分组；判断哪些能恢复主线、哪些是唯一证据、哪些还需所有者判断。
4. 所有结果齐后另开“清理与并线”计划；那时才可提出精确路径/提交的可逆操作。本施工包本身不授权那些操作。

## 并行交接边界

各 lane 的 source repo 不重叠，写集只落到 `results/<repo>.md` 一个文件；CWP lane 是唯一例外，必须只在 harness 回复中回传，不落目标仓。Lane harness 不互相等待、不改其他结果、不调用总计划状态文件。总指挥是唯一维护本总计划/汇总结果的人。
