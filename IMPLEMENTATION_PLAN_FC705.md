# FC-705: legacy bridge 观察与关闭条件（真实 seam、双窗口门、可回滚）

Plan: FCAP-2026-08-09-r2 task_plan Phase 7 FC-705. Owner: company-wiki。

## 问题

WU-1500 已有：observer seam（_source_metadata 可选 observer）、freeze gate、rollback 演练、period ledger。
缺口（FC-705）：
1. observer 用 store facade 直调 `_source_metadata`，不是**真实 resolver seam**（SourceResolver.resolve
   请求路径）；不能证明 "所有 active request 不命中 bridge"。
2. period ledger 无机器可验的**两个>=24h zero-hit 窗口**关闭门。
3. 无 bridge-off drill 测试（flag off → fail closed、v2 请求仍 REUSED_EXACT、observer 静默；rollback 恢复）。

## 设计

- **真实 seam 观察**：`scripts/legacy_observer.py` 升级为通过 `SourceResolver(catalog, observer, runtime_policy=snapshot)` 解析
  canary request matrix（CN 601899 FY2024/25、HK 03690 FY2024、US AAPL FY2025 + 全部 16 个 active assertion 请求），
  逐请求 status + legacy_bridge_hits。两种模式：
  - 当前态（production 快照原样）：诚实计数（今天 flag v2_resolve_active=False → hits>0 → 门不开）。
  - cutover 演练（v2_resolve_active=True + pinned epoch/cohort + bridge off）：canary 全部 REUSED_EXACT、hits=0
    → 证明 cutover 就绪。只读（mode=ro）。
- **双窗口关闭门**：`close_gate_allowed(periods)` — 连续两个周期各 hits=0 且时长>=24h → 允许关闭；否则 not allowed
  （含原因）。period ledger 写真实 started_at；新周期开始时旧周期记 ended_at。
- **bridge-off/close/rollback drill tests**（T0 fixture）：
  - leg07 bridge off → legacy 容器不读 + observer 静默（fail closed）。
  - leg08 v2 reader + bridge off → active assertion 请求 REUSED_EXACT、零 hit（cutover 演练 T0）。
  - leg09 rollback：flag 恢复 on → legacy 容器可读（行为恢复）。
  - leg10 close_gate_allowed 验证：双窗口 0-hit/>=24h → allowed；单窗口、hits>0、<24h → not。
  - leg11 canary 观察模式：逐请求 status + hits，只读（fixture catalog）。

## Stage

### Stage 1: close gate + period ledger（resolver 旁新模块或 observability）
**Goal**: `close_gate_allowed` 纯函数 + ledger 时间戳语义。
**Success Criteria**: leg10 green；ruff clean。
**Status**: Not Started

### Stage 2: real-seam observer（scripts/legacy_observer.py）
**Goal**: SourceResolver.resolve 路径观察 canary matrix；当前态 + cutover 演练两模式；只读。
**Success Criteria**: leg11 green；对真实 catalog 只读运行（mode=ro）；ledger 写入独立 audit 文件。
**Status**: Not Started

### Stage 3: bridge-off/rollback drill tests（tests/contract/test_legacy_observation.py 扩展）
**Goal**: leg07/08/09。
**Success Criteria**: green；mutation（去掉 bridge-off fail-closed）必死。
**Status**: Not Started

### Stage 4: closure（全量 suite、receipt、review）
**Status**: Not Started
