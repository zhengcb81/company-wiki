# CI Contract 红灯修复交接卡（2026-10-02）

> 给后续模型/agent 的接手说明。先按本卡继续，不要重做已完成根因分析，也不要放宽来源哈希、证据绑定或其他业务校验。用户要求：大节点验证即可，不要为每个小修改新增审查节点。

## 当前事实

- 分支：`master`；上次读取时本地 `HEAD` 与 `origin/master` 都是 `1504d6a`。
- 最近远端 Actions：run `37012332197`（commit `1504d6a`）。Python 3.11/3.12/3.13 的 Unit tests 全部通过；Contract tests 三个版本均失败。
- 该 run 的 Contract 失败身份：
  - `tests.contract.test_zr203_reader_rewire::test_read_entrypoints_never_construct_catalog_store`
  - `tests.contract.test_zr1003_shadow_assertions::test_c2_recorded_review_unblocks`
  - `tests.contract.test_source_catalog_temp_worker_governance::test_stop_does_not_touch_unowned_live_workers_or_temporary_files`
  - `tests.contract.test_fc905_receipt_envelope::test_pi09_envelope_to_dict_deterministic`
  - `tests.contract.test_fc905_receipt_envelope::test_pi02_reviewed_detected_and_ignored_forwarded`
  - `tests.contract.test_fc905_receipt_envelope::test_pi01_reviewed_not_detected_forwarded`
- 本地有未提交修改，当前修改范围为测试、CI 诊断、门禁和本计划文档；生产原文、raw、配置和数据库没有改动。
- 本轮直接运行受影响用例：**33 passed in 9.28s**。收窄后的 `metadata-reader-contracts` pre-commit hook 实际运行并通过。
- 本轮随后对远端最新六项失败身份做独立复跑：**6 passed in 4.37s**（Windows/Python 3.13.9）；新增的短路径集成回归门也通过。
- pre-push 的 pytest 临时目录 bug 已被证实并修复于当前工作树：旧随机目录长度超过 60 字符、被 conftest 重定向到用户 Temp，且 CI gate 隐藏了重定向证据；现在使用 `tmp/pp*`，验证 `relocated=false` 和 run root 清理。
- 早先一次 `python tools/pre_push_gate.py` 曾因终端会话断开而无结果；该次进程和专属目录已清理。随后修正 basetemp 根因后，本轮完整门禁已重新运行并全部 GREEN，且真实 pre-commit hook Passed。

## 六项失败的根因与当前处理

| 失败 | 判断 | 当前工作树中的处理 |
|---|---|---|
| ZR-203 reader rewire | `d5162e5` 已有意移除 `_remediation_pending`，因为补救提案状态不再阻断读取；AST 测试仍把已删除方法列为入口。 | 从结构性入口清单移除该方法，继续检查 `resolve` 不构造 writer。 |
| ZR-1003 C2 review receipt | 测试沿用旧的“仅填 status/reviewer/evidence hash”形状；当前写入合同要求 SHA-256 格式、source/policy 双绑定、证据载荷与 hash 一致并复核扫描 verdict。 | 只修正测试 fixture，填入有效 source SHA、policy hash、evidence payload 和匹配 hash；生产校验没有放松。 |
| Worker temp governance | 测试在默认 `paused` 状态下期待 stop 删除外来 runtime/lock，和当前“暂停时保留、显式 resume 才 reconcile stale 文件”的行为矛盾；测试标题及安全描述要求不要触碰外来 worker。 | 断言外来 PID 未被终止且 runtime/lock 内容原样保留。 |
| FC905 三项 | 远端失败；此前 WSL/Python 3.12 相同三项均通过，说明仍有远端/本地差异，根因未证实。当前远端注解没有异常类。 | reporter 已在工作树增加从 JUnit `failure.message` 安全提取异常类名的 fallback；只输出 testcase identity 和异常类，不输出异常正文。新增隐私回归测试。必须由下一次 Actions 结果继续定位。 |

## 为什么 pre-commit 没拦住

