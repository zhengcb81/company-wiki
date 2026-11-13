# MB-CWP 发现

## 起始状态（2026-11-12）

- 工区 `C:/Users/郑曾波/Projects/mb11-cwp`，分支 `codex/mb11-cwp`，基线 `08dfe8bf1`（`docs(pwf): clarify P3 publication state`）。
- 原仓 master 在审计时为 `879953c7f`；本卡基线按卡要求固定为 `08dfe8bf1`。
- `src/company_wiki` 共 479 个 Python 文件（`rg --files` 计数），与 `review/cwp_architecture.md` §5 一致。
- 无 `mb11-cwp` 工区/分支此前存在（`git worktree list` 核对），本卡为首次建立。

## 四项已确认缺口的当前代码事实

### CWP-01

- `src/company_wiki/automation/narrative_transport.py:365` — `normalization = self._normalization or NarrativeNormalization.from_reader(self._reader, enabled=...)`。
- `NarrativeTransportReader.__init__`（`narrative_transport.py:173`）**已经**接受 `normalization=` 参数；CLI `narrative_transport_cli.py:194-199` 两个分支都没有传。
- `NarrativeNormalization.from_reader`（`source_catalog/narrative_normalization.py:78-85`）用 `getattr(reader, "catalog", None)` 拿 `catalog.config.project_root`，再读 `config/local_ocr.json`。
- 全仓 `from_reader` 只有这一个调用点，且**无任何测试覆盖**该分支。
- 已有的注入点：`NarrativeRuntimeDependencies.normalization`（`automation/narrative_runtime.py:41`）、`NarrativeNormalization.from_snapshot` / `from_project`（`narrative_normalization.py:62,69`）、`replay_verified_narrative_evidence(..., normalization=)`（`narrative_material_replay.py:172`）。
- 结论：owner 能力已存在，缺的是 CLI/composition 的显式构造与注入；`from_reader` 是第二条配置发现路径，可撤销。

### CWP-02

- `src/company_wiki/source_catalog/narrative_selection.py:105,112` — 函数内 `from company_wiki.resource_budget import new_document_work_budget` + 无参调用。
- `src/company_wiki/resource_budget.py:49-55` — `budget_policy_path` 用 `COMPANY_WIKI_BUDGET_CONFIG` 环境变量，否则 `Path(__file__).parents[2]/config/resource_budget.yaml`。
- 预算类是 `WorkBudget`（`resource_budget.py:110`），API 是 `charge(n=1)` / `scoped(max_work_units, *, phase=None)`；**没有** consume/reserve/remaining。
- `RawNarrativeSelector.__init__`（`narrative_selection.py:45-52`）只有 `pdf_reading` / `normalization` / `selector` 三个入参，无预算工厂。
- 生产上唯一构造点 `automation/narrative_select.py:143`；composition root `automation/narrative_runtime.py:34-76`；生产调用方 `automation/narrative_worker_factory.py:377`。
- `config/resource_budget.yaml` 在仓库根，不入 wheel；`resource_budget.py:55` 在 wheel 安装后指向不存在的路径。
- `narrative_selection.py` 的内容参与 `selection_algorithm_sha256()`（`narrative_selection.py:270-272`，被 `narrative_decision_inventory.py:42` 引用）——改这个文件会改变 decision-inventory 身份，属算法身份变更，需要评估。

### CWP-03

- `src/company_wiki/automation/narrative_source_guard.py:9-12` — `from company_wiki.source_catalog.source_reader import SourceRef, VerifiedContent`。
- `source_catalog/source_reader.py:20-43` 模块级导入 `resolver` / `service` / `store` / `read_budget` 等具体 runtime。
- `SourceRef` / `VerifiedContent` 的真正 owner 是 `source_contract/source_version.py:26-78` 与 `:146-196`；`source_reader.py:39-43` 只是重导出同一对象，`__all__` 在 `:914-920`。
- `automation/narrative_transport.py:27-31` 同样经 `source_catalog.source_reader` 取 `SourceRef` / `VerifiedContent` / `SourceReadError`。
- `automation/narrative_verify.py:18` 已经走 `company_wiki.source_contract.source_version`——正确范式已存在。
- `src/company_wiki/source_catalog/__init__.py:139-145` 自身就把 `SourceRef` / `VerifiedContent` / `SourceReadError` 的公开归属指向 `..source_contract.source_version`。
- 结论：切换 import 是纯依赖方向变更，对象同一性不变。

