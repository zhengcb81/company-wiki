# G4-CWP-PIPELINE — Findings

**Base**：`5930a644453ed46494c2c83c5ecfb97767fa9492`（worktree 已建，分支 `codex/g4-cwp-pipeline`，原仓有未提交 G2 获取线，非本包依赖、未触碰）。

## 1. 旧族现状（开工时事实）

- `scripts/full_pipeline.py`（377 行）：module-level `from common import ...`、`from gate_system import ...`（含 5 个 gate 具名 import），末尾 `_enforce_legacy_writer_freeze(__name__, __file__)`。`main()` 先 `require_legacy_writer_permission` 再 argparse。`python -S` 下 gate_system→yaml 不可用 → ImportError，属于 `PRE_GUARD_CRASH[("full_pipeline.py","nosite")]` 记录的“守卫不可达”缺陷。
- `scripts/gate_system/**`：11 文件、2786 行（base/registry/config_loader/diagnostics/retry + 5 gates）。
- `config/pipeline_rules.yaml`（257 行）：Gate0–5、approval_threshold、human_review、escalation 路由。

## 2. Caller 清单（rg/结构核对）

### gate_system 生产 caller
- **仅** `scripts/full_pipeline.py`（import）。stage1–6/scheduler 均不引用 gate。
### gate_system 测试 caller
- **仅** `tests/unit/test_gate_system.py`。
### pipeline_rules.yaml 消费者
- **仅** `scripts/gate_system/config_loader.py` + `tests/unit/test_gate_system.py`。
- `scripts/config_doctor.py` 只校验 `config/source_catalog.yaml`（CI 依赖，不受影响）。

### full_pipeline.py 的引用（全部核过）
| 位置 | 性质 | 处理 |
|---|---|---|
| `scripts/test_framework.py:109,139` | 子进程调用（自身 mixed-frozen） | 超出写集 → main_wiring 记录 |
| `scripts/batch_process.py:110` | 子进程调用（自身永久退休） | 同上 |
| `src/company_wiki/deployment.py:219` | 退役报告条目 | 本包改（§4.3） |
| `scripts/writer_policy.py:76` | PERMANENTLY_RETIRED 分类 | 保护文件，不改（stub 仍被 78 拦） |
| `scripts/common.py` | require_legacy_writer_permission | 保护文件，不改 |
| `tests/unit/test_writer_freeze.py:81` | explicit_orchestrators 含 full_pipeline + `len(guarded)>=49` | 本包同步 |
| `tests/unit/test_legacy_entrypoint_simplification.py:102` | PRE_GUARD_CRASH 例外 | 本包移除 |
| `tests/unit/test_deployment.py:226-246` | 报告内容断言 | 本包同步 |
| `tests/unit/test_common.py:190` | permission 恒 False（common 层） | 不受影响，保持绿 |
| `tests/contract/test_legacy_caller_reachability.py:27,177,304-310` | inventory 冻结 + permission + **源码须含 `enforce_direct_cli` 字面量** | **不在写集 → stub 必须满足** |
| `tests/contract/test_lt_uj_e2e.py:329` | 无关同名 fixture（无 scripts/full_pipeline 引用） | 无影响 |
| `tests/unit/test_pipeline.py:428` | 无关同名 mock 管道测试 | 无影响 |

### hook/CI/wiring
- `.pre-commit-config.yaml`、`.github/workflows/ci.yml`、`pyproject.toml`、`tools/pre_push_gate.py`：**无任何 gate_system / pipeline_rules / full_pipeline 引用**。
- CI `ruff check ... scripts ...` 覆盖新 stub；`scripts/*.py` 有 E402/E741/F401 per-file-ignore。
- `tests/integration/test_full_pipeline.py` 是纯 PDF `classify→extract→validate`（pdf_extract_v3），与旧 Pipeline 无关，保留。

### 文档（不在写集 → main_wiring 建议 MAIN 删除/改写）
- `docs/GATE_SYSTEM.md`（大量 gate_system/pipeline_rules 引用）、`docs/使用说明书.md`（115/262/481/688 行）。
- `artifacts/gates/*.json`：历史审计快照（只读事实记录），不删。

## 3. 关键约束推导

1. **stub 只能 import stdlib + writer_policy**：`tests/contract/test_legacy_caller_reachability.py`（不在写集）要求源码含 `enforce_direct_cli`；`blocked_message`（永久退休版）同时含 `LEGACY WRITER BLOCKED` 与 `PERMANENTLY RETIRED` 且已推荐 `company-wiki-source-catalog`。writer_policy 自身纯 stdlib、零初始化（D1）。
2. **direct CLI 输出须含三标记**：`LEGACY PIPELINE` 侧标记 `LEGACY_PIPELINE_RETIRED` 由 stub 自打，`LEGACY WRITER BLOCKED`/`PERMANENTLY RETIRED` 来自共享 blocked_message（D2 顺序：先自打行 → enforce exit78）。
3. **harness 断言**（test_legacy_entrypoint 对全部 PERMANENTLY_RETIRED 参数化）：exit78 + `PERMANENTLY RETIRED` + 无 trap → 用共享 blocked_message 即可满足，无需改断言体。
4. **test_writer_freeze**：stub 无 writer pattern → 从 `explicit_orchestrators` 移除后自然跳过；`len(guarded)>=49` 按卡删除，改为“每个 direct CLI 脚本要么在现行支持名单、要么被冻结”的行为检查（非新固定数）。
5. **test_gate_system.py 整体退休**：全部为旧框架行为（状态机/重试/人工升级/配置路由/固定分），无现行接口价值；来源价值反例（页数/max_pages/质量分）已由 `tests/integration/test_full_pipeline.py` 覆盖 → 不新建迁移测试（D3）。
6. **部署报告**：legacy_entries 4 条形状不变；status/reason 换为“已退休 + 现行来源 CLI 推荐”（`company-wiki-source-catalog`、`company-wiki-source-read/query/export-v2`、有限叙述运行说明），不推 scheduler/ingest/migration。

## 4. RED 前基线观察（真实复现）

- `python -S scripts/full_pipeline.py --company 示例 --stage review --no-gates` → 当前：ImportError 崩溃（gate/yaml），非 78。
- `generate_retirement_report()` 当前 4 条全部 `replacement: scheduler.py/ingest.py/migration.py`（旧 writer），`status: blocked`。

## Errors Encountered

| Error | Attempt | Resolution |
|-------|---------|------------|
| rg 不在 git-bash PATH | 1 | 改用 Grep 工具/`grep -rn` |
| resolver PWF_PLAN_ROOT 钉住后指向 `.planning/<id>` 不存在 | 1 | 按卡 fail-closed：显式调用传相同 PlanRoot，注入为空即不竞争；计划文件直接放 `docs/implementation/g4-cwp-pipeline/` |
