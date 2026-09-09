# 修复总计划独立审查

日期：2026-09-06。审查者：audit_filing；非remediation-plan.md作者。审阅版本：R1、NOT_IMPLEMENTATION_AUTHORIZED。范围：总依赖/门、assurance/filing/H01发现覆盖、独立agent节点、授权/副作用/自然窗口以及弱模型误执行风险。未重新独立审计全部矿业/收入公式，不把本review算全部产品验收。仅本文件为新增写入物，未修改总计划或产品。

## 总结与verdict

**changes_required（计划级，不是产品运行判决）**。计划已经覆盖本审查涉及的主要问题，G0–G5每个节点明确独立review，禁止直接实施/启动/外发/删除的边界清楚；没有发现工作包编号层面的显式依赖环。但依赖尚未落实到可机器判定的具体门，WP12真实运行前置门也不完整，弱模型可能陷入验收互等或在后续安全包未过时进入G4。两项P1应在把计划交给实施模型前解决。

## P1-PLAN-01：依赖“包完成”与“设计/隔离门完成”混用，可能互等或过早放行

位置：依赖表33–47、通用节点16–27、WP00步骤5/7、WP13步骤3–5。

证据：WP01写“00设计门”，WP07写“06隔离门”，但WP02/WP03/WP04/WP09等只写裸00/02。通用执行卡又要求每包G4实际接线、G5签收全部required结果；WP00要求真正closure消费入口和required真实tier，后续原目标结果却要由WP02–14才能产生。

两种解释都危险：

- 将裸WP00解释为全包G5+production_verified，会要求先拿到后续实际目标结果，后续包又不能开始，形成语义上的验收互等。
- 将其解释为“代码写完”，则可在证据机器本身未独立验证或安全依赖未过时跳到G4。

具体修改要求：

1. 增加一张**gate级依赖表**，每条边必须精确如`WP02.G0 <- WP00.G1`、`WP02.G3 <- WP00.G3`；不再使用裸编号或“全部所需门”等无法机械判断的文本。
2. 将WP00分为证据能力交付与原目标最终资格判定两个不同状态：前者可在隔离fixture和真实CLI消费路径G3验证后解锁DEV；后者只在WP13/14后形成，不是后续DEV的前置。
3. 为WP11持续CI门同样区分bootstrap能力与最终覆盖率；每个实现包只需依赖其适用的CI gate版本，不能等待“所有后续包都接入”才开始。
4. 将未来每包G4是否适用做明确decision：纯格式/helper/验证器包可在独立operator批准的隔离真实CLI中完成接线，不能被通用卡强迫打开生产DB/联网。N/A须由独立reviewer签范围理由，而不是把N/A自动标production_verified。
5. 计划自身验收：独立agent拓扑排序gate DAG；空/未知gate拒绝；造“WP00等WP13、WP13等WP00”的负例必须被检测；检查所有G4之前具有必需授权与安全门祖先。

这里不是声称当前文本有明确数字环；问题是尚未定义裸依赖对应状态，足以让弱模型产生互等或错误放行。

## P1-PLAN-02：WP12实际T2/Monthly的前置安全与业务门未列全

位置：依赖表45、WP12步骤2–6、WP13依赖、全局规则4。

证据：WP12仅列00/03/04/11；但其Daily要跑实际resolve/bundle/Reader-live-WAL/fault/完整pipeline，Monthly要轮换真实broker/矿企/非矿企。它实际消费WP05外发/cohort、WP06worker安全/取消、WP07broker、WP08资产、WP09发布、WP10回测。虽全局规则说安全未过不启动worker，局部操作表缺少这些具体门，且WP13又依赖WP12“全部所需隔离门”，容易把报告能力先跑真当作完成。

具体修改要求：

