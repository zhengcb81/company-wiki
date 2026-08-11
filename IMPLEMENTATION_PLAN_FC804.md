# FC-804: 并发、重试和恢复（single-flight、崩溃恢复、幂等）

Plan: FCAP-2026-08-09-r2 task_plan Phase 8 FC-804. Owner: company-wiki/filing。

## 问题

close-gap 事务的 FETCH 在 CatalogOperationLock 之外——两个并发相同 close-gap 会双重 fetch
（DL-08：最多一次 provider fetch + 一次 canonical commit）。可重试 adapter 失败无有界重试
（OPS-02）。崩溃后恢复依赖 writer 幂等（DL-09 ✓ 已有，需测试钉住）。

## 设计

1. **single-flight（DL-08）**：close-gap execute 的 step 3（fetch）之前获取
   `catalog_dir/close_gap_locks/<txn_id>.lock` 的跨进程文件锁（复用 lock._acquisition_mutex 模式）；
   锁内**重新验证 gap**——第一个调用者可能已关闭 gap → 直接 `_complete_reused`（fetch=0）；
   否则 fetch + commit。锁超时 → 有界失败（CatalogOperationLockedError → failed，调用者可重试）。
2. **有界重试（OPS-02）**：staging 调用对 retryable 错误（AdapterProcessError.retryable 或
   provider_unavailable）最多重试 3 次（backoff 1s/2s）；非 retryable 立即失败。
3. **崩溃恢复（DL-09）**：writer 按 content_sha256 幂等去重 + journal 可重建 outcome；
   新增并发/重跑测试钉住。

## 场景（tests/contract/test_close_gap_concurrency_fc804.py）

- CG-C1（DL-08）：两个真实子进程并发执行同一 binding（spy fetch 慢 0.5s）→ spy log 恰 1 次 fetch；
  两进程都 exit 0（一个 downloaded_new、一个 reused/gap-closed）。
- CG-C2（OPS-02）：spy 前 2 次 fetch 返回 retryable 错误、第 3 次成功 → 事务重试后 completed。
- CG-C3（DL-09）：运行一次后再运行 → reused、无重复文档（幂等）。
- CG-C4：锁超时（短超时 + 慢 fetch）→ failed（有界失败，可重试）。

## Stage

### Stage 1: single-flight + 有界重试（close_gap.py）
**Status**: Not Started

### Stage 2: spy 扩展（SPY_ADAPTER_SLEEP/RETRYABLE）+ 并发测试
**Status**: Not Started

### Stage 3: closure（全量 suite、receipt、review）
**Status**: Not Started
