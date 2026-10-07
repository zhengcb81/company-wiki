# G2-RF-TOOLS：RF可选工程工具和收尾流程简化

> 当前状态：2026-10-07 MAIN已验收107项及静态/公开mypy绿，正常快进main `1a2f9428a599504eb8355fcaebf86c6cbcaccbb3` 并push，精确CI37608673031所有步骤绿29秒；三owner日志保持，六测试×三安装副本已获具体授权定点同步。见[MAIN收据](results/g2_revenue-forecast_main_acceptance_2026-10-07.json)。本卡已交付；报告的uc.quality/旧manifest漂移归MAIN P1，不重派本卡。下文为原施工合同。

**实施依赖已备齐。** 这是RF仓内一整组可选工程工具改造，不依赖MAIN的CWP Store/pin改动。不要把它扩展为新的forecast/evidence/source adapter项目；本卡可单独交给一个harness。

## 1. 已核基线与目标

仓库`C:/Users/郑曾波/Projects/revenue-forecast`，main=`e241389adeda37bc9cbb53d7831063718552a936`。三个owner文件未提交：`assurance/runs/daily_alert.jsonl`、`weekly_alert.jsonl`、`weekly_manifest.json`；保留，不能checkout/reset/暂存。多个历史worktree不借用、不清理。日常`quality.yml→tools/pre_push_gate.py`单Python、11文件离线行为组已合理，commit仅Ruff/公共契约mypy/host检查，不扩大它们。本次核查只读、未跑长测。

实际待改：release_readiness默认要求三仓HEAD/197场景/2GB容量/backup，直接读CWP内部SQLite，写read-probe/rollback；coverage与final_ratchet要求全套900秒、84%及8模块40–80%、历史mypy错误69；session_checklist每次全测/E2E/安装全MATCH并apply/owner配置必须等HEAD。新增release_checklist又跑全套/mutation/registry/安装，固定EXPECTED_RED且只解析FAILED文字，没有严守pytest返回码。

目标：默认可选检查真正只读本仓和明确指定的版本化输入；数值诊断，不要求邻仓/备份/签收。真实类型/测试/配置错误、工具异常及提供的坏SHA仍失败。全套仅明确集中命令，不每session或helper重复。

## 2. 独占目录与写集

```powershell
git -C 'C:/Users/郑曾波/Projects/revenue-forecast' status --short
git -C 'C:/Users/郑曾波/Projects/revenue-forecast' log -1 --oneline
git -C 'C:/Users/郑曾波/Projects/revenue-forecast' worktree add -b codex/g2-rf-tools 'C:/Users/郑曾波/Projects/_g2/revenue-forecast' main
```

已有目标目录/分支先核归属，不能覆盖。若main推进先解释相关diff并记录新base，不因HEAD不同加人工许可。之后所有实现仅在`_g2/revenue-forecast`，自己的`.planning/g2-rf-tools/{task_plan.md,findings.md,progress.md}`，PLAN_ID=`g2-rf-tools`/PWF_PLAN_ROOT=`.planning`。

**允许：**

- `tools/release_readiness.py`、`run_coverage_gates.py`、`final_ratchet.py`、`release_checklist.py`、`session_checklist.md`、`.coveragerc`。
- `tests/test_zr1001_release_readiness.py`、`test_zr906_final_ratchet.py`，`test_ca303_arch_quality.py`仅本卡工具职责测试；新增`tests/test_rf_optional_tools_e2e.py/test_rf_coverage_report.py/test_rf_release_checklist.py`。
- 本卡计划及`docs/implementation/g2-rf-tools/{HANDOFF.md,handoff.json}`。必要的薄工程脚本只在tools，不能新建泛化检查/权限中心。

**不允许：**`scripts/**`及forecast/calculation/evidence/narrative/source adapter/closure规则；三个owner日志、生产config、历史资料或其他旧计划；`.github/workflows/quality.yml`、`tools/pre_push_gate.py`和hook本卡不改；任何CWP/FF/SW/ET/IQS/Dayu或installed技能写。

用户后续已经放松缺hash闭环：缺hash诊断、已提供而不符失败；本卡不能恢复早期全path强制hash，也不能修改当前业务closure。public SHA/来源/as-of自动正确性继续由原层负责。

## 3. 接口与系统改造细节

