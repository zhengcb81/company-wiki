# N5-RAW-DUP progress

- [x] Worktree/分支建立：`codex/n5-raw-duplicate-audit` @ `e46108b4f30d5b7e47bfc712e360f173c00b702c`
      （`C:/Users/郑曾波/Projects/cwp-lanes-20261006/raw-duplicate-audit`）
- [x] 读卡：`n5_raw_duplicate_audit.md` + 总包 `n5_parallel_packages_2026-10-06.md`；AGENTS 职责边界确认
      （只出只读盘点工具与估计，不出投资结论，不写 StockWiki）。
- [x] Desk survey：`source_catalog/store.py::_DDL`、`reader.py::ReadOnlyCatalogReader`、
      `config.py::load_catalog_config`、`config/source_catalog.yaml`（4 roots）、
      `tools/legacy_storage/*` 记账口径、P5 交接格式与 N5 `cwp-independent-handoff/1` 模板。
- [x] 生产只读探针（无写入）：locations 46,606 / sources 43,112 / roots 4；
      多引用 source 3,531；`companies/` 有 1,007 个 UNPINNED 云占位文件。
- [x] RED：`test_raw_duplicate_audit_accounting.py`（12 例）、
      `test_raw_duplicate_audit_budget.py`（6 例）先失败确认。
- [x] 实现：`tools/raw_duplicate_audit/{__init__,core,catalog,classify,verify,report,assessment,cli}.py`
      + `README.md`；`scan` / `verify` 两个子命令，报告 schema `raw-duplicate-assessment/1`。
- [x] 单元 18 项 GREEN。
- [x] Integration `test_raw_duplicate_audit_fixture_set.py` 11 项 GREEN（真实 schema 隔离 DB、
      真实 hardlink、七类夹具、ACL 拒绝经 icacls 实测、预算/截止 partial、两个拒绝码、
      原件+config+catalog 前后不变、报告 1MiB/5000 行上限）。
- [x] E2E `test_raw_duplicate_audit_e2e.py` GREEN（`slow`+`real_data`+`e2e`）：
      候选组 3,531；`logical_duplicate_bytes_upper_bound = 7,804,167,537`（22.2% of 35,110,881,225）；
      verify `--max-groups 3` 实读 6 文件 / 316,447,064 B / 96.715 s，确认 158,223,532 B；
      scan 101.761 s / 0 B；`deleted_bytes=0`；`protected_unchanged=true`；
      原件 SHA/size/mtime、config sha、catalog 大小与 mtime、catalog 目录清单全部不变。
- [x] 两份报告留在 `.planning/n5-raw-duplicate-audit/`（1,048,267 B / 1,046,591 B，均 ≤1MiB）。
- [x] 性能与正确性修复：候选组才做 realpath（observe 222 s → 96 s）；
      报告 1MiB 上限改为"写入前最后一次变更 + 与 write_json 同参数度量 + 13 位占位符二分"。
- [x] ruff `tools/raw_duplicate_audit` 全绿。
- [x] 集中一次 Unit/Integration/E2E 验收（命令见 handoff）。
- [x] 集中验收（最后一次，与提交内容一致）：`python -m pytest tools/raw_duplicate_audit/tests -q --no-header -p no:cacheprovider` → 31 passed / 150.40 s；`python -m ruff check tools/raw_duplicate_audit` → All checks passed；`git diff --check` → 干净。
- [ ] 提交代码 + `docs/implementation/handoffs/N5-RAW-DUP/{HANDOFF.md,handoff.json}`。
- 测试临时 root：pytest basetemp 由根 `conftest.py` 管理；本 lane 没有留下临时目录，
  本机绝对路径输出写在系统 temp（未进 Git）。
