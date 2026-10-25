# W16/W17/W18 施工包独立审查

审查日期：2026-10-25。独立审查agent：`/root/w16_w18_packet_review`，未参与施工卡编写或种子准备。最终结论：**PASS，可以发包；无未解决finding。**

## 范围与方法

独立阅读README、COMMON、三份施工卡及handoff模板，并按需只读核对RF历史收入校验/报告、Audit导入/文档状态join、已有DU5/W15交接，以及CWP现有benchmark与零费用预检实现。重点审查任务是否重复、责任层与接口是否清楚、三线是否写冲突、是否新增门禁或强迫语义PASS，以及独审、修复、测试恢复、空间和交接要求是否完整。

最终复核实读dispatch、三工区START_HERE/INPUTS、24份seed文件SHA；通过Git只读命令核对实际HEAD、分支、父提交、相对base变更与tracked状态。未运行产品测试、未调用模型/金融API、未下载原件、未修改产品代码或工区；本审查只保存本报告及同名JSON。

## 初审发现与处置

| ID | 初审发现 | 修复与最终复核 |
|---|---|---|
| P01 | README中的CWP完整SHA与Git实读不符；发包前需纠正并补实际工区/seed的dispatch。 | 已统一为`ba8f8543c0351f6857e1ce24e943ad9da1b664ef`。三工区实际HEAD/branch均与dispatch一致，HEAD父提交均等于固定代码base；各自只增加8份本地PWF文档。关闭。 |
| P02 | W18只禁止复制第二套选材算法，未明确要求复用现有金标/评测/恢复设施，弱模型容易另建框架。 | W18新增明确条款：优先复用`tools/document_understanding_benchmark`的gold/records/recovery/native及`holdout_acceptance_contracts.configured_preview`，新工具只做薄编排；不适用时说明具体接口缺口。工区卡与中央卡逐字一致。关闭。 |

## 最终核对结果

- W16复用DU5数量/货币owner，处理显式历史收入口径与实际预测基数采用；不重做币种注册表，不改CWP/FF/Audit。
- W17复用W10 join及W15设施，六维观察保持observed/unknown/conflict边界；不制造业务PASS，不依赖W16/W18新增字段。
- W18仅写独占的新测试工具/样本/PWF目录，生产源码由ROOT负责；冻结候选，源侧gold先冻结，机械可见性不冒充摘要语义通过。H06允许现有样本不足时如实交INCOMPLETE，不强迫造样本。
- 三卡都有大节点集中测试、未参与实现的独立agent审查、全部本范围问题修复/复测/复审、最终版本绑定、原始失败保留、独立测试根恢复、空间限制和固定交接接口；没有小节点签收要求。
- 三工区tracked状态均为空；相对代码base的变更均仅为各自8份PWF seed。24份seed的实读SHA与dispatch全部一致，三施工卡及COMMON中央/工区副本逐字一致。产品实施尚未开始。
- W18的`core.filemode=false`与`core.longpaths=true`均来自其专属`.git/worktrees/company-wiki-w18-holdout/config.worktree`，`extensions.worktreeConfig=true`；pre-push实际字节与HEAD blob同为`3f7f309e8690f39f41ebe90634c1247e8a82d32e`。cone包含目录与dispatch一致。该核对未写原主工区或hook。

## 已实读seed版本

| 施工包 | 固定代码base | 实际seed HEAD |
|---|---|---|
| W16-RF-BASIS | `094d55ad884e4a886b1537c0e76f3a0bede16ca2` | `97e7e149d434d5ce36c147531efa4405a88fcb1c` |
| W17-AUDIT-COVERAGE | `bb41d9beda94fead3aba4bc65ed8c6dce4314e97` | `02ee879ccf8e4aed67342bcc7c8c7e20de2401c9` |
| W18-CWP-HOLDOUT | `ba8f8543c0351f6857e1ce24e943ad9da1b664ef` | `9051bbb7a69347f52d79e5cce37a6b8c40b7912f` |

## 最终文档SHA-256

| 文件 | SHA-256 |
|---|---|
| README.md | `a6f8900498065eb884e3dfe9f752ca11236271e0fb5eb9ac82645c5f9619a506` |
| COMMON.md | `de0126a8274c585621a574f9da3a602f3e808b76e307143b3bd16927d2f053af` |
| W16-RF-BASIS.md | `4674c8d57d9112250c19f4b340543fc13bfa5ed8d7c27cfe64df8abe0a55ca49` |
| W17-AUDIT-COVERAGE.md | `02b88ae3be8c0fbe10aa5b8ca55e12b7bcab347769bedc6b26b5f74741e678e4` |
| W18-CWP-HOLDOUT.md | `3f27a5ae5cd4ad858cd05d35c8456b5930e113c363c5669324a34e86cd02379f` |
| handoff.template.json | `32588d5d7ec2e4f432d286def41c79e48fe9c6f2925c7517de8def36e3b5d96f` |
| dispatch.json | `39b9bb72a95cf52e71f6b2e593b9921b814521dce7b68326af77987e2f424337` |

本次PASS证明施工包完整、可执行且并行边界清楚；不证明尚未实施的产品代码、真实摘要质量、RF实际采用或annual14内容验收通过。执行期间的新产品finding仍按各卡保留和处理。
