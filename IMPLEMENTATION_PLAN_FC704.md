# FC-704: ResolutionEnvelope + AcquisitionTrace（outcome/journal 对账；伪 download_calls 必死）

Plan: FCAP-2026-08-09-r2 task_plan Phase 7 FC-704. Owner: company-wiki（跨三仓）。

## 问题

1. resolve CLI 只返回 ResolutionResult（status/reason/matches/debug_trace），无 policy/epoch、
   无 journal 对账 outcome、无 bundle 状态。
2. revenue `scripts/source_preparation.py:99` 的 reuse_receipt 用
   `"download_calls": 0 if handle else 1` —— 由 handle 是否存在倒推下载计数
   （scenario_matrix §2 禁止：计数必须来自事件/journal，不得由结果倒推）。
3. taxonomy 未对账：journal（reused_before_download/reused_after_discovery/downloaded_new/...）
   与 plan 的（reused_existing/reused_after_discovery/downloaded_new/gap/ambiguous/rejected）之间无映射层。

## 设计

- **company-wiki**：`ResolutionEnvelope`（resolver.py）+ `build_resolution_envelope(resolution, policy_snapshot, journal)`
  纯函数。outcome = journal[request_id].outcome（存在时）否则结构性映射
  （REUSED→reused_existing、AMBIGUOUS→ambiguous、MISSING→missing、IDENTITY_CONFLICT→rejected）；
  download_events = 1 iff journal outcome ∈ {downloaded_new, deduplicated_after_download} 否则 0；
  policy_hash/activation_epoch 来自 RuntimePolicySnapshot（无快照则 None）；
  bundle_status="unavailable"（显式，FC-901 前不得伪造空绿色）。
  CLI resolve 与 ensure 的 resolution 子 dict 均附加 `resolution_envelope`。resolve 保持零写
  （journal 只读）。
- **filing-fetch**：`validate_resolution_envelope`（schema/outcome taxonomy/download_events∈{0,1}/
  bundle_status 枚举）；`resolve_filing` 把 envelope 证据原样附加到返回的 handle 上
  （`handle["resolution_envelope"]`，N/N-1：上游无 envelope 时不伪造）。
- **revenue**：reuse_receipt 从 envelope 证据构建（download_calls = envelope.download_events），
  envelope 缺失/非法 → fail closed（raise，绝不静默 0）。receipt 同时记录 outcome/policy_hash/
  activation_epoch/bundle_status。旧 "0 if handle else 1" mutation 必死。

## 场景

- ENV-01~08（company-wiki T0）：结构性 outcome 映射、journal 对账（downloaded_new→1、
  reused_after_discovery→0）、policy/epoch 转发、bundle_status 显式 unavailable、
  to_dict 确定性、resolve 零写（journal 文件不变）。
- ENV-09~12（revenue）：download_events=1→download_calls=1（旧规则给出 0，mutation 必死）、
  download_events=0→0、envelope 缺失 fail closed、receipt 携带证据字段。

## Stage

### Stage 1: company-wiki envelope（resolver.py + cli.py + tests）
**Goal**: ResolutionEnvelope + build_resolution_envelope + CLI resolve/ensure 附加。
**Success Criteria**: ENV-01..08 green；resolve 命令仍零写；ruff clean。
**Tests**: tests/contract/test_resolution_envelope_fc704.py
**Status**: Not Started

### Stage 2: filing-fetch 转发与校验（filing_contracts.py + fetch_filing.py + tests）
**Goal**: validate_resolution_envelope + resolve_filing 转发 envelope 证据。
**Success Criteria**: 校验测试 green；旧 payload（无 envelope）N/N-1 不破坏。
**Tests**: tests/test_fetch_filing.py 追加
**Status**: Not Started

### Stage 3: revenue 回执修复（source_preparation.py + tests）
**Goal**: reuse_receipt 从 envelope 证据构建；缺失 fail closed；旧 mutation 必死。
**Success Criteria**: ENV-09..12 green；全量 revenue suite green。
**Tests**: tests/test_source_preparation.py 追加
**Status**: Not Started

### Stage 4: closure
**Goal**: 三仓全量 suite、ruff、receipt 密封、独立 review。
**Status**: Not Started
