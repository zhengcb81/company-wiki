# 三仓原始痛点审计与独立修复计划

> **2026-09-09 深夜并发状态（只读核对，覆盖 9/7 观测）**：请先读 [current-delta-2026-09-09.md](current-delta-2026-09-09.md)。要点：① worker v5 独立轨道全部完成（冻结 51 项 + 三轴独立审查 accepted，仍 PLAN_ONLY、不授权实施）；② FC-705 门仍 `close_gate_allowed=false`（last-two = P7 23:59:41 ✗ / P8 24:00:11 ✓），预计 **2026-09-10 22:00 运行后**转 true；③ **R9 批 3 范围失真**——实测仅 `artifact_backfill.py` 零生产读者，`backfill_v2`/`portfolio_promoter`/`_scan_root_v1`/`legacy_bridge_enabled` 均有活跃调用者，批 3 需技术门 + owner 政策门并重新拆分（清单见 revenue `r9_batch3_checklist.md`）；④ 本轮未运行产品测试、未改产品代码/配置/DB/任务/worker。下方 9/7～9/8 内容保留为当时交付记录。

> **2026-09-08六类问题实施细化**：在既有R4下使用[逐步实施与关闭条件](r4-remediation-steps.md)和[117项逐行修复映射](r4-unit-remediation-map.md)。显式覆盖H01、WP02–10、FC-903、117目标、旧95门处置、9处架构泄漏与7类真实验收；只细化文档，不代表产品修复或真实测试完成。原R4两核心文档及历史独立签署保持原字节；本次补充另做审查。

> **当前执行路线：R4（2026-09-07制定，09-08复核）**。用户批准按虚拟数据湖减法调整规划。请从[R4详细实施计划](simplified-execution-plan.md)开始，再读[36组真实测试与审计矩阵](simplified-test-matrix.md)及[旧15包完整迁移表](r4-transition.md)。主线为A合同、B位置透明读取、C瘦消费者/唯一生产入口、D安全运维；收入M独立。原117项、GP和历史目标保留，不再叠加旧95门。全部仍PLAN_ONLY，未授权产品实施。下方R2/R3的编排和review说明仅是历史交付记录，不覆盖R4。

> **2026-09-07后续交付**：用户追加批准跨仓planning状态同步及细化，已同步活动根/子目录入口，冻结原计划/receipt/v5基线保留。当前源码/运行状态以[9/7并发差异](current-delta-2026-09-07.md)覆盖下方9/6观测：有其他任务删除旧工具和修调度，原审计不是新HEAD复跑结论。详细执行从[execution-handbook.md](execution-handbook.md)开始：15包、逐步检查点、各G0–G5独立审查、真实源数据/真实进程E2E、恢复与授权隔离。已获[独立计划复核](execution-independent-review.md)，不代表产品实施或真实E2E已通过。

执行细节分为[控制面](execution-control-plane.md)、[数据面](execution-data-plane.md)、[模型与三公司链](execution-model-plane.md)。[机器依赖展开](gate-dag.json)和[只读结构验证](validate_execution_plan.py)仅验证计划，不准许运行。主/子目录一致性处置见[独立文档复核](document-consistency-review.md)；历史冻结文件不改正文，由当前入口覆盖解释。

审计日期：2026-09-05至09-06。范围：company-wiki、filing-fetch、revenue-forecast。此目录是独立新增审计成果，不并入旧计划；所有整改均待另行批准，未实施。

## 结论先读

**不能根据117/117 accepted宣称原始痛点已经解决。** 已有真实局部改进，但部分验收把真实环境、完整业务旅程、自然观察移到“以后部署”，再用accepted互相证明完成；当前业务代码也仍有实质反例，不只是缺观察时间。

1. **恢复worker前应先堵住数据安全缺口。** 旧归档目录日期可触发对全部retired EvidenceSpan的回收，未逐条证明可信归档和可恢复；worker周期会调用apply=True。已独立核验代码风险，**没有证据证明实际误删发生，也不是raw PDF删除结论**。
2. **慢的问题仍须分阶段测量。** 8/12历史调查指向候选筛选相关EXISTS、高CPU长查询、停止检查前fetchall及900秒重启/失败预算机制；当前相关结构仍在。历史902秒/96.8%CPU不是本轮新profile结果。计划要求在隔离真实规模副本测SQL、扫描、hash、Python子进程、provider、parser、LLM及缓存失效各阶段，先修复杂度/取消/无效重复，再考虑其他优化。
3. **资料链与模型链存在业务缺口。** 包括root policy传递与eligible选择、修订排序、补缺授权/重试预算/失败计数、持久需求及artifact接线；以及矿山单位/TC-RC/期间股权、真正模型消费、发布事务、回测与confidence。详见各分报告的反例和局部已解决部分，不能一概称全部不可用。
4. **完成与监测门不能可靠证明真实成果。** 缺required tier、未来时间、部分skip、报告缺SLI等负例仍被部分helper/消费门放行；helper缺陷不等于已发生生产release。新daily命令参数已经修复，旧参数故障不再当当前问题。

