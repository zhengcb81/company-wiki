# DU-ROOT 进度日志

## Session 1 — 2026-10-13

### 已做

- 建立 ROOT worktree：`_harness_worktrees/document-understanding-20261013/root`，
  分支 `codex/du-root-integration-20261013`，base `7f6f7cbd`。
- 核验三 lane 现状：
  - STRUCTURE：已实现并提交（f35c5806 / f8f456a3），47 测试绿。
  - PROFILES：已实现，138 测试绿，**未提交**，无 handoff → 交由子代理收尾。
  - BENCH：已实现，47 测试绿，**未提交**，无 handoff → 交由子代理收尾。
- 合并 structure lane 到 ROOT（本地集成，未并 master）。

### 新增（ROOT 独占）

- `src/company_wiki/document_understanding/__init__.py`（上层包，只导出 build_observation）
- `src/company_wiki/document_understanding/observation_adapter.py`
  现有 parser units → du-input/1；补 DU-S-ADAPT-1/2/4/6
- `src/company_wiki/document_understanding/orchestration.py`
  structure → 依赖闭合的可预算包（du-packages/1）
- `tests/unit/document_understanding_root/`
  - `test_du_root_integration.py` 25 项（合成，常跑）
  - `test_du_root_real_samples.py` 10 项（`-m real_data`，真实原件）

### Adapter 关闭的缺口

| 缺口 | 状态 | 证据 |
|---|---|---|
| DU-S-ADAPT-4 表头/caption | **关闭** | `row_index==0` → `table_header`；`单位：` → `table_caption`；`table_id = p{page}:t{idx}` |
| DU-S-ADAPT-2 column | **关闭** | 真实几何测列：恒锋/名创均得到 lane 0/1；跨栏块给 None |
| DU-S-ADAPT-6 table_id | **关闭** | 同上 |
| DU-S-ADAPT-1 heading_level | **部分** | 编号标题可判（第X节/一、/（一）/Item N.）；**无编号标题仍无法判** |

### 真实发现（推翻计划假设）

**名创 p12 的左右栏语言方向与计划 design.md 的描述相反。**

design.md 写「中英左右栏」。实测：**左栏 (x0≈57) 是英文，右栏 (x0≈349) 是中文**。
两栏各自语言统一，不存在跨栏的同位中英对。
因此 `language_parallel` 跨栏不触发是**正确行为**，不是缺陷。
真实的中英并排对（`As of December 31,` / `截至12月31日`）在**同一栏内**相邻。

→ 已把这个事实写进测试断言，不再沿用 design.md 的错误假设。

**恒锋 p62→63 两期建设保留成功**：`（四）项目建设周期` 包内含
「一期2019年1月拿地…2021年1月一期建成投产。二期…预计2021年1月启动建设…2022年二期建成投产」，
跨页未断。这正是不对称计划里说基线漏掉的「建设期」。

### 未关闭

- **DU-S-ADAPT-1 剩余部分**：无编号纸质标题（如 `Store Network`）需要 parser 保留字号证据。
  真实 parser 只留 bbox/pdf_block，丢弃 span 字号。不做几何猜测（会误伤同页同样短的表格片段）。
  这是需要改 parser 的真实工作项，不是 adapter 能补的。
- **DU-S-ADAPT-5 QA 双套单元**：仍需 ROOT 决定保留哪套角色。

### 测试结果

- `pytest tests/unit/document_understanding_root -q` → **35 passed**（含 10 项真实）
- `pytest tests/unit/document_understanding_root tests/unit/document_understanding_structure -q` → **72 passed**
- ruff：All checks passed
