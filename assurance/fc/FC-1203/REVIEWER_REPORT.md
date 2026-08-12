# FC-1203 独立评审报告（reviewer-fc1203-independent）

- 评审日期：2026-08-12（UTC `2026-08-12T22:14:31Z`）
- 裁决：**ACCEPTED**（零阻塞发现）
- 实施者：honest-implementer（Hermes Agent）
- 评审环境：全部重放于干净 git worktree（F-6 规则）：
  - `C:/Users/郑曾波/Projects/.fcap-review/fc-1203/result-wiki` @ `460d2730719acb6e4fdf59886c568c847d10d028`
  - `C:/Users/郑曾波/Projects/.fcap-review/fc-1203/base-wiki` @ `a6937f34081cdc928704d511e0b011f71b061a90`
  - 主 checkout（company-wiki / revenue-forecast / filing-fetch）全程未做任何 `git checkout <rev> -- <paths>`；所有变更/回退均为文件级操作（`git show >`、reverse edit、`rm`），结束后两 worktree `git status --porcelain` 均为空。

## 1. 提交与 diff 核验（step 1）

wiki `fcap` 分支 FC-1203 序列（4 个提交，任务清单列出 3 个 + 1 个未列出的 comment 提交）：

| 提交 | 说明 | 评审结论 |
|---|---|---|
| `f58b52e` | feat: dead-helper=0 删除 + extractive 注册 | 16 文件 +267/-850，与描述逐项吻合 |
| `c91b066` | docs: gate allowlist 注释（architecture_gate.py 3 行） | **任务清单未单列此提交**，但其内容（architecture_gate.py comment note）在预期变更清单第 1 条内；纯注释，无代码变更。非阻塞，记录在案 |
| `90102c2` | test: FC-906-b 守卫修订 + 合同 Addendum | 2 文件 +22/-2，与描述吻合 |
| `460d273` | docs: implementer receipt sealed | 仅新增 `11_implementer_receipt.json`，docs-only |

逐提交全量 diff 已审。结论：

1. **删除项**：`validate_normalized_filing`（normalized_meta.py，-81 行）、`entity_resolver.py`（-64）、`reuse_latest_policy.py`（-51）、`flags.atomic_rollback`（-19）、`scripts/wu905_catalog_switch_check.py`（-285）、tests：`test_entity_resolver.py`（-66）、`test_latest_gap_closure.py`（-102）、`test_coop_scenario.py`（-57）、`test_rollback_drills.py`（-98）；`test_policy_and_flags.py` 移除 atomic_rollback import + 2 用例；`test_fc1201_root_hardcode_gate.py` 将 entity_resolver.py 从 token-free 读取循环移除（注释说明删除是最强 token-free）。全部与任务描述一致。
2. **注册项**：`source_bundle.py` GENERATOR_REGISTRY + `source_catalog_extractive_summary: {SUMMARIZER_VERSION}`（+4 行，含注释）；`summarizer.py` INSERT 扩为 16 列（+schema_version、source_sha256），created_at 改 `strftime('%Y-%m-%dT%H:%M:%SZ','now')`，ON CONFLICT DO UPDATE 同步新列，metadata 双写 schema_version。**列数/占位符/元组 arity 逐一核对：16 列 = 15 个 `?` + strftime(created_at)，元组 15 值，一致**。`ARTIFACT_HANDLE_SCHEMA_VERSION = "1.0"` 存在于 artifact_handle.py（L26）。store.py artifacts 表 schema_version 列已存在（FC-906-d）。
3. **FC-906-b 修订**：`EXTRA_PRODUCER_GENERATORS` + summarizer.py 入 producer_modules scan；`03_change_contract_fc906b.md` 加 2026-08-12 Addendum（FC-1203 裁决引用）。符合该合同自身协议（加 producer 须修订测试 + 角色合同）。
4. **新增测试**：`test_fc1203_dead_helpers_absent.py`（3 断言：2 模块不可导入 / 2 属性不存在 / 1 文件不存在）；`test_fc1203_extractive_summary_binding.py`（3 测试：registered / v2-bindable REUSABLE / schema_version 列戳记）。
5. **保留项**（不判死码，合同 §2 登记）：`evaluate_candidate`（test_sidecar_production_scan_fc502.py + test_dbx_fixture_e2e.py 承重）、`restore.py`（scripts/wu904_remediation_restore.py L31/L135 生产调用 restore_asset）、`validate_flag_state`（runtime_policy.py L24/L64 生产调用）——三者调用者均已在 result worktree 复核属实。
6. **revenue `fb77fe1`**（docs-only）实际只改 2 文件（progress.md + work_unit_registry.md）。见发现 F1。
7. wiki `a6937f3..90102c2` 变更文件集合（19 个）与 receipt `changed_files` 的 wiki 条目**逐项精确吻合**。

