# 当前项目状态 — 2026-11-01

**P0三个CI失败已根修；P1新版华利及Berkshire的有界真实卡片/排名、缓存恢复和P2新版华利RF实际采用已独审通过，正在正常发布当前代码。整个公司研究循环尚未完成。** 唯一入口是本页及[机器状态](CURRENT_STATUS.json)；接手看[HANDOFF](HANDOFF.md)，实施看[task_plan](task_plan.md)，完成条件看[MAINLINE_LOOP_GOAL](MAINLINE_LOOP_GOAL.md)。

| 节点 | 现在的真实状态 | 尚未签收的范围 |
|---|---|---|
| P0 CI延期合同 | 已发布，精确CI41247282332绿 | 不靠删断言/加额度 |
| P1 新版华利 | 1次MiMo，15完整原文卡/12业务原子，activation及同跨run缓存0重复POST，独审PASS | /5为摘录卡＋排名，不是生成式概述/全文完整 |
| P1 Berkshire | 1次DeepSeek，88任务/73卡/15延期，10所需业务原子保全；真实恢复/读取独审PASS | 15 unprocessed，全文partial；股东信不是10-K，曝光开发样本不是盲测 |
| P2 新版华利v6 native采用 | **新a466 artifact**完整t3/出处/理由进入参数、公式、报告、snapshot/registry；45独立检查PASS | 条件算例，不是当前公司买方研究通过 |
| P3 公司研究循环 | 未完成；本节点发布CI后恢复W12新attempt，再新公司/固定八家 | 不能用工程卡数量替代公司四审及真实研究 |

## 本轮共因与验收

- P0旧三例在lookahead前已耗尽，完整延期由frontier0表达；已覆盖真实lookahead及实际消费者，生产限额不变。[证据](review/mainline-closeout-20261031/p0/README.md)。
- P1旧模型收到88任务、canonical只准72卡，74249B不能在原预算下请求；group发现顺序还挤掉后附的重要业务段。现在同级按真实来源坐标分配，完整support/context只存一次且只发送准入卡；未发送项继续unprocessed。Berkshire实际39520B/预留47840小于既有50000，未加额度、未截原文、未写公司特判。[当前独审/真实运行](review/mainline-closeout-20261031/p1-current/README.md)。
- 可读原文与可作事实支持被一个execution validator混淆，混合context_only/unresolved＋support会失败。已由来源generation-reason唯一判定，正例与伪造admitted负例通过。其后两个验证依赖变化由独立免费增补签收；两份已付费HTTP、draft及每项execution逐字相同，旧运行签名不重写。
- RF先前完整摘要只在旁收据、正式claim仅首段，现已由纯证据DTO持久完整支持/context及采用理由，计算层无物理源IO。非零小单价显示、操作数锚、投影与反向引用也已根修。新版v6确切artifact再次进入实际公式；正式报告仅在RF仓，CWP不存投资结论。[先前P2根修](review/mainline-closeout-20261031/p2/README.md)。
- RF日常测试曾隐含读CI不检出的docs夹具，6原字节夹具归tests后同环境81P，未加CI/下载。当前P1测试：受影响域90P/3旧presentation断言，保持拒绝要求适配后6目标绿；source-use域53P，最终新文件23P，Ruff绿。正常发布/精确CI尚待本次实查，不拿旧绿代签。

## 发布、资源与恢复

本轮前CWP master/远端为2b5b89c6；最新实际已完成基线[CI41255499232](https://github.com/zhengcb81/company-wiki/actions/runs/41255499232)绿（acf11bb2），2b5为文档提交未触发CI。当前代码发布后更新精确SHA/CI。RF生产main535604fa、[CI41254752622](https://github.com/zhengcb81/revenue-forecast/actions/runs/41254752622)绿；v6仅新增验收材料/离线重放。三逻辑技能入口/2物理目标定点运行代码已同步，重复零写、3新进程实际通过，无新RF运行代码需重部署。

配置累计10M tokens/$20；当前母账1,849,869tokens/$0.739510，历史unknown保留。最新两次总14094tokens/$0.005271，另早期华利8217/$0.001425已含其中；计量是费用估计而非发票。预算/逐材料许可没有阻塞，原生goal active。门禁简化及存储虚拟接口主要工程已完成，当前问题是内容/采用/研究质量。

两份运行和RF v6均有禁止网络的离线重放；收据约623KB，没有PDF或整库归档。完整provider envelope临时清除后未留，仅保留decoded最终回复、native用量、pin/hash和当时实际恢复证据，不冒作可重建envelope。测试临时湖已清，用户原件/config不改；此前新下载年报及全规范化已清4662644B，仅保留62个实际原文span。本轮不恢复整库，不再扩包。

## 唯一下一步

完成当前P1根修与P2新版验收材料的正常提交/推送、确认精确CI，再恢复P3药明康德W12新attempt。W21 canonicalC2增强/严格成员对齐、长文余项、跨市场新样本/US RPO在相关P3责任中承接，不能用nativefallback或此股东信代签。

Dayu/IQS/Dashboard不动。RF三份assurance定时产物和CWP hook mode差异为外来WIP；保留不暂存/恢复。外包只看[PACKAGE_STATUS](PACKAGE_STATUS.md)，不再把旧READY当新待交付。
