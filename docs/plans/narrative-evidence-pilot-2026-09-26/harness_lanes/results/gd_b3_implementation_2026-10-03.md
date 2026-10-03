# G-D B3 实现交付（待总指挥发布/生产执行）

按已冻结 [B3 实施卡](../../gd_b3_archive_retirement_implementation.md) 和 [metadata 审计](gd_b3_metadata_audit_2026-10-03.json)实施。没有 production apply、commit/push、共享 PWF/ADR 或跨仓修改。

## 实现

- `scripts/retire_derived_archives.py`：固定两条精确派生 archive 路径，版本化 audit → plan → durable intent → 两件逐个 unlink → receipt；使用既有 B1 path/hash/JSON/write helpers 和 CatalogOperationLock。原文/当前 DB/任意 target、reparse、字节或依据漂移拒绝。
- 当前 DB 完整 SHA/size/mtime 绑定审计；metadata 全覆盖与 prepared/scan 历史证明自洽，无 span/原文全库验证。要求 Worker paused、WAL 无帧；不写当前库、不恢复旧库。
- 逐件 intent 可恢复 unlink 后中断；历史 deleted_bytes、当前调用 newly_deleted_bytes、恢复 recovered_deleted_bytes 分开计。重复 apply 不新增释放。第二件漂移时拒绝、不落完成 receipt。
- `retire_catalog_snapshot.py`：仅在 snapshot 已不存在且匹配完成 intent/receipt 时可回显 B1；新的删除仍须实际保留 archive 验证。
- `evidence_query.py`：只移除“仍在 verified cold snapshot”的断言，保留旧 error_type=legacy_evidence_archived、retryable=false，明确 source identity 留存。
- `writer_policy.py`：归类为 source lifecycle 工具，研究 writer 冻结不变。
- B3/B1 维护 CLI 输出 ASCII JSON，JSON 中 Unicode 路径的值保持不变，避免 GBK native stdout 被 PowerShell 当 UTF-8 解码。

## TDD 与一个大节点

最初三个核心 RED 都实际失败：工具尚不存在、B1 依赖被退役的 archive、旧 query 文案不真实。正式 E2E 首次也发现 scratch fixture 留有 WAL；只在 scratch checkpoint 后建立审计，产品非空 WAL 拒绝规则不变。

最终一次受影响节点命令（禁 pytest 默认插件与 cache，独立短 basetemp）：

```text
python -B -m pytest -q -p no:cacheprovider -o addopts='' tests/unit/test_retire_derived_archives.py tests/unit/test_retire_catalog_snapshot.py tests/contract/test_source_catalog_evidence_query.py tests/integration/test_retire_derived_archives_e2e.py tests/unit/test_writer_freeze.py --basetemp .gd-b3-final
```

**64 passed / 45.23 秒**，一个既有 asyncio_mode warning。后来发现真实 stdout 编码缺陷，再补强制 GBK、独立 Unicode root 的一项真实 CLI 回归，实测 `UnicodeDecodeError` RED → **1 passed / 1.26 秒** GREEN。合计65项不同检查通过，未重复64项或增加全仓 coverage/PDF 消费节点。

| 施工卡检查 | 对应节点 / 实际结果 |
|---|---|
| dry-run 零写、精确 apply、重复不重计、DB/raw 不变 | `test_plan_apply_retry_keep_database_and_raw` |
| GBK native stdout 仍可无损解析 Unicode 路径 | `test_cli_json_paths_survive_non_utf8_stdout`，独立“资料”root、PYTHONIOENCODING=gbk，1 passed |
| 第一个 unlink 后崩溃 → 只新删第二件，准确恢复字节 | `test_interruption_after_first_unlink_reconciles_exact_increment` |
| SHA/size/metadata/basis/DB/WAL/control 漂移拒绝 | `test_drift_refuses_without_deleting_targets`，7 cases |
| 原文/主库/目录/越界/reparse拒绝 | `test_arbitrary_candidates_rejected_even_if_other_bindings_match`，4 cases；`test_reparse_target_is_refused` |
| 无 intent 缺件不冒充完成；中断后第二件漂移不宣称完成 | `test_missing_target_without_intent_is_refused`；`test_resume_refuses_changed_second_archive_without_reporting_completion` |
| 来源工具分类，legacy writer 冻结 | 新归类单测及既有 `test_writer_freeze.py`，21 cases |
| B1 archive 合法退役后回显，新 snapshot 仍不能绕过 archive | `test_completed_receipt_can_replay_after_retained_archive_is_retired`；`test_new_snapshot_cannot_reuse_completed_receipt_without_archive`，加 B1 旧回归共14 cases |
| 旧 evidence code 不变，active/unknown 正常 | 受影响 `test_source_catalog_evidence_query.py`，11 cases |
| 正式 narrative CLI → 真实小 catalog/gzip/zstd 删除 → 原 raw/主库字节与mtime不变 → CLI 同包回读、active查询同结果、retired具名不可用、unknown NotFound | `test_retirement_keeps_source_facts_raw_query_and_formal_narrative_cli`，1 passed |

Ruff（全部9件受影响 Python 文件）通过；host guard 扫 scripts/src/tests，new violations=0。测试 Zstandard frame 使用标准 single-segment/raw-block 格式；本机 zstandard 解码 10/131072/131073/262145 B 四件小型构造数据均逐字节相等，未解压任何生产归档。

## 一次真实生产 dry-run

命令：

```text
python -B scripts/retire_derived_archives.py --project-root . --audit docs/plans/narrative-evidence-pilot-2026-09-26/harness_lanes/results/gd_b3_metadata_audit_2026-10-03.json
```

首轮 **20.501 秒，exit 0 / status=dry_run**，字节验证通过，但 native stdout 经 PowerShell 捕获后中文路径乱码，**该捕获不能用作路径收据，已替换**。增加 ASCII JSON 输出及 GBK 单测后，针对这项真实缺陷获准纠正重跑：Python subprocess 捕获 bytes → json.loads → write_text(UTF-8)，强制 child PYTHONIOENCODING=gbk；**16.724 秒，exit 0/status=dry_run**，native_stdout_ascii=true，所有保存路径与实际 project/audit 一致、两件仍存在。

两轮仅实读当前 DB 和两件 archive 的完整流式 SHA，候选两件 **11,406,183,129 B**；原始文档未 hash/改动，没写维护 intent/receipt 或主库，没有 production apply。有效 plan 为 [gd_b3_production_dry_run_2026-10-03.json](gd_b3_production_dry_run_2026-10-03.json)。生产 apply 同样使用 Python 捕获 bytes/UTF-8 保存，不能再用 PowerShell 的未限定 native text 重定向。

## 测试目录恢复与交接

`.gd-b3-red`、`.gd-b3-unit`、`.gd-b3-e2e`、`.gd-b3-final`、`.gd-b3-encoding-red`、`.gd-b3-encoding-green` 均经绝对路径 containment/reparse 检查后精确删除，surviving_roots=[]。正式 E2E 的 published fixture finally 也验证 baseline 空目录恢复。没有触碰其他历史 scratch 根。

总指挥下一步：审查本差分、正常提交推送、精简 CI 绿后执行 **同一 audit 的 --apply**，记录实际释放、原 DB pin 和幂等结果；更新 PWF/ADR。当前旧归档仍存在，旧 span 可恢复性的最终放弃尚未实际发生。
