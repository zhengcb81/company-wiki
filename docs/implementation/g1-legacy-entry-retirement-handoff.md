# G1-LEGACY 交接：旧入口许可收敛与已完成运维工具退役

## 1. 版本与分支

| 项 | 值 |
|---|---|
| 仓库 | `C:\Users\郑曾波\Projects\company-wiki`（worktree `C:\Users\郑曾波\Projects\company-wiki-g1-legacy`） |
| base（代码基线） | `1cfec10786d8703c45fef24388a9cda1114b6165` |
| 实现 head | `1cf818364e39cd43de1d6d355764804fc01ef434` |
| 分支 | `codex/g1-legacy-entry-retirement`（本交接文档为该分支随后单独提交；分支最终 head 见 `git log -1`） |
| 计划文档基线 | `376ed90` |

## 2. 精确改动清单

修改：

```text
scripts/writer_policy.py            # 删除 legacy_writer_authorized；静态分类；混合入口文案去环境变量
scripts/common.py                   # require_legacy_writer_permission 文档改静态分类语义（委托不变）
tests/unit/test_writer_freeze.py    # 移除双因素测试与 legacy_writer_authorized 导入；来源 pilot 参数表只留 2 个
tests/unit/test_common.py           # 新增 TestLegacyWriterPermission（环境不变性）
tests/unit/test_legacy_entrypoint_simplification.py   # 新增本卡测试 114 项（责任包合计 142）
.planning/g1-legacy-entry-retirement-20261004/**       # 局部 PWF
docs/implementation/g1-legacy-entry-retirement-handoff.md  # 本文
```

退役删除（仅 worktree 内 Git 代码，12 个路径，`git rm` 已暂存于实现提交）：

```text
scripts/retire_source_catalog_db.py     scripts/cutover_source_catalog_db.py
scripts/audit_catalog_retirement.py     scripts/audit_catalog_consumers.py
scripts/retire_catalog_snapshot.py      scripts/retire_derived_archives.py
tests/unit/test_retire_source_catalog_db.py
tests/unit/test_retire_catalog_snapshot.py
tests/unit/test_retire_derived_archives.py
tests/integration/test_retire_catalog_snapshot_e2e.py
tests/integration/test_retire_derived_archives_e2e.py
tests/support/derived_archive_fixture.py
```

未改动：`src/**`、生产配置/原件/数据库/retirement 记录、共享 Contract 测试、CI/pre-commit、AGENTS。
`scripts/sitecustomize.py` 无需修改（与脚本自身 guard 共用同一策略函数）。
生产 retirement 记录（9 份小事实记录）不在 Git 跟踪内，本包未触碰。

## 3. 支持 / 永久退休分类（交付后）

- **支持（直接执行，无环境许可）**：`CONTROL_TOOL_ALLOWLIST` 9 项
  （`architecture_gate`、`clean_env_gate`、`config_doctor`（新加入）、`legacy_observer`、
  `recovery_baseline`、`secret_audit`、`semantic_gate`、`snapshot_manifest`、`wr109_step6_capture`）
  + `SOURCE_WORKFLOW_TOOL_ALLOWLIST` 2 项（`narrative_evidence_pilot.py`、
  `narrative_summary_review_pilot.py`）。六项已完成一次性退役工具已移出支持集合。
- **永久退休（永远退出 78，环境无法恢复）**：`PERMANENTLY_RETIRED_SCRIPTS` 38 项，清单未变。
- **混合旧入口（未正规化，保持冻结，不因“不在永久列表”放行）**：57 项，见
  `.planning/g1-legacy-entry-retirement-20261004/findings.md` 完整清单。要点：
  - 自带 guard 的 13 项（`collect_reports`、`test_framework`、`collect_news`、`graph`、`search`、
    `run_downloader`、`status_tracker`、`stage1/2_extract`、`fix_report_dates`、`audit_config`、
    `build_extracts`、`source_catalog_pilot_check`）在普通与 `PYTHONPATH=scripts` 两种启动下结果一致（78）。
  - 无 guard 的直跑 CLI（如 `lint.py`、`monitor.py`、`state_store.py` 等）：plain 放行、
    sitecustomize 拦截 —— 与基线一致，属未完成正规化，**由 MAIN 决定归支持集或补 guard 调用**。

## 4. 公开函数行为（固定对主线接口）

| 接口 | 行为 |
|---|---|
| `enforce_direct_cli(module_name, script_path, environment=None)` | 签名保留；支持入口直接执行，不读两枚环境许可；永久退休与混合入口退出 78 |
| `legacy_script_execution_allowed(script_path, environment=None)` | 签名保留（含薄兼容 `environment`，显式 `del`）；结果=纯分类函数，任何环境值不改变结果 |
| `is_legacy_script_cli(script_path)` | 保留：scripts/ 下非支持、非 sitecustomize/writer_policy 的直跑 .py 为 True |
| `common.require_legacy_writer_permission(script_name)` | 签名保留；永久退休 caller（4 个生产 caller 全部）恒 False，支持工具恒 True，混合恒 False；仍只打印一次警告 |
| `legacy_writer_authorized` | **已删除**（无真实 caller 后） |
| `blocked_message` | 永久退休文案不变（仍含 `PERMANENTLY RETIRED` / Environment overrides cannot re-enable）；混合文案不再出现 `COMPANY_WIKI_WRITE_MODE` / `COMPANY_WIKI_LEGACY_WRITERS` 指引 |

