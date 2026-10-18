# DU11 最终交接报告（2026-10-18）

状态：**CONDITIONAL_READY** —— B2 与 C 工程侧已交付；C 内容按用户决定以 CN 8/10 收尾；本地 master 未推送、无 exact CI。

## 1. 起止分支/commit、变更文件
- 起点：B2 修复链 `d55d3369` → `6a2ee853` → `2a80acf6`（origin/master 上已验证）。
- 本地 master：`b59e2141`，领先 `origin/master` `ccc5bc7e` 7 个提交（开关、Mapping/冻结容器修复、相位 C 观测器、PWF、收尾文档）。
- 远端分支：`du11-close-docs`（e6280e6e，收尾文档）、`du11-repair-flag`（09cb49ad，补写默认关闭开关）。
- 关键变更文件：`src/company_wiki/document_understanding/operating_states/{product_reference,relations}.py`（B2）；`src/company_wiki/automation/{narrative_summarize,execution_snapshot,execution_context,registry}.py`（补写实验）；`tools/document_understanding_benchmark/phase_c_observer.py`（相位 C 观测器）。

## 2. RED→修复→GREEN
- B2：110 项 du11 单测 PASS（`tests/unit/du11_source_closure`）；三源回放 CN 10/10、HK 7/7、US 8/8，绑定 `b2-final3-20261018`、`b2-real-sources-final2-20261018`；原件/gold 未变、0 API。
- C 工程：CN/US 各 1 次真实 POST；`activation_recovery=PASS`（同 attempt、无新增扣费）；`cross_run_zero_POST=true`；FF 复用与 RF 读取通过。
- 补写实验：离线单测覆盖 partial→repair→merge、失败回退；真实 CN 实测 2 次 POST 并进入 `activation_pending`。

## 3. t32/t34、额度与预算
- t32/t34 状态见 `objective-completeness-20261018-v2.md`；测量口径为 ledger 去重（database+attempt_id）。
- 累计：**55 个 attempt、1,074,406 tokens / $0.2709**（含 HK 69,046 tokens / $0.031208 unknown hold；上限 2M / $20）。

## 4. 独立审查
- B2 最终复审 PASS：`b2-antecedent-final-review-20261018-v3.md`。
- C 内容复审：`c-content-review-20261018-cn-v3.md`（CONTENT_FAIL，8/10）、`-cn-v4.md`。
- 交接完整性复审（2026-10-18）：CONDITIONAL_READY，发现的文本失真已在本报告与 handoff 中修正。

## 5. push 结果与 exact CI
- **未完成**：本地 master 7 个提交未推送；`origin/master` 仍是 `ccc5bc7e`（无条件补写版）。
- 唯一 exact CI：`2a80acf6`（`b2-final3-20261018/ci-39139605025.json`，success）；本地 HEAD 无 CI。
- 两个分支的 pre-push 门禁均 GREEN。

## 6. 真实 provider 与缓存/恢复
- 真实模型：CN = MiMo（`mimo-v2-flash`），US = MiniMax；HK 未跑（`DEEPSEEK_API_KEY` 401）。
- 同 run 恢复不重复扣费；跨 run 复用 0 POST；FF 复用与 RF 读取均有收据。
- 收据目录（工作区、未入 git）：`.planning/shared-reading-production/du11/live-{cn,us,hk}-*`。

## 7. 清理
- 已删除仓库根 12 个本轮遗留临时目录（b2-review2/3-*、cwpaW03-*、cwplC-*、tmp5_*、pytest-of-*）。
- 未清理：RF 旧 assurance 工作文件与 `output/`（按 handoff 要求保持原样）；`review/b2-antecedent-final-review-20261018-v3.json` 已纳入。

## 8. 仍未完成与唯一下一步
- **未完成**：本地 master 推送与 exact CI；C 内容 8/10（用户接受）；补写与 `activation-resume` 的冲突；HK 因密钥未跑。
- **唯一下一步**：在 GitHub 合并 `du11-repair-flag`（门禁 GREEN）使远端补写默认关闭；随后修两个既有失败测试（`test_fresh_cache_behavior_receipts`、`test_official_projection_shared_reading...`）再推 master。
