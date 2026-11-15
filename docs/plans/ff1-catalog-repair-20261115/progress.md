# 进度登记 — ff1-catalog-repair-20261115

## 2026-11-15 开工

- [x] 主工作区建独立 worktree `company-wiki-ff1-catalog-20261115`（分支 codex/ff1-catalog-repair-20261115，base ac8841c55；任务书基线 66c97834d 之后 master 另有 4 个 docs-only 提交，src 无差异，已在 task_plan.md 记录偏离）。
- [x] 探索：resolver._resolve（unknown_date_matches 计数、_excluded_candidate 结构、_result 工厂）、scanner（_DECLARING_KEYS/_merge_columns FILL 规则/_merge_document_row verified pinning）、registration_scope（register_catalog_sources）、cli register 分支、acquisition_service._ensure、canonical_writer._record_validated_capture、operation_contract/operation_projection、acquisition_journal。
- [x] 实测根因确认（只读查询主工作区 catalog.sqlite3）：
  - 4 个 undated MDB 行（2022/2023/2024 dayu + 2026 company_raw）均有 2026-11-08 批量写入的 verified source-facts 断言，patch 内 published_date=None / filing_date=None。
  - `_record_validated_capture` 的 `facts = {k:v for k,v in facts.items() if k not in previous}` 把后续带 filing_date 声明的导入 facts 过滤掉（显式未知优先），documents.published_date 永远填不上 → B3 根因。
  - scanner `_merge_document_row` 的 verified fact pinning（new_raw==old_raw → effective=事实值 None）：对这些带 None-patch 断言的存量行，单纯 re-register 不会清掉 pin —— B2 按任务书只做定向登记，存量 pin 行不在 B2/B3 修复范围（记入 findings，需独立 facts 修正 pass）。
- [x] PWF 文件建立。

## 节点推进

- [N0] 基线核对（干净 baseline worktree @ ac8841c55 实测，2026-11-15）：
  - 预存失败（非本 lane 回归，照实登记）：
    - `tests/contract/test_source_version_reader_cli.py::test_ensure_cli_latest_as_of_projects_gap_without_fetch_or_raw_change`（adapter candidate security_id does not match request，环境相关）
    - `tests/contract/test_source_version_reader_cli.py::test_ensure_cli_latest_as_of_preserves_provider_unavailable_gap`（同上）
    - `tests/contract/test_fc1301_reason_taxonomy.py::test_every_emitted_reason_is_registered`（src 里 60+ narrative_*/local_* 等 code 未注册；均非本 lane 引入——本 lane 新 code 已全部注册）
    - `tests/contract/test_activation_transaction.py::test_cli_activation_apply_rollback_roundtrip`（activation 命令已退役 vs 旧测试）
  - 全量基线数字：跑批中（后台 exec_c468fb2a，完成后续记）。
- [N1] B1 实现完成：resolver.py（reason 拆分 + unknown_date_match_count + _excluded_candidate 白名单增强 + 常量导出）、observability.py（7 个新 code 注册 REASONS/STAGES）、新测试 tests/contract/test_ff1_unknown_date_classification.py（6 用例 + 注册枚举参数化，全绿；test_source_qualification.py 回归全绿）。
- [N1] B1 提交 da35f6c25（首次提交被 pre-commit mypy 拦截：Mapping vs dict 形参不匹配，正当修复后通过）。
- [N2] B2 实现完成：
  - 新模块 catalog_repair.py（只读预检 plan_undated_group_repairs + GroupRepair + CatalogRepairJournal append-only catalog_repairs.jsonl，事件 catalog_repair_applied 含 root/relative_path/sidecar_kind/filing_date/data_source）。
  - registration_scope.register_groups(catalog, root_id, relative_paths) 库函数（提取 register 子命令定向登记；service.register_sources 与 cli register 分支均改为委托，行为不变；CLI 冒烟实测 rc=0、ScanReport 形状一致；tests/integration/test_financing_scanner_cli.py 为环境门控 skip）。
  - acquisition_service._ensure 挂 _heal_undated_catalog_sources：命中两类 unknown-date reason → 预检 → 有声明才 register_groups（每 root 一次，锁序：ensure 互斥段之前，无嵌套）→ journal 事件 → 恰好重跑一次 _select_for_ensure；登记失败降级为具名失败（warning 日志）。
  - 测试 tests/contract/test_ff1_ensure_catalog_repair.py 4 用例全绿：company_raw 声明→一次修复后 REUSED（calls==2、published_date=2026-02-20、journal 事件断言）；无声明→unique_match_published_date_unknown 直接失败（calls==1、无 journal）；dayu 组 meta.json 声明→修复 REUSED（sidecar_kind=group_meta_json）；预检只读（规划后行未变、无 journal）。
  - 回归：test_source_catalog_acquisition / scoped_scan / scanner_direct / verified_reuse / canonical_acquisition_scope / scan_candidate_immutability 74 通过。
- [N2] B2 提交 1cf52e825（首次提交被 ruff F401 拦截：3 个未用 import，删除后通过）。
- [N3] B3 实现完成：canonical_writer._record_validated_capture 的 prior-patch 过滤加显式未知豁免——previous[key] 为 None/""（显式未知=空列）且本次 facts 带非空声明（published_date/filing_date，值=candidate.filing_date）时保留该 fact，走既有 prepare_source_fact_write/write_source_fact_projection 落库（断言 evidence locator canonical-commit:/candidate/published_date + provider-metadata-import/1）；prior 非空值仍获胜、scope 冲突检查不变、无猜测值。
  - 测试 tests/contract/test_ff1_import_published_date.py 3 用例全绿：声明导入→published_date=2026-03-11+声明溯源；prior 显式未知（模拟 2026-11-08 批量）+声明再导入→填上；prior 已知日期→不被导入替换。
  - 回归：test_source_catalog_canonical_writer.py 全绿（17 通过含新增 3）。
