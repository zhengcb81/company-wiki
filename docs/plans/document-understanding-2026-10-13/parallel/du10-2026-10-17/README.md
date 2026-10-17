# DU10 并行施工包 — 2026-10-17

状态：`READY_FOR_DISPATCH`。三个施工包分别在 filing-fetch、company-wiki、earnings-transcripts 的独立工作目录内进行；没有共享源码文件或共享测试目录。CWP 主线生产接线仍由 ROOT 负责。

## 总览

| 卡 | 项目/工作目录（需从指定基线新建隔离 worktree） | 唯一交付范围 | 与主线的关系 |
|---|---|---|---|
| [DU10-FF41-CLOSE](du10_ff41_close.md) | `C:/Users/郑曾波/Projects/filing-fetch-du10-41-matrix` | FF 的完整 41 例矩阵及中断恢复 | 关闭已知 OPEN 验收项；只读使用固定版本 CWP/ET |
| [DU10-CWP-SUMMARY-GOLDSET](du10_cwp_summary_goldset.md) | `C:/Users/郑曾波/Projects/company-wiki-du10-summary-goldset` | CWP 摘要质量的来源定位基准语料 | 只增独立计划/标注/校验器，不改生产实现 |
| [DU10-ET-TXT-FIDELITY](du10_et_txt_fidelity.md) | `C:/Users/郑曾波/Projects/earnings-transcripts-du10-txt-fidelity` | ET 电话会文本切分与原文定位保真 | ET 仓单独修改；不改 FF/CWP |

三个工作目录当前尚未创建。开工时各自从下列已核基线建独立分支/worktree；不要在同一 checkout 先后执行。建议分支分别为 `codex/du10-ff41-close`、`codex/du10-cwp-summary-goldset`、`codex/du10-et-txt-fidelity`。

| 项目 | 固定起始提交 | 当前已知工作树情况 |
|---|---|---|
| filing-fetch | `c7c8867da35cd19d4f419fa70947332615e8e9c0` (`main`) | 主树有未跟踪配置密钥；卡要求保持在原树，不读、不复制、不提交 |
| company-wiki | `900dbf6489f3b995a0bfb7fcbb8a001a68df241d` (`master`) | 主树有历史未跟踪 `.planning/` 证据；不读取/清理/搬动 ROOT 私有临时物 |
| earnings-transcripts | `7d06777e250ee3f7ae58f0be2cee62944bd2c104` (`main`) | 主树现有 `.workbuddy-ai/` 与 `eval_results.json` 未跟踪文件保持原样 |

## 共用交接与独立审查规则

每个作者先在自己的 worktree 建 PWF（`task_plan.md`、`findings.md`、`progress.md`），最后交 `handoff.md`、`handoff.json` 和精简 `receipts/`；提交完整变更并冻结最终 HEAD。不得只交聊天摘要。

交接前必须由**作者之外的独立 agent**审查最终 HEAD：审查范围、HEAD、diff 文件清单/SHA、测试收据都写入报告。审查者核对卡片每项交付、接口兼容、测试真实性、遗漏、测试数据清理及仓库边界。发现任何问题，作者逐项修复并重跑受影响测试，再由同一审查 agent 对最终版本复核；报告无未解决问题才可正式交接。没有独立 agent 时保持 `IN_PROGRESS`，不得作者自审代替、不得先交接再补审。

只设 A（基线/复现）、B（实现与受影响测试）、C（端到端/独立最终审查）三个大节点；不在每个小提交上加签收。失败、部分完成、缺资料写明实际状态，不改阈值、不删除失败、不把 `NOT_RUN` 写成通过。临时目录以初始清单和 sentinel 为准，结束后精确恢复。默认离线；不翻译、不下载原件、不调用付费模型或供应商 API。

| 卡 | 代码所有权 | 禁止修改 |
|---|---|---|
| FF41 | filing-fetch `tools/offline_contract_matrix/` 与本卡新增的专属测试/fixtures | CWP、ET、Dayu、生产下载脚本、provider secrets/config、原 oracle 与 41 个 case 定义 |
| CWP Goldset | 仅本卡目录下的样本清单/JSON 标注/校验器和专属测试 | `scripts/`、`automation/`、`document_understanding/`、`profiles/`、其他计划/测试目录、任何原件 |
| ET Fidelity | ET 根 `transcript_extraction.py` 与本卡新增的专属测试/小型 fixtures | `transcript_tool.py` 下载/provider/HTTP/预算行为、CWP、FF、翻译功能、全量真实 TXT 副本 |

ROOT 在三个包完成后分别按卡接口收件；同一仓库只做快进/挑选提交，不把作者工区当临时目录清理。该批不表示 CWP 深页生产接线、摘要真实模型验收或 FF 矩阵已完成。
