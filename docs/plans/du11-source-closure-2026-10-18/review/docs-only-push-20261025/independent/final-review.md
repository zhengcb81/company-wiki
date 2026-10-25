# 纯文档推送快路径：最终独立审查

## 结论与范围

**PASS，当前修改无未解决的产品问题。** 初审 P2 `TRUSTED_EMPTY_SCOPE` 已在范围分类器责任层修复；初审反例、失败收据均保留。结论仅覆盖本次 pre-push 文档快路径、范围分类与对应测试，不代表公司内容、摘要、RF 或整个项目已经验收。

最终审查对象为 `tools/pre_push_gate.py`、`tools/changed_unit_tests.py`、`tests/unit/test_daily_push_policy.py`、`tests/unit/test_ci_push_selection.py`。四份文件完整 SHA、证据 SHA 和逐项结论见同目录 `final-review.json`。独立探针执行前后源码 SHA 一致；终审再次核对一致。hook 和 CI 文件内容与既有版本一致。本节点不扩审 ROOT 正在独立施工的 A05 源码。

## 首次问题及闭环

旧分类器会把根 `config.yaml`、未知 `startup.ps1`、`misc/runtime.json` 当作无行为变更。旧 gate 仍会合并 smoke，本次提前退出若直接信任该空结果，会把既有漏分类扩大成实际漏测。初审已真实复现并立即交回 ROOT，记录在 `initial-findings.json`。

最终方案修复 `select_unit_tests`：先保留既有归档根处理，再仅扣除明确根文档 README/CONTRIBUTING/CHANGELOG/AGENTS.md 与 `docs/` 下 md/rst/adoc；其余未知资源继续保守判断。没有在 gate 按 reason 文字或对单个 `config.yaml` 打补丁。ROOT 留存的 scope-red 为 **14 FAIL / 11 PASS**，证明新增反例在修前失败；当前独立根配置、文档加配置、未知命令、未知 JSON、provider 配置、未知 range 等检查均通过。

## 逐项复核

| 项目 | 结论 | 依据 |
|---|---|---|
| 可信文档空目标 | PASS | `_push_targets` 返回空；`main` 在 runner 分发前返回，日志为 `tests_not_run`，不宣称 GREEN 或测试已通过。没有空参数 pytest 调用。 |
| 未知/运行配置 | PASS | 根配置、未知资源和 src/tests 下 Markdown 不因扩展名或附带计划文件变成免测；保留现有 smoke/full 建议。 |
| 完整推送范围 | PASS | `changed_paths` 未改。独立真实 Git commit 范围包含“先代码、后文档”的较早代码；实际 gate 仍分发相应测试并传播失败。 |
| 实际 Git/hook 联调 | PASS | ROOT 隔离仓测试覆盖纯计划 push、前一未推代码失败加最后文档 commit；后者 remote ref 不前进。独立探针不冒充该端到端证据。 |
| CI 与显式 full | PASS | 实际分发探针保留 CI smoke 一次分发、full 六阶段；workflow/hook 内容未改。 |
| 失败与启动错误 | PASS | 既有失败传播、runner 缺失/启动失败、未知动态范围断言保留；唯一环境失败原断言定点复测通过。 |
| 旧测试调整 | PASS | 将“纯文档必须跑 smoke”的过期前提改成真实 runtime/unknown 输入；覆盖成员、失败、CI/full、去重等断言没有删除。通用 `docs/receipt.json` 改成明确归档 `docs/plans/run/receipt.json`，符合收紧后的责任边界。 |
| 文档和清理 | PASS | README 已纠正最终四文件范围与分次验证结果；独立与 ROOT 收据的自有临时目录均恢复不存在。 |

## 验证证据与分次边界

1. ROOT 首批 TDD：3 FAIL；修前的分类器反例：14 FAIL / 11 PASS。初版 105 PASS 属于分类器修复前版本，不用于替代最终验收。
2. 最终四相关测试文件主跑：**129 PASS / 1 FAIL，160.84 秒**，wrapper 167.48 秒。唯一失败为 `test_real_push_with_missing_gate_runner_is_blocked`：Git 自带 sh 在 hook 启动前发生 `NtCreateDirectoryObject` 环境错误，没有到达缺 runner 断言。
3. 保留原断言、源码不变，只在主机定点复跑该一例：**1 PASS，3.36 秒**，wrapper 7.29 秒；`environment-rerun-receipt.json` 记录 exit 0、cleanup=true。准确边界是 **129 项主跑通过 + 1 项定点环境复跑通过**，不能描述成一次 130 项全绿。
4. 独立 `independent_probe.py` 使用自有真实本地 Git 提交和真实 `changed_paths` / classifier / gate 分发入口。八项检查全部 PASS，故意拦截 runner 并模拟 exit 7 检查传播，没有重复 ROOT 的 pytest/Git-push E2E。外网调用 0、pytest 子进程 0；源码前后相同、临时 Git 仓恢复不存在。

独立探针曾有两项自身环境问题，均留在 `review-notes.md`：启动路径缺 repo sys.path，以及 Windows Git 对象只读造成清理重试。只修自有探针和精确验证的自有目录，最终收据在修复后重跑产生；两者不归作产品缺陷。

## 发布边界

可以由 ROOT 提交、推送本次四文件与相关 PWF/审查证据。本审查未测量真实网络推送总耗时；证明的是可信纯文档范围不再启动 smoke，而不是所有 Git 操作零延迟。CI/full 仍保持原运行方式。本次不重新审查其他源码节点，不覆盖旧 A13 内容报告，也不宣称正式摘要或 RF 通过。
