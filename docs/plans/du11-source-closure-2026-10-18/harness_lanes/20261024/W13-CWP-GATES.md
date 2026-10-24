# W13-CWP-GATES：推送快反馈与完整验收分层

**可以立即开工，与W14/W15及ROOT并行。** 独占工作目录 `C:/Users/郑曾波/Projects/company-wiki-w13-gates`，分支 `codex/w13-cwp-gates-20261024`。源码基线 `a31300a70215319e6bcf3a03d32b2882bdf1aeaa`。设置 `PLAN_ID=w13-cwp-gates-2026-10-24`、`PWF_PLAN_ROOT=docs/plans`，只维护本工区对应子PWF。完整读[共同接口](INTERFACES.md)；母计划状态只作背景，不接管annual14。

## 问题与结果

当前正常代码push在 `select_unit_tests` 的全量fallback下跑8126单测/24既有skip，耗389.84秒，另有146契约smoke42.09秒；远端CI再次全量。纯文档push154项45.17秒。`.pre-commit-config.yaml`说明“push affected、CI full”，但动态执行/未知配置/宽依赖很容易使日常push退化为full。反复加并发和时限不能消除重复责任。

交付一个简单明确的层级：commit继续静态检查；日常push做有界快反馈；完整本地模式及远端CI保留全量。**本地快速通过只证明本次确实运行的范围，不能打印成全量验收成功。** 这是修改测试执行政策，不是删测试、绕钩子或新增人工许可。

## 写范围

允许：`tools/pre_push_gate.py`、`tools/changed_unit_tests.py`、`.githooks/pre-push`；`tests/unit/test_ci_push_selection.py`、`test_changed_resource_scope.py`、`test_changed_test_module_scope.py`、`test_pre_push_temp_scope.py`、`test_pre_push_parallel_phases.py`、`test_pre_push_full_unit_workers.py`；新增 `tests/unit/test_daily_push_policy.py`；`.pre-commit-config.yaml`仅同步注释/说明；`docs/plans/w13-cwp-gates-2026-10-24/**`、`delivery/w13/**`。

禁止：所有`src/**`、业务scripts、模型/预算/来源config、`.github/workflows/**`、测试fixture/金标/业务断言、其他测试、母PWF、公司原件/DB、安装目录。ROOT并行修改来源源码；不要rebase到移动主线追着它改，不修改全量CI的集合。

## 固定行为要求

| ID | 必须实现和证明的行为 |
|---|---|
| G01 | 保留 `.githooks/pre-push` → `python tools/pre_push_gate.py --push-checks` 入口及真实Git ref stdin；不加跳过环境变量、人工授权文件或仅凭缓存绿灯 |
| G02 | 日常push不会隐式启动整个`tests/unit`。小且可解释的受影响文件集可运行完整文件；宽依赖/配置/未知range采用固定关键smoke，并明确其余委托全量CI。不要任意截断列表声称受影响测试完整，也不要再造复杂依赖证明系统 |
| G03 | 保留现有`FAST_CONTRACT_CASES`的全部成员，日常push复用该集合并去重同一test/file执行；它也被远端`--fast-contracts-only`使用，禁止从共享常量删成员来减少远端覆盖。原样smoke实测约45秒，主要收益来自移除本地重复full；若仍慢，报告剩余开销，不借本卡删业务测试 |
| G04 | 保留 `python tools/pre_push_gate.py` 的完整本地模式与 `--fast-contracts-only --junitxml PATH` 的远端调用合同。完整模式仍执行原本完整单测/静态检查/指定合同，不能缩集合；完整模式保留有界worker与自有TEMP清理 |
| G05 | 输出本地模式/实际targets/未运行范围与原因；用 `local_fast_pass`/`full_validation_pending`等明确语义。完整mode绿和快速mode绿的文案不同，不再无条件称“safe”或全工程通过 |
| G06 | 任一确实运行的测试、子进程启动、timeout、异常失败都返回非零并保留首个真实失败；不能吞失败再说留给CI。现hook在runner文件缺失时exit0也应修成明确非零，并用临时Git反控实际证明。快速mode的范围不足作为诊断，不恢复成权限门 |
| G07 | ref删除、多ref、new branch、未知old SHA、空stdin、rename/delete、docs-only、工具/配置/源码/测试变更有清晰行为；既有选择函数可继续返回full建议，但push政策层应显式决定快速反馈，不把建议当成日常full命令 |
| G08 | 在真实临时Git仓/本地bare remote调用hook，注入“快集合内真失败”确认push失败；并在独立完整模式证明“快集合外失败”仍会被全量发现。保留旧指纹/业务断言；原本只断言“每push必须full”的调度政策测试应按新规范先TDD调整 |
| G09 | 大节点集中测实际耗时：同一机器、同一固定范围记录docs/narrow/wide/unknown。目标日常push通常≤60秒，先减少重复责任；这是实测优化目标，不加易抖动的墙钟审批阈值或拉长超时 |

## A/B/C实施顺序

**A**：读`select_unit_tests`、`pre_push_gate.main`、hook及上述测试；记录当前选择和实际测试集合，不需再花六分钟复跑已留证基线。先写政策分层和失败回传的RED反控；写清固定smoke/受影响测试的选择规则，尽量复用现有函数。

**B**：把调度政策与pytest执行/自有TEMP分开；修改既有入口，不新建第二套hook。小函数只决定mode/targets/deferred_reason，runner负责执行和真实退出码。保留现有完整执行器；不要把代码源身份/旧hash变成门禁。

**C**：集中跑下列相关测试，真实临时Git push E2E和完整本地模式各一次，记录完整mode全集/skip与失败反馈。调用独立agent审查所有G01–G09、产品diff、正反例、性能证据和清理；全部修复后对最终代码补审，再交接。

```powershell
python -m pytest -q --tb=short -p no:cacheprovider tests/unit/test_ci_push_selection.py tests/unit/test_changed_resource_scope.py tests/unit/test_changed_test_module_scope.py tests/unit/test_pre_push_temp_scope.py tests/unit/test_pre_push_parallel_phases.py tests/unit/test_pre_push_full_unit_workers.py tests/unit/test_daily_push_policy.py
python -m ruff check tools/pre_push_gate.py tools/changed_unit_tests.py tests/unit/test_ci_push_selection.py tests/unit/test_changed_resource_scope.py tests/unit/test_changed_test_module_scope.py tests/unit/test_pre_push_temp_scope.py tests/unit/test_pre_push_parallel_phases.py tests/unit/test_pre_push_full_unit_workers.py tests/unit/test_daily_push_policy.py
python tools/pre_push_gate.py
```

新增测试包含真实hook E2E；用自有短TEMP，测试前后sentinel不变。全部失败场景均做清理。完整本地模式是C节点一次验收，不恢复为每commit/push全量。已有测试若揭示超出本包的业务问题，按INTERFACES报具体复现，不改业务文件或放宽断言。

## 交接

固定 `delivery/w13/handoff.md/json`；另有 `scope-report.json`（四类Git范围的实际targets、deferred范围/原因、退出码、耗时、测试数量）和 `review.md/json`。独审必须绑定最终代码commit及变更文件SHA；实现者不能自评。可推本codex分支，ROOT负责并线并核主线CI。包完成仅表示调度层正确且更快，不表示ROOT annual14已完成。
