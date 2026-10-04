# G1-LEGACY progress

- 状态：**完成并已推送**。实现提交 `1cf8183`，交接提交 `23a2e6a`，
  分支 `codex/g1-legacy-entry-retirement` → origin（pre-push 门 GREEN）。
- 分支：`codex/g1-legacy-entry-retirement`（worktree `Projects\company-wiki-g1-legacy`，基线 `1cfec10`）。

## 已完成

1. 基线复现：config_doctor plain=0 / `PYTHONPATH=scripts`=78；38×2 trap 矩阵（见 findings.md）。
2. RED：`tests/unit/test_legacy_entrypoint_simplification.py` 首轮 15 failed / 99 passed（51s）。
3. 实现：
   - `scripts/writer_policy.py`：删除 `legacy_writer_authorized`；支持集合静态化
     （CONTROL 加入 `config_doctor.py`，SOURCE 只留两个 narrative pilot）；
     `legacy_script_execution_allowed` 结果只取决于分类，`environment` 仅兼容保留；
     混合入口 blocked 文案不再提示环境变量。
   - `scripts/common.py`：`require_legacy_writer_permission` 文档改为静态分类语义（行为仍委托 writer_policy）。
   - `tests/unit/test_writer_freeze.py`：移除双因素测试与 `legacy_writer_authorized` 导入；来源 pilot 参数表只留两个。
   - `tests/unit/test_common.py`：新增 `TestLegacyWriterPermission`（4 个生产 caller 恒 False、支持工具恒 True、混合恒 False，5 组环境变量不变）。
4. 退役：`git rm` 六个一次性工具 + 5 个专属测试 + `tests/support/derived_archive_fixture.py`（共 12 个路径，仅 worktree 内 Git 代码）。
5. 集中验收（一次）：
   - `python -m pytest tests/unit/test_writer_freeze.py tests/unit/test_common.py tests/unit/test_legacy_entrypoint_simplification.py -q` → **142 passed（55s）**
   - `python -m ruff check <6 个目标文件>` → All checks passed
   - `git diff --check` / `git diff --cached --check` → rc 0
6. 附加核对：config_doctor plain/`PYTHONPATH=scripts` 均 rc0；`tests/contract/test_legacy_caller_reachability.py` 25 passed / 1 failed
   （唯一红灯 `test_non_r1_source_compatibility_keeps_explicit_override_contract`，按卡 §6.1 属 MAIN 改写项）；
   `tests/unit/test_clean_env_gate.py` + `tests/test_config_doctor.py` 18 passed。

## 未完成 / 移交

- 交接文档：`docs/implementation/g1-legacy-entry-retirement-handoff.md`（含写集外发现：refine guard 不可达、
  5 个脚本 `-S` guard 不可达、auto_discover guard 前读配置、source_catalog_pilot_check guard import 未调用、混合入口分类）。
- MAIN 侧（卡 §6）：Contract 新语义、clean_env_gate 旧变量收口、历史引用、合入主线。