1. 这轮 Contract 失败的三项过期测试不在当时的 commit hook 三模块范围（shared reader、FC905 receipt、B10）内；hook 是按改动路径触发，不是全量 Contract CI。
2. FC905 三项虽然在重点集合中，但 WSL/Python 3.12 本机结果是通过；因此本地 hook 没有复现远端 Linux matrix 的差异。
3. pre-push gate 也只跑选定高风险 contracts，并不运行整个 Contract matrix。之前的 GREEN 只证明所选测试通过，不代表 CI 全集通过。
4. Windows 默认 `%TEMP%` ACL 会使 pytest fixture setup 失败。commit hook 现复用 `tools/pre_push_gate.py` 的短 workspace basetemp、UTF-8 和 cache-provider 设置；仍只跑三个 reader/receipt/B10 模块。完整 Unit 放在 push 前，广泛 Contract 放在远端 CI，避免每次提交运行整个矩阵。
5. 本机 pre-commit cache 位于用户配置目录且当前只读。执行 `pre-commit` 命令本身时需可写 cache；本轮用临时 `PRE_COMMIT_HOME` 完成了验证。这是本机环境问题，不是远端失败的根因。
6. 原门禁所称“短 basetemp”并不短：仓库路径约 34 字符，`.pp-` 加随机 suffix 约 36 字符，总长约 71，触发 `conftest.py` 的 60 字符重定向。成功 pytest 的输出被 `_run` 捕获，GREEN 日志未显示 `relocated=true`；本轮真实 cleanup 回执为 `removed=false`。当前修复移至 ignored `tmp/` 短 run root，并要求可见证据确认没有重定向及执行后已删除。

## 接手后按此顺序完成

1. **先确认状态和差异**：`git status --short`、`git diff --check`、查看本卡列出的工作树修改。不要 reset、clean 或改动 raw/数据库/生产配置。
2. **跑聚焦 hook**：`python tools/pre_push_gate.py --metadata-reader-contracts-only`。该命令覆盖 reader/receipt/B10 三个模块及本轮三项 Contract 回归，使用仓库 `tmp/` 短隔离目录并检查未重定向及清理。需要验证真实 hook 时再运行 `pre-commit run metadata-reader-contracts --files ...`；若默认 cache 只读，用 workspace 临时目录设置 `PRE_COMMIT_HOME`，不要把环境故障误判为测试失败。
3. **本机集成验收已完成**：本轮 `python tools/pre_push_gate.py` 全部通过，包含静态检查、全量 Unit、既定重点 Contract 和本轮三项失败回归；所有 pytest 阶段均验证 `relocated=false` 且 run root 清理完成。真实 pre-commit hook 也已通过。
4. 把修复、诊断 helper、hook 和 PWF 更新一起做一次普通提交并推送 `origin/master`；不使用 `--no-verify`、force push 或绕过 hook。用户已授权正常提交/推送。
5. **唯一最终验收点**：核对新 Actions run。Unit 与 Contract 的 3 个 Python 版本以及 workflow 其他必需 jobs 均绿，任务才算完成。WSL 当前返回 `E_ACCESSDENIED` 且未发现 Docker/其他 Python minor runtime；若 FC905 仍失败，使用本次修复后的 reporter 读取异常类，并以 GitHub Linux matrix 为依据定位。不得仅因 Windows 本机通过就关闭，也不得仅因诊断 reporter 通过就关闭。
6. 最后把最终 commit、Actions run 和绿灯状态写回 `task_plan.md`、`findings.md`、`progress.md` 和本入口 README，然后停止。只在这个集成验收节点做一次整体确认，不增设逐文件/逐小步骤签收。

## 本轮未提交文件

- `.pre-commit-config.yaml`
- `tools/pre_push_gate.py`
- `tools/summarize_junit_failures.py`
- `tests/unit/test_summarize_junit_failures.py`
- `tests/contract/test_zr203_reader_rewire.py`
- `tests/contract/test_zr1003_shadow_assertions.py`
- `tests/contract/test_source_catalog_temp_worker_governance.py`
- 本交接卡和同目录 PWF 更新

