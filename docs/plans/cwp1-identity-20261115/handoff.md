# handoff — OWNERPKG-CWP-CANDIDATES-01（CWP-1 阿里身份候选唯一化）

- 交回日期: 2026-11-15
- owner: company-wiki
- 分支: `codex/cwp1-identity-suffix-20261115`（独立 worktree `company-wiki-cwp1-identity-20261115`）
- **release commit（40 位，供 Dashboard 消费）**: `8de23487113bc8316b45bd5c8ca6a2680be6b333`
- 机器可读版本: `handoff.json`（同目录）
- 未 push、未并入 master；Dashboard 按 commit 消费，不按分支名追踪。

## 1. 施工包目标与结论

目标：让 `Alibaba Group Holding Limited` / `BABA` / `09988` 在 CWP 身份库解析出
确定、唯一、可引用的候选，使 FF ensure 与 RF source_preparation 不再命中
`fuzzy_candidates_require_user_selection`。

**已达成**。根因不是零候选，而是两个叠加缺陷：
1. 官方名 `Alibaba Group Holding Ltd`（库）与请求 `...Limited` 的后缀差异 →
   strong_fuzzy 5 候选 → 无名 fuzzy 集（A1 后缀等价归一化，只用于比对、不改数据）；
2. `BABA` 同时精确命中 HK 别名与 US ticker → 两个 verified exact，旧 reason
   不说明如何消歧（A2 具名 reason `cross_market_dual_listing_requires_market_selection`）。

## 2. §5 验收四项

| 项 | 结论 | 关键证据 |
|---|---|---|
| §5.1 三查询解析探针 | delivered | 全称→`resolved` US BABA (`official_name_exact`)；`09988`→`resolved` HK 09988；`BABA`→`ambiguous` + 具名双上市 reason + 2 个带 market/exchange/ticker 的候选；4 个 `--market` 消歧探针全部 `resolved`。均非 fuzzy 模糊集。 |
| §5.2 FF reuse_only 联动 | delivered | 未修复 master：阿里 20-F FY2025 → `exit=2 / identity_error / fuzzy_candidates_require_user_selection`（复现施工包 §1）；修复后 → `exit=0 / source_candidate / reused_existing / download_events=0`，命中 20-F 原件 sha256 `36daec0c…`。BABA 无 market 保留为具名失败样本。 |
| §5.3 RF 六路线联动 | delivered（含具名剩余缺口） | route3 → `exit=0 / found_capture_ready`（完整来源记录 + verified_read 收据）；其余 5 条具名原因：`invalid_local_prepare_request` / `acquisition_validation_failed`，全部 `downloads=0`、`provider_started=false`。 |
| §5.4 证据与失败样本 | delivered | 每条探针 command/stdout/stderr/exit 落盘；失败样本未改写；复跑脚本与 tmp 夹具副本在 `evidence/replay/`。 |

**诚实归因（务必随交接传递）**：六路线在**未修复 master 与修复后 lane 下逐条完全一致**，
route3 两边都成功。因此 route3 的 `found+capture_ready` **不是本包身份修复的功劳**
（该路线用 `阿里巴巴－Ｗ` 精确别名 + 元数据完整的 FY2025 原件，从未撞身份歧义）；
本包**未引入** RF 回归；剩余 5 条失败是既有下游契约/元数据缺口，
不是 fuzzy/ambiguous 复发。本包唯一可归因的下游解锁是 **§5.2 的 FF 20-F identity_error 消失**。

## 3. §4 红线核验

- 未改 Dashboard 侧适配器；实现只动 `security_identity.py`、`observability.py`（纯增量
  注册 1 个 reason）与 `tests/contract/test_source_catalog_security_identity.py`。
- 未动既有已登记实体、未删除任何候选数据；`schema_version` / identity schema 未改。
- `BABA` 无 market 保持 `ambiguous` 是刻意保留的 fail-closed 语义：不静默选边，
  但 reason 具名且候选可引用，请求可用 `--market`/`--exchange` 显式选定。
