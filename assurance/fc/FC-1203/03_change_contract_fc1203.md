# FC-1203 变更合同 — 模块边界和 API 收敛（Interpretation A，findings 59 修订版）

日期：2026-08-12。Owner: company-wiki（本 FC 单仓；三仓中的 revenue/filing 侧 API 收敛已在 findings 59 核实为「无需修改」）。

## 1. 已删除（dead-helper=0，全部 AST+grep 验证零生产调用者）

| 符号/文件 | 验证证据 | 处置 |
|---|---|---|
| `validate_normalized_filing`（normalized_meta.py:57） | 零调用者、零测试（`canonical_hash` 保留——assertion_service/remediation 生产使用） | 删函数 |
| `entity_resolver.py` 整模块 | 零生产 import；唯一测试 import = test_entity_resolver.py | 删模块 + 删测试 |
| `atomic_rollback`（flags.py:59） | 唯一非测试调用者 = wu905 一次性脚本（不入 CI、无 receipt 引用）；被 activation.py 事务替代（FC-203） | 删函数 + 删 test_rollback_drills.py + 删 scripts/wu905_catalog_switch_check.py + 删 test_policy_and_flags 中 2 个 atomic 用例 |
| `reuse_latest_policy.py` 整模块 | 零生产 import；close_gap.py 自带 gap_hash policy binding（L217/323）+ 自有测试（test_close_gap_fc801/804） | 删模块 + 删 test_latest_gap_closure.py + test_coop_scenario.py |

门测试：`tests/contract/test_fc1203_dead_helpers_absent.py`（模块不可导入 / 属性不存在 / 文件不存在三断言）——复活任一 → 红。

## 2. 预检时误列、核实后**保留**（防误删合同）

| 符号 | 核实结论 | 保留理由 |
|---|---|---|
| `evaluate_candidate`（admission.py:244） | 零生产调用者，但 `evaluate_admission` 是 Dropbox focus-only 专用入口，**不构成替代**；ADM-01..10 不在 95 强制场景 | **Phase 14 R3/R5 未接线政策**：sealed FC-502 契约测试（test_sidecar_production_scan_fc502.py）与 test_dbx_fixture_e2e.py 承重。生产接线属发布波次，不在 FC-1203 删 |
| `restore.py` 整模块 | `restore_asset` gates 被生产 remediation 工具 `scripts/wu904_remediation_restore.py` 真实调用（用户批准的执行器，FC-403 review 链条引用） | **有真实生产调用者**——REST-01..06 政策门 + 审计回执。store.restore_document 是存储原语，不构成替代 |
| `validate_flag_state`（flags.py:41） | runtime_policy.py:24 生产调用（flags 快照校验） | 生产使用，保留 |

## 3. extractive summarizer 注册裁决（findings 45/59 关闭）

- 事实：`summarize_catalog` 有生产入口（SourceCatalog.summarize → CLI summarize + run pipeline），但产物三重缺陷永不可绑定（schema_version 列 NULL、generator 未注册、created_at 非 ISO-Z）。
- 裁决：**注册不删**（有生产入口）。交付：GENERATOR_REGISTRY + `source_catalog_extractive_summary`；INSERT 写 schema_version 列 + metadata 双写 + `strftime('%Y-%m-%dT%H:%M:%SZ','now')`（与 llm_summarizer FC-906-a 同构）。
- 效果：既有生产 CLI 的产物从「必然 rejected」变为「可绑定」。生产 catalog 无该 generator 存量行（FC-906 preflight：235 空 generator_name 行为旧版遗留，非本 generator），无需回填。

## 4. 不变式

- 零生产数据写入/删除；worker 无需重启（本次未改 worker 调用的 producer 写路径；summarize 由 CLI/run 按需调用）。
- 保留项的「未接线」状态是发布波次（R2-R5/R9）资产，非 FC-1203 缺口——已在本合同登记，FC-1502 对抗审查可复核。
- 删除即永久：rollback = revert commit。
- 「绝不伪造」：删除依据 = 机器证据（grep 交叉验证 CodeGraph 索引 gap），不凭印象。
