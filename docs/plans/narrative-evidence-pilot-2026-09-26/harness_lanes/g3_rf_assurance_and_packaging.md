# G3-RF-ASSURANCE：历史质量工具与技能包装职责收敛

**最新状态：已完成MAIN验收并入本地主线，不再派发/重建。统一验收见[MAIN收据](../g3_main_acceptance_2026-10-07.md)。生产资料应用及真实安装仍按总计划由MAIN处理，不冒充本包已执行。**

## 1. 目标和已知事实

RF的G2-RF-TOOLS已完成，不重做release_readiness、coverage工具、session_gate或日常CI。当前main及origin/main为`1a2f9428a599504eb8355fcaebf86c6cbcaccbb3`，其日常107项/精确CI29秒已绿。本卡完成原PWF G2 P1中的真实遗留：

- `assurance/unified_completion/uc/quality.py::strict_targets/compute_baseline`按workflow字面找`python -m mypy`；现workflow委托`tools/pre_push_gate.py`，读工具就抛异常。旧coverage 84→0仍被历史ratchet当“弱化”，工程阈值退休后再次被旧层阻断。
- `uc/manifest.py::verify(check_mtime=True)`、`uc/cli.py`五处`--mtime`默认strict；`tests/test_ca303_arch_quality.py::test_c5_manifest_verifies_offline`在干净checkout因文件系统mtime不同失败。相同原文SHA+size应保持完整性；明确严格时间检查可保留为诊断选项，不把checkout时间当来源事实。
- `tools/sync_installations.py::ROOT_DIRECTORIES`包含整个tests；六个刚同步的工程测试引用repo-only tools，安装一致不等于技能可用。应该按实际技能caller决定包装职责，不能整套补拷贝工程控制面。

保留真正输入损坏/指定SHA或size不符/非法配置/实际工具失败非零。覆盖率/复杂度/固定历史数量、无关邻仓HEAD或旧workflow文本差异是诊断；不通过重新冻结旧manifest/修改历史账目消除失败。

## 2. 独占工作目录与边界

原仓：`C:/Users/郑曾波/Projects/revenue-forecast`。新根：`C:/Users/郑曾波/Projects/_g3/RF-ASSURANCE/revenue-forecast`。新分支：`codex/g3-rf-assurance`。先确认不存在/不被其他任务占用，使用当前OS账号：

```powershell
git -C 'C:/Users/郑曾波/Projects/revenue-forecast' status --short
git -C 'C:/Users/郑曾波/Projects/revenue-forecast' worktree add -b codex/g3-rf-assurance 'C:/Users/郑曾波/Projects/_g3/RF-ASSURANCE/revenue-forecast' 1a2f9428a599504eb8355fcaebf86c6cbcaccbb3
```

可写仅：

- `assurance/unified_completion/uc/quality.py/manifest.py/cli.py`；在同目录允许新增仅这项质量report的辅助模块，不改state/closure/receipt/ledger/control/lock。
- `assurance/unified_completion/tests/test_zr104_quality.py/test_manifest.py`及新`test_g3_quality_reporting.py/test_g3_manifest_checkout.py`。
- `tools/sync_installations.py/tools/tests/test_sync_installations.py`；新包装责任测试可放`tools/tests/test_g3_skill_package.py`。
- `tests/test_ca303_arch_quality.py`只改C5 checkout责任及确实受本卡影响的质量读取测试；其他模块新增测试放`tests/test_g3_assurance_cli.py`。
- `SKILL.md`仅说明用户技能/仓库工程工具职责，不改研究方法或源证据规则。
- `docs/implementation/g3-rf-assurance/**`本卡PWF/交接与必要小报告。

禁止写原仓`assurance/runs/{daily_alert.jsonl,weekly_alert.jsonl,weekly_manifest.json}`；禁止改预测/evidence/来源adapter/模型预算、`tools/pre_push_gate.py`、workflow、hook、已完成G2工具以及`audit_review/**`和冻结control资产。禁止写其他仓和`.agents/.claude/.codex`安装根。确实发现边界外caller，只交MAIN精确接线表；不要借此复制新框架或全仓重构。

## 3. TDD实施顺序与冻结责任

