# G2-SW-DAILY：StockWiki日常工程检查与大节点分离

<!-- CURRENT_PWF_NAV -->
> **历史施工/调查材料：**当前状态与唯一下一步见[总计划](../task_plan.md)。下方旧待办、暂停、人工签收和预算只是当时记录，不自动恢复；R3/R5的真实剩余范围以总计划为准。

> 当前状态：2026-10-07 MAIN已验收303项日常责任绿并正常快进本地master `0b48919065a912f1da10d89d36bf6bf1e659db88`，owner16文件保持。本仓无remote，不声称已推。见[MAIN收据](results/g2_stockwiki_daily_main_acceptance_2026-10-07.json)。本卡已交付，不再开工；下文为原施工合同。

**实施依赖已备齐。** 这是进一步收敛工程检查的大包，不是已完成的`stockwiki_engineering_gate_simplification.md`旧卡。旧卡8d4fdf7只将两遍全套合一，刻意保留73/40及体量门；本卡清理这些真实剩余并统一入口。单独拿本卡即可执行。

## 1. 基线和目标

仓库`C:/Users/郑曾波/Projects/StockWiki`，2026-10-07实读master=`9f552a6741dd093dc760ad6965458989cd027251`，clean、无remote。hooksPath未配置，.git/hooks只有sample；yaml声明不等于已安装hook。旧计划`.planning/2026-09-29-stockwiki-engineering-gate-simplificatio/task_plan.md`可解释前次交付，不重做旧卡。本次只读未跑测试，不使用旧929/935计数冒称本次验收。

当前CI跑check_all全套+73%overall/40%UI；pyproject另有fail_under73，AGENTS要求commit前全套；hook虽然无pytest，但validate-framework扫描wiki/content/成熟度。framework_validators_okf中600/1000行实际error，注释却说warning。tests/test_check_all_script将旧阈值当硬合同。目标是一份编排定义日常短责任、commit静态和大节点完整测试，体量/coverage诊断，真实framework/来源/研究错误继续失败。

## 2. 隔离目录与workspace陷阱

```powershell
git -C 'C:/Users/郑曾波/Projects/StockWiki' status --short
git -C 'C:/Users/郑曾波/Projects/StockWiki' log -1 --oneline
git -C 'C:/Users/郑曾波/Projects/StockWiki' worktree add -b codex/g2-sw-daily 'C:/Users/郑曾波/Projects/_g2/sw/StockWiki' master
$env:STOCKWIKI_PROJECT_PARENT = 'C:/Users/郑曾波/Projects/_g2/sw'
```

目标目录/分支存在先核归属，不能覆盖；主线推进先解释相关diff、记录实际base，不resetowner。只在上述新worktree实现；自己的PWF `.planning/g2-sw-daily/{task_plan.md,findings.md,progress.md}`，PLAN_ID=`g2-sw-daily`/PWF_PLAN_ROOT=`.planning`。不写CWP总计划。

**不能仅cd新worktree就认为隔离。** `stockwiki.paths.default_workspace_root()`会优先找到现存生产StockWiki。新目录末级必须StockWiki，测试子进程启动前显式传STOCKWIKI_PROJECT_PARENT；新编排调用CLI同时显式`--root <own checkout>`。记录实际resolved workspace等于own root，生产data/wiki/config不读写混入夹具。

## 3. 完整允许写集

- 新`scripts/checks.py`；`scripts/check_all.sh`薄shim。
- `.github/workflows/ci.yml`、`.pre-commit-config.yaml`、`pyproject.toml`、`AGENTS.md`。
- `stockwiki/framework_validators_okf.py`体量诊断；必要时`stockwiki/framework.py`抽纯framework/config assets校验。原`validate_framework(paths)`完整默认语义/签名保留，不能默认忽略业务成熟度。
- `tests/test_check_all_script.py`、新`tests/test_checks.py`；framework工具相关测试、`tests/test_e2e_real_workspace.py`仅体量/工程断言。
- `tests/e2e/test_cwp_source_export_v2.py`仅去硬编码producer路径/设置显式只读样本根、保留所有行为；必要时`test_cwp_narrative_source.py`仅隔离路径/环境，不改来源断言。
- README、docs/implementation_plan当前工程命令；本卡PWF和`docs/implementation/g2-sw-daily/{HANDOFF.md,handoff.json}`。

**禁止：**生产data/wiki/config/runs、身份/SourceExport/NarrativeReader实现与DTO/golden、研究accepted/rejected/review/identity_receipts、provider/sync；其他仓/installed写。不因receipt/review名字而删除投资业务或来源完整性条件。