1. 拆出`WP12a`调度/报告/告警能力的隔离验证、`WP12b`获授权真实运行、`WP12c`自然时间累积；它们可仍归WP12，但状态和entry gate必须不同。
2. WP12b任何pipeline/worker步骤至少依赖WP01/02/04/05/06对应isolated_green与独立安全签收；使用broker/mining/backtest/render的case分别追加WP07/08/09/10能力门。
3. WP13先使用WP12a报告能力完成真实小cohort，WP12b/12c再使用WP13已验证case定义进行持续运行。禁止用未通过真实cohort的case开始计算成功soak。
4. WP12c不足7/2/1/1只保持observing/pending，不阻断无副作用DEV继续，但始终阻断WP14相关退出资格。告警演练和网络预算须预先批准，不能因需要自然run自动开启provider。
5. 加反例：WP05未过而WP12b请求LLM→拒绝；WP06未过而Daily启动worker→拒绝；Monthly只有synthetic样本→不计数；仅注册task→不计自然run。

## P2-PLAN-03：调度部署、手动启动和自动启动授权类型仍有空隙

位置：全局三种授权规则、WP12步骤4–6、WP14步骤1/6。

DEV明确只含代码/测试，CANARY描述是数据/DB行/文件/网络/费用，AUTOSTART描述是后台/登录启动；但WP12创建/修改Windows计划任务、配置watchdog/告警sink属于持续外部状态变更，不能由普通CANARY数据授权推导。WP14亦区分session启动与登录启动，但未在授权表给出两者独立记录字段。

修改建议：不必增加复杂角色体系，但应给CANARY的操作subtype明确`manual_worker_run`、`schedule_register_or_update`、`watchdog_enable`、`network_case_run`等；每项列exact task name/SID/action/profile、周期/失效时间、最大run数与日/月预算、撤销动作/恢复原注册快照。注册任务不授予无限未来网络/LLM调用。登录启动继续单独AUTOSTART，禁止从手动启动授权推定。

## P2-PLAN-04：可信归档计划缺稳定读快照与clock注入的显式要求

位置：WP01步骤1–5；对应retention-independent-review的P1归档覆盖风险。

覆盖/hash/原子publish已安排，但“开始COUNT→分页SELECT→结束校验”的一致性策略尚未写明。弱模型可能只给旧算法加输出SHA，仍没有一个稳定span集合。原测试硬编码日期随日历变化的问题也未明确纳入测试要求。

修改建议：

- G1冻结一致snapshot或等价高水位/版本合同；manifest的精确PK集合与实际导出都取同一稳定数据视图，不能跨批刷新状态却只比较总数。
- 注入可信clock用于隔离测试；新增retention边界前1秒/恰到/后1秒、未来目录名、真实retired_at晚于archive、同日空archive之后新增退役文档负例。
- 明确archive/prune不同事务窗口中的重激活/新增span必须使删除资格失效或仅保留原精确集合，不以operation lock本身代替生命周期检查。

## P2-PLAN-05：部分发现只有工作包总目标，缺对应测试ID与输出检查

已经覆盖大部分发现，但建议加入下列不可被总称“失败事实完整”或“来源hash检查”吞掉的显式测试：

| 审计发现 | 建议新增目标/ID | 最低oracle |
|---|---|---|
| filing F-F06 structured gap缺calls/downloads；一般fatal丢stats | WP03 T07 gap分支/T08 unexpected fatal | 真实CLI JSON含统一schema及已知阶段计数；unknown不可缺省0，spy计数独立对账 |
| filing F-F08 bundle内外hash只是字符串相等 | WP04 D10 两处hash保持相等但改payload | 真canonical recompute的生产消费者拒绝；不得只比较两个字段 |
| A04 legacy ledger不可读、scan JSON坏值被当无问题 | WP12 O13/O14 evidence unavailable | 未知必需输入不能ok/fresh，不以0 errors代unknown；保留明确缺失原因 |
| A03 scenario_runner dry-run写目录/evidence；按test名开启下载变量 | WP00/WP11 E13/Q10 | 真实CLI dry-run在OS写哨兵下0写；测试名称变化不得扩大network grant |
| A06 scanners-only将未跑quality维度填ok | WP11 Q11 selected-scope report | 未执行维度not_run而非ok，release required维度缺失即阻断 |

计划最后应提供finding ID→WP→具体RED/fault ID→G3/G4证据字段表。仅把117项标“已记录”不足以机械证明整改计划无遗漏。

## P2-PLAN-06：删除后的RPO0与恢复对象要定义，不能用口号扩大承诺

