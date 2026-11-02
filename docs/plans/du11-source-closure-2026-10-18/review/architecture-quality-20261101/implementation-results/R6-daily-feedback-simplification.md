# R6 daily push 快反馈简化

状态：**作者实施及工具域验证通过，等待 ROOT 同节点独审/正常发布**。候选工区 `tmp/architecture-r2`，基线 HEAD `a6841e9420dbe3eb6dac6e30563c29e4293a31e7`。ROOT 正常 push 的旧失败日志保留于 `.planning/architecture-quality-20261101/r6-publication/r3-candidate-push.log/json`：总耗时234.764s，旧32/379文件策略加固定smoke实际收集1787case，在98%因180s子进程预算超时；不是已观察到断言失败。文件数不是测试工作量，AST选测也占启动时间。

本次只改daily --push-checks策略及其测试/开发说明：文档range 0pytest，其他range固定FAST_CONTRACT_CASES一次。保留现180s/输出界、child失败红、precommit静态、CI全unit与固定contracts；changed_unit_tests保留独立分析工具。没有新真实push时，不声称新策略实际push耗时。

## 共用根因与新责任

旧正常push日志明确 `planned 65 targets`：只取32/379已知影响文件、347已知文件和281非unit建议留给CI。即使“只有32个文件”，每个文件可包含大量parametrized case，因此实际1787case；依赖图构建另需遍历AST，不能把文件数量上限当作日常反馈工作量上限。

现在 `--push-checks` 只读取原有完整Git ref范围的 changed_paths，然后做字符串路径的正向文档分类：

- 空的已知改动集、明确根文档、docs下md/rst/adoc、既有docs/plans与.planning归档：0 pytest，输出tests_not_run，不宣称GREEN或local_fast_pass。
- 代码、测试、配置、mixed range、未知suffix/位置、无法比较的range：同一份原 `FAST_CONTRACT_CASES` 一次。没有全仓rglob/AST图，没有自动追加单元文件、32 cap或whole-file与node去重策略。
- `local_fast_pass` 只签固定smoke；输出明确change-specific tests由作者在实施时运行，完整Unit/合同与真实E2E留给原CI和大节点。当前ROOT已有433/262相关测试的事实由ROOT原收据维护，本工具不重跑或代签。

删除冗余 `_push_targets` 和 `DAILY_PUSH_MAX_AFFECTED_TARGETS`；删除只证明旧known-consumer日常策略的 `test_known_push_scope.py`，重写旧cap测试为实际main策略正反控。`changed_unit_tests.py` 字节未变，独立分析与真实选测测试仍保留且已运行。`docs/OPERATIONS.md` 改为真实hook `--push-checks` 入口和新的范围说明。

## TDD 与测试

1. **RED先于产品实现**：新增main行为断言，给Path.rglob装禁止调用的反控。正常宿主结果 **6 failed / 9 passed，6.19s**：代码、config、显式unit、379文件、mixed及未知文件均实际进入旧全仓图；None/纯文档与原失败传播已有正确行为。RED工区trace指向候选tools路径。
2. **GREEN**：只跑工具自有必要域、保留的独立selector测试及三个实际child失败/输出溢出例，**173 passed，121.78s，exit0**。时间包含多次隔离bare-repo的真Git hook push及其fixture smoke，不是“新候选远端push耗时”，也不是固定167案例的单次性能测试。
3. 真实隔离Git hook验证固定smoke成功后允许推送、固定节点失败阻止并保留远端HEAD、纯归档文档0pytest、早期代码+最后文档仍按整个push range执行smoke、缺runner拒绝。另一个smoke外故障证明本地smoke可通过，而显式完整unit会失败，防止把窄通过说成全面通过。
4. 180s daily总子进程deadline、stdout4MiB/stderr512KiB、失败实际exit code/诊断、输出溢出red及临时根cleanup行为保留。另以只读AST对比HEAD证明FAST_CONTRACT_CASES、CURRENT_CI_REGRESSION_CASES、deadline/caps、`_run`、`_run_pytest_gate`、`_dispatch_gate`、`_open_scratch` 的执行AST均未变化。
5. 所有变更Python的Ruff通过，定点diff-check通过。没有跳hook、提高timeout、删CI或删固定smoke节点；没有新候选branch push或完整源码CI运行。

实际GREEN命令（cwd=候选工区）：

