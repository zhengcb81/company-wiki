# G1-LEGACY findings

## 已复现

1. `python scripts/config_doctor.py --help` → 0；`$env:PYTHONPATH="scripts"` 后同命令 → 78
   （sitecustomize 加载 writer_policy，config_doctor 不在支持集合）。
2. `legacy_writer_authorized` 真实 caller 只有 `writer_policy.legacy_script_execution_allowed`
   与 `tests/unit/test_writer_freeze.py`；可安全删除（卡 §4）。
3. `common.require_legacy_writer_permission` 生产 caller 恰好 4 个且全部永久退休：
   `full_pipeline.py:289`、`batch_process.py:214`、`cleanup_junk.py:166`、`batch_ingest.py:113`。

## 38 个永久退休脚本基线（trap harness，76 次运行）

- 37/38 plain 模式退出 78；`refine.py` plain/`-S` 均在 `from extract import clean_text`
  （`scripts/extract.py` 不存在，历史遗留）处 ModuleNotFoundError，guard 不可达 → 报 MAIN。
- `-S` 下 `build_links/full_pipeline/generate_index/generate_slides/stage3_analyze`
  在模块级 `import yaml`（或 `from config import Config`）处 ImportError，早于 guard、
  早于配置/LLM/网络/写入 → 仍"先退出"，但退出码是 1 而非 78；脚本不在本卡写集 → 报 MAIN。
- 无任何脚本触发写入 / socket 连接 trap。
- `auto_discover.py` plain 模式在 guard 之前执行模块级 `TOPIC_KEYWORDS =
  load_topic_keywords()`（auto_discover.py:324）读取 `config_rules.yaml` →
  "配置未初始化"唯一违例，脚本不在写集 → 报 MAIN。
- `llm_client` 模块级仅 stdlib + `common`/`prompts` 导入，无客户端实例化；
  改为 trap `LLMClient.__init__`/`get_llm_client()` 调用而非模块导入。

## 混合入口分类（非支持、非永久，共 57 个）

- 自带 guard（两种启动模式都 78、结果一致）：`audit_config.py`、`build_extracts.py`、
  `collect_news.py`、`collect_reports.py`、`fix_report_dates.py`、`graph.py`、
  `run_downloader.py`、`search.py`、`source_catalog_pilot_check.py`、`stage1_extract.py`、
  `stage2_structure.py`、`status_tracker.py`、`test_framework.py`。
  注：`source_catalog_pilot_check.py:752` 只 import 未调用 `enforce_direct_cli`
  （`# noqa: F401`），plain 模式实际放行、PYTHONPATH=scripts 时被 sitecustomize 拦截
  —— 两种启动不一致，属"未完成正规化"，报 MAIN 决定归支持集或补 guard 调用。
- 无 guard 的直跑 CLI（plain 放行、PYTHONPATH=scripts 被拦，基线即不一致）：
  `auto_suggest.py`、`bridge_off_equivalence.py`、`check_broken_links.py`、
  `classify_documents.py`、`clean_watermarks.py`、`clip_handler.py`、`config.py`、
  `contradiction_detector.py`、`copy_docs.py`、`enrich.py`、`extract_v2.py`、
  `framework_loader.py`、`gold_gate.py`、`host_assumption_guard.py`、`ingested_db.py`、
  `lint.py`、`llm_client.py`、`llm_output_validator.py`、`merge_financial_reports.py`、
  `migrate_raw.py`、`monitor.py`、`pdf_extract_v2.py`、`pdf_extract_v3.py`、
  `readonly_canary.py`、`real_root_probe.py`、`resolve_bundle.py`、`section_discovery.py`、
  `sector_distiller.py`、`shadow_resolver_probe.py`、`snapshot_catalog.py`、
  `source_discoverer.py`、`state_store.py`、`test_pdf_compare.py`、`validate_companies.py`、
  `wu904_remediation_restore.py`；其余为无 `__main__` 的库模块。
  本卡不放行、不补 guard，只在交接报告，由 MAIN 处理真实迁移。

## 删除影响核查（rg）

- 六工具 + `tests/support/derived_archive_fixture.py` 只被其专属测试链与
  `tests/unit/test_writer_freeze.py` 参数表引用；docs/计划文档中的引用为历史记录（只读）。
- CI / pre-commit / pre_push 不使用 `COMPANY_WIKI_WRITE_MODE`、`COMPANY_WIKI_LEGACY_WRITERS`。
- 契约 `test_non_r1_source_compatibility_keeps_explicit_override_contract`
  （collect_reports/test_framework 放行）将变红 → 按卡 §6.1 交 MAIN 改写，本卡不碰共享 Contract。

## 写集外发现（只报不改）

- `refine.py` guard 不可达（缺 `scripts/extract.py`）。
- 5 个脚本 `-S` 模式 guard 不可达（模块级第三方 import）。
- `auto_discover.py:324` guard 之前读 `config_rules.yaml`。
- `source_catalog_pilot_check.py:752` guard import 未调用。