## 2. 聚焦测试（step 2，result-wiki）

```
python -B -m pytest tests/contract/test_fc1203_dead_helpers_absent.py
  tests/contract/test_fc1203_extractive_summary_binding.py
  tests/contract/test_fc906b_role_producer_contract.py
  tests/contract/test_policy_and_flags.py
  tests/contract/test_fc1201_root_hardcode_gate.py -q
→ 22 passed in 5.33s（3+3+3+8+5）
```

注：任务清单写"期望 12 passed（3+3+3+1+2）"，与其自身后续说明（policy_and_flags 现 8 测试、fc1201 gate 5 测试）矛盾；按逐文件计数 **22 passed 正确**，与任务指定的每文件测试数精确一致。

## 3. RED-at-base（step 3，base-wiki）

把两个新测试文件 + 修订后的 FC-906-b 测试复制进 base worktree（fc906b 原件先备份 `.fc1203-review.bak`），运行：

```
7 failed, 2 passed in 3.93s
```

| 失败测试 | 失败原因（全部为"正确原因"） |
|---|---|
| test_deleted_modules_are_unimportable | entity_resolver / reuse_latest_policy 在 base 可导入 |
| test_deleted_attributes_are_absent | validate_normalized_filing / atomic_rollback 在 base 存在 |
| test_deleted_files_are_gone | scripts/wu905_catalog_switch_check.py 在 base 存在 |
| test_extractive_summary_generator_is_registered | base 注册表无该 generator |
| test_extractive_summary_artifact_is_v2_bindable | metadata schema_version 为 None（base INSERT 未戳记） |
| test_extractive_summary_writes_schema_version_column | artifacts.schema_version 列 NULL（base INSERT 未写该列） |
| test_catalog_producers_write_only_registered_roles | GENERATOR_REGISTRY drift（base 缺 extractive generator）——**证明 FC-906-b 修订是必要的**（不修订则全量套件红） |

2 passed = FC-906-b 的 non-catalog-roles 与 producer_modules scan（base 的 summarizer.py 已写 `source_catalog_extractive_summary` 名，scan 通过）。回退：`rm` 两个新测试文件 + `mv` 备份还原 fc906b 原件；`git status --porcelain` 空。

## 4. Mutation 重放（step 4，result-wiki）

| Mutation | 操作 | 结果 | 回退 |
|---|---|---|---|
| M-revive-1 | `git show a6937f3:` 还原 entity_resolver.py | gate FAILS（test_deleted_modules_are_unimportable） | rm |
| M-revive-2 | 还原 reuse_latest_policy.py | gate FAILS（同上，一并验证） | rm |
| M-revive-3 | 还原 scripts/wu905_catalog_switch_check.py | gate FAILS（test_deleted_files_are_gone） | rm |
| M-revive-4 | flags.py 末尾重加 atomic_rollback（原函数文本） | gate FAILS（test_deleted_attributes_are_absent） | reverse edit 切除；CRLF 恢复，diff 清零 |
| M-revive-5 | normalized_meta.py 末尾重加 validate_normalized_filing（原函数文本） | gate FAILS（test_deleted_attributes_are_absent） | reverse slice 切除；CRLF 恢复，diff 清零 |
| M-unregister | GENERATOR_REGISTRY 删除 extractive 条目（Edit 工具） | binding 2 FAILS：registered 断言 + v2-bindable（`reusable=False, reason='artifact_generator_unregistered'`，精确击中） | Edit 工具复原 |

每步后运行对应 gate/binding 测试确认 kill；全部回退后聚焦 5 文件复跑 **22 passed**，`git status --porcelain` 空。中途出现一次 CRLF 行尾漂移（`git show` 输出 LF vs worktree CRLF），已转回 CRLF 清零 diff——纯格式回退，未动用 `git checkout --`。

## 5. 全量套件（step 5）

result-wiki：`python -B -m pytest tests/ -q` → **2215 passed / 2 failed / 1 skipped（506.92s）**，与预期精确一致。

