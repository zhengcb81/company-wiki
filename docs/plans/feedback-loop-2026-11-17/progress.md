# 进度与恢复入口

2026-11-19。F4 的两条真实宿主闭环及 FF 短请求、MC 转录反馈组合已验收。四张在途接续卡走各自现有 harness。分仓施工、真实收据和发布状态由此页维护。

| 节点 | 状态 | 证据或下一步 |
|---|---|---|
| F0 | 12 仓计划已落地，可发卡范围独审通过 | [协议](interfaces.md)、[模块与施工卡](dispatch.md)、[CWP 实施](company-wiki.md) |
| F1 | 离线总控及 CWP 首次接线独审通过 | [35 项测试、实际后台唤醒、封存 H1 和适用范围](f1-acceptance.md) |
| F2 | ET、SID、IR、FF 短请求和 MC 转录反馈均已发布。四张接续卡已交现有 harness。 | [首批签收](f2-owner-acceptance.md) · [FF 和 MC 交付](dispatch.md#ff-和-mc-隔离施工交付) · [现有 harness 接续卡](dispatch.md#现有-harness-接续卡) |
| F3a | 真实宿主、FF 本地复用中断验收通过 | [独立验收与原生计数](f3a-host-acceptance.md) |
| F3b | 两份正式摘要、恢复和两条 RF 采用通过独审 | [实际组合与适用范围](f3b-live-acceptance.md) · [草稿与精选余项](issues/cwp-draft-scope-and-focus.md) |
| F3c | 已修正草稿范围与自动精选，保存响应及五份真实样本复验通过 | [真实回放、原始定位与保留对照](f3c-saved-response-acceptance.md) |
| F4 | CWP/FF 与 RF/Audit 闭环、FF 短请求和 MC 发布清单闭环通过独审，按正式交接验收其余 owner | [FF 与 MC 组合](f4-acceptance.md) · [RF/Audit 复验和回告](f4-rf-audit-acceptance.md) |

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

F4 RF/Audit 在已审 RF 版本 `24e8f978` 上完成，RF 公开作业相关 34 项通过，CWP 反馈宿主及实际 FF 强杀 21 项通过。Audit 全量 797 项离线测试通过，代码与 PWF 在本地 `main@9a38021`，该仓当前没有 Git remote。独审认可两份收据的验收范围。[RF/Audit 验收](f4-rf-audit-acceptance.md)

MC 开工基线的 4 个失败都来自合段后译文夹具长度不符，81 通过。作者版修正成功夹具，保留真正的段数不符校验，完成后交实际 JSONL、受审提交和独审收据。[MC 作者交接](../../../../MeetingConverter/docs/plans/f2-mc-output/handoff.md)

ROOT 完成 F4 的外层进程未启动时恢复。两条实际退出用例从红转绿，启动器错误诊断反例通过。最终定向 27 项和 RF/Audit 离线组合复验通过，独立复审已收口。[宿主恢复补验](f4-acceptance.md#4-外层-worker-未启动原生命令时的恢复)

ROOT 独立完成 F4 的回告已落盘、宿主丢回复恢复。FF/RF 真实端口强停后仅用原 action 的 owner 查询，各只写一次，原工作区在可信完成后继续排队动作。38 项定向与现有 RF/Audit 离线组合通过，独立复审通过。[验收和复跑](f4-acceptance.md#5-责任仓已保存回告时的恢复)

2026-11-19 签收 F2-FF-SHORT。ROOT 修复非法请求意图丢失终态的通用类型问题，最终 224 项和 8 子例通过。FF 已发布 `main@95769c0`。实际 CLI 与受控 provider 的 FF→CWP→ROOT 测试通过并清理测试根。首取后按同一 SHA 复用，重复导入零新增请求，两条未知用量如实保留。独审在最终 FF 版本和 ROOT 组合测试上复验。[组合验收](f4-acceptance.md#6-f2-ff-短请求进入总控)

2026-11-19 签收 F2-MC-OUTPUT。ROOT 在真实公开入口复现调用身份冲突及旁路误伤，反馈层修复后 MC 全量 302 项、CWP 定向 29 项通过。独审在最终候选独立复跑 MC 46 项和组合 1 项。MC 远端主线为 `1d3fd6c`，覆盖率原文件指纹和作者工作树保持。陈旧译文发现侧复验已完成，自动分诊和回告仍待公开运行端口。[MC 组合验收](f4-acceptance.md#7-f2-mc-转录发布反馈进入总控)

MC `8b8e574` 新增本仓公开运行端口并接通本机 F4 宿主。自动分诊、清单修复、复验及持久回告均实际执行。两个强退窗口找回同一动作，无重复转录或翻译，旧费用未知保持。MC 全量 310 项、总控 33 项通过，最终独审复验通过。[MC 运行验收](f4-acceptance.md#8-mc-公开端口自动恢复发布清单)

四张在途卡均已交正式收据。只读核定首次正式交付（UTC）：StockQA `ca896a0` 20:14:34，StockWiki `1da1e4f` 20:16:50，IQS `556bf3a` 20:21:30，Dashboard `6073069` 20:35:15。ROOT 以此顺序进入验收，正式完成版本仍以最后独审为准。[分发与排队](dispatch.md#现有-harness-接续卡)

### 四张接续卡 ROOT 验收

| 顺位 | 验收结果和发布状态 |
|---|---|
| 1. StockQA | 补齐已发布 IQS 同一版公开合同后，证实普通 approved owner 恢复已结算失败响应时被重复模式校验拒绝。修复后 102 项定向及 14 项实际恢复正反例通过，独审复跑 14 项。原回执、租约与账本复验通过。坏单题有明确诊断，合法兄弟仍可恢复。已发布 `codex/qa-content-filter-resolution-01@7093681`，原主线分歧归既有恢复线。 |
| 2. StockWiki | 冻结黄金经公开入口正式登记，身份与 SourceRef、旧及混尺度结果共 177 项通过。ROOT 验收本地 `master@47a2cf3`。本仓当前无 Git remote。 |
| 3. IQS | 逐题覆盖、V2 分组、合法部分、缺失和查询反馈共 50 项通过。已发布原 `codex/iqs-manifest-delivery-01@c73801f`。正式结果经真实 StockWiki 命令读取，保留原 ID、三组和历史。 |
| 4. Dashboard | 真实组合复现兼容版本误拒。在适配器读取同协议的兼容版本后，正式结果、历史和六条反馈均绑定同一 ID。121 项及 32 子例通过，独审 27 项、6 子例及真实 HTTP 组合通过。已发布 `main@1e5f101`。D00 临时工作树和在途 FF 手册按原归属。 |

九份正式侧车交付合计 86 条唯一观察（74 预期、10 未知、2 偏差），无导入诊断和未配对开始。两条 IQS 注入偏差归 StockWiki，发现仓保持 IQS。原样重投结果一致。隔离组合使用真实 StockWiki 正式登记、真实 IQS 投影和 Dashboard HTTP 入口，保留同一结果、期次、历史与三组上游来源。完整的逐组 UI 展示继续归既有 D01。

生产扩展匹配各 owner 现有计划；业务仍按父计划接续新版生成的真实公司组合及 RF 正式采用。CWP 本仓修理继续走[技能](../../../skills/repair-company-wiki-issue/SKILL.md)。

### 版本与诊断引发的误拒

Dashboard `5018207` 与 IQS 原交付分支 `ac26a3b` 统一读兼容版本，真实三仓组合再次读回同一正式 V2 结果。CWP `90ba3a64f` 的同投影、不同排版复用通过 82 项验收。FF `c380f99` 按现有来源字段投影可选诊断，368 项定向测试通过。四处均通过独审。RF 原文收据、完整溯源表示和其他余项按实际证据和既有 owner 队列接续。[证据、设计规则及反例](gate-design-review.md)
