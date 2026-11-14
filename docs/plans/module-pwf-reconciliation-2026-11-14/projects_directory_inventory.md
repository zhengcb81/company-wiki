# Projects 顶层目录候选清单（2026-11-14）

只读枚举 `C:\Users\郑曾波\Projects` 的直接子目录。匹配本次模块前缀的候选目录共 63 个；这不是 Projects 下所有无关项目的全量清单。该清单只记录路径存在，不代表它们都是临时目录，也不构成删除授权。每个目录仍需由对应 owner 用 Git worktree、branch、PWF/handoff、dirty 文件、运行配置和原件/数据依赖逐一分类。

| 模块前缀 | 数量 | 候选目录 |
|---|---:|---|
| company-wiki / CWP | 5 | `company-wiki`; `company-wiki-et-live-20261004`; `company-wiki-gates`; `company-wiki-r1-local-observation`; `company-wiki-storage-audit-20261003` |
| filing-fetch / FF | 14 | `filing-fetch`; `filing-fetch-du10-41-matrix`; `filing-fetch-du11-local-transcript-reuse`; `filing-fetch-du6-portable`; `filing-fetch-du67-integration`; `filing-fetch-du8-integration`; `filing-fetch-du8-matrix`; `filing-fetch-r1-boundary`; `filing-fetch-r1-local-observation`; `filing-fetch-s3-limits`; `filing-fetch-source-ref-v2-20261004`; `filing-fetch-transcript-companion`; `filing-fetch-w19-sina-statements`; `filing-fetch-w20-replay` |
| revenue-forecast core | 14 | `revenue-forecast`; `revenue-forecast-dashboard-owner-release-20261109`; `revenue-forecast-du11-citation-closure`; `revenue-forecast-du5-units`; `revenue-forecast-du6-targets`; `revenue-forecast-du67-integration`; `revenue-forecast-du8-comparison`; `revenue-forecast-r1-boundary`; `revenue-forecast-r1-local-observation`; `revenue-forecast-r1-research`; `revenue-forecast-r1-targets`; `revenue-forecast-w14-clean-chain`; `revenue-forecast-w16-basis`; `revenue-forecast-w20-adoption` |
| revenue-forecast-audit (separate skill/review repo) | 9 | `revenue-forecast-audit`; `revenue-forecast-audit-du5-summary`; `revenue-forecast-audit-du6-import`; `revenue-forecast-audit-du67-integration`; `revenue-forecast-audit-du8-integration`; `revenue-forecast-audit-du8-measures`; `revenue-forecast-audit-w15-portable`; `revenue-forecast-audit-w17-coverage`; `revenue-forecast-audit-w20-checkpoints` |
| earnings-transcripts family | 8 | `earnings-transcripts` (container; Git repo is nested); `earnings-transcripts-du10-txt-fidelity`; `earnings-transcripts-du6-ff-readonly`; `earnings-transcripts-du7-extraction`; `earnings-transcripts-du7-integration`; `earnings-transcripts-du9-legacy-comparison`; `earnings-transcripts-s3-deadline`; `earnings-transcripts-s3-runtime` |
| StockInfoDLSimple | 1 | `StockInfoDLSimple` (container; primary Git repo is `StockInfoDLSimple/v2-clean-rewrite`) |
| investment-dashboard | 3 | `investment-dashboard`; `investment-dashboard-e15`; `investment-dashboard-owner-adapters-20261109` |
| invest-quick-scan | 1 | `invest-quick-scan` |
| StockWiki family | 8 | `StockWiki`; `StockWiki-f05-integration`; `StockWiki-f05-mainline-wt`; `StockWiki-identity`; `StockWiki-lane-integration`; `StockWiki-sw-ident`; `StockWiki-v2-reader`; `StockWiki-w04-g2b` |

## 解释与安全边界

- 当前目标结构是每个模块一个明确的长期主仓目录，不是强制把所有任务历史都搬到主仓或立即删除其他目录。
- `.planning`、`.mimosa`、`.workbuddy-ai`、日志、隔离测试报告、未提交代码、原件及其他用户数据不能因目录名看似临时而删除。
- 有活动 worker、对应未合并分支、运行配置引用、未交接 PWF 或不能解释的 dirty 文件时，该目录标记 `KEEP_ACTIVE`，由 owner 收尾后再评估。
- owner、PWF、branch 或 dirty 内容尚未查明的路径标记 `UNCLASSIFIED_HOLD`；只有归属和用途明确后才能改成保留/吸收/删除类别，不能因 unknown 直接清理。
- 已确认结案且仅含可重建产物的目录可标记 `DELETE_AFTER_RECEIPT`；每项清理须由仓库 owner 在自己仓内执行，并在其 PWF 留下路径和释放空间收据。
- StockWiki 8 个目录全部暂缓分类和清理，直到并行项目 owner 交接。

## 初步 Git 规模（不等同可删除数量）

- company-wiki 当前注册 8 个 worktree、13 个非祖先候选 refs；待本仓卡逐项核 ancestry、dirty 状态和 PWF。
- filing-fetch 当前 35 个注册 worktree、3 个未并入 `main` 的候选 ref；详细状态见 FF owner 盘点。
- revenue-forecast 当前 61 个注册 worktree、19 个未并入 `main` 的本地 ref；所有 RF 仓内 ref 由 RF owner 判定，即使源自 Dashboard-facing 工作。独立的 `revenue-forecast-audit` 由其自身 owner 处理。
- investment-dashboard 当前 80 个注册 worktree、92 个本地分支 ref；全部交 Dashboard D00 owner 对账。
- earnings-transcripts 当前 12 个注册 worktree、0 个本地非祖先 ref；StockInfoDLSimple 当前 3 个 worktree、0 个本地非祖先 ref。
- revenue-forecast-audit 当前 18 个注册 worktree（主仓加 8 个交付目录），17 个 clean；W08 证据目录含未跟踪 PWF 数据，须先确定归属再清理。
