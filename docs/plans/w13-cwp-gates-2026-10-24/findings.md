# W13-CWP-GATES 调查记录

源码基线 `a31300a70215319e6bcf3a03d32b2882bdf1aeaa`。实际问题、需求ID、写范围和输入接口以中央卡为准。bootstrap只新建独立工区/PWF，未实施产品、未运行测试、未调用模型或下载。

后续记录：实际根因、反控、边界问题和修复证据；不改ROOT中央run或母PWF。

## A 节点（2026-10-24）：现状与根因

- 卡内基线引用（不重跑）：代码push全量fallback 8126单测/24skip/389.84s + 146契约smoke42.09s；纯文档push 154项45.17s。
- `tools/changed_unit_tests.py` 的 `select_unit_tests` 在 config/`tools/`/资源/dynamic/未知range等宽场景返回全量建议 `["tests/unit"]`（reason 如 "configuration or test entrypoint changed"、"unknown push range"）。
- `tools/pre_push_gate.py --push-checks` 把该建议当命令执行：`selected == ["tests/unit"]` 时经 `_run_parallel_pytest_gates` 隐式启动整个 `tests/unit`（约390s）+ smoke。这就是"日常push退化为full"的根因；policy 层缺失，选择函数的建议被直接当调度。
- `.githooks/pre-push` 在 `tools/pre_push_gate.py` 缺失时 echo 后 `exit 0`（G06违规：runner缺失静默放行）。
- 完整本地模式 `python tools/pre_push_gate.py`（ruff/compileall/config_doctor/host guard/全量单测/focused contracts）与远端 `--fast-contracts-only --junitxml` 是独立合同，均不经 push 路径；本卡不改其集合。
- `FAST_CONTRACT_CASES` 共 29 条（22 个不同文件），为远端与本地共享常量（G03不得删成员）。
- narrow 路径现状（affected files + smoke去重，单gate）与 docs-only 路径（仅smoke）已经是有界快反馈，保留并成为唯一push行为；全量建议路径改跑固定smoke并把其余显式委托CI。
- 附带发现（不属本包，不改业务）：无。

## 反控与期望冻结（RED先行）

- 新增 `tests/unit/test_daily_push_policy.py`：policy 纯函数（mode/targets/deferred）、G02不变量（push targets 永不含 "tests/unit" 全量元素）、G03成员保全与去重、G04完整模式/junitxml不缩集合、G05两种绿文案+local_fast_pass/full_validation_pending语义、G06失败/子进程启动失败/异常非零、G07各Git范围行为、hook缺失runner非零+stdin透传、真实临时Git push E2E（快集合内真失败→push被拒；绿路径通过；unknown范围+快集合外失败→push绿但声明full_validation_pending且直接全量命令抓到失败）。
- TDD 调整两条断言"每push必须full"的旧测试（G08授权）：`test_ci_push_selection.py::test_push_failure_is_propagated_and_suites_are_not_duplicated`、`test_pre_push_parallel_phases.py::test_full_push_dispatch_keeps_every_existing_case_exactly_once`，其余旧指纹/断言保留。
- 全量建议路径退役后 `_run_parallel_pytest_gates` 失去唯一调用者；按"简单明确层级"删除该调度器，`test_pre_push_parallel_phases.py` 改写为单阶段push调度合同（失败传播、无隐式第二阶段、自有TEMP）。`_run`/`_run_pytest_gate` 完整执行器与其有界worker/TEMP合同不动。
