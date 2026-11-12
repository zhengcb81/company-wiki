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