- 浏览态 0 下载 / 0 模型 / 0 网络：所有 FF/RF 证据 `downloads=0`、`provider_started=false`。
- 生产配置 `config/source_catalog.yaml`、`config/company_wiki.json` 零改动；
  联动探针用 tmp 夹具（AGENTS.md R4.1 合规）。
- 独立分支 + 独立 worktree；每次提交前核分支；未 push、未并入 master。

## 4. §8 三要求状态

- **§8-1 独立重审**：`INDEPENDENT_REVIEW.md`，`reviewer_status=approved`，
  **0 OPEN P1/P2**；4 条 P3 全 CLOSED（F-R4 汇总字段口径 / F-R5 主探针命令文件 /
  F-R6 run.log 中间态 / F-R7 handoff SHA）。F-R5 已补实（7/7 命令文件齐全），
  F-R7 由本 handoff 的 40 位 SHA 闭环。P3 随本 handoff 交回。
- **§8-2 PWF**：`task_plan.md`（节点 1-11 全 done）、`progress.md`（每节点一行）、
  `findings.md`（F-01…F-06、NOT_RUN、§8-3 交接任务）。
- **§8-3 并线**：走**情形 2「不能并线 → 明示交接」**（见 §5）。

## 5. §8-3 显式并线交接任务

> `OWNERPKG-CWP-CANDIDATES-01` 分支 `codex/cwp1-identity-suffix-20261115`
> release commit `8de23487113bc8316b45bd5c8ca6a2680be6b333` 已通过独立重审
> （0 OPEN P1/P2）。**待主工作区在途 PWF（module-pwf-reconciliation-2026-11-14）收口、
> 且 `codex/ff1-catalog-repair-20261115` lane 的 B4 并入或确认不冲突后**，
> 由 **company-wiki 主线 owner（操作者）** 执行并线，并在 PWF `progress.md` 记录
> 并线 commit 与回归结果。Dashboard 侧在此之前按上述 40 位候选 commit 消费。

不强行并线的原因：主工作区有他人在途 WIP，且与另一条在途 lane 尚未收口；
强行 merge 会与在途 WIP 互踩，违反 §4 红线。

## 6. 交回路径（施工包 §6）

1. 本 handoff（含 40 位 release commit）→ 操作者。
2. Dashboard D00 侧重跑阿里 FF drill 与 RF 六条采集路线，按 commit 消费。
3. 阿里解锁后通知 m5 / RF `INPUT-AUTHOR-01` 的 Alibaba 半边继续。
4. 剩余 2 类下游缺口分别派工（**注意：不是身份缺口，不要退回本包**）：
   - **FF owner**：`ff_local_source_prepare.py` 把 `identity_scope` / `issuer_link_id`
     与 `schema_version="1.0"` 一起发给 CWP，而 CWP `resolver.py:591` 要求 identity
     scope 字段使用 schema `1.1`。修 FF 侧契约或协商 schema 版本。
   - **CWP FF1 lane**：`ensure` 的 `acquisition_validation_failed` /
     `local_metadata_incomplete`，属目录层元数据缺口（CWP-2 范围）。

## 7. 提交链

| SHA | 说明 |
|---|---|
| `7fa16a213` | A1 公司后缀等价归一化（含词边界修正与全库差分） |
| `7595473f2` | A2 跨市场双上市歧义具名 reason |
| `a311c3127` | PWF 收尾 |
| `8cdff1e5e` | F-01 勘误：枚举身份相关测试选集 |
| `4b0fc3fe5` | §5 四项验收证据 + PWF 节点 6-9 |
| `8de234871` | 独立重审报告 + F-R5 证据闭环 + PWF 节点 9b/10/11 |

基线 `ac8841c55`（master HEAD @ 开工）。全部提交在 lane 分支，线性、无 merge、
只含本包写域内文件。

## 8. 证据索引

`evidence/README.md` 为总索引；`evidence/baseline-master/`（未修复 master 对照）、
`evidence/rf-routes/`（修复后六路线）、`evidence/rf-routes-master/`（六路线归因对照）、
`evidence/replay/`（复跑脚本与 tmp 夹具副本）。证据全量落盘，未裁剪。
