# FC-1201 WU 卡片 — root/source hardcode 清零（AST 门 + 安全清理，v1 延后 R9）

> 创建 2026-08-12。Owner: company-wiki。前置：FC-701 ✓ accepted、FC-1005 ✓ accepted。无 execution lock。
>
> 用户决策（2026-08-12）：**Interpretation A** — 门禁棘轮 + 安全清理，v1 scanner 延后 R9（bounded backlog）。符合 code_quality_plan §3 step7「关桥后才删 legacy 代码」。

## 1. 范围锁定（preflight 后）

FC-304 已建 `no_root_specific_hardcode` 门（substring 匹配 4 token：`dropbox_stock`/`company_raw`/`dayu_portfolio`/`Dropbox`），但：
- **门在 contract 层无测试**（`tests/contract/test_architecture_gate.py` 不调用它）— FC-1201 补。
- allowlist 显式白名单了「documented FC-1201 backlog」文件 — 需冻结为 R9 bounded 合同。
- resolver.py 已清（FC-701 用 `config.reusable_root_kinds`，无行为分支）— 可移出 allowlist。

### 真实 hardcode 地貌（preflight 实测）

| 文件 | token 使用 | FC-1201 处置 |
|---|---|---|
| `scanner.py` | v1 行为分支 ×7（L170/181/283/377/452/981/984） | **R9 backlog**（v1 生产回退，cutover 未完成：legacy_bridge_hits=6，v2 flags OFF） |
| `canonical_writer.py` | Python L126（写根选择 `kind=="company_raw"`）+ SQL L283（dedup `r.kind='company_raw'`）+ 注释/错误信息 | **DEFERRED（loader 阻塞）**：生产 1.x loader `config.py:75-84` 的 `allowed_root_fields` 不含 `canonical_write_target` 且严格拒未知字段 → 加 yaml label 会 CatalogConfigError。重构需同时改 loader（生产 config 加载路径）+ yaml + 写根选择 + 可能级联破坏未设 target 的测试 fixture。超出「安全清理」范围 → 留 frozen allowlist，记为 FC-1201 follow-up / R9 prep 合同。 |
| `cli.py` | L1251 portfolio 根查找 + help 文本 | **DEFERRED（同上）**：按身份引用特定根（同 `admission.py` FOCUS_ROOT_ID），literal 内禀；留 frozen allowlist 记理由。 |
| `models.py` | `ROOT_KINDS` enum owner（L39/107/176） | **保留**：合法 kind enum 单一来源 |
| `portfolio_promoter.py`、`backfill_v2.py` | v1 legacy 工具 docstring/CLI default | **R9 backlog** |
| `admission.py`、`focus_cleanup.py` | Dropbox canary（`dropbox_stock`/重点关注，FC-501） | **保留**：文档化 root-specific canary 机制 |
| `resolver.py`（L679 注释）、`observability.py`（L76 示例）、`entity_resolver.py`（L1 docstring） | 仅注释/docstring 提及 | **改写注释** → 移出 allowlist（零行为变更） |

## 2. 交付物（preflight-refined：safe core；canonical_writer/cli DEFERRED）

1. **注释清理**（零行为变更）：resolver.py:679 / observability.py:76 / entity_resolver.py:1 去掉 4-token 注释/docstring 提及 → 三文件移出 allowlist（real shrink）。
2. **门 contract 测试**：`no_root_specific_hardcode` 被 contract 测试钉住（现存于 `test_future_root_config_only.py`，FC-1201 显式断言 cleanup 后仍 ok）。
3. **棘轮测试**：`_ROOT_HARDCODE_ALLOWED_FILES` 冻结为精确集合（post-cleanup）；新增文件 → 测试红 → 强制 review。精确 pin：增删都需更新测试（= deliberate review）；shrink 鼓励。
4. **EX-08 再证**：frozen+ratcheted 门下 future-root config-only 仍通过（`test_future_root_config_only.py` 现有断言 + allowlist 收缩后保持绿）。
5. **R9 backlog 合同**：剩余 allowlist（scanner/models/portfolio_promoter/backfill_v2/admission/focus_cleanup/canonical_writer/cli）= bounded v1 cutover + loader-blocked backlog，门注释 + 本卡记录。
6. **DEFERRED 项合同**：canonical_writer（写根选择按 canonical_write_target）+ cli（portfolio 根查找）需生产 loader 改动，记为 FC-1201 follow-up（或并入 R9 prep），本 FC 不动生产加载路径/写路径/config。

## 3. exit gate 判定（Interpretation A，preflight-refined）

- 无**新** root-specific hardcode（门 + 棘轮强制）✓
- 非 v1/非 loader-blocked hardcode = 0（resolver/observability/entity_resolver 清理后移出 allowlist）✓
- v1 + loader-blocked backlog 有界、可审计、有合同（frozen allowlist + 本卡）✓
- EX-08：新 root 仅改 config 即可（v2 adapter_dispatch 路径）✓
- **不触碰** v1 scanner（生产回退）、不删 legacy（R9）、不动生产 config loader/write path/yaml（零生产风险）。

## 4. TDD 步骤

1. RED：`tests/contract/test_fc1201_root_hardcode_gate.py`
   - 门 contract：`no_root_specific_hardcode()` ok。
   - 棘轮：allowlist == 冻结集合（post-cleanup）。
   - canonical_writer：选根按 `canonical_write_target`（无 token root → CanonicalImportError；有 → 写根正确）。
   - EX-08：future-root config-only 在门下通过。
2. GREEN：canonical_writer 重构 + config label + 注释清理 + allowlist 收缩 + 棘轮。
3. MUTATION：M1（canonical_writer 回退到 kind 选择）→ 测试死；M2（allowlist 新增文件）→ 棘轮死；M3（门 token 列表删）→ EX-08 死。
4. 全量 wiki 套件零新失败（pre-existing 2×PORT-01 除外）。
5. schema-2.0 implementer receipt → 干净 worktree 独立 reviewer（F-6 规则：base 复现用第二 worktree）。

## 5. 不变式

- 零生产数据写入/删除；config 仅加声明式 `canonical_write_target`（可逆）。
- 不动 v1 scanner/legacy bridge（R8/R9 范围）。
- allowlist 只缩不涨。
- 「绝不伪造」：门必须真阻断新 hardcode；棘轮必须真冻 allowlist。
