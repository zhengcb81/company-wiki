# 并行施工与ROOT职责

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

## 原并行安排

- 五卡可同时做A/B/C：它们均保持现有跨仓协议；内部新端口和测试仅归本repo。已通过的现有能力不重做。
- 资源只够三个harness时先CWP、RF、ET；后续空出的harness接SID、FF。这是资源建议，不是额外依赖。
- StockWiki与Audit不增加新分包卡。StockWiki由ROOT在自己的SW隔离工区按reconciliation.md接收C38/B03公开合同差额，再做真实组合；Audit只准备公开fixture/现有test清单并验证。真实RED归所属owner有限修复，不建立无限“每发现一项再来一轮全仓审计”。
- Dashboard原4项WIP已由ROOT受测接收至2049356并推main，后续仍由原owner接续；不派竞争作者。IQS/Dayu不改。SID11项WIP纳入MB-SID A0修复接收；RF四项assurance已归档原字节后restore，旧失败事实保留。

## ROOT 组合验收顺序

当前进度以 [组合记录](review/root_composition_20261114.md) 为准。

1. 汇总各harness实际baseline、声明接口版本和新增fixture路径；记录一个生产者/消费者组合清单。文档提交不改变代码基线，不为文档SHA重跑测试。
2. 选定四份已有真实文档与已有报告/三表快照，仅通过公开owner入口取得引用；在跑结果前冻结E04必需检查点。不要全库复制或重新下载。
3. 核实Dashboard选择的code-root/HEAD/contract/data-root组合，不把配置当运行进程证明。ROOT在StockWiki自己的隔离工区按C38/B03合同差额接收；CWP和RF历史接口差额已归各卡A0，由各自作者承接。ROOT不跨层补内部调用、不改IQS、不对真实状态repair/apply。真实stream24-case待CWP T-READ后明确组合验证。
4. 交付一个接一个接收：确认实际diff在卡范围内、测试与独审对应最后源码版本；兼容且无共享冲突即可并入所属主线并推已有remote，不积压全部支线。跨卡依赖变更仅协调相关两方，无需其他卡停工。
5. CWP完成后再修改ROOT组合runner；执行acceptance E01–E09、现有D4/D5相关场景、安装/移动目录/错误/恢复反控，集中一次独审。失败按owner修，复跑受影响矩阵格。
6. 全部必需格通过即CLOSED；清理本次自有worktree与临时数据、保留必要完整小证据，父PWF恢复R4/T4/真实摘要/恢复/RF循环。

## 并线规则

- CWP目标master；FF/RF/ET目标main；SID正式目标v2-clean-rewrite。分支名不同是当前事实，不创造假的统一main。
- 新工区只从所列已提交基线起步。旧worktree/未跟踪文件不是默认可删；不把未知WIP通过git add -A带入。
- ROOT merge前核current main增量，只处理与接口/范围相关冲突；不可把别人的未提交文件restore成旧版本。必要时将卡的独立commit应用到新干净integration工区。
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
