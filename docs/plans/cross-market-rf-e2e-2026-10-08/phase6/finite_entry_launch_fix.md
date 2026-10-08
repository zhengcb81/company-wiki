# 有限叙述配置入口真实启动修复（2026-10-09）

状态：隔离实现与集中验证完成；尚未提交、并线、发布或重新执行 NVDA。本项由主协调员在当前四路审查封存后集成，不代表公司审计已通过。

## 范围与根因

- 工作树：`C:/Users/郑曾波/.codex/worktrees/audit-provider-cause/company-wiki`。
- 初始 Git HEAD：`ade1d9912d5801e3e25a94d88a181190afdddb31`，初始状态干净。
- 真实执行暴露的症状：`scripts/narrative_batch_configured.py --help` 被 `LEGACY WRITER BLOCKED` 拦截。
- 该入口只把 `Config.load` 的权威模型配置组合到有限来源处理 CLI；不生成投资研究或 legacy Wiki。
- 当真实启动环境的 `PYTHONPATH` 同时包含 `src/` 和 `scripts/`，Python 启动时加载 `scripts/sitecustomize.py`。静态入口分类遗漏已经正规化的 `narrative_batch_configured.py`，因而它被误判成未知混合 legacy 条目。
- 既有配置单元测试只 import 并直接调用包装器；既有 CLI 端到端子进程仅设置 `PYTHONPATH=src/`。两者都未覆盖实际启动钩子，因此过去的绿色结果无法证明此入口可启动。

## TDD 与实施

1. 先新增真实子进程 `--help/-h` 测试，工作目录只含隔离 sentinel，不加载生产 `.env` 或真实密钥；同时覆盖研究 writer、退休工程工具、未知混合入口在旧许可变量存在或不存在时仍退出 78。
2. 将既有完整有限 CLI 测试的启动环境改为 `src + scripts`，保留本地 HTTP、原件哈希、真实有限 worker、配置权威性与 resume 不重复请求等断言。
3. RED：11 个目标用例中 5 FAIL / 6 PASS。两个 help 子进程实测退出 78；三套配置组合用例在启动输出解析处失败（被阻断后不再输出 JSON）。六个真正冻结入口负例均 PASS。
4. 实现只将 `narrative_batch_configured.py` 加入现有 `SOURCE_WORKFLOW_TOOL_ALLOWLIST`，并说明其规范来源职责。没有改变 `sitecustomize`、退休列表、未知条目的默认分类、运行预算或配置加载器；没有新增许可环境变量。
5. GREEN：同一 11 个目标用例全部 PASS，19.28 秒。MiniMax、MiMo、DeepSeek 为配置档名和本地 HTTP 测试，使用伪密钥，不是外部供应商请求；MiMo 仍验证从配置 fallback 选择，请求文件中的旧模型设置不能覆盖配置。
6. 大节点集中回归：177 PASS / 1 deselected，93.72 秒。唯一 deselected 为明确依赖只读真实原件和 RF 检出目录的 `real_data` 用例，未伪造其输入或将其标记 PASS。

## 可复现命令

工作目录为上述隔离工作树，Python 采用 UTF-8 和禁写 bytecode。目标测试：

```powershell
python -X utf8 -B -m pytest -q tests/unit/test_finite_configured_entrypoint_launch.py tests/integration/test_narrative_batch_cli_e2e.py::test_configured_entrypoint_uses_existing_loader_through_real_worker_and_resume --basetemp .test-tmp/finite-entry-launch-green
```

集中回归：

```powershell
python -X utf8 -B -m pytest -q tests/unit/test_finite_configured_entrypoint_launch.py tests/unit/test_narrative_model_config.py tests/unit/test_writer_freeze.py tests/unit/test_legacy_entrypoint_simplification.py tests/unit/test_g5_legacy_checks_retirement.py::test_writer_policy_gives_the_six_names_their_own_retirement_category tests/unit/test_g5_legacy_checks_retirement.py::test_retired_engineering_tool_is_never_allowed tests/integration/test_narrative_batch_cli_e2e.py -m 'not real_data' --basetemp .test-tmp/finite-entry-launch-regression
```

测试框架按已有 Windows 短路径规则将 basetemp 重定位到本机短临时目录，三次执行均打印 `removed=true`。原始 XML 属一次性测试资料，提取下述计数与 SHA 后删除；不长期保存重复日志或模型请求体。

### 实际 JUnit 摘要（删除临时 XML 前提取）

```json
[
  {
    "phase": "red",
    "tests": 11,
    "failures": 5,
    "errors": 0,
    "skipped": 0,
    "elapsed_seconds": "5.512",
    "xml_sha256": "e45d21788d7e4be3964acf562dc689ebe7ebcb601a7b1022490088231b6d2842"
  },
  {
    "phase": "green",
    "tests": 11,
    "failures": 0,
    "errors": 0,
    "skipped": 0,
    "elapsed_seconds": "19.283",
    "xml_sha256": "33551666c8b6ab144bb2bee1e6fa1a7bafbada255c01e9fa87525f2f79bd7cc9"
  },
  {
    "phase": "regression",
    "tests": 177,
    "failures": 0,
    "errors": 0,
    "skipped": 0,
    "elapsed_seconds": "93.720",
    "xml_sha256": "acab7c294f17a5d7523d6aa18e74eebc28123b10daf5b460c1f2f7e53dc7d1c1"
  }
]
```

## 交接、边界与剩余验收

变更文件只有：

- `scripts/writer_policy.py`
- `tests/unit/test_finite_configured_entrypoint_launch.py`（新增 8 个真实启动/冻结用例）
- `tests/integration/test_narrative_batch_cli_e2e.py`（真实启动环境与更明确的误拦截断言）
- 本记录

配置文件、下载原件、其他仓库、安装副本与 Dayu 均未修改；供应商调用数 0、供应商费用 0。完整有限 CLI 夹具验证原件、配置与不属于本批次的任务未变，运行子目录在 `finally` 删除并恢复 sentinel 基线。此次不是 NVDA 或其他公司的经济模型验收，也不能据此宣称供应商账户、真实资料覆盖或公司预测已经通过。

主协调员下一步：审查这四个路径、在当前循环审查封存后集成，再由新的真实 executor 使用修复后的入口继续执行；任何公司级数据、经济假设和其它根因仍按独立审查结果处理。本工作树不提交/不推送，交由主协调员统一并线。
