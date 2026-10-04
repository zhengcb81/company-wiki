# G1-LEGACY 旧入口许可收敛与运维工具退役 — 任务计划

- 卡：`docs/plans/narrative-evidence-pilot-2026-09-26/harness_lanes/g1_legacy_entry_and_retirement.md`
- 基线：代码 `1cfec10`，计划文档 `376ed90`；worktree `C:\Users\郑曾波\Projects\company-wiki-g1-legacy`，分支 `codex/g1-legacy-entry-retirement`
- 局部 PWF（本目录）为唯一本卡状态；主仓/CWP/RF/FF/ET 等一律只读。

## 步骤

1. [x] 读卡、AGENTS、writer_policy/sitecustomize/common/相关测试；CodeGraph/rg 核 caller。
2. [x] 复现双启动差异：`python scripts/config_doctor.py --help`=0，`PYTHONPATH=scripts` 时=78。
3. [x] 基线扫描 38 个永久退休脚本 plain/`-S` 两种启动与 trap 矩阵（配置/LLM/网络/写入）。
4. [x] 先 RED：新增 `tests/unit/test_legacy_entrypoint_simplification.py`。
5. [ ] 收敛 `writer_policy.py`/`common.py`（删除 `legacy_writer_authorized`，静态支持/退役分类，环境值不改结果）。
6. [ ] 退役六脚本 + 专属测试链（12 个路径，仅 Git 代码）。
7. [ ] 同步 `test_writer_freeze.py`、`test_common.py`。
8. [ ] 一次集中验收：三测试文件 pytest + ruff + `git diff --check`。
9. [ ] 交接 `docs/implementation/g1-legacy-entry-retirement-handoff.md`；commit/push 本分支。

## 验收命令

```powershell
$env:PYTEST_ADDOPTS='-p no:langsmith_plugin'
python -m pytest tests/unit/test_writer_freeze.py tests/unit/test_common.py tests/unit/test_legacy_entrypoint_simplification.py -q
python -m ruff check scripts/writer_policy.py scripts/sitecustomize.py scripts/common.py tests/unit/test_writer_freeze.py tests/unit/test_common.py tests/unit/test_legacy_entrypoint_simplification.py
git diff --check
```