## 4. 唯一检查接口

```text
python -B scripts/checks.py                # 默认日常短离线责任
python -B scripts/checks.py --static-only  # commit：静态，不pytest/coverage/联网
python -B scripts/checks.py --full         # 大节点：一次完整仓内离线suite
```

Python用sys.executable，shell/CI/hook只薄委托，不各写列表/阈值。默认不运行完整suite、真实跨仓E2E/网络/覆盖率；--full最多一次完整，不先精选再完整重复。显式coverage诊断输出仅独占scratch，数值不决定成功；真正工具失败/pytest/type/format/config/悬空引用失败仍非零，不用echo/exit-zero/tee掩盖。

模块>600/1000只warning/诊断，不添加baseline豁免白名单。frameworktaxonomy/forest/policy一致性为实际静态责任，不能变成全部ignore；hook不扫描整个生产wiki或业务状态。完整业务data_contract/真实workspace测试保留在相关大节点；研究状态不因工程简化而升级accepted。

短责任包候选（施工量测后按真实责任选择最终名单，不另设固定数量门）：

```text
tests/test_checks.py
tests/test_check_all_script.py
tests/test_framework_validation.py
tests/test_okf_conformance.py
tests/test_identity_snapshot.py
tests/test_identity_mapping.py
tests/test_identity_g2b_export.py
tests/test_source_export_v2_reader.py
tests/test_narrative_source.py
tests/test_cli_core.py
tests/test_cli_smoke.py
```

默认静态/短CI必须覆盖真实来源/身份/引用行为，不可只用shim或空import。CI单受支持Python，不把完整workspace数据回归塞每次commit。

## 5. 先TDD，再一次集中验收

先写有效RED：默认精选、commit静态、full只一次、真正Ruff/pytest/framework失败非零；73/40以下与600/1000以上仅诊断；shim/Python同参数/退出码；跨cwd明确own workspace而不是生产root；隐藏pyproject阈值和AGENTS不再恢复全测。

实现唯一编排/纯静态责任模式、同步CI/hook/pyproject/说明/旧工程期待。修改“必须数值”的旧测试是授权的合同变化，但taxonomy/引用/来源/期次/字节/预算/研究反例不得删除。

大节点一次仓内full（包含test_data_contract和真实workspace，显式own root），加冻结producer的真实消费者CLI；开发只跑相关责任。Windows实际长路径环境失败先用本卡独占短tmp验证，不删反例/降断言。实测时长/计数记录事实，不固定900秒或935数量通过门。

## 6. 冻结producer，避免MAIN代码并行竞态

本卡依赖已经发布且CI绿的CWP代码`93ac5a534e24ecbf9e1fc873f88bd106278f2fd6`，**无需等待MAIN**。从CWP只读Git对象导出到SW自身独占scratch，不新建CWP worktree、不安装/写CWP生产环境：

```powershell
$g2SwScratch = '<SW本卡新建的独占短临时目录>'
$g2SwZip = Join-Path $g2SwScratch 'cwp-published.zip'
$g2SwProducer = Join-Path $g2SwScratch 'cwp-published'
git -C 'C:/Users/郑曾波/Projects/company-wiki' archive --format=zip --output=$g2SwZip 93ac5a534e24ecbf9e1fc873f88bd106278f2fd6 src scripts tests/support tests/integration/__init__.py tests/integration/test_narrative_runtime_e2e.py pyproject.toml requirements.txt requirements-test.txt
Expand-Archive -LiteralPath $g2SwZip -DestinationPath $g2SwProducer
$env:STOCKWIKI_CWP_PROJECT = $g2SwProducer
```

scratch先记录absent并创建，不能复用别的harness目录。SourceExport测试旧CWP_SRC硬编码改为同一STOCKWIKI_CWP_PROJECT/src；producer/verified-open子进程用冻结src，StockWiki子进程用自身root；Narrative helper需要冻结tests。不执行整个CWP integration文件，只导入fixture helper；不pip install -e生产CWP。所有子进程参数/env显式传递，防PYTHONPATH混到别的worktree。

实际CLI链分别`stockwiki.cli source-read-v2 --bundle ... --reader-config ... --source-id ...`及`source-read-narrative --request ... --reader-config ...`。至少保留TXT精确引文/原语言/SHA、PDF manifest-only不编造locator、Narrative正例及坏SHA/身份/期间/as-of、partial/needs_review诊断无需人工receipt；上游资料读取不生成投资accepted结论。

