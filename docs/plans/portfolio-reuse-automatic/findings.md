# 研究发现 — portfolio 复用"已提交但不生效"的根因（深入调查）

调查日期：2026-08-04
关联：`../portfolio-reuse-fix/`（手动桥接方案，commit 7ce2774 已提交）；本文件记录
"为什么已提交的功能不生效"的完整证据链，以及系统化改进的落点。

---

## 发现 1：功能已实现并已提交，机制本身有效

- commit `7ce2774`（2026-08-03）`feat(source-catalog): promote dayu-portfolio filings to company_raw for reuse`：
  `portfolio_promoter.py`、`cli.py import-portfolio`、`canonical_writer._write_provenance`（G1 修复）、
  8 项测试、ADR-007、OPERATIONS.md §一点五。
- 金山云 7 份财报提升成功；提升后 filing-fetch 只读复用零下载（8-03 验证）。
- 本机实测：`import-portfolio --dry-run` 对 6082 能找到文档并返回 dry_run —— 发现/映射逻辑正常。

## 发现 2：全系统无任何自动调用点 —— "孤儿"手动命令（第一层根因）

穷尽搜索（src/ 全部 .py + filing-fetch/scripts/）：
- `promote_from_portfolio` / `promote_all_for_entity` **只被 `cli.py` 的 import-portfolio 命令处理器调用**。
- worker 管线阶段：SCANNING → NORMALIZING → FINGERPRINTING → LLM → EXPORT，**无提升阶段**。
- `acquisition_service.ensure()` / `acquisition.py`：**零 portfolio/promotion 引用**。
- `filing-fetch` 脚本（fetch_filing.py / filing_fetch_client.py）：**零 import-portfolio 引用**。
- resolver：`company_raw_root_ids` 过滤保持原样（fail-closed 未削弱）。

⇒ 已提交的修复是一个**只有人类（或按 OPERATIONS.md 手工操作）才会触发的 CLI 命令**。
任何自动流程（revenue-forecast → filing-fetch → ensure → dayu）都永远不会经过它。
"已提交"≠"已生效"：提交交付的是**能力**，不是**流程**。

## 发现 3：手动调用也会被 worker 的 catalog 锁挡住（第二层根因）

- `import-portfolio`（非 dry-run）→ `import_staged` → `CatalogOperationLock(operation="canonical_import")`，
  要取全局 `operation.lock`。
- 实测（三次）：`CatalogOperationLockedError pid=1980`、`pid=23160`、暂停恢复后再跑仍失败。
- **无 pause-around、无锁重试**——与 filing-fetch v1.4.0 的 `PausedWorkerScope` 形成对比。
- 8-03 金山云验证之所以通过，是因为 spike 期间**手动 `worker-pause`**（progress.md 有记录）。
- `--dry-run` 能过是因为不写盘、不取锁。

⇒ 在本机（worker 几乎永远在跑 ~2 万文档回填批）上，import-portfolio 的**真实执行在常见场景下必然失败**。

## 发现 4：端到端期望在架构上从未成立（第三层根因）

- 原计划（Strategy A）刻意"filing-fetch 零改动"，把 import-portfolio 定义为**手动、每公司一次性**桥接。
- 因此"filing-fetch 自动跳过 dayu 已下载文档"这一用户期望的端到端行为**从未被接线**：
  获取路径（resolve 只认 company_raw）对 portfolio 的存在一无所知，也没有任何环节会触发提升。

## 发现 5：系统化修复的正确落点

- **自动提升应发生在 company-wiki 的 `ensure`（acquisition service）内**：resolve 返回 MISSING
  且显式 `--allow-download` 时，在路由到 adapter（dayu/cninfo）**之前**，先查 dayu_portfolio 是否有
  匹配文档（identity + document_kind + fiscal_year + as_of_date），有则经 `import_staged` 提升并返回
  canonical source（零下载）；无则维持现状走 adapter。
- **单一集成点**：所有走 ensure 的消费者（filing-fetch 及下游 skill）自动获益；filing-fetch 保持零改动
  （延续 Strategy A 的"主仓库=company-wiki"原则，但行为从手动变自动）。
- **锁健壮性**：filing-fetch v1.4.0 的 `PausedWorkerScope` 已包裹 ensure → 自动提升在 filing-fetch 路径下
  免费获得锁保护；直接 ensure CLI 调用者与手动 import-portfolio 仍需处理锁（见 task_plan Phase 2）。
- **不变量全部保留**：companies/ 子树、不可变 sidecar、单一写者（import_staged）、
  "仅 company_raw 可复用"的 fail-closed 语义（只读 resolve 永不提升）。

## 证据位置速查

| 事实 | 证据 |
|---|---|
| 功能已提交 | `git show 7ce2774`（portfolio_promoter.py / cli.py / tests / ADR-007 / OPERATIONS.md） |
| 无自动调用者 | `grep -rn "promote_from_portfolio\|promote_all_for_entity" src/` → 仅 cli.py |
| worker 无提升阶段 | worker.py 阶段序列 SCANNING/NORMALIZING/FINGERPRINTING/... |
| ensure 无 portfolio 钩子 | acquisition_service.py / acquisition.py grep portfolio = 0 |
| import-portfolio 撞锁 | 实测 `CatalogOperationLockedError pid=1980/23160` |
| 提升机制有效（金山云） | portfolio-reuse-fix/progress.md Phase 1-3 验证记录 |
| 6082 dry-run 正常 | 实测 import-portfolio --dry-run → dry_run 状态 |
