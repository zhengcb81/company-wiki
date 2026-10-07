# main_wiring — G5-CWP-CHECKS

本卡未发现需要跨白名单修改的运行 caller。全仓 grep（`import/from <module>` +
`scripts/<name>.py` 路径字符串，排除 `artifacts/gates/*.json` 历史快照与 `docs/`）确认
六个旧 CLI 的全部消费者都在写集内的测试文件里。下面列出**写集外**的引用与接线事项，
供 MAIN 在合入时核对；`action` 取值与 `handoff.json.main_wiring[]` 一致。

| repo | path | action | symbol | reason |
|------|------|--------|--------|--------|
| company-wiki | `src/company_wiki/deployment.py` | no_change | `LEGACY_ENTRIES`（含 `"batch_process.py"` 字面量，约 :239） | 退役报告只输出名字字符串，不依赖文件存在、不 import；`src/**` 禁写。可复现反例：`python -m pytest tests/unit/test_deployment.py -q` → 全绿（实测含于 1955 passed 的整套 unit）。 |
| company-wiki | `docs/implementation/g4-cwp-pipeline/{retirement_map.json,handoff.json,main_wiring.md,findings.md,HANDOFF.md}` | verify | `scripts/test_framework.py:109,139`、`scripts/batch_process.py:110` | G4 交付把二者记为「仍以子进程命令串引用 `scripts/full_pipeline.py`，自身冻结不可执行，建议下一卡整族退休」。本卡即那一卡：两个外壳已变成退休薄壳，命令串随实现一起消失。历史交付文档按卡不在写集内，不回改；MAIN 合入后可按需标注已解决。 |
| company-wiki | `docs/contracts/legacy-caller-reachability-v1.md` | verify | `test_framework.py`（:83、:111 混合旧入口清单） | 合同文档把 `test_framework.py` 列为「未正规化混合旧入口」；本卡后它属于工程退休类别，`legacy_script_execution_allowed` 仍为 False（合同的行为结论不变，分类措辞已过时）。文档不在写集内。 |
| company-wiki | `control/architecture.json` | no_change | `scripts/architecture_gate.py:87`（`--config` 默认值） | 已按卡删除：全仓唯一代码消费者就是退休工具本身；`.pre-commit-config.yaml` / `.github/workflows/ci.yml` / `.githooks/pre-push` / `tools/pre_push_gate.py` 均无引用。`artifacts/gates/*.json` 中的命中是不可变历史快照，禁止回改。 |
| company-wiki | `artifacts/gates/*.json` | no_change | `control/architecture.json`、六个 `scripts/*.py` 条目 | 历史收据含旧文件 sha/清单，属 immutable raw 语义，不得因本卡编辑。 |
| company-wiki | `.pre-commit-config.yaml` | no_change | `files:` 正则 `^(src/\|tests/unit/\|tests/contract/\|tests/e2e/\|scripts/).*\.py$` | 已覆盖本卡新增的 `tests/unit/test_g5_legacy_checks_retirement.py` 与 `scripts/*.py`；`tests/support/`、`tests/integration/`（除已列名）、`tests/acceptance/` 不在 ruff scope，已单独手跑 `ruff check` 全绿。hook 禁写，无需改。 |
| company-wiki | `.github/workflows/ci.yml` | no_change | `CLI smoke test`（`collect_news.py --help` → 78 + `LEGACY WRITER BLOCKED`） | 该冒烟针对 `collect_news.py`，不在本卡六名之内，行为未变；本卡六名由 `tests/unit/test_g5_legacy_checks_retirement.py` 覆盖。CI 禁写。 |
| company-wiki | `.githooks/pre-push` / `tools/pre_push_gate.py` | no_change | `--fast-contracts-only` 清单 | 清单不含 gold/gate 测试；实测 `python tools/pre_push_gate.py --fast-contracts-only` → GREEN。二者禁写。 |
| company-wiki | `scripts/sitecustomize.py` | verify | `enforce_direct_cli("__main__", sys.argv[0])` | 无需改动：三个 gate 移出 `CONTROL_TOOL_ALLOWLIST` 后自动被拦截，`blocked_message` 新分支给出工程退休 banner。实测 plain 启动 exit 78 + `LEGACY_ENGINEERING_TOOL_RETIRED`。 |
| company-wiki | `scripts/config_doctor.py` | verify | `catalog_dir` / `security_master` 检查 | 环境事实（非本卡回归）：`.source_catalog/` 被 `.gitignore` 忽略，新鲜工作树没有该目录，本地直跑 `PYTHONPATH=src python scripts/config_doctor.py` 会报 `catalog_dir is not a directory` 并 exit 1；`CI=true` 时该分支被跳过（`scripts/config_doctor.py:57`），实测 `CI=true PYTHONPATH=src python scripts/config_doctor.py` → `OK` exit 0，与 CI 环境一致。本卡未改 `config/**` 与 `config_doctor.py`。 |
| company-wiki | `tests/unit/test_deployment.py`、`tests/contract/test_gold_corpus.py` | no_change | `batch_process.py`（名字断言）、gold 语料扫描 | 未在写集内改动；实测全绿。 |

## 未接线/无 caller 的结论

- 六脚本在 `scripts/`、`src/`、`tools/`、`tests/`（写集外）、hook、CI、pyproject 中
  **没有任何生产或工具 caller**，因此没有需要 MAIN 追加的工程清单接线。
- G4 记录的 `test_framework.py:109,139` / `batch_process.py:110` → `full_pipeline.py`
  残余子进程调用，随本卡整族退休一并消失，不再需要 MAIN 决定。
- 本卡没有引入新的 CLI、flag、用户权限或签名 schema；不需要改 `pyproject.toml` 的
  `[project.scripts]`。