2 failed = `tests/contract/test_check_unique_test_symbols.py::test_duplicate_test_definition_fails` + `test_syntax_error_is_reported_as_failure`（PORT-01；子进程 GBK 字节按 UTF-8 解码 UnicodeDecodeError 0xd4）。**base-wiki 复跑同文件：同样 2 failed / 3 passed，同解码错误类（0xa1 / 0xd4）**——预存在，且该文件不在 FC-1203 diff 中。零新增失败。

## 6. 残余引用扫描（step 6）

对 `entity_resolver / reuse_latest_policy / atomic_rollback / validate_normalized_filing / wu905_catalog_switch`（排除 .git、__pycache__、assurance/fc/FC-1203/、门测试自身）全仓扫描：

- `.py` 命中仅 8 处，全部为注释/字符串/子串误报：architecture_gate.py L162-163（FC-1203 删除注释）、test_fc1201_root_hardcode_gate.py 3 处（docstring + allowlist 断言字符串 + 删除注释）、test_source_catalog_security_identity.py 3 处（`identity_resolver` 子串）。
- 其余 4 个 token 在 `.py` 中 0 命中。**零 live import。**
- 非 `.py` 命中均为历史记录：assurance/fc/FC-1201/* 与 FC-201 receipt（历史文档/receipt，immutable）、artifacts/gates/*.log（identity_resolver 子串）。

## 7. 实施者 receipt 结构校验（step 7）

```
cd revenue-forecast && python tools/receipt_validator.py
  --receipt company-wiki/assurance/fc/FC-1203/11_implementer_receipt.json
→ OK: 1 receipt(s) valid
```

依赖 receipt 存在性复核：`company-wiki/assurance/fc/FC-906/12_reviewer_receipt.json` 存在 ✓。实施者全量套件自述（run 1: 2214/1/3 含 fc906b drift 红 → run 2 修订后 2215/1/2）与本评审独立复跑（2215/1/2）吻合；RED 自述（6 failed，正确原因）与本评审一致；6 mutation 自述（5 revive + 1 unregister 全杀）与本评审逐一复现一致。

## 8. 发现（全部 info 级，非阻塞）

- **F1（receipt 精度）**：`11_implementer_receipt.json` 的 `changed_files` 多列了 3 个 revenue 文件（findings.md、task_plan.md、assurance/fc/FC-1203/00_wu_card.md）——revenue `fb77fe1` 实际只改 progress.md + work_unit_registry.md（`git show --stat` 证实）；那 3 个文件最后一次修改在 base 提交 `5ef1079` 内。全部位于 allowed_files 内，receipt_validator 仅校验 changed⊆allowed 故通过。实际 delta 无任何未申报变更；方向是"多报"而非"漏报"。处置：非阻塞，信息登记。
- **F2（提交清单差异）**：任务清单列 3 个 wiki 提交，实际 4 个（多 `c91b066` comment-only）。其内容在预期变更描述内（architecture_gate.py comment note）。处置：非阻塞。
- **F3（任务计数笔误）**：任务期望"聚焦 12 passed"，但其自身按文件计数（3+3+3+8+5=22）与实际一致。处置：非阻塞，按 22 记录。
- **F4（base 门测试的 RED 依赖属性）**：RED-at-base 依赖复制新测试进 base；base 全量历史套件（含被删的 4 个测试文件）自然通过——删除行为由 result 侧门测试钉住，base 侧 RED 证明门测试有牙。处置：非阻塞，评审方法已按任务执行。

## 9. 裁决

ACCEPTED。所有 7 个评审步骤全部完成；diff 与描述精确一致（唯一的"多"是 1 个纯注释提交 + receipt 多报 3 个文档文件，均非阻塞）；聚焦 22/22、RED-at-base 7 败因全部正确、6 mutation 全杀全回退、全量 2215/2/1 与 base 预存在失败一致、残余引用零 live import、receipt 结构校验 OK。零阻塞发现。

## 附：主 checkout 洁净度声明（F-6）

本评审对主 checkout（company-wiki / revenue-forecast / filing-fetch）只执行只读操作（git log/show/diff/rev-parse、receipt_validator、sha256sum）+ 在 company-wiki 写入本报告与 12_reviewer_receipt.json（任务要求的两份交付物，untracked 新增）。评审结束时观测到的主 checkout 脏状态全部非本评审所为：revenue `00_wu_card.md`/`findings.md` 修改与 `2026-08-12_zijin_skill_run_audit/` 未跟踪目录（并行会话/技能运行产物）、wiki `llm_cost_log.csv` 修改与 `.claude/settings.local.json` 删除（环境侧既有）。两个评审 worktree `git status --porcelain` 均为空。

