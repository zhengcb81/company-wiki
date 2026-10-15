# 进度

2026-10-15 ROOT 已创建独立稀疏工作树、复制施工卡/接口/真实观察。READY，未实施、未运行本卡测试；不继承主线工程通过结论。

2026-10-15 DU4-FORM 作者实施完成，STOP 等 ROOT 接收。实际命令与证据：

- 环境确认：`PYTHONPATH=src python -B -c "import company_wiki; print(list(company_wiki.__path__))"` → 指向本工作树 `src`（Python 3.13.9 / pytest 9.1.1 / ruff 0.15.18 / mypy 1.19.0）。
- A（RED）：接口骨架 `source_signals/{__init__,contract}.py` 建立后运行 `PYTHONPATH=src python -B -m pytest -q tests/unit/du4_source_signals` → 54 failed / 14 passed，失败全部为语义断言（38 处显式 AssertionError，0 import 错误）。回执：`results/red-a-semantic-counterexamples.log`。
- B（实现与集中验证）：`collect_source_signals` 完成 bounded pure collector（表单/轮次证据、scope、reserved_unit_ids、预算计费、observed_counts）。同一命令 → **72 passed / 0 failed / 0 skipped**。回执：`results/green-b-concentrated-tests.log`。真实夹具 sha256 对照 `fixtures/manifest.json` 复核通过（`test_saved_observations_match_manifest_hashes`）。
- 独立质量审查（review agent 全量核对 card/INTERFACES/handoff 并重跑三条命令）：整体 PASS、无阻断项；2 个 minor 缺陷（斜杠字面值 `10-Q/A` 声明比较误拆分、预算耗尽时冲突诊断被跳过）与 3 处测试加固（大量前导普通单元、无 visibility 的 DEI、空标签断言）已全部修复并回归，重跑 72 passed / ruff clean / mypy clean。
- C（静态检查）：`python -m ruff check src/company_wiki/document_understanding/source_signals tests/unit/du4_source_signals` → clean（`results/green-c-ruff.log`）；`MYPYPATH=tests/unit/du4_source_signals python -m mypy src/company_wiki/document_understanding/source_signals tests/unit/du4_source_signals` → no issues in 9 files（`results/green-c-mypy.log`）。
- 交接：`handoff.md` / `handoff.json`（接口实例已逐字段核对真实输出）。未测范围：生产 E2E、VRSK 原件重放、真实 transcript/8-K holdout 均属 ROOT，本卡 NOT_EVALUATED。
- 边界遵守：只写 `src/company_wiki/document_understanding/source_signals/**`、`tests/unit/du4_source_signals/**`、本 PWF；无生产写入、无供应商调用、未改配置/CI、未动兄弟目录。
