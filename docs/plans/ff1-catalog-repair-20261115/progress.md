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
- [N3] B3 待提交。
