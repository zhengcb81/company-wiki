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

## C 节点（2026-10-24）：测量与基线外发现

四类范围同机实测（数据见 `delivery/w13/scope-report.json`）：docs 44.5s / narrow 66.8s / unknown 46.6s（改造前该类约430s → 46.6s）/ wide 628.6s 撞既有600s上限 exit 124（closed-list路径与改造前逐字节相同：同执行器、同targets、同上限，非回归；按G09不拉长超时）。真实 `git push` 新分支走真实 hook 42.2s 绿、defer语义正确。

完整本地模式一次：ruff/compileall/host guard 绿；config_doctor 红于本worktree无 `.source_catalog` 运行时数据目录（基线同现，环境限制）；units 8126 passed/24 skip/19 失败——19个全部是 xdist -n 2 下原子写 `*.json.*.tmp` 的 FileNotFoundError，3个同文件串行复跑58/58绿（执行器路径本包未动，Windows并发抖动类）；focused contracts 221 passed/3 失败——全部是 `test_b10_read_chain.py` ratchet，其扫描输入 src 与基线字节一致（`git diff a31300a7..HEAD -- src/ scripts/ config/` 为空），即基线已红。

超出本包的业务问题（按INTERFACES上报，不在本包修）：
1. `tests/contract/test_b10_read_chain.py` 三个 ratchet 在基线 a31300a7 即失败：`test_b10_no_new_column_value_handoff`（新列值调用点 assertion_service.py::restore_document_facts 等7处未登记）、`test_b10_handoff_baseline_has_no_stale_entry`（基线仍列3个已不传列的站点）、`test_b10_no_new_confirmed_direct_reader`（narrative_artifact_store.py::NarrativeArtifactReader.visible_subject_metadata）。复现：`python -m pytest tests/contract/test_b10_read_chain.py -q`（focused contracts 日志 delivery/w13/logs/full-mode-focused-contracts.log）。责任层：ROOT/来源源码 ratchet 登记。
2. 新worktree环境限制：config_doctor 需要 `.source_catalog` 数据目录（fresh worktree 必红）；完整本地模式的 units/focused 阶段在本机存在 xdist tmp-file 并发抖动（19例，串行全绿）。完整模式验收以 GitHub CI（ubuntu）为准，本机结果作诊断。