位置：WP13步骤4“失败恢复RPO0”、WP01生产删除操作卡、WP14真实cohort回滚再激活。

修改建议：逐操作写恢复对象及loss边界：raw不可修改；EvidenceSpan精确恢复locator/parser/hash；publication registry保留append-only intent与失败事实；provider外部调用不可撤销则计费/unknown事件不能通过回滚抹掉。回滚验证不等于再次启动被暂停worker；每次再激活仍需当前运行授权。无法实现物理RPO0的外部副作用应给补偿/人工处置，不虚构“撤回下载/费用”。

## 主要发现覆盖检查

| 审计范围 | 已覆盖工作包 | 复核结论 |
|---|---|---|
| assurance A01/02 假完成、valid/accepted、拒绝与历史重签 | WP00、WP11、WP14 | 已明确区分资格，较原审计措辞更严谨；需P1-01门级拆分 |
| assurance A03 tier/skip/rc/映射 | WP00、WP11 | 主要覆盖；dry-run与文件名授权见P2-05 |
| assurance A04 daily SQL代理/三root/精确当前组合 | WP12、WP00 | 主要覆盖；缺输入fail-closed见P2-05 |
| assurance A05 release helper/atomic/未来/soak/停跑告警 | WP12、WP14 | 主要覆盖，真实入口独立review明确；依赖/授权见P1-02/P2-03 |
| assurance A06 fanout/requiredCI/AST/工具失败/legacy | WP11、WP14 | 主要覆盖，不以旧accepted证明删除 |
| filing F-F01/02 policy与eligible | WP02 | 覆盖上下文注入/per-root false/替代副本/symlink与negative tests |
| filing F-F03/04 freshness/授权/单飞 | WP03 | 覆盖4反例/period/byte cap/多项partial/不同授权同候选 |
| filing F-F05/06 deadline与事实保留 | WP03 | 核心已覆盖，完整CLI分支见P2-05 |
| filing F-F07 profile | WP06 | 全阶段wall/CPU/RSS/I/O、真实样本与不删除慢样本明确 |
| filing F-F08 FC903/真实T3/bundle | WP00、WP03、WP04、WP13 | 历史字节保留/独立重放/三市场授权明确；bundle mutation需单列 |
| H01 prune/归档/自动入口 | WP01、WP06、WP14 | P1安全门充分表达，snapshot/clock进一步明确 |
| H02/H03/H04/H05 | WP07/WP02/WP06及全局边界 | 未重新启用Strategy A/研究writer，不误把v5规划当实施，方向正确 |

## 独立agent与实施纪律的已通过部分

- 每WP全G0/G1/G2/G3/G4/G5均安排独立角色，不只是最后一次review；Reviewer-C不得是实现者或原oracle作者，角色隔离有实际taskID/hash/结果要求。
- 未获最终verdict、skip、额度中断、工具缺失均不能当PASS；不存在为赶进度自动豁免自然时间的文字。
- DEV/CANARY/AUTOSTART分开、保持paused、来源/研究边界、并发dirty保护、旧收据不重签覆盖、真实外发逐manifest上限，都明确。
- 本次仅审查计划可执行性。即使上述修改完成并获计划级独立accepted，仍不等于任何产品WP通过G3/G4/G5，也不授予产品修改或生产运行权限。

## R2 delta 独立复核（2026-09-06 20:52 BST）

审阅对象：remediation-plan.md R2，raw SHA-256=`07a0741d1ebe8a7ac82798efc9f0e33fcc77dd20d8119a703d9a097be24f562d`。本次核对R2头部优先级声明、第2节主题导航降级、新第5节gate依赖/动作门/12a-b-c、第6节操作卡与新增RED；没有重写R1历史verdict。

**R2 verdict：accepted_for_planning_delta（计划修订通过，NOT_IMPLEMENTATION_AUTHORIZED保持不变）。** 前次两项P1与四项P2已得到实质处理；在本次有界delta内未发现新的阻断性P1/P2。此结论仅关闭R1计划审查finding，不关闭产品问题。

### Finding逐项处置

