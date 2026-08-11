# FC-801: CloseGap transaction contract（DL-02/03/07/09、LT-10；事务 journal）

Plan: FCAP-2026-08-09-r2 task_plan Phase 8 FC-801. Owner: company-wiki。

## 问题

WU-4.2（GapPlan）+ WU-4.3（DownloadAuthorization）已存在；coordinator 有完整 staging 路径。
缺口（FC-801）：
1. 无固定步骤的 close-gap 事务（输入绑定 → gap/policy 重验 → fetch staging → validate →
   canonical commit → scan/assert → re-resolve）；partial failure 无显式 journal 状态。
2. DownloadAuthorization 缺少 **policy_hash** 绑定（DL-03：stale policy hash → fetch=0）。
3. DL-07（staging 无效 → 不 commit + 可审计清理）、DL-09（中断后幂等恢复）、LT-10（部分失败
   不得谎报 complete）无事务级测试。

## 设计

新模块 `src/company_wiki/source_catalog/close_gap.py`：

- `CloseGapBinding`：request_id、gap_plan_hash、policy_hash、provider、allowed_accessions、
  max_items、max_bytes、expires_at（输入绑定契约）。
- `DownloadAuthorization` 增加 `policy_hash` 字段（receipt hash 纳入；DL-03）。
- `CloseGapTransaction.execute(binding, request)` 固定步骤：
  1. **policy 绑定检查**（DL-03）：当前 runtime policy 的 policy_hash ≠ binding.policy_hash
     → rejected stale_policy_hash，fetch=0。
  2. **gap 重验**（DL-03）：rediscover（metadata only，latest_as_of 路径）→ 当前 gap_hash ≠
     binding.gap_plan_hash → rejected stale_gap_hash，fetch=0。
  3. **fetch staging**（DL-02）：coordinator.resolve_or_stage + authorization；过期/错授权
     → rejected（精确 reason），fetch=0。
  4. **validate**（DL-07）：receipt bytes/hash/sidecar 非法 → 不 commit；staging 目录清理
     （可审计：记录 staged 路径 + 清理结果）；catalog 不变。
  5. **canonical commit**（DL-09）：writer.import_staged（content_sha256 幂等去重）。
  6. **scan/assert + re-resolve**：writer 已做；最终 SourceResolver 重解析 → FC-704 envelope
     （outcome 从 journal 对账）。
- 事务 journal：复用 acquisition journal（outcome 固定集），每步失败 → `failed` + error_type/
  reason + txn_id；成功 → 真实 outcome（downloaded_new / deduplicated_after_download /
  reused_before_download）。重启重跑安全（幂等）。
- LT-10：结果只有 re-resolve 找到文档才报 complete；任何失败 → 显式 rejected/partial 状态。

## 场景（tests/contract/test_close_gap_fc801.py）

- CG-01（DL-03）：policy hash 过期 → rejected stale_policy_hash，fetch=0。
- CG-02（DL-03）：gap hash 过期（provider 已发布新版本）→ rejected stale_gap_hash，fetch=0。
- CG-03（DL-02）：授权过期/错 accession → rejected，fetch=0，reason 精确。
- CG-04（DL-07）：staging receipt 非法（bytes 不符）→ 不 commit、staging 清理、catalog 不变。
- CG-05（DL-09）：commit 后重跑 → 幂等：reused（无重复文档/位置），outcome reused_before_download。
- CG-06（LT-10）：adapter fetch 抛错 → failed 状态 + txn 可重跑；绝不报 complete。
- CG-07：成功路径：downloaded_new → re-resolve REUSED_EXACT → envelope outcome downloaded_new、
  download_events=1。
- CG-08：authorization receipt hash 纳入 policy_hash（绑定不可变）。

## Stage

### Stage 1: authorization policy_hash（authorization.py + 现有测试更新）
**Status**: Not Started

### Stage 2: close_gap.py + tests（RED → GREEN）
**Status**: Not Started

### Stage 3: CLI close-gap 命令（入口契约）
**Status**: Not Started

### Stage 4: closure（全量 suite、receipt、review）
**Status**: Not Started