1. 读本卡和当前相关源码/测试；CodeGraph优先查结构，已打开文件查具体内容。列quality/manifest/packaging的实际入口、返回值、caller及写副作用。现`uc.quality`有legacy `freeze/verify/strict_targets/compute_baseline/check_critical_complexity`，保持必要导入API；先判哪些是历史解码，哪些是真当前用户工具。
2. 先写RED：委托当前mypy入口的workflow；coverage门退休；邻仓不在；干净checkout同SHA/size不同mtime；同size篡改正文；实际进程return2但无FAILED字样；独立安装包不带repo tools却能运行真实技能入口。RED需来自目标行为，夹具/导入错误单独记录。
3. 质量层集中改为报告，旧字段可解码但不能再次变成数字资格门。当前RF类型目标以实际工程定义为依据，不能恢复workflow内联mypy或执行任意YAML文本。没有邻仓时报告not_available/范围，不能造0或隐式复制邻仓；显式用户指定但不可读/损坏输入明确失败。旧跨仓product_tree漂移按历史对比报告；实际用户提供manifest的SHA/size仍验真。不要继续要求对工程退休重新“签收/重冻”。
4. manifest默认校验SHA+size；mtime作为诊断或显式旧strict选择，库/CLI/current test语义统一。不改冻结manifest、原spec表或真实SHA。所有读入口只读，不能通过build/update自动修复坏输入；缺文件、路径逃逸、相同长度换字节反例仍非零。若当前验证还有与本项无关真实坏SHA，如实交剩余项，不清空problems列表。
5. 包装按实际技能入口依赖划定运行文件，仓内工程测试/tools留仓内；安装测试只保留能在技能分发包独立运行的责任子集，或退出默认运行包。避免纯`tests/**`全部移除后漏掉真正runtime import。`installable_files/manifest/installation_diff/sync_installation`需要兼容旧caller，差异只比较所负责runtime，不将旧repo-only残留当使用许可。默认check不写；显式sync在tmp中定点更新所属文件并保留未知文件、用户配置、output，不整目录替换、不借包装升级恢复全MATCH门。
6. 集中运行责任包和公共CLI/包装E2E；通过后正常commit。报告真正remaining与MAIN安装处理建议；不在用户安装目录应用。

## 4. 测试包和一个集中节点

- 单元：委托类型入口、历史阈值报告、合法schema解码、实际异常/退出码；manifest mtime变化与真实SHA/size破坏分离；installable集合实际runtime闭包、未知/config/output保留、check-only0写。
- 集成：quality→CLI真实退出状态，库/CLI默认同义；复制小假repo/spec到scratch不冻结生产资产；新安装集合→tmp skill根→真实公开模块/CLI，不用import空包冒称可用。
- E2E：真实当前仓的`python -m uc.cli manifest-verify`（cwd=`assurance/unified_completion`）在干净worktree正常读，实际SHA+size；在scratch复制的单项同size换字节必须失败，不能改仓内历史spec。质量report的实际CLI使用隔离显式输入，check-only0文件写。tmp安装只装runtime，运行`SKILL.md`确实推荐的本地无网络入口/help/离线最小输入，工程工具缺席不阻用户运行；缺runtime依赖应失败。
- 已有责任：`python -m pytest -q assurance/unified_completion/tests/test_zr104_quality.py assurance/unified_completion/tests/test_manifest.py tools/tests/test_sync_installations.py tests/test_ca303_arch_quality.py`加本卡新增包。CA303其他历史真实问题单列，不扩大到所有assurance或重复完整预测模型。
- 最后可运行一次现成`python tools/pre_push_gate.py`，不改其11包、不每commit运行full/coverage。Ruff只核实际改动和已有正常提交规则。

全离线、模型/下载/生产写0。测试根`.planning/g3-rf-assurance/scratch`，运行前记录absent/原清单，finally恢复；import日志/临时安装/pycache也在自身根，不能依赖真实用户output。严格保留生产配置与owner三日志。不要执行真实整套sync/import-installation或备份恢复。

## 5. 交接与MAIN接口

本仓交付`docs/implementation/g3-rf-assurance/{task_plan.md,findings.md,progress.md,HANDOFF.md,handoff.json}`，正常commit，可推自己分支；不合main。若JSON被忽略，仅精确add该小文件。

```json
{"schema_version":"g3-handoff/1","lane":"G3-RF-ASSURANCE","base_commit":"1a2f9428a599504eb8355fcaebf86c6cbcaccbb3","head_commit":"实际代码HEAD","branch":"codex/g3-rf-assurance","worktree":"实际绝对路径","commits":[],"changed_paths":[],"tests":[{"command":"实际命令","exit_code":0,"seconds":0,"passed":0,"failed":0,"skipped":0}],"behavior_changes":[],"compatibility":[],"protected_state":{},"cleanup":{"roots":[],"restored":true},"external_effects":{"model_posts":0,"downloads":0,"production_writes":0,"installation_writes":0},"remaining":[],"main_integration":{"cli_changes":[],"runtime_file_set":[],"old_engineering_residues":[],"installation_actions":[]}}
```

数值填实测，NOT RUN不能报pass。HANDOFF列每个旧门实际caller/退休处理、真正输入错误如何失败、RED→GREEN、命令时长/副作用、runtime依赖集合与三安装副本下一步。MAIN只核本卡写集和集中责任，正常并线/push核精确CI，再处理已发布runtime的安装；不增签名、TTL、coverage或每小步人工门。