### CWP-04

- `pyproject.toml:19-30` 声明 11 个 console scripts；`[tool.setuptools.package-data]` 只覆盖 3 个包。
- `tests/contract/test_packaging_contract.py` 39 行纯 TOML 文本检查，从不构建/安装 wheel。
- `tests/conftest.py:56` 把 `src` 插进 `sys.path`（注释："CI 不装 editable"），所以全部测试都从源码树导入。
- `.github/workflows/ci.yml:48-50` 只装 `requirements*.txt`，全仓无 `pip install .`。
- `document_normalization/__init__.py:31-32` 急切导入 `docx_parser`，后者模块级 `from lxml import etree`；**`lxml` 在 `pyproject.toml` 里完全没声明**（只在 `requirements.txt` 里）。干净 `pip install .` 后 `import company_wiki.document_normalization` 直接失败。
- `model_config.py:34` 与 `resource_budget.py:55` 都读仓库根 `config/`，不入 wheel。
- `scripts/narrative_batch_configured.py:9` `from config import Config` 依赖未安装的 `scripts/` 目录。
- 公开 module CLI：`python -m company_wiki.source_catalog.processed_document_cli`（`processed_document_cli.py:102-103`）、`python -m company_wiki.source_catalog.financial_statements.cli`（`financial_statements/cli.py:236-237`）。

## A0 逐项处置（2026-11-12 实测）

| 子项 | 处置 | 证据 |
|---|---|---|
| T-READ | 移植 `source_stream_cli.py`（薄传输，2.2 双回执协议），全部准入/预算/取消走当前 `stream_version` owner；`locked` 回执改为惰性（首字节前发出；无字节的拒绝不带锁行），见「公开协议升级事项」 | `tests/contract/test_source_stream_cli.py` 7 项（含同尺寸篡改 [locked,unavailable] 无 ok）；`test_source_reader_exact_history.py` 9 项（自 `89fd952a5` 恢复） |
| T-CANON | 移植 `public_canonical_browser.py`(1332)+CLI(166)+两测试(1615+57)；`public_document_browser` 增 3 个 typed-port 有界枚举方法（无裸 SQL） | 101 项通过（canonical 51 + calendar 9 + document_browser 20 + port_boundaries 21） |
| T-B33 | 移植 readiness/link/recovery 六模块+三测试；`resolver._ReadBudget`→`read_budget.ReadBudget` 适配；owner 级 pair 精确读取（见上节） | 118 项通过（readiness 86 + link 15 + recovery 8 + exact_history 9） |
| T-B34 | `record_unresolved`（去重无固定帽）+ `_cn_ipo_prospectus_cover`（全前页扫描） | 33 项通过（diagnostic 18 + prospectus 15） |
| T-N4 | 核销（可复现命令见下）；signal-free skip 是主线有意的计数规则，不恢复 | 两条命令全绿（9 + 78） |
| T-CONFIG | 8 个严格类型反例 RED→GREEN（`max_tokens`/`temperature` bool+str、`reasoning_split` 字符串、`max_document_chars` 全部）；`bool("false")` 强转改为具名拒绝；旧 M3 等 profile 反例被主线 `test_unselected_fallback_is_not_constructed` 有意取代，不加第二 `load_llm` | `test_narrative_config_scope.py` 33 + `test_narrative_model_config.py` 39 = 72 项 |

### T-N4 核销的可复现证据（2026-11-13 复跑）

```powershell
python -B -m pytest tests/unit/test_narrative_evidence.py -k "titleless or quarterly or signal or current" -q -p no:cacheprovider
# 9 passed：含 test_current_operating_progress_is_selected_for_titleless_known_documents 的
# quarterly_report×{industry_dynamics,core_business,capacity_projects} 与
# investor_relations×{new_business,overseas} 五个参数 —— 即历史 2b5bec914 新增测试的
# 四类中文类别文本（景气度/生产装置/新业务/境外）在主线的等价选中行为；
# 以及 test_complete_quarterly_financial_table_can_skip_as_non_narrative。

python -B -m pytest tests/unit/test_narrative_selection_architecture.py tests/unit/test_narrative_select_handler.py -q -p no:cacheprovider
# 78 passed
```

