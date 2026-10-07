# G4-CWP-PIPELINE：冻结旧处理链整体退休

**状态：complete / accepted / published。CWP df7d7ba已并master/推远端，211责任绿，精确CI37673393822全部步骤绿74秒；MAIN指南/工程清单接线已完成。**

正式收据：[G4 MAIN验收](../g4_main_acceptance_2026-10-07.md)。以下为已完成施工细则/历史基线，不再重新开工。

## 1. 背景与完成目标

company-wiki只负责原始资料、规范化、可定位证据、检索与只读export。旧金融分析/Wiki writer已冻结；当前叙述Worker使用既有AUTO/隔离子进程，不调用旧Pipeline。

现有G2-03明确待办仍未落实：`config/pipeline_rules.yaml`、`scripts/gate_system/`保留Gate0–5、approval_threshold/human_review和旧金融writer；`full_pipeline.py`甚至先import旧gate/yaml再走冻结，因此`python -S`不是明确退休而是导入崩溃。`DeploymentManager.generate_retirement_report()`仍推荐scheduler.py/ingest.py等旧入口。已完成G1旧入口卡不能代替本次整族退出。

本包整体删除无现行职责的旧Gate实现/配置/专属测试，保留纯stdlib薄退休脚本；有实际来源解析价值的反例进入当前责任包。**不恢复研究writer，不新增“允许旧Pipeline”的flag，不保留disabled审批空壳，不复制大archive。**原件与AUTO/来源核心不变。

## 2. 工作树与上下文

原仓：`C:/Users/郑曾波/Projects/company-wiki`。已发布基线：`5930a644453ed46494c2c83c5ecfb97767fa9492`；之后MAIN有文档提交和未完成获取线，均不是本包依赖。

```powershell
git -C 'C:/Users/郑曾波/Projects/company-wiki' status --short
git -C 'C:/Users/郑曾波/Projects/company-wiki' worktree add -b codex/g4-cwp-pipeline 'C:/Users/郑曾波/Projects/_g4/CWP-PIPELINE/company-wiki' 5930a644453ed46494c2c83c5ecfb97767fa9492
```

目录或分支占用时先核归属，换独占后缀并交接，不能reset不明工作。工作树建立后只在该目录执行代码/测试/计划；不用原仓未提交代码、不在原仓运行全套测试。读适用AGENTS及planning-with-files，自己的PWF目录是`docs/implementation/g4-cwp-pipeline/`。设置`PLAN_ID=g4-cwp-pipeline`、`PWF_PLAN_ROOT=<自身worktree>/docs/implementation`，显式resolver传相同PlanRoot；不创建竞争根task_plan，不改CWP总PWF。

开工最少阅读：本卡、当前AGENTS职责边界、实际full_pipeline/gate_system/config、`tests/unit/test_gate_system.py`、`tests/unit/test_legacy_entrypoint_simplification.py`、`tests/unit/test_writer_freeze.py`、`tests/integration/test_full_pipeline.py`、deployment报告及其测试。先CodeGraph结构/caller，已打开文件再rg字面配置/import；索引无caller不能推导“全部可删”。

## 3. 独占写集

允许修改/删除：

- `scripts/full_pipeline.py`：删至下节薄stub。
- `scripts/gate_system/**`全部旧Gate专属实现；`config/pipeline_rules.yaml`退休删除。
- `src/company_wiki/deployment.py`：仅generate_retirement_report的旧入口描述/替代推荐，保留其他部署API行为。
- `tests/unit/test_gate_system.py`：退休旧框架专属测试；有来源价值的反例按下节映射，不重新维持Gate类。
- `tests/unit/test_deployment.py`、`tests/unit/test_legacy_entrypoint_simplification.py`、`tests/unit/test_writer_freeze.py`：仅本次退休行为及旧固定writer数量期待的责任同步。
- 新`tests/unit/test_g4_pipeline_retirement.py`、新`tests/integration/test_g4_pipeline_retirement_e2e.py`，必要有价值来源反例放新`tests/contract/test_g4_preserved_source_behavior.py`，只调用当前解析/选择接口，不修改核心实现。
- `docs/implementation/g4-cwp-pipeline/**`自己的计划、迁移映射、交接和小报告。

