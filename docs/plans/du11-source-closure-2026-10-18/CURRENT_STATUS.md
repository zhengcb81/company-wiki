# 当前项目状态 — 2026-11-01

**P0旧三个CI失败已根修；P1真实源卡/排名、恢复与P2新版RF采用已独审通过，但93f561ef新精确CI又报3项版本合同错误，当前先收口这项修复。P3药明康德新attempt只做免费预检，不进入付费/正式验收。** 唯一入口是本页及[机器状态](CURRENT_STATUS.json)；接手看[HANDOFF](HANDOFF.md)，实施看[task_plan](task_plan.md)，完成条件看[MAINLINE_LOOP_GOAL](MAINLINE_LOOP_GOAL.md)。

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
- RF日常测试曾隐含读CI不检出的docs夹具，6原字节夹具归tests后同环境81P，未加CI/下载。正常pre-commit已在推送前拦住一处新list缺类型注解，已补正确类型且独审/免费重放通过，无算法变化；当前P1测试：受影响域90P/3旧presentation断言，保持拒绝要求适配后6目标绿；source-use域53P，最终新文件23P，Ruff绿。93f561ef精确CI已failure3例，不能拿旧绿代签；已本机3F→54目标绿，旧HTTP捕获不改，新private view单独精确冻结。

## 发布、资源与恢复

本轮前CWP master/远端为2b5b89c6；最新实际已完成基线[CI41255499232](https://github.com/zhengcb81/company-wiki/actions/runs/41255499232)绿（acf11bb2），2b5为文档提交未触发CI。当前93f561ef已推master，[CI41261403683](https://github.com/zhengcb81/company-wiki/actions/runs/41261403683)新3F：两旧版本pin、一旧/5捕获未迁移；新修复待发布精确CI。RF生产main535604fa、[CI41254752622](https://github.com/zhengcb81/revenue-forecast/actions/runs/41254752622)绿；v6仅新增验收材料/离线重放，已[85054d7b](https://github.com/zhengcb81/revenue-forecast/commit/85054d7b260a3805b43ce6a4d49d44579745a015)推main，[精确CI41260918155](https://github.com/zhengcb81/revenue-forecast/actions/runs/41260918155)绿。三逻辑技能入口/2物理目标定点运行代码已同步，重复零写、3新进程实际通过，无新RF运行代码需重部署。

配置累计10M tokens/$20；当前母账1,849,869tokens/$0.739510，历史unknown保留。最新两次总14094tokens/$0.005271，另早期华利8217/$0.001425已含其中；计量是费用估计而非发票。预算/逐材料许可没有阻塞，原生goal active。门禁简化及存储虚拟接口主要工程已完成，当前问题是内容/采用/研究质量。

两份运行和RF v6均有禁止网络的离线重放；收据约626KB，没有PDF或整库归档。完整provider envelope临时清除后未留，仅保留decoded最终回复、native用量、pin/hash和当时实际恢复证据，不冒作可重建envelope。测试临时湖已清，用户原件/config不改；此前新下载年报及全规范化已清4662644B，仅保留62个实际原文span。本轮不恢复整库，不再扩包。

## 唯一下一步

先修版本捕获及选测共因，独审后推送并确认新精确CI；W12 r1-remediation-03已沿原2026-10-21截止冻结、独立executor免费预检中，待CI绿再进入正式执行。W21 canonicalC2增强/严格成员对齐、长文余项、跨市场新样本/US RPO在相关P3责任中承接，不能用nativefallback或此股东信代签。

Dayu/IQS/Dashboard不动。RF三份assurance定时产物和CWP hook mode差异为外来WIP；保留不暂存/恢复。外包只看[PACKAGE_STATUS](PACKAGE_STATUS.md)，不再把旧READY当新待交付。

选测共因：不确定范围原来把已知消费者一并丢掉。候选保留32个changed/最近静态consumer，仍一进程180秒、固定smoke不扩、远端CI不改；本次旧push范围10.64秒选图（此前36.88秒），其余明确延期。它仅部分覆盖，不能保证旧3例都被快速hook抓到，原子协议旧范围仍在32外；当前已修改测试会优先进入。

版本合同/选测候选已独审0OPEN，真本地Git正反E2E与Python3.10便携夹具单例通过，见[收口证据](review/mainline-closeout-20261031/p1-ci-repair/README.md)。新版发布精确CI仍待观察，不提前写绿。

正常push已在本机实际拦住9个旧Windows测试夹具宿主假设（642P/9F120s），fb2336c1暂仅本地；测量式共用夹具及长路径自清理已19P/13.28s并独审通过。远端未前进，新正常push后才能更新CI结论。