## 阅读路径

R4已获[独立修订复核](r4-independent-review.md)：修正VR/AR互等、本地验收混入worker、broker目标归属等问题，结论仅为计划可执行性通过，绑定两份R4文件hash；旧R2/R3review仍仅指历史版本。

| 目的 | 文档 |
|---|---|
| 当前详细修复、顺序、测试与关键节点独立review | [R4执行](simplified-execution-plan.md)、[测试矩阵](simplified-test-matrix.md)、[旧包迁移](r4-transition.md)；旧remediation与分面手册仅供映射后的领域细节 |
| 逐项117个原目标的结论/证据定位 | [unit-ledger.md](unit-ledger.md)、[机器索引](unit-ledger.json) |
| 防假绿、收据、CI、调度、自然窗口 | [assurance-audit.md](assurance-audit.md) |
| Worker、安全、真实加工、资源和复用 | [wiki-audit.md](wiki-audit.md) |
| 文件发现/根策略/修订/下载与性能 | [filing-audit.md](filing-audit.md) |
| 收入、矿业、合并、发布与回测 | [revenue-audit.md](revenue-audit.md) |
| 旧空间治理/section/portfolio/v5 | [historical-projects-audit.md](historical-projects-audit.md)、[legacy-inheritance.md](legacy-inheritance.md) |
| GP10及上游资产601–604补核 | [gp-audit.md](gp-audit.md)、[upstream-asset-audit.md](upstream-asset-audit.md) |
| 独立审查与纠偏轨迹 | [证据门复核](assurance-independent-review.md)、[回收风险复核](retention-independent-review.md)、[计划复核](remediation-plan-independent-review.md)、[细化文档复核](r4-remediation-detail-review.md) |
| 过程、限制及下一步 | [task_plan.md](task_plan.md)、[findings.md](findings.md)、[progress.md](progress.md) |

## 覆盖与证据强度

- 25个CA+92个ZR=117项，逐项索引无缺项；GP10另列，旧FC/closure/waves共81个唯一历史引用另作继承。117项原完整目标聚合判定为53 CONTRADICTED、58 PARTIAL、6 HISTORICAL_ONLY；**不是53个模块全坏，更不是117项当前生产重跑**。
- [证据库存](evidence-inventory.json)含351个主要receipt的元数据/hash，长字段有excerpt标识；不是宣称逐字读完全部收据。44个冻结计划输入hash+size相符；197个场景均passed但fixture_hash/oracle均缺，不能代替实际执行证据。
- [35个选定源码/证据快照](source-evidence-snapshot.json)在最终核验仍全部hash一致。[基础探针](probe-results.json)与[扩展探针](probe-results-extended.json)是经审阅具名纯函数/内存反例，不是生产回放。独立报告另列各自检查方法和未读范围。
- 观测HEAD：wiki `853dca2d30bc2b85dc95e3117a6afc3b448daec7`；filing `89c8bdb2cfba4d88720d005d0558f422957e8ade`；revenue `2ff20d9b410d3498181f7258a23ed9625caab826`。并发dirty已记录，不能把其他任务变化归于本审计；实施前必须重新校验版本。

## 本轮未做、不能据此推断的事项

未修改产品源码、旧计划、生产配置/数据库/收据、安装或Windows任务；未恢复worker、下载、调用LLM、prune或运行有生产副作用的全套测试。本审计写入限定本新增目录。当前暂停控制、已知HKCU启动项和历史launcher记录仅是有限证据；CIM进程查询权限不足，不能宣称所有进程都不存在或所有可能自启动通道都禁用。49GB目录数据库仅取stat，不为审计触发扫描/写锁。

真实多公司/多root当前完整链、生产性能、所有任务实际Action及自然7/2/1/1仍未全部重新验证，均作为明确未完成门保留。独立计划审查只判方案质量；任何WP的产品实施、真实验收与运行授权都没有因本报告自动通过。

下一步是阅读R4并批准精确DEV范围，从A合同与真实只读基线开始；D安全准备可按实际依赖并行，不阻A/B原文读取。网络、真实写入、持续调度和自启动分别另授权。不得直接照此恢复worker。