## 5. 测试命令与结果（一次集中验收）

```powershell
$env:PYTEST_ADDOPTS='-p no:langsmith_plugin'
python -m pytest tests/unit/test_writer_freeze.py tests/unit/test_common.py tests/unit/test_legacy_entrypoint_simplification.py -q
#   => 142 passed in 55.12s
python -m ruff check scripts/writer_policy.py scripts/sitecustomize.py scripts/common.py tests/unit/test_writer_freeze.py tests/unit/test_common.py tests/unit/test_legacy_entrypoint_simplification.py
#   => All checks passed!
git diff --check        # rc 0（staged 与 unstaged 均 0）
```

测试证明要点：

- 支持工具在无许可 / 双变量齐全 / 仅单变量 / deny 值 / `os.environ` 下结果恒 True；38 个永久退休恒 False；混合恒 False。
- config_doctor `--help`：plain 与 `PYTHONPATH=scripts`、有/无 legacy 环境对，4 组合全部 rc0（基线为 0/78）。
- 38 个永久退休入口 × {plain, `python -S`} =76 次 trap-harness 运行：69 次退出 78；
  其余 7 次（`refine.py` 两种启动；`build_links`/`full_pipeline`/`generate_index`/
  `generate_slides`/`stage3_analyze` 的 `-S`）在 guard 之前的模块级 import 处死亡
  （`G1-ERROR`，rc≠0）—— 属 §6 写集外既有缺陷，测试以显式例外集钉住，且证明其
  未触发写入 / socket / LLM / 配置 trap；非例外运行全部无写入、无 socket 连接、
  无 LLM 客户端初始化。
- 六工具与专属导入链退出（文件不存在、`find_spec` 为 None、scripts/ + tests/ 无字面残留）；两个来源 pilot `--help` 两种启动 rc0。
- `git status --porcelain` 全部路径 ⊆ 卡片写集 ∪ 退役删除集；删除项只在 `scripts/`、`tests/`。
- 隔离夹具（原件 raw + state + log）在 legacy 环境对下运行被拦入口后快照不变。

附加核对（非责任包）：

- `tests/contract/test_legacy_caller_reachability.py` → **25 passed / 1 failed**；唯一红灯
  `test_non_r1_source_compatibility_keeps_explicit_override_contract`（期望 `collect_reports`/`test_framework`
  在 legacy 对下为 True）—— 按卡 §6.1 由 MAIN 改为新静态支持/退役语义。
- `tests/unit/test_clean_env_gate.py` + `tests/test_config_doctor.py` → 18 passed。

## 6. 写集外发现（只报不改，建议 MAIN 处理）

1. `scripts/refine.py`：guard 不可达 —— 模块级 `from extract import clean_text`（`scripts/extract.py`
   已不存在），plain/`-S` 均 ModuleNotFoundError 而非 78。建议补 guard 前移或修复/退役该入口。
2. `-S` 下 guard 不可达（模块级第三方 import 先失败，但仍在配置/LLM/网络/写入之前）：
   `build_links.py`、`full_pipeline.py`、`generate_index.py`、`generate_slides.py`、`stage3_analyze.py`。
   建议把 `enforce_direct_cli` 调用前移到这些 import 之前。
3. `auto_discover.py:324`：模块级 `TOPIC_KEYWORDS = load_topic_keywords()` 在 guard 之前读
   `config_rules.yaml`（trap 矩阵唯一配置读取违例）。建议改为惰性加载。
4. `source_catalog_pilot_check.py:752`：`enforce_direct_cli` 只 import 未调用（`# noqa: F401`），
   plain 放行而 `PYTHONPATH=scripts` 被 sitecustomize 拦截。建议二选一：纳入支持集合或补调用。
5. `src/company_wiki/deployment.py:223-244` 仍把 `COMPANY_WIKI_LEGACY_WRITERS=allow` 写进
   rollback 提示（src 禁改，未处理）。
6. MAIN 侧既有事项（卡 §6）：Contract 新语义、`clean_env_gate.py` 旧变量收口、
   AGENTS/总 PWF 历史引用、源层 archive/prune CLI 漏 `now` 的入口缺陷。

## 7. 临时根与恢复

- 本包未创建任何持久临时根；测试全部使用 pytest `tmp_path`（pytest 自动回收）与
  `%TEMP%` 下的会话 basetemp（根 conftest 既有 fallback 清理机制）。
- harness 脚本写入各测试的 `tmp_path`，随 pytest 会话清理，无 finally 残留风险。
- 生产 `config/source_catalog.yaml` 会话前后 SHA 断言（既有 session fixture）通过；
  本包未写穿生产 YAML，未运行任何退休/切库/切库烟测命令。
