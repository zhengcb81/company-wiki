# PDF ROOT补丁交叉独审（独立于PDF实现）

原作者基线 `dc423843`；首审 `_w22r/tools/pdf_runtime_deployment/deployment.py` raw/LF SHA 均为 `7e818ba766b36e8c7fc612826e728f7aa04cf3aa8b7798f04147264f9d7236e6`，与ROOT指定一致。

审查读取deployment.py、README、test_w22_pdf_reception.py及其mini_source/FakeVenv依赖，并逐差分对照作者提交。没有启动SDK、真实venv、模型、网络或部署环境；未修改实现。

## 首轮结论：NEEDS_FIXES

八个独立fake反例在获准host Python执行，6通过、2真实失败（首次sandbox机械调用因junction/hardlink拒写不可判，改为同命令host执行，没有改测试或绕过平台拒绝）。完整结果在 `pdf-cross-results-initial.json`，复现脚本 `pdf-cross-counterexamples.py`。

通过项：blocking_errors plan在写目录前拒绝；旧tool SHA plan不得自动重绑定；output_config逃逸在写前拒绝；空target junction拒绝且referent空；恢复env junction拒绝且旧receipt未改；缺失interpreter走修复而非REUSED。

未关闭项：

- **[P2] 损坏解释器仍REUSED。** `_reconcile_fully_consistent:567-570`仅核python.exe存在与pyvenv隔离；将完成树解释器改成`NOT AN INTERPRETER`仍REUSED。receipt未冻结scaffold字节，不能保证当前venv可用。
- **[P2] 改变venv解释器home仍REUSED。** pyvenv.cfg改为`home = C:/different-python`并保留`include-system-site-packages = false`，仍REUSED。隔离开关正确不证明scaffold身份相同。

ROOT已交原PDF审查agent定点修复，待新工具SHA复审；不能把旧版本6P/2F称最终通过。

## 其余判断

`_require_real_paths`在build/deploy/write_receipt校验所有已有祖先、最终路径lstat/reparse属性；对本轮静态目录替换反例，在任何目标写入前拒绝。未做并发目录置换攻击或SDK真实性检验，不扩大为安全对抗认证。

`load_plan`校验blocking_errors、精确tool_identity、绝对target及owned output_config，阻断旧失败plan与旧工具plan的静默部署。旧部署/constructor/E2E收据仅证明其作者工具版本和配置的历史执行；当前补丁改变implementation SHA，应重新build计划并对当前版本做独立验证，不因修复文件相同路径就把旧实测证据升级。

OCR当前README的ROOT reception corrections明确写明历史receipts仅exploratory PARTIAL、600秒请求、累计超30分钟、holdout被pilot使用不可通过改代码/标签追认，且存储值相同不证明compute parity；满足本轮“历史result不等于严格within-card/盲holdout”的说明需求。本审查未改历史JSON。

所有junction由用例finally移除后才清理解析确认归属的`.ocr-cross-tmp`；`temp_removed=true`。无作者tree/cache、ROOT生产src、共享PWF变更。

## 最终定点复审：PASS（仅工具机制域）

独立PDF agent修复后的deployment.py raw/LF SHA 均为 `9487ca8179f422ad562287ed8346156da4572aa31eb7ec176aa5f333ccf8a1b9`。与原指定7e818ba7版本分开绑定，不抹去首审缺陷。

新实现第508-525行先核收据中python.exe与pyvenv.cfg双SHA，不同在复用/恢复写入前TargetConflict；旧COMPLETE缺绑定诚实拒绝。第549-552行恢复缺文件后须重新匹配旧SHA；COMPLETE/INCOMPLETE保留绑定，不把本机新scaffold自动代签旧解释器。已读新增参数化篡改测试和legacy无绑定测试，未参与实现。

相同八个独立fake反例只更换预期工具SHA后重跑，**8/8通过**（host命令1.56秒），最终 `pdf-cross-results.json`；首轮6P/2F仍单独保存。损坏解释器与修改home均被拒绝，原marker保留。临时`.ocr-cross-tmp`不存在，SDK/真实部署均未启动。原部署与E2E历史证据仍只支持原工具版本，不能因本轮机制修复直接升级为新版本完整实测。

顺带复核ROOT OCR三处datetime修正：manifest/run_comparison/run_x1仅把Python3.11新增UTC别名改成timezone.utc，按LF归一后反向还原字节与前阶段LF SHA完全一致（当前工作树已有CRLF变化，raw SHA另列）（ocr-timezone-compat-cross.json）。新增fresh-process测试原写法直接del datetime.UTC会在真Python3.10无此属性时报错，已向ROOT指出需hasattr/delattr条件删除；不影响三处产品代码修正本身。本报告不代签尚未执行的真实3.10完整模型运行。
