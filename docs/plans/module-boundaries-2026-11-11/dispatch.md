# 并行施工与ROOT职责

## 当前 owner 并线规则（2026-11-14）

并线由代码所属模块的 owner 在所属仓库完成。Owner 负责核对提交与未提交差异、对当前公开接口做适配、运行本模块测试、提交并入本仓主线、推送并更新本仓 PWF。ROOT/company-wiki 负责维护本计划、接口对齐、只读查收状态和最终公开接口组合验收；不能代替其他仓库做 checkout、stage、restore、commit、merge 或 push。

StockWiki 正有另一项目在施工，所有 StockWiki 代码和工作区操作均暂停到该项目正式交接以后。现有审查结果只作已知背景；不能据此与在途改动并行施工。Dashboard、FF、RF、ET、SID 的剩余并线问题分别交回对应 owner。CWP 自己的支线由 CWP owner 处理。若组合验收暴露跨层问题，ROOT提供复现与接口证据，所属模块 owner 在本仓修复。

此规则覆盖本文件后续历史章节中由 ROOT 直接接收 StockWiki、合并外仓分支的旧安排；旧提交记录保留为事实，不作为当前跨仓写权限。

**五卡与 ROOT M2 均已收口。** 卡片保留为交付依据，原作者工区已回收。版本、测试和处置见 [组合记录](review/root_composition_20261114.md) 与 [对账表](reconciliation.md)。

## 已完成的写入划分

| Lane | 独占代码仓与新工区 | PWF只写自己的目录 | ROOT不同时写 |
|---|---|---|---|
| MB-CWP | company-wiki → Projects/mb11-cwp | docs/plans/mb11-cwp-2026-11-11 | CWP src、局部tests、打包/本仓CI |
| MB-FF | filing-fetch → Projects/mb11-ff | docs/plans/mb11-ff-2026-11-11 | FF scripts、tests、发布清单 |
| MB-RF | revenue-forecast → Projects/mb11-rf | docs/plans/mb11-rf-2026-11-11 | RF scripts、tests、发布清单 |
| MB-ET | earnings-transcripts/earnings-transcripts → Projects/mb11-et | docs/plans/mb11-et-2026-11-11 | ET contracts/runtime/worker/tests |
| MB-SID | StockInfoDLSimple/v2-clean-rewrite → Projects/mb11-sid | docs/plans/mb11-sid-2026-11-11 | SID provider API/adapter/metadata/tests |