历史 `2b5bec914` 的 signal-free 分支（`test_fully_scanned_signal_free_quarterly_skips_cleanly` 断言 `skipped_no_narrative`）与主线**有意相反**：主线 `narrative_finalize.py:237-244` 注释明确"Financial counts are diagnostics, not an independent terminal proof"，改用计数规则，且 `test_titleless_signal_free_quarterly_remains_reviewable`（`test_narrative_select_handler.py:357`）钉住 `needs_review`。按卡「不能恢复旧 eligibility 策略」，该分支记为被主线替代，不移植。

## 非 primary 版本读取（owner 级变更，T-B33/T-READ 交汇）

历史 89fd952a5 有更丰富的历史版本能力，当前主线曾缺失；最初交付把默认 query_ref 扩为 pair-precise，后来 ROOT 基于 Dashboard 已有默认拒绝合同决定不改变默认行为。最终合同以本节“ROOT 最终决策”为准。

最初诊断的三道读取门：
1. query_ref → query_source_reference 只查 primary（document_source_mismatch 拒绝）；
2. _current_source_location 用 primary 行比对 ref（source_ref_changed）；
3. resolver candidate_rank > 0 门（历史版本位置 role=original_attachment 排位 0，role_not_original_primary）。

已保留的 owner 能力：
- reader.exact_source_pair(document_id, source_id)：pair 精确 UNION 查询，含 primary_source_id；未注册 pair 不返回行；primary 不会替代目标 pair；
- source_references.query_exact_pair_reference：错误映射与历史一致；registration 路径 query_source_reference 及其 primary 语义不变；
- SourceVersionReader.query_exact_pair_ref：独立的精确历史读取入口；query_ref 保持 primary-only；
- resolver 用 pair 行核对现存 SourceRef 身份；非 primary 且非 reuse 的位置按 browser 版本角色（original_primary/attachment/indexed_only + active + 无 .rejections 段）准入；root 各门照旧；reusable_only（filing_reuse）与 primary 排位语义不变。

### ROOT 最终决策（2026-11-13）

Dashboard 既有测试要求默认 query_ref 对历史版本拒绝。因此最终代码保持 query_ref 的 primary-only 语义；只有调用 query_exact_pair_ref，或 CLI 显式传 --exact-pair，才读取精确历史版本。初版 pair-precise query_ref 是已被替代的中间状态，不是最终公开合同。最终集成证据见本计划 handoff.md §8。

## 其他发现

- 主线 `tests/integration/test_source_processing_handler_wire.py::test_current_wire_feature_is_bound_to_the_actual_recipe` 在 baseline `879953c7f` 即失败（`_versions` 未定义名，ruff F821/F401），属既有损坏，不在 MB-CWP 写集合（`tests/integration/`），列给 ROOT。
- `lxml` 曾只在 requirements.txt、未进 pyproject catalog/all extra（CWP-04 缺口），已补声明。
- 提交钩子 Mimosa L3 以基线既有文件（`test_automation_migrations.py`/`test_llm_client.py`/`identity_candidates.py`）拦截；按 AGENTS 跑正式封印扫描（`scan-2026-11-12T21-35-54`、`scan-2026-11-12T22-18-39`、`scan-2026-11-12T23-08-43`，各 137 项发现、本卡 diff 零新增）后带证据放行，未改写命令或绕过。

## 公开协议升级事项（按 interfaces.md 交 ROOT 协调）

### 升级 1：`locked` 回执语义（已按我方裁量修正 + 披露）

- **失败例（独审复现）**：Dashboard `tests/adapters/cwp_original_stream/test_adapter_stream.py::test_missing_file_refuses_before_lock` —— 历史 `3199adab` 的 `ByteLock` 在**全量字节验真后**才发 `locked`；初版移植在 `begin_candidate`（验真前）即发，缺文件时消费端首行收到 `locked` 而非拒绝。
- **最小兼容方案（已实施）**：`locked` 惰性化——首字节跨 stdout 前发出（空原件在 `commit_verified` 前发出）；**无字节的拒绝不带锁行**；`ok` 才是全量验真声明（文档字符串已改写）。2.2 schema 不变。
- **结果**：`test_missing_file_refuses_before_lock` 由 FAIL → PASS；我方 `test_source_stream_cli.py` 以两条用例钉住新序（无字节→仅拒绝；同尺寸篡改→[locked, unavailable] 无 ok）。Dashboard 24 条现 21 过。
- 剩余 3 条见升级 2 与 OUT-SCOPE 清单。