```powershell
& C:/Miniconda/python.exe -B -X utf8 -m pytest tests/unit/test_daily_push_bounds.py tests/unit/test_daily_push_policy.py tests/unit/test_pre_push_gate.py tests/unit/test_pre_push_parallel_phases.py tests/unit/test_ci_push_selection.py tests/unit/test_changed_resource_scope.py tests/unit/test_pre_push_temp_scope.py tests/unit/test_pre_push_process_cleanup.py::test_child_failure_keeps_actual_exit_code_and_diagnostic tests/unit/test_pre_push_process_cleanup.py::test_output_overflow_is_bounded_red_with_retained_progress -q --tb=short --basetemp C:/Users/郑曾波/Projects/company-wiki/tmp/dg-green-d9b04ca5/g
```

该命令是历史精确收据，目录已经清理，不应原样复用。测试进程TEMP/TMP/TMPDIR使用可写短Projects根供现有fixture分配并自行清理独占子目录。下一轮使用新的已核owned根，并加 `-p no:cacheprovider` 避免outer pytest刷新工程缓存。

最初测试根误选 `C:/Windows/Temp/cwdg-red-3b92d500`，mkdir被环境拒写；该次8P/7setup errors只属于测试入口错误，不计产品RED。此路径确认未创建/不存在，未改ACL。已改为项目内明确owned根且用terminating errors防止创建失败后继续执行。

## 延迟改善的边界

已消除全仓依赖图构建与自动追加32文件的两段工作量；固定清单仍35个target（约167案例来自此前观察，不是本次新采集），不再随379文件扩大到1787case。预期返回原固定smoke的反馈量级，取消旧图扫描开销；**没有凭此保证某台主机N秒，也没有编造新正常push测量**。ROOT完成独审后以一次正常候选push及其精确CI记录实际效果。完整CI、相关变更测试和真实公司验收仍各负其责。

## 隔离清理与未触碰范围

已记录初始absent、解析后的绝对containment、非reparse检查，只删除本次明确owned目录：

- `C:/Users/郑曾波/Projects/company-wiki/tmp/dg-red-fbefbd03`：after=false，RED退出1。
- `C:/Users/郑曾波/Projects/company-wiki/tmp/dg-green-d9b04ca5`：after=false，GREEN退出0。

fixture的临时Git仓库、bare remote、生成smoke文件均在owned根内删除；临时短scratch另有既有fixture的contextmanager/存在性断言验证。不把pytest默认cache等同已自动恢复：outer pytest没有事前绑定 `.pytest_cache` 初态，故本次**不声称工程所有ignored缓存字节已恢复**，不猜路径删除历史文件；明确owned测试资料已恢复为absent。

未操作真实仓库Git/index/分支/main PWF，未改源语义owner、模型、原件、生产配置、凭证或数据库。只在owned测试仓库中做Git commit/push以验证hook。原 `.githooks/pre-push` 的外来100755→100644模式WIP仍原样保留，未改内容或mode；它的旧影响文件选测注释未由本作者越权改写，实际入口仍委托新工具。

## 冻结SHA-256

| 文件 | SHA-256 |
| --- | --- |
| `tools/pre_push_gate.py` | `2604bae33ae3b79d523fadb11a11d555fc6c78d78ea98750db1293ecf0614f45` |
| `tests/unit/test_daily_push_bounds.py` | `c044e231ef13a7c8f5994618659402aacc1bdc273c49bdf897ee685b3dc36301` |
| `tests/unit/test_daily_push_policy.py` | `44b20bd704689d673c572a7593740afa1421d6c977c8714e51e2e785760ff6cc` |
| `tests/unit/test_pre_push_gate.py` | `656c93f4845a8998b23f89c3dae0df557db08956b5a7c10bc512e74a400dccbd` |
| `tests/unit/test_pre_push_parallel_phases.py` | `a2923c0c6c518fbf0187d464bfdc1c2cbf27425f7e28669baacad2ffdf00f9aa` |
| `tests/unit/test_ci_push_selection.py` | `2aa294da3e441012c0236aece8cd859cbe08dcdf90cb48091d92c66d4249fcee` |
| `docs/OPERATIONS.md` | `ad4cbf7902e163ed09071cdfd46cb5ea2768d209902954942c567816f2bc8792` |
| `tests/unit/test_known_push_scope.py` | 删除，仅旧日常自动选测策略测试 |

保留的独立工具 `tools/changed_unit_tests.py` 为 `2715957cc38cd953908aba5fb7d15f7961aaa8ec5f24eca3204d0ce831563f30`。

作者 **STOP**；ROOT负责集中独审、正常提交/推送与真实候选CI，不把本工具收口冒称源语义/C/T3或公司循环已完成。