- [N3] B3 提交 c2d621cb5（安全门禁一次通过）。
- [N4] B4 实现完成：
  - operation_contract.py：SourceOperationInput 新增 candidates（解析 resolution.excluded_candidates）与 reason（acquisition.reason→resolution.reason 优先级）两个可选字段；导出 OPERATION_REASONS 闭集（resolver 终态 11 个 + coordinator 决策 8 个，含契约示例的全部 4 个）。
  - operation_projection.py：status∈{ambiguous,not_found} 且有候选时投影 candidates（白名单逐字段构造，多 match→multiple_candidates，excluded→各自 reason，≤5 截断保留原序）；reason 仅在闭集内透传（未知词表省略可选字段，不臆造映射）；completed/gap 永不携带；白名单外的键（含物理路径）逐项剥除 + 顶层 _contains_physical_field 兜底；operation_schema_version 保持 "1.0"。
  - 测试 tests/contract/test_ff1_operation_candidates.py 10 用例全绿：白名单逐字段、多 match 投影、≤5 截断原序、completed/gap 不携带（含带 excluded_candidates 的载荷）、未知 reason 省略、pathless guard（注入 canonical_path/absolute_location 被剥除）、6 组畸形候选拒绝、闭集导出断言。
  - 回归：test_source_operation_v2 35 通过（含新增 10）；acquisition_failure_return_paths / canonical_acquisition_scope / verified_source_operation 共 49 通过。
- [N4] B4 待提交。
- [N4] B4 提交 63a665005（mypy 首拦：result dict 值类型注解，补 `result: dict[str, Any]` 后过）。

## [N5] 回归对照（基线 vs 分支，同一命令顺序执行）

- 全量混合跑两次都被环境强杀（exit 137，双实例资源争用），按 CI 门禁范围做同口径对照：
  - `pytest tests/unit`：基线 **29 failed / 11448 passed / 25 skipped**（16:44）；分支首次 **30 failed / 11447 passed / 25 skipped**（17:04）——多出的 1 个为 `tests/unit/test_acquisition_failure_diagnostic.py::test_after_provider_success_completion_error_retains_operation_accounting`（B2 hook 未容错无 resolution 的 decision stub），已修（fa517aac8，getattr 容错）并针对性重跑绿；总数守恒（30+11447 == 29+11448），基线 29 个失败全在 document_understanding/narrative/pdf 域（与 source_catalog 无交集）。
  - `pytest tests/contract`：基线 **51 failed / 3087 passed / 22 skipped**（45:05，失败集中在 lt_uj(_real)、portfolio_promoter、cn_stockinfo、download_authorization、gap_plan、parser_liveness、pilot_receipt、source_system_docs、zr404/zr501、ensure CLI latest_as_of——环境预存）；分支跑批中。
- 本 lane 新增/触及域定向回归全绿：ff1 四个新测试文件（B1 12、B2 4、B3 3、B4 10）、source_qualification、source_version_reader(_cli 除预存 2)、identity_resolver、canonical_writer、acquisition 系列、scanner 系列、operation_v2、acquisition_failure_return_paths、canonical_acquisition_scope、verified_source_operation、fc1301（预存失败不变）、stage_taxonomy、financing_scanner_cli（环境门控 skip）。
- CLI register 子命令冒烟：refactor 后 rc=0，ScanReport 输出形状不变（/tmp/ff1-cli-smoke）。

## [N5续] 收尾（2026-11-15 下午）

- 分支 contract 套件复跑（无截断）：**51 failed / 3119 passed / 22 skipped（32:13）**——失败数与基线持平，passed 恰好多 32（= 本 lane 4 个新验收测试文件）。
- 失败逐名甄别：基线日志被 tail 截断少记 14 行；把该 14 项 + parser_liveness×2 在干净 baseline worktree 实测——14 项中 12 项基线同样失败（activation、automation_store_boundary、cross_root_dedup_fc603、fc1301、gp002、layer_public_boundaries、location_switch×4、lt02、lt08），另 2 项（fc1201_root_hardcode_gate、future_root_config_only）为**真回归**：catalog_repair.py 硬编码 root kind 触发架构门禁。修复 aa35d8609：kind 分派上移 scanner.declared_group_publication_date（layout owner），planner 无 root token；两门禁转绿，B2 测试/scanner 回归全绿。parser_liveness×2 基线全量跑失败、单跑通过（子进程型 flaky，非本 lane 域）。分支失败集 51 项全部=基线预存。
- 修复桩容错提交 fa517aac8（unit 对照多出的 1 例）；门禁重构提交 aa35d8609。
- 四件套验收批：tests/contract/test_ff1_*（4 文件 32 用例）全绿。
- scanner.py 改动后 unit 套件最终复跑：**29 failed / 11448 passed / 25 skipped**（20:21）——失败集与基线**逐名完全一致**（diff 为空）。回归不低于基线达成。

## [N5] 定稿

- 分支最终 commit（6 个）：da35f6c25(B1) → 1cf52e825(B2) → c2d621cb5(B3) → 63a665005(B4) → fa517aac8(决策桩容错) → aa35d8609(架构门禁重构)。
- 全部验收与对照数据齐备，本文件与 findings.md 以 docs(pwf) 提交收口。不 push、不并 master。