### 升级 2：primary 查询与历史精确读取分开命名（ROOT 已裁决）

- **冲突证据**：Dashboard `test_non_primary_history_version_refused_like_the_reader` 明确要求旧 `query_ref(HISTORY)` 拒绝 `("not_found","document_source_mismatch")`；最初把它改成 pair 精确会破坏既有 whole-buffer 与 stream 一致性。
- **ROOT 决定采用方案 B**：`query_ref` 保持既有 primary-only 语义；同一个 `SourceVersionReader` 增加 `query_exact_pair_ref`，由它处理精确的历史/附件版本。`describe_version`、`verify_version`、`open_version` 等以既有 `SourceRef` 为输入的操作沿用该精确身份，不再重新收窄到 primary 行。
- `source_reader_cli` 与 `source_stream_cli` 保留默认 primary-only 行为；新增 `--exact-pair` 后才能按完整 document/source/SHA 对读取非 primary 版本。旧 Dashboard 调用不需改动或新增批准步骤；浏览器/历史版本调用方可显式选用 exact pair。
- **验证结果**：CWP 历史/reader/stream 合同 61 项通过；Dashboard 既有 non-primary 拒绝合同通过；CWP owner proof library 在合并当前主线后 138 项通过；另外 exact-history + stream 合同 16 项、readiness 历史身份 4 项通过。ROOT 本轮重新跑 Dashboard adapter suite 为 22 passed / 2 failed：失败仅是 Dashboard 测试导入 CWP 基线即不存在的私有 _ReadBudget；本仓不恢复私有实现，消费端需改用公开 port。最终 CWP 修复提交 0a03b5886 的独审为 PASS。

### OUT-SCOPE（列给 ROOT，不在 MB-CWP 写集合）

- Dashboard `test_midstream_source_replacement_never_reaches_the_consumer` 与 `test_same_size_tamper_before_the_pass_is_refused_before_any_byte`：`from company_wiki.source_catalog.resolver import _ReadBudget` 与 `reader._admitted_candidates(...)` 是 X-C04 分支私有名，**基线主线也不存在**（消费端历史分支耦合）；主线不为它们恢复第二读取/预算 owner（卡禁），需 Dashboard 侧改用现行公开端口（`read_budget.ReadBudget`、`catalog.source_location_candidates`）。
- 基线既有红（全部在 baseline `08dfe8bf1`/`879953c7f` 复现，与本卡 diff 无关）：
  - `tests/unit`：6 个收集错误（`ImportError: cannot import name '_admitted' from narrative_reading`，旧测试文件引用已被祖先 `e5dd29b1f` 删除的私有名）+ 3 个失败（`test_operating_relation_production` 的 `_financial_only`、2×`test_source_contract_reader_port`）——CI Unit 步骤在基线即红；
  - `tests/contract`：61 个失败（本卡修复其中 `test_source_catalog_module_contracts` 1 个——即独审 blocker 1；其余 60 个基线同失败，其中多数不在 fast gate 内）；
  - `test_fc1301_reason_taxonomy::test_every_emitted_reason_is_registered`：基线 65 个未注册 code；本卡注册了 14 个（13 个新增发射 + `catalog_unavailable`），现剩 **64 个全部是基线既有发射点**（独审 round 2 逐行核对：7 个虽在本卡触碰过的文件内被报告，但发射行全部是基线行；`residual ∩ 本卡新增行字符串字面量` 为空）；本卡净贡献 0。
  - `test_source_system_docs`（README/ARCHITECTURE/OPERATIONS，三文件本卡未动）。

### `scripts/config.py` 写入披露（finding 8）

`git diff 08dfe8bf1..HEAD -- scripts/config.py` = +27/−3（8 个严格类型反例的修复 + `reasoning_split` 不再 `bool()` 强转）。该文件是卡 A0 **T-CONFIG 行点名的四个文件之一**（`旧M3的config.py、narrative_batch_configured.py、test_narrative_model_config.py、test_w04_llm_config_scope.py`），故属本卡授权，但 §写范围的枚举未含它——在此披露：owner 行已补入 `ownership.md` §2（配置责任），改动仅限 `validate()` 类型检查与 `reasoning_split` 构造，未动 loader 结构（`Config.load(validation_scope=)` 保持主线形态）。
