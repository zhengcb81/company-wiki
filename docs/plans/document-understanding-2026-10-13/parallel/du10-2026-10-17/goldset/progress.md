# DU10-CWP-SUMMARY-GOLDSET — 进度（progress）

## 2026-10-17

- [x] worktree 建立：`C:/Users/郑曾波/Projects/company-wiki-du10-summary-goldset`，
  分支 `codex/du10-cwp-summary-goldset`，基线 `900dbf6489f3b995a0bfb7fcbb8a001a68df241d`。
- [x] A 节点：缺口盘点完成（对照 29 个既有 DU-Gold sample、DU2 families/facets 约定、
  摘要合同六类错引）。冻结 11 个 case / 10 份唯一原件，全部本地存在、文本可提取、
  SHA 已算。收据 `receipts/node_a_freeze.json`；缺口矩阵 `findings.md` §1。
  先用（prior-use）逐公司核查完成（fresh×2、元数据-only×2、同公司不同原件×7）。
- [x] B 节点：`cases/`（11 case + index，schema `du10-summary-goldset-case/1`）、
  `tests/`（结构校验 58 项 pytest + 只读锚点核对工具）完成。
  - 结构测试 58 passed（0.95→2.6s，离线，0 网络模型）。
  - 锚点核对 11/11 PASS（SHA+mtime+118 anchors 回放）。
  - 施工中修正 3 处（见 `receipts/node_b_tests.json` fixes_during_node_b）。
- [ ] C 节点：独立 agent 实读复核。
- [ ] 终审 + handoff。

## 环境与卫生

- 原件只读：全部读取走 PyMuPDF/BeautifulSoup 只读抽取；verify 工具核对 mtime 前后不变。
- 机内 bindings 在 `~/.du10-goldset/bindings.local.json`（两仓之外，不提交）。
- 测试零外部夹具：pytest 收集只读本卡 JSON；无 owned temp 残留待清理（无写测试）。
- `catalog.db` 观察为空库（只读查询零表）；未触碰任何配置/生产目录。
