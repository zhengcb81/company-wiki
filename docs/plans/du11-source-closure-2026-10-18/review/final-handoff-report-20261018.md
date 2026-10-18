# DU11 最终交接报告（2026-10-18）

状态：**CONDITIONAL_READY** —— B2、C 工程侧、四张施工包已交付并合入 master；C 内容按用户口径（数字可近似、不可写错）**HK PASS 7/7**、CN 8/10、US 2–4/8（用户接受 8/10 收尾）；master 的收尾提交正在推送，exact CI 尚未产生。

## 1. 起止分支/commit、变更文件
- 起点：B2 修复链 `d55d3369` → `6a2ee853` → `2a80acf6`（origin 上已验证）。
- 主线：`origin/master` 已包含补写默认关闭开关、Mapping/冻结容器修复、P1–P4 四包、PWF 与收尾文档；之后的测试清理与 fixtures 修复仍在本地待推。
- 远端分支：`du11-close-docs`（收尾文档）、`du11-repair-flag`（09cb49ad，补写默认关闭）。
- 关键变更文件：`src/company_wiki/document_understanding/operating_states/{product_reference,relations}.py`（B2）；`src/company_wiki/automation/{narrative_summarize,execution_snapshot,execution_context,registry}.py`（补写实验）；`tools/document_understanding_benchmark/phase_c_observer.py`；`tests/conftest.py` 与两个 lane conftest（fixtures 解析）；P3 `tests/unit/test_identity_audit/p3_fixtures/`（原 `fixtures/` 改名，避免与 `tests/fixtures` 冲突）。

## 2. RED→修复→GREEN
- B2：110 项 du11 单测 PASS（`tests/unit/du11_source_closure`）；三源回放 CN 10/10、HK 7/7、US 8/8，绑定 `b2-final3-20261018`、`b2-real-sources-final2-20261018`；原件/gold 未变、0 API。
- C 工程：CN/US/HK 各 1 次真实 POST；`activation_recovery=PASS`（同 attempt、无新增扣费）；`cross_run_zero_POST=true`；FF 复用与 RF 读取通过。
- 补写实验：离线单测覆盖 partial→repair→merge、失败回退；真实 CN 实测 2 次 POST 并进入 `activation_pending`；`activation-resume` 仍冲突。
- 施工包：P1 40 / P2 70 / P3 50 / P4 34 全绿；P4 无 env 时 34 skipped（按设计）；全量单测在 fixtures 改名后待复跑。

## 3. 额度与预算
- 测量口径：`usage.jsonl` 按 database+attempt_id 去重。
- 累计：**56 个 attempt、1,091,219 tokens / $0.278311**（含 HK 16,813 / $0.00742，以及 69,046 / $0.031208 的 unknown hold；上限 2M / $20）。

## 4. 独立审查
- B2 最终复审 PASS：`b2-antecedent-final-review-20261018-v3.md`。
- C 内容复审：`c-content-review-20261018-cn-v3.md`（8/10）、`-cn-v4.md`；HK 7/7 目前只有文字结论，**缺独立复审文件**。
- 交接完整性复审：2026-10-18 两轮（CONDITIONAL_READY → NOT_READY），NOT_READY 的根因（`fixtures` 包冲突导致 CI 命令 15 errors）已修复；其余文档失真已按复核修正。

## 5. push 结果与 exact CI
- `origin/master` 已包含 71f4a8c6 及之前全部提交；测试清理、fixtures 修复与本文档更新的提交正在推送。
- 唯一 exact CI：`2a80acf6`（`b2-final3-20261018/ci-39139605025.json`，success）；收尾提交的 exact CI 待推送后补。

## 6. 真实 provider 与缓存/恢复
- 真实模型：CN = MiMo（`mimo-v2.6-flash`）、US = MiniMax（`MiniMax-M3`）、HK = DeepSeek（`deepseek-flash`，用 Windows 用户级有效密钥）。
- 同 run 恢复不重复扣费；跨 run 复用 0 POST；FF 复用与 RF 读取均有收据。
- 收据目录（工作区、**未入 git**）：`.planning/shared-reading-production/du11/live-{cn,us,hk}-*`。

## 7. 清理
- 已删除仓库根 12 个本轮遗留临时目录（b2-review2/3-*、cwpaW03-*、cwplC-*、tmp5_*、pytest-of-*）。
- 未清理：RF 旧 assurance 工作文件与 `output/`（按 handoff 要求保持原样）；`review/b2-antecedent-final-review-20261018-v3.json` 已纳入。

## 8. 仍未完成与下一步
- **未完成**：收尾提交的推送与 exact CI；冻结 holdout 与 RF 审查循环（全部 receipt 标注 development regression, not holdout）；RF/FF 自身套件未在本机复跑；覆盖修复的 `activation-resume` 冲突；HK 独立复审文件；`.planning` 收据树未入 git。
- **下一步**：① 推送收尾提交并取 exact CI；② 补 HK 复审文件（带 gold id 表）；③ 启动 holdout + RF 循环；④ 按各自 CI 环境复跑 RF/FF；⑤ 决定覆盖修复的去留（修好或删除）。