不修改：MAIN的`source_catalog/cli.py/code_identity.py/acquisition.py/acquisition_service.py/close_gap.py`及获取测试；G3维护后端/其测试；source reader/store/config/scanner/canonical writer/AUTO；scripts/common.py/writer_policy.py；hook/CI/pre_push_gate/pyproject；总PWF、生产配置/库/raw、别仓和安装副本。现行`tests/integration/test_full_pipeline.py`确实是PDF classify→extract→validate，不删除、不靠名字认定过时。

删除只针对本卡工作树中上述已跟踪旧源码/config/test，不对companies、数据库、其他工作树或未跟踪文件执行clean。owner `config/source_acquisition.yaml`在原仓保持；本包不能把它复制进新配置。

## 4. 冻结输出接口与行为

### 4.1 旧入口

`scripts/full_pipeline.py`仅stdlib，保留`main(argv=None)->int`和direct脚本壳。直接执行无参数、`--help`、旧stage/--no-gates/--dry-run/--gate-log、未知flag，均明确退休、exit78；说明当前来源CLI，沿用兼容标记`LEGACY WRITER BLOCKED`并补`LEGACY_PIPELINE_RETIRED`，不提示授权、review或恢复旧writer。

正常import静默、无配置/LLM/网络/目录/子进程初始化。调用main只输出退休说明并返回78；不能先argparse拒绝、读.env、import common/Config/Gate/金融writer。`python -S`、普通启动与旧允许/拒绝环境变量结果一致。保留冻结是已退休产品职责，不是个人权限开关。

### 4.2 删除与保留映射

交`retirement_map.json`，每个旧模块/测试组列：path、旧职责、实际生产/测试caller、disposition（retired / preserved_in_current_test）、reason、replacement_test。不要把数据身份/SHA/真实解析失败反例与投资评分/人工review一并删除。

无需重造GateResult/GateRegistry/RetryOrchestrator兼容层，无合法现行import就整体删除；若发现新增现行caller超出写集，交MAIN具体文件/符号/重现，不扩到共享CLI。纯金融评价、固定分数、人工签收、旧配置路由测试退休；解析页数/坏输入/未知证据等有价值行为由当前接口验证。`test_full_pipeline.py`原两个真实PDF反例继续运行。

### 4.3 部署报告

`generate_retirement_report()`仍返回原小dict形状、generated_at/current_stage/legacy_entries/failure_drills等兼容字段；已退休入口status/reason与替代推荐准确，不推荐scheduler/ingest/migration旧writer。可推荐现行`company-wiki-source-catalog`、`company-wiki-source-read/query/export-v2`及有限叙述运行说明；不能捏造命令或要求发布签收。未知历史恢复不宣称已可回滚。

### 4.4 MAIN接线

交`main_wiring.md`列逐项真实清单引用：hook/CI/mypy/pre_push/pyproject/职责文档/测试收集是否仍引用gate_system或pipeline_rules，建议删除什么，明确“当前没有引用”也可。本包不改这些共享文件。MAIN统一接线后才宣称全项目发布通过。

## 5. TDD与实施顺序

1. 建自身三份PWF，记base/status/写集和保护文件；调查旧配置/模块/入口及现行caller，形成retirement_map初稿。
2. **先真实RED：**运行旧full_pipeline的-S启动与导入副作用反例；新增部署报告不再推荐冻结writer的反例。不能把缺依赖/夹具错误当产品RED。对旧脚本设置配置、模型、网络、子进程及写入trap，证明退休发生在初始化之前。
3. 用纯stdlibstub替代full_pipeline，删除旧专属族；逐项处理专属测试，有价值source反例移到当前公开接口。不为删除旧类而删掉坏原文/SHA/locator的当前责任测试。
4. 更新原`PRE_GUARD_CRASH[(full_pipeline.py,nosite)]`例外：该入口现在必须真正exit78，不能仍允许import崩溃。其他脚本历史缺陷只记录，不顺手重构。writer AST清单不把纯stub当金融orchestrator；移除`len(guarded)>=49`人造数量门，保留真实仍可写脚本必须冻结/归现行入口的行为检查，不换成另一个固定数字。
5. 更新部署报告和相应契约；执行下节一次集中责任与真实脚本E2E，记录remaining/main_wiring，正常commit交MAIN。不得自己合master、修改工程总清单或安装。