1. release_readiness默认不查邻仓内部DB，不要求未消费的HEAD、197、2GB、backup。已有明确输入验证复用既有RF工具，非法配置/明示坏SHA真实非零；未提供材料报告not_supplied，而非伪称已经验真。保留有用的本仓检查和准确JSON/CLI字段。
2. check-only成功/失败均零文件写：不造probe/rollback/receipt/.coverage；没有有状态发布就不要求备份。真正发布/rollback过程由既有发布层处理，本卡不执行发布。
3. coverage默认报告可用已有结果，不偷偷启动全套；显式参数才运行集中离线pytest。coverage文件全部在显式scratch，pytest真正失败/启动失败/超时非零，低数字仅诊断。不能erase用户现存.coverage。
4. final_ratchet默认仅相关轻检查/准确诊断，显式完整模式才调用一次离线责任组；类型错误以真实工具结果解释，不以“不超过69”宣称无错误。现有非零/诊断需要兼容时准确区分，不能将mypy故障显示绿或把全业务设ignore。
5. release_checklist依真实returncode，pytest返回2/收集失败/启动失败不能因没有FAILED行报成功；删除EXPECTED_RED固定免责，不把旧固定迁移文档/全MATCH/apply/mutation巡检当每发布资格。薄委托既有检查，不再另复制一套全测。
6. session_checklist写为相关责任/大节点、owner保护、正常commit/push/真实待办；不要求每会话全套真实E2E、全安装匹配、重跑历史197或checkout用户配置。

### 必须保留的兼容面

`scan_hardcode/scan_legacy/scan_encoding`被`test_ca304_r9_removal.py/test_zr1102_adversarial_audit.py/test_ca303_arch_quality.py`真实导入，保留API及真正正负例，可作为显式诊断；不要按名字删掉。

`assurance/unified_completion/uc/quality.py::_revenue_coverage`会AST读取`.coveragerc.fail_under`和`run_coverage_gates.PER_MODULE_MINIMUM`。本卡保留兼容形状**fail_under=0、PER_MODULE_MINIMUM={}**并明确只为历史报告解码、不决定资格，不保留84/40–80门。旧quality-verify的三仓冻结要求退出当前施工说明，不重冻manifest或扩大到整个assurance系统。其strict_targets仍按旧workflow找mypy是既有历史漂移，报告MAIN，不为此改日常workflow。若确需扩大该读取器退休写集，先报告具体caller与反例，不能擅自写整个assurance。

`tools/sync_installations.py`包括tests、不包括tools；本卡测试修改会使安装副本待同步，**交MAIN合入后定点同步**。harness不run apply，不把安装差异变成新门。

## 4. TDD及集中真实CLI节点

先建立有效RED，之后系统收敛同类调用，不逐处加特例：

- 隔离RF没有FF/CWP/backup/197样本也能默认检查；前后文件清单/内容SHA/mtime不变。
- 低coverage/任意历史错误计数不单独阻断；明示非法配置/坏SHA仍非零、缺hash诊断。
- pytest返回2无FAILED、mypy不存在/异常/超时均非零；默认不启动全套/coverage/安装apply。
- 显式coverage运行只一次相关pytest，真实失败不能被低数值处理吞掉，输出仅在独占scratch。
- 三scanner真实反例有效；历史AST报告空阈值可读取；日常11包检查职责不变。

实现完成后**一个集中节点**：相关责任tests、真实subprocess CLI（默认/check-only/显式完整/错误路径）、暂存root前后恢复、Ruff/diff，再正常commit。真实CLI用仓内合法已提交的输入/临时证据字节和短配置，不需要邻仓服务、外网/LLM或生产备份。测试不是只mock输出PASS；同一实际入口必须证明副作用/错误传播。

集中命令（新文件先创建再跑，不猜不存在文件）：

```powershell
python -B -m pytest -q --tb=short -p no:cacheprovider tests/test_zr1001_release_readiness.py tests/test_zr906_final_ratchet.py tests/test_rf_optional_tools_e2e.py tests/test_rf_coverage_report.py tests/test_rf_release_checklist.py tests/test_ci_smoke_plan.py --basetemp '<本卡独占短临时目录>'
python -B -m ruff check tools tests
python -B tools/pre_push_gate.py
git diff --check
```

ca303工具/scanner责任定向运行；其三仓manifest冻结旧漂移不作为扩散改造理由。全套不每天/每commit跑，真实失败不得删测试或改成无断言；时长/用例数如实记录、不设数字门。

## 5. 恢复和交付

临时根原先absent或有清单，成功/失败清掉本轮新文件恢复原状；不得动三owner日志/raw/config，不完整恢复备份。递归清理前核绝对路径包含/所有权/无reparse，不使用git clean或跨shell字符串删除。

普通commit到`codex/g2-rf-tools`，可正常push同名施工分支；不合main、不写installed。完成后freeze并交`docs/implementation/g2-rf-tools/HANDOFF.md/handoff.json`给MAIN。

JSON `schema_version=g2-lane-handoff/1`：lane_id=`G2-RF-TOOLS`、repo/base_commit/branch/worktree/delivery_commits/changed_files；retired_controls/retained_checks/compatibility_surfaces；RED/GREEN每条command/exit_code/count/seconds；实际CLI before_after、zero-write/return2/noFAILED证据；temporary_paths/cleanup/owner_files_preserved；installation_sync_pending；external_provider_calls/paid_calls/production_writes/raw_deleted均0；remaining_issues/limitations/merge_notes。不含密钥/原始外部响应，skip不是pass。

这是工程简化交接，不造authorization/release签收文件。MAIN集中复核并线后同步相应安装测试、确认原日常快CI绿；不重新运行全部已绿跨仓/付费节点。
