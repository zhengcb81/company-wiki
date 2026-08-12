# FC-1201 变更合同 — root/source hardcode 门棘轮 + 安全清理

> Owner: company-wiki。前置：FC-701 ✓、FC-1005 ✓。用户决策 Interpretation A（2026-08-12）。
> 本 FC 不动 v1 scanner、生产 config loader、写路径、生产 yaml。零生产数据变更。

## 1. 变更内容（allowed_files）

| 文件 | 变更 | 性质 |
|---|---|---|
| `src/company_wiki/source_catalog/resolver.py` | 注释去 token（L679 `default company_raw` → `default: the canonical write-root kind`） | 零行为（注释） |
| `src/company_wiki/source_catalog/observability.py` | 注释去 token（L76 示例） | 零行为（注释） |
| `src/company_wiki/source_catalog/entity_resolver.py` | docstring 去 token（L1） | 零行为（docstring） |
| `src/company_wiki/source_catalog/architecture_gate.py` | `_ROOT_HARDCODE_ALLOWED_FILES` 移除 resolver/observability/entity_resolver（3 文件）+ frozen-ratchet 注释 + backlog 分类注释 | 门收缩（棘轮） |
| `tests/contract/test_fc1201_root_hardcode_gate.py` | 新增 5 测试：ratchet frozen / cleaned files left allowlist / cleaned files token-free / gate green after cleanup / detection still works | RED→GREEN |
| `assurance/fc/FC-1201/00_wu_card.md` + 本文件 | FC 范围 + 合同 | 文档 |

## 2. 不变量

- **零生产数据写入/删除**；零 config loader / yaml / 写路径改动。
- **allowlist 只缩不涨**（frozen ratchet，新增文件 → 测试红）。
- v1 scanner（7 root 分支）= R9 backlog（生产回退，cutover 未完成）。
- canonical_writer/cli 重构 **DEFERRED**：需生产 1.x loader 接受 `canonical_write_target`（`config.py:75-84` 严格拒未知字段）→ 留 frozen allowlist，记为 FC-1201 follow-up / R9 prep。
- 门检测不弱化（M2 击杀证明：删 token → 对抗模块漏检 → 测试死）。

## 3. exit gate（Interpretation A，preflight-refined）

- 无新 root-specific hardcode（门 + 棘轮强制）✓
- 非 v1 / 非 loader-blocked hardcode = 0（resolver/observability/entity_resolver 清理后移出 allowlist）✓
- v1 + loader-blocked backlog 有界、可审计、有合同（frozen allowlist + 本卡）✓
- EX-08：新 root 仅改 config 即可（v2 adapter_dispatch 路径，`test_future_root_config_only` 保持绿）✓

## 4. 回滚

纯注释 + 门 allowlist 收缩 + 新增测试；回滚 = revert 提交。无数据/迁移。
