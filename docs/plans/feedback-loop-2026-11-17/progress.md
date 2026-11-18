# 进度与恢复入口

2026-11-18。F4 的真实宿主与 FF 原生作业恢复已验收；F2 首批三张卡已验收、发布。分仓施工、真实收据和发布状态由此页维护。

| 节点 | 状态 | 证据或下一步 |
|---|---|---|
| F0 | 12 仓计划已落地，可发卡范围独审通过 | [协议](interfaces.md)、[模块与施工卡](dispatch.md)、[CWP 实施](company-wiki.md) |
| F1 | 离线总控及 CWP 首次接线独审通过 | [35 项测试、实际后台唤醒、封存 H1 和适用范围](f1-acceptance.md) |
| F2 | ET、SID、IR 已独审、离线组合验收并发布 | [三仓签收](f2-owner-acceptance.md)。其余按[分工](dispatch.md)，FF 的 job 协调、RF 实际消费与 Audit 接线仍归 ROOT |
| F3a | 真实宿主、FF 本地复用中断验收通过 | [独立验收与原生计数](f3a-host-acceptance.md) |
| F3b | 两份正式摘要、恢复和两条 RF 采用通过独审 | [实际组合与适用范围](f3b-live-acceptance.md) · [草稿与精选余项](issues/cwp-draft-scope-and-focus.md) |
| F3c | 已修正草稿范围与自动精选，保存响应及五份真实样本复验通过 | [真实回放、原始定位与保留对照](f3c-saved-response-acceptance.md) |
| F4 | CWP/FF 首条无人值守闭环与强杀恢复通过独审 | [验收及重跑](f4-acceptance.md)。其余 owner 的生产应用待接续；公司池按原有启停条件 |

### F0 发布与独立验收

- 采集 ET `68836237`、SID `16499a03`、IR `9b347fd7` 三张卡已发布。IR canonical 入口澄清旧工作区选择器的提交为 `f0ab95ff`，分发的卡内容一致。独立审查核对原生夹具、所属仓和写集合，判断三卡可并行。总控用三个实际卡上的机器样例导入两次，得到三次唯一发生，分别为合法 402、候选缺失和报告错误零命中。
- FF 主线 `a17fc632` 已发布，正常推送快测 11 项和同版 CI 通过。RF 远端主线 `51b26dcf0` 与原工作区 `698eabd1b` 的本次计划内容一致。另一个项目的九个原提交和三份运行记录归其原工作线。Audit `be450f80` 与 StockWiki `246910db` 在本地主线，两仓均无 remote。
- IQS 主线 `02a6c7fc`、活动分支 `3dde7fa6` 有同份计划，Dashboard 主线 `57e97d2b`，MeetingConverter `b43a76a3`，QA `21d3c99d`。QA 的发布从隔离工区完成，其活动分支尚未接入该主线文档，可使用[精确版本入口](dispatch.md)。原 QA 源码、Dashboard 交接资料和 MC 的覆盖率文件按实际所属保留。
- 独立读者从历史证据分辨 RF 周跑四次失败、随后 SID 身份和测试临时目录问题以及预期的损坏件拒绝，能从零退出的业务产物定位错误。修订将分诊转派、原消费方、新证据接续、同一运行的兄弟步骤身份与真实预算区分写入协议。

### F1 主线发布

总控、CWP 完成事件接线和测试已并入 `master`，源码提交 `0acb7e915b88ee89b98cdb6415b46b39a2d3d604`。推送前正常快测 23 项通过，用时 33.42 秒。远端同一提交的 Python 3.12 快测通过，作业用时 5 分 47 秒。35 项大节点复验和历史半年报的覆盖范围单列在[本地验收记录](f1-acceptance.md)。[远端 CI 作业](https://github.com/zhengcb81/company-wiki/actions/runs/44175698906/job/134366324766)

### F3 主线发布

F3a 源码 `71ca0791dd13a12290b71970d2d008869433da16` 已推主线，固定快测 23 项通过，用时 16.66 秒。远端同提交 CI 通过，用时 5 分 29 秒。[远端作业](https://github.com/zhengcb81/company-wiki/actions/runs/44185233338/job/134399879124)

F3b 源码和验收 PWF `c5c233c43bea16fe38ca49a5f4a55a054c16cf68` 已推主线。Ruff、mypy 和推送前固定快测通过，快测 23 项用时 10.10 秒。远端同提交 CI 通过，用时 5 分 30 秒。[远端作业](https://github.com/zhengcb81/company-wiki/actions/runs/44188395609/job/134410926044)

F3c 范围及精选提交 `603934c49`，公开接口修正 `d5cb85c1e1d382b001a8f079072b465a7d0e42e7`。定向回归、真实回放和独审通过。公开接口修正版已推送主线，推送前固定快测 23 项通过，19.63 秒。远端同一源码版 Python 3.12 全量单测和定向契约通过，作业用时 7 分 09 秒。 [远端作业](https://github.com/zhengcb81/company-wiki/actions/runs/44197811500/job/134443744029)

### ROOT 接续

F3b 已完成真实组合，F3c 已完成保存响应修复。F2 首批三卡的版本和组合已核对。F4 已验收到真实宿主自动分诊、采用确定的修复、原发现端复验、FF 回告。生产扩展匹配各 owner 现有计划；业务仍按父计划接续新版生成的真实公司组合及 RF 正式采用。CWP 本仓修理继续走[技能](../../../skills/repair-company-wiki-issue/SKILL.md)。