| R1 finding | R2证据 | delta判定 |
|---|---|---|
| P1-PLAN-01 裸依赖/验收互等 | 第2节明确只导航，第5.1将WP00能力签收与WP14最终资格分离；WP11 bootstrap与最终矩阵分离；第5.2逐G0/G3列边；内部G0→G5边明确；G4显式scope | 关闭（计划级）。能力拒绝缺tier不要求先取得目标真实成功，因此不再用最终目标完成阻塞基础证据能力。 |
| P1-PLAN-02 WP12真实门不足 | 第5.3按动作取安全门并集；12a=隔离，WP13只依赖12a；12b依赖WP13.G5和相应动作门；12c依赖12b+真实7/2/1/1；WP14.G4依赖12/13.G5 | 关闭（计划级）。真实cohort先验证，持续/自然计数后进行，不再允许把注册/合成报告当自然资格。 |
| P2-PLAN-03 调度/手动启动授权 | 第6节列manual_worker_run/network_case_run/schedule_register_or_update/watchdog_enable独立subtype、起止时间/max runs/日月预算/撤销与原注册快照；第5.3注册保持disabled至12b | 关闭。注册不默认授权未来网络/LLM或登录启动。 |
| P2-PLAN-04 snapshot/clock | 第6节同稳定视图PK与字节、跨批count不等于集合；H11–H16覆盖保留期边界/未来/空archive/并发/重激活 | 关闭。后续G1仍需实际选定快照协议及恢复合同，未定时不可实施生产动作。 |
| P2-PLAN-05 显式测试遗漏 | 第6节T07/T08/D10/O13/O14/E13/Q10/Q11全部列为强制G1/G3+独立oracle；WP00.G1一条原条款/发现一行机器映射，缺失阻断 | 关闭。未来执行结果字段pending、不伪填hash这一限制清楚。 |
| P2-PLAN-06 RPO0边界 | 第6节区分raw、EvidenceSpan精确恢复、append-only publication与不可撤销provider费用；再激活另授权 | 关闭。没有继续承诺撤回外部调用或删除失败历史。 |

### 依赖与提前运行风险的独立核对

人工检查的无环主链为：WP00能力G1/G3 → WP01/02/09/11设计/隔离能力 → WP03/04 → WP05 → WP06 → WP07 → WP08 → WP10；WP12a依赖00/03/04/11隔离能力；WP13在01–12的G3之后进入真实cohort；随后12b真实持续case → 12c自然资格 → WP14真实退出。WP09和WP11可在各自精确门后并行，不需要等待所有后续包最终签收。

关键非环边界已明确：

- WP00.G3只测试真实CLI拒绝缺证据的能力，不等待WP13成功。
- WP13.G3只等WP12.G3（12a），不等WP12.G5（12c）。
- WP12b才等WP13.G5，因此不会形成WP13与自然soak互等。
- 安全Sxx由对应WP.G3加独立Ops/Safety复核产生，不等待同包G4，这允许先证明隔离安全再准入真实动作。
- 所有authorized_canary必须本包G3、00.G3、11.G3、版本适用CI、精确授权及独立Ops批准；作用域不明默认拒绝。涉及多个动作取门的并集，不能只挑最宽松动作标签。

因此未发现R2文本中的显式gate环或通过裸WP编号直接提前真实运行的通道。这里是人工计划审查，不是假称执行器已实现这些防护。

### 仍保留的实施前义务（不是新计划缺陷）

1. gate-dag.json、实际拓扑验证、环负例、每个G4安全/授权祖先枚举尚未生成或执行；R2明确它们是未来G1必需门。不能用本人工review替代。
2. G1的integration_scope、exact allowlist、适用case矩阵和具体授权尚待逐包冻结；没有这些字段就保持pending，不能因本R2 accepted自行填值或运行。
3. isolated_cli与authorized_canary的证据不可互换；N/A仅在独立签理由后适用且不产生production_verified。
4. 本review不批准创建计划任务、启动worker、任何网络/LLM、归档或删除；不确认7/2/1/1自然窗口已发生，也不确认任何产品bug已修。

本次只向本独立review文件追加记录，未改主计划或产品，未执行任何产品操作。