## 6. 测试包、恢复与验收

**Unit：**import与main无业务初始化；普通/-S/旧env/参数退休一致；报告真实推荐；删除的旧框架不再成为当前入口依赖。类型/语法检查只核实际改动，不以score/coverage为门。

**集成：**在独立短tmp cwd创建一个sentinel原件、小sqlite、配置和目录前镜像；真实进程调用stub，配置/network/LLM/写入trap零触发，源字节/DB/schema/目录状态不变。另运行现成两项真实PDF提取集成，保留页面数量、max_pages和提取质量真实责任。

**E2E：**直接`python -S <自身worktree>/scripts/full_pipeline.py --company 示例 --stage review --no-gates`与普通启动；记录exit78及明确说明。用旧授权环境变量不能改结果。import/runpy trap是副作用验证，不能替代真正-S进程。

集中责任命令（新增文件由本卡创建）：

```powershell
python -B -m pytest -q -p no:cacheprovider tests/unit/test_g4_pipeline_retirement.py tests/integration/test_g4_pipeline_retirement_e2e.py tests/unit/test_deployment.py tests/unit/test_legacy_entrypoint_simplification.py tests/unit/test_writer_freeze.py tests/integration/test_full_pipeline.py
```

若确实需迁移有价值source行为，创建`test_g4_preserved_source_behavior.py`并将其加入同一次集中命令；无需迁移则在映射引用现成PDF/解析责任，不创建空测试或重复抄现成测试凑数量。开发只测红灯责任，完工集中跑一次，不重复全仓、真实模型或所有PDF。

短测试根从系统TEMP分配本卡唯一`cw4p-<随机>`路径，先记absent，child cwd/输出/日志只落本卡owned根；CWP pytest若重定位basetemp，记录实际路径与自动cleanup结果，不能只检查请求路径。自身`.planning/g4-cwp-pipeline/`只存小收据。成功失败finally关闭进程/DB后清owned临时副本，测试目录恢复原状；删除前核绝对路径包含和无reparse。原件删除0、production写0、网络/模型0。

完成看公开责任与实际证据，不看固定case数。报告绿色责任范围及尚待MAIN工程接线；发现共享接口问题给可复现例子，不能把pending当已绿。

## 7. 交接接口

自己的`docs/implementation/g4-cwp-pipeline/`交六份PWF/交接文件，另`retirement_map.json`与测试小收据。HANDOFF明确删/保留/迁移的API和每个真正RED→GREEN、临时根恢复、生产0写、MAIN清单建议。

```json
{"schema_version":"g4-handoff/1","lane":"G4-CWP-PIPELINE","base_commit":"5930a644453ed46494c2c83c5ecfb97767fa9492","implementation_head":"实际实现提交SHA","delivery_branch":"codex/g4-cwp-pipeline","worktree":"实际绝对路径","commits":[],"changed_paths":[],"tests":[{"command":"实际命令","exit_code":0,"seconds":0,"passed":0,"failed":0,"skipped":0,"evidence":"本卡小收据相对路径"}],"behavior_changes":[],"compatibility":[],"protected_state":{},"cleanup":{"roots":[],"restored":true},"external_effects":{"network_requests":0,"model_posts":0,"raw_deleted":0,"production_writes":0},"remaining":[],"main_integration":{"retirement_map":"retirement_map.json","wiring":"main_wiring.md"}}
```

示例数值不是验收事实，完工填实际结果。实现commit与后续交接commit分别列；delivery分支指向最后正常提交，避免要求JSON写自身尚未生成SHA。可正常推自己分支，但不合主线，不跳hook；MAIN接收后集中接线与发布。