五份卡文件只由ROOT维护，harness对自己的PWF负责。共享测试/生产代码文件不存在双作者；CWP integration/** 与 tools/run_source_system_tests.py 属ROOT，必须在CWP卡交付后才修改。跨仓通信兼容现行公开wire，因此无需同步重写邻仓。

## M2之后的Dashboard独立续核卡

以下是本轮只读盘点后发现的未收口差额，不重开M2，也不允许以旧分支覆盖当前模块结构。三卡都以 Dashboard 当前 modular main 为产品边界，交付时分别使用独立工区与独立 handoff：

| 卡 | 独占范围 | 不得触碰 | 当前基线/完成条件 |
|---|---|---|---|
| [C01证据可移植性](harness_lanes/dashboard_c01_evidence_portability.md) | C01 schema-7 rehearsal evidence、manifest、verifier、C01测试 | Dashboard产品代码、其他仓库、非C01证据 | main `ff6e764f`；两个 `core.autocrlf` 新鲜检出都通过，原28场景不减，manifest精确覆盖文件集，独审绑定最终HEAD |
| [B-real预览模块适配](harness_lanes/dashboard_preview_module_adapter.md) | documents preview UI、Dashboard transport及其定向测试 | `application/ops`、公共契约、CWP/FF/StockWiki源码、旧 staged worktree | main `ff6e764f`；仅通过公开UI→HTTP→application operation→owner adapter/source port完成功能，原件身份/hash/locator不变 |
| [B03独审收据收口](harness_lanes/dashboard_b03_review_closeout.md) | 仅旧B03 handoff/review/evidence和隔离复验 | 任何产品代码或生产数据；不得把集中式旧adapter/service合并 | 旧B03 R1当前为PENDING且报告有字面占位符；只有独立reviewer给出绑定源码SHA的最终结论才可标完成 |

三卡目录、改动清单与验收证据不得交叉写入。B-real只新增产品代码；C01与B03只改各自历史交接证据。即使不同harness并行，其合并顺序也是各自独立提交到当前Dashboard主线，出现共享接口差额时回到owner公开合同，不允许跨层调用。

## 原并行安排（历史记录；当前以本页 owner 并线规则为准）

- 五卡可同时做A/B/C：它们均保持现有跨仓协议；内部新端口和测试仅归本repo。已通过的现有能力不重做。
- 资源只够三个harness时先CWP、RF、ET；后续空出的harness接SID、FF。这是资源建议，不是额外依赖。
- StockWiki与Audit不增加新分包卡（历史安排）。此前 C38/B03 接收已记为完成；StockWiki 当前另有并行施工，后续由 StockWiki owner 等该项目正式交接后自行处理。Audit只准备公开fixture/现有test清单并验证。真实RED归所属owner有限修复，不建立无限“每发现一项再来一轮全仓审计”。
- Dashboard原4项WIP已由ROOT受测接收至2049356并推main，后续仍由原owner接续；不派竞争作者。IQS/Dayu不改。SID11项WIP纳入MB-SID A0修复接收；RF四项assurance已归档原字节后restore，旧失败事实保留。

## ROOT 组合验收顺序

当前进度以 [组合记录](review/root_composition_20261114.md) 为准。

1. 汇总各harness实际baseline、声明接口版本和新增fixture路径；记录一个生产者/消费者组合清单。文档提交不改变代码基线，不为文档SHA重跑测试。
2. 选定四份已有真实文档与已有报告/三表快照，仅通过公开owner入口取得引用；在跑结果前冻结E04必需检查点。不要全库复制或重新下载。
3. 核实Dashboard选择的code-root/HEAD/contract/data-root组合，不把配置当运行进程证明。StockWiki 的 C38/B03 与公开来源实现由 StockWiki owner 在其仓内处理；ROOT只记录接口依赖并用公开入口做组合验证，不写 StockWiki、不改 IQS、不对真实状态 repair/apply。真实 stream24-case 等 CWP 的公开入口就绪后再由组合验收验证。
4. 各模块 owner 逐项确认 diff 范围、测试及独审绑定最终源码版本，并自行决定在本仓适配、提交、并线和推送。ROOT只核对交接和公开接口兼容性；有冲突时把具体冲突交还 owner，不直接在外仓改解。跨卡依赖只需相关 owner 对齐公开合同，其他卡可以继续施工。
5. CWP完成后再修改ROOT组合runner；执行acceptance E01–E09、现有D4/D5相关场景、安装/移动目录/错误/恢复反控，集中一次独审。失败按owner修，复跑受影响矩阵格。
6. 全部必需格通过即CLOSED；清理本次自有worktree与临时数据、保留必要完整小证据，父PWF恢复R4/T4/真实摘要/恢复/RF循环。

## CWP 本仓并线规则

- CWP owner 可在 company-wiki 内负责目标 `master` 的本仓并线。FF/RF/ET 的目标为各自 `main`，SID 目标为 `v2-clean-rewrite`；这些仓库的实际并线由对应 owner 操作，分支名不同是当前事实，不创造假的统一main。
- 新工区只从所列已提交基线起步。旧worktree/未跟踪文件不是默认可删；不把未知WIP通过git add -A带入。
- CWP merge前核当前 `master` 增量，只处理 CWP 自己接口/范围内冲突；不可把别人的未提交文件 restore 成旧版本。外仓 owner 自己在其仓内完成相同检查，不把外仓独立提交应用到 CWP integration 工区。
- 模块大节点运行对应完整CI一次、ROOT大节点组合一次；日常commit保留轻量静态hooks，pre-push不扩成几十分钟全链，推送不自动部署全局技能。
- 交付状态只用 PLANNED → IN_PROGRESS → REVIEWED → MERGED → COMPOSED/CLOSED；NO_CHANGE_PROVEN是有证据的正常结果；environment-blocked必须写具体不可执行点，不能伪装产品FAIL或PASS。

## PWF选择

本机installed PWF PowerShell脚本中PWF_PLAN_ROOT代表绝对项目根并拼`.planning`，并非旧文档中的docs/plans。对本计划使用显式参数，避免恢复错目录：

```powershell
$env:PLAN_ID='module-boundaries-2026-11-11'
Remove-Item Env:PWF_PLAN_ROOT -ErrorAction SilentlyContinue
& 'C:/Users/郑曾波/.agents/skills/planning-with-files/scripts/resolve-plan-dir.ps1' -PlanRoot 'C:/Users/郑曾波/Projects/company-wiki/docs/plans'
```

每条lane改为自己的工区/PlanId；该命令只绑定当前命令进程，不谎称已改变harness父进程hooks。各harness可直接按卡中绝对PWF路径读取；不修改仓库共享.active_plan去抢其他任务。