### 真实原件也只读一次，复制后用own scratch

archive不含原件。现有SourceExport P06、多根迁移和Narrative P04/P07是真实原件节点，不能把它们冒称全合成或missing skip算通过。资料已存在，可只读如下CWP `companies/`相对路径及对应sidecar，先核SHA/size/mtime，再复制选中小样本到SW own scratch：

| 原件 | 相对companies路径 | 真实SHA |
|---|---|---|
| P06募集说明书 | `三角防务/raw/research/三角防务：西安三角防务股份有限公司向特定对象发行股票并在创业板上市募集说明书（注册稿）.PDF` | `cd803fe9528f4646f8f29b518a450ae4bd5b5968c482eb49789f9786b523595b` |
| P04招股书 | `中微公司/raw/prospectus/中微公司：首次公开发行股票并在科创板上市招股说明书.pdf` | `19cdb41e03b2d86ac15007753784f5859e1450a2bf79b514a7c0d4bd6830be67` |
| P07 IR | `万润股份/raw/research/万润股份：投资者关系活动记录表20260515.pdf` | `221467c15a24180205a8226f96fea9bda0262c866d5ba8aa31889ec96e6466d7` |

原根`C:/Users/郑曾波/Projects/company-wiki/companies`只读；不全根扫描/改元数据/造verified。生产sample真字节SHA必须匹配；测试capture身份可为fixture但报告不得冒称生产metadata已修。P06现测试另验sidecarSHA=`b34ace23f1651c606ab6d646202445d407c6a50db932ad65995312cd5e1a40bb`/208B；若现场不同，解释合法来源版本，不能改原件/随便改oracle。

将P06测试的样本根也改成显式`STOCKWIKI_CWP_RAW_SAMPLES_ROOT`指scratch/companies；Narrative真样本通过`COMPANY_WIKI_E6_PROJECT_ROOT`和`COMPANY_WIKI_E6_COMPANIES_ROOT`指同scratch。这样反复测试只读已复制的冻结输入，不随MAIN后续来源metadata变化。_e6_production_fingerprint此时只查scratch，**另保存真正原件前后SHA/size/mtime证明**。临时sidecar/数据库/模型Replay均在scratch，不写CWP，不翻译、不调用供应商。

集中可运行：

```powershell
python -B -m pytest tests/test_checks.py tests/test_check_all_script.py tests/test_framework_validation.py -q --tb=short --basetemp '<本卡短tmp>'
python -B scripts/checks.py --static-only
python -B scripts/checks.py
python -B scripts/checks.py --full
python -B -m pytest tests/e2e/test_cwp_source_export_v2.py tests/e2e/test_cwp_narrative_source.py -q --tb=short --basetemp '<本卡另一短tmp>'
git diff --check
```

全套默认应不依赖活跃producer，最后显式跨仓节点一次，不把此长链加daily。缺原件或真正合同失败明确report，不伪造pass/跨仓补代码；仓内可继续，MAIN只处理实际公共接口问题，不新增签收流程。

## 7. 恢复、提交、交接

测试前后核ownroot、生产data/wiki/config/三原件事实、临时根清单；本轮新copied/raw/db/report全部删到原状态，原件绝不丢。删除前核绝对路径包含/归属/无reparse，不git clean、不整库backup恢复。供测试的producer源码快照和ZIP结束删除，不能commit或形成永久依赖副本。

普通commit `codex/g2-sw-daily`，**该仓无remote，仅本地交付**；不擅自加remote、不合共享master、不改用户installed。最后freeze，报告`docs/implementation/g2-sw-daily/HANDOFF.md`和小`handoff.json`。

JSON `schema_version=g2-lane-handoff/1`：lane_id=`G2-SW-DAILY`、repo/base_commit/branch/worktree/delivery_commits/changed_files；modes/final_daily_test_files；RED/GREEN每条command/exit_code/count/seconds；73/40/600/1000诊断反例；resolved_workspace/production_root；producer_sha/archive_paths、实际TXT/PDF/Narrative CLI证据和真实raw SHA；临时清理/owner保护；external_provider_calls/paid_calls/production_writes/raw_deleted=0；remaining_issues/limitations/merge_notes。skip和合成不能代真实原件pass，不含密钥。

MAIN根据commit集中并线并在总G2B接线；本卡实现完成不代表所有StockWiki投资研究或CWP生产计划完成。
