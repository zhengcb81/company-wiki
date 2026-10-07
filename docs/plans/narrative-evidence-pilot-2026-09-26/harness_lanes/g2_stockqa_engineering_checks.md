# G2-SQA-CHECKS：StockQA工程入口与workflow统一

**ready，现在可独立启动。** 这是StockQAbyLLM工程工具实现包，无CWP/StockWiki/RF新接口依赖；不触invest-quick-scan/IQS活动项目。请完整读本卡，所有必要上下文均在此，不需要读CWP历史长计划。

## 1. 目标和基线

仓库`C:/Users/郑曾波/Projects/StockQAbyLLM`，2026-10-07实读master=`6a9ff13864ebb160d5c4ab3cf2f42155d9f4aa99`。tracked/staged干净，7项owner untracked保留：`.codegraph/`、`.workbuddy-ai/`、`nul`、`pilot_runs/b2a_2026-10-03/`、`pilot_runs/g2b_alphabet_2026-10-04/`、`pilot_runs/l02_2026-10-04/`、`progress_update.txt`。远端`https://github.com/zhengcb81/StockQAbyLLM.git`；本次只读未跑测试，旧绿灯不作为本卡验收。

现CI有9runner/8安装、两Python全套/87%覆盖率；本地sh管道tee吞退出码、pylint exit-zero却虚报达标，bat另复制逻辑；hook每commit always_run pytest/联网pip-audit，默认pytest输出coverage/XML/HTML。Black24.10/26.5/裸安装、mypy strict等不同；空`import src`未证明CLI可用。另security每push重复安全runner，release另保留70%/8分门，docs每代码push重新部署。要统一全部当前入口，不只删一行pytest。

用户已要求取消个人项目多余门禁、每commit全套和数字阈值；仍保留真正格式/类型/测试失败、来源/预算/恢复错误和密钥泄露检查，不删除真实业务反例。

## 2. 独占worktree与允许写集

从最新主线核对相关进展后建立独占目录；若已存在先查任务归属，不能reset：

```powershell
git -C 'C:/Users/郑曾波/Projects/StockQAbyLLM' status --short
git -C 'C:/Users/郑曾波/Projects/StockQAbyLLM' log -1 --oneline
git -C 'C:/Users/郑曾波/Projects/StockQAbyLLM' worktree add -b codex/g2-stockqa-checks 'C:/Users/郑曾波/Projects/_g2/StockQAbyLLM' master
```

创建后只在`_g2/StockQAbyLLM`施工。原root及7owner资料只读。自己的PWF为`.planning/g2-stockqa-checks/{task_plan.md,findings.md,progress.md}`，设置PLAN_ID=`g2-stockqa-checks`、PWF_PLAN_ROOT=`.planning`；不要改已有业务计划或CWP总计划。

**完整允许写集：**

- 新`scripts/checks.py`，`scripts/run_ci.sh`、`scripts/run_ci.bat`。
- `.github/workflows/ci.yml/security.yml/release.yml/docs.yml`。
- `.pre-commit-config.yaml`、`pyproject.toml`及确有必要的`requirements-lock.txt`工具版本同步。
- 新`tests/unit/test_ci_checks.py`、`tests/integration/test_ci_checks_cli.py`；已有工程入口专属断言按实际caller仅调整其工程责任。
- README相关开发命令、CONTRIBUTING、docs/development，以及本卡`.planning`与`docs/implementation/g2-stockqa-checks/`记录。旧工程文案只加当前方案指针，不能把业务计划全部改complete。

**不允许写：**`src/**`业务、生产配置/凭证、任何pilot/历史真实结果、其他仓库或已安装技能；不改模型/预算/身份/恢复规则。如果发现业务问题，说明真实失败交MAIN，不删用例凑绿。不能为了import日志污染改业务logger。

## 3. 一个运行接口

```text
python -B scripts/checks.py                 # 默认短离线CI
python -B scripts/checks.py --static-only   # commit，仅静态
python -B scripts/checks.py --full          # 大节点，全部离线unit/integration一次
python -B scripts/checks.py --metrics --output-dir <本卡独占短目录>
```

唯一Python定义步骤，使用`sys.executable -m ...`；sh/bat只定位仓根、传全部参数、原样返回退出码。默认责任包见第5节；不能空import或echo PASS。pytest/mypy/Black/离线真安全发现及工具启动失败/超时真实非零。pylint/radon/coverage数值为诊断，文案不再称“达分门通过”，不得用`|| true/exit-zero/tee`吞真实检查错误。

默认pytest不生成coverage/XML/HTML/reports；指标模式才在显式output-dir输出，成功/失败恢复测试根。Black统一现合法工具版本/锁，mypy以pyproject一份配置为准，不散落额外strict；类型错误不能改成全部忽略。

默认/--full强制离线，排除live/benchmark及tests/benchmarks，即使继承`STOCKQA_RUN_LIVE_E2E=1`也不能调用收费provider。实际CLI smoke导入`main/main_with_llm/BasicRunner`及模型/config模块；`src/utils/logger.py`导入会创建logs，必须在自己的TemporaryDirectory子进程中导入并正确设置PYTHONPATH，清理scratch，不让logs污染owner root。

