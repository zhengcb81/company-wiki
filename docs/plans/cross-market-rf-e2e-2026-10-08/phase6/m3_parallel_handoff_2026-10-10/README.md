# 三条可立即接管的独立施工线

更新：2026-10-10。这是现有 W02/W06/W07 的施工接管，不是另外增加三组需求。本目录只有三张任务卡；用户每个 harness 只交一张。冻结专家包保持原字节不改。

## 当前事实

- MAIN 已发布 CWP master 3c791e3c2a16c12627cc25d0bd8681cc9458e48b；精确 CI 38058744767 已 success。
- 三个内置 agent 均因账号额度返回 terminal errored；2026-10-10 实查各自工作树没有源码修改，只有明确归属的前期计划。不得把计划当实现，也不得重启原 agent 与接管 harness 双写。
- CWP/FF/RF 基线分别是 3c791e3c、41ba0150、0c248d9a。各卡必须记录完整实际 HEAD；已经创建工作树，优先复用，不再复制整仓/原件湖。
- MAIN 继续独占 W04 模型运行时、共享 AUTO 接线、共同发布/安装、真实三公司大节点和研究审查。

## 只发这三张卡

| 卡 | 任务 | 开工目录 | 源码基线 |
|---|---|---|---|
| M3-JSON / W02 | 官方多公司 JSON 原件、公司投影、定位与公开读取 | C:/Users/郑曾波/.codex/worktrees/m3-official-json-20261010/company-wiki | CWP 3c791e3c |
| M3-USAGE / W06 | CWP→FF→RF 下载成功/失败/复用的真实用量保真 | C:/Users/郑曾波/.codex/worktrees/m3-acquisition-usage-20261010/company-wiki；同级 filing-fetch、revenue-forecast | CWP 3c791e3c / FF 41ba0150 / RF 0c248d9a |
| M3-FLOW / W07 | RF 半年/季度 flow 和未来机制证据角色的新显式合同 | C:/Users/郑曾波/AppData/Local/Temp/rf-period-evidence-20261010 | RF 0c248d9a |

卡文件分别为 official_json_projection.md、acquisition_usage_chain.md、rf_period_evidence_contract.md。路径只认本表和各卡，旧工作卡是只读需求依据。

## 为什么可以同时开工

三个 harness 的物理工作目录不重叠；M3-USAGE 是一条线内部的三仓串行管道，不拆给多个 harness。各卡的源码/测试文件也分开。JSON 只处理原文及投影，不修改下载预算/来源操作投影；USAGE 不修改 JSON importer 或 RF 研究合同；FLOW 不修改下载/来源准备或原 RF output。

共享文件由 MAIN 修改，不以抢同一个文件或另建替代入口解决冲突。参见 INTERFACES.md。发现需要共享接线时交具体 patch/DTO/红测，继续自己写集中的工作；这是实现分工，不是新增用户许可或人工签收门。

## 最终接收

每条线完成自己的真实责任测试、隔离恢复和正常 branch commit/push；不自行合主线、不复制安装技能、不运行付费公司审计。MAIN 在一个大节点串行集成共享入口，核精确 CI，并定点安装 changed runtime 闭包，然后做原三家全链四审/新三家泛化。独立交付不代表整体目标完成。

每卡交 HANDOFF.md + handoff.json + INTERFACE_CHANGE.md + 测试原始日志。统一格式见 HANDOFF_TEMPLATE.md，机器字段见 handoff.schema.json。没有增加逐小节点人审。