## 4. 同步所有入口，防遗漏

- 日常CI单受支持Python、单job、一次依赖安装、调用同checks入口。兼容矩阵/full/report仅显式相关大节点，不以每天重复矩阵替代正确性。
- commit hook仅便宜静态，无always_run pytest、联网pip-audit、报告生成；不扩大hook。
- release验证委托统一`--full`，去70%/8分等第二标准；保留真实发布步骤/权限，本卡不打tag、不触发真实release或PyPI。
- security复用已有weekly/manual报告机制，退出每push重复环境pip-audit；审计项目依赖而非任意开发环境。真实密钥泄露/离线安全反例保留；不要创建新的人工安全签收。
- docs按文档相关路径触发，保留原发布权限/逻辑，不由本卡主动部署。
- 文案准确记录default/full/static/metrics；不留CONTRIBUTING要求每次全套或数值达标。

## 5. TDD与一个集中验收点

先建立真实RED：子命令返回7/收集失败/不存在/超时不能被编排报绿；实际sh/bat转发参数和非零；仓外cwd、空格/中文路径正确；默认无报告副作用；低coverage/pylint只诊断而真实失败仍失败；真实CLI模块导入错误非零、导入logs scratch最终恢复。

日常责任包至少覆盖以下当前真实文件（量测后允许按责任精选，报告最终节点名单）：

```text
tests/unit/test_models.py
tests/unit/test_config_manager.py
tests/unit/test_llm_config.py
tests/unit/test_basic_runner.py
tests/unit/test_main_with_llm.py
tests/unit/test_q07_checkpoint.py
tests/unit/test_quick_scan_budget.py
tests/unit/test_q09_budget_concurrency.py
新编排unit/CLI反例
tests/integration/test_quick_scan_cli.py的公开CLI精选节点
```

公开CLI至少保留：`test_public_cli_exports_eight_score_entity_timestamp_model_and_search_receipt`、`test_public_cli_refuses_to_infer_question_id`、`test_public_cli_persists_every_failed_transport_retry_without_error_details`、`test_public_cli_does_not_retry_uncertain_server_error_without_reconciliation`、`test_public_cli_fake_health_schema_rejects_before_http`、`test_public_cli_pauses_after_unpriced_attempt_without_sending_backup`。实际测试模块在tests/integration，不是调用生产provider。

大节点保留Q07 saved/missing恢复、状态分区不丢、late receipt只settle一次；预算拒绝在HTTP前、backup不可破总cap、unknown保持预留、deadline停止新dispatch但不阻settle。一次完整`--full`包含`tests/integration/test_quick_scan_budget.py::test_two_processes_share_budget_and_real_dispatch_concurrency_slots`真跨进程节点。不要每小改动重跑全套。

运行可先用：

```powershell
python -B -m pytest tests/unit/test_ci_checks.py tests/integration/test_ci_checks_cli.py -q --tb=short -p no:cacheprovider --basetemp '<本卡独占短临时目录>'
python -B scripts/checks.py
python -B scripts/checks.py --full
python -B -m ruff check scripts tests/unit/test_ci_checks.py tests/integration/test_ci_checks_cli.py
git diff --check
```

完整代码改好后只设一个集中节点：default/full/wrapper负例/真实CLI和预算恢复/静态/临时清理；失败只定位相关责任，不扩大数字门。实测时长和测试计数记事实，不设置固定数量/秒数通过门。

## 6. 保护、提交和交接

测试只用本卡短tmp配置、loopback/模拟transport及自己的临时SQLite；供应商HTTP/paid/翻译/生产写0。前后记录临时根清单、原owner状态，恢复所有本轮生成logs/report/cache/数据库。删除前确认绝对路径属于本卡且无reparse，不递归清理owner树或完整备份演练。

普通commit自己的`codex/g2-stockqa-checks`，可push同名施工分支；不合master、不发布、不申请“每个小步骤签收”。交付`docs/implementation/g2-stockqa-checks/HANDOFF.md`及`handoff.json`，freeze写集后告诉用户此路径。

JSON使用`schema_version: g2-lane-handoff/1`，至少包含：`lane_id=G2-SQA-CHECKS`、repo/worktree/branch/base_commit/delivery_commits/changed_files、最终检查模式/用例名单、每次RED/GREEN的command/exit_code/count/seconds、wrapper失败与真实CLI/预算证明、tool_versions、workflow触发前后、清理前后、owner_root_untouched、external_provider_calls/paid_calls/production_writes/raw_deleted全部0、remaining_issues/merge_notes。报告说明与真实测试对应；skip/NOT RUN不可冒作pass，不含密钥/raw provider响应。

MAIN会按此代码接入总G2B、合主线并核准确CI；工程检查全部完成也不能宣称投资业务或整个CWP计划完成。
