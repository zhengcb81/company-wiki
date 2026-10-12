# W08 三个可以现在独立启动的施工包 — 2026-10-12

本批只发这三张新卡，工作目录已准备；不是前次W07的重复。ROOT负责总接口/共享PWF/最终验收并线安装；workers不推main。

| 卡 | 做什么 | 工作目录 | 施工卡 |
|---|---|---|---|
| W08-RF-COMBOS | 补五组已确认遗漏的原生模型组合；保留原16/36 | C:/Users/郑曾波/Projects/_harness_worktrees/w08/rf-combinations | [卡](cards/W08-RF-COMBOS.md) |
| W08-AUDIT-EVIDENCE | 在已有四审覆盖工具上实读执行证据/locator与当前attempt，报告缺口 | C:/Users/郑曾波/Projects/_harness_worktrees/w08/audit-evidence | [卡](cards/W08-AUDIT-EVIDENCE.md) |
| W08-CWP-G2-REPLAY | 做可复现的摘要→公开read→固定RF消费离线包，不修改W04 core | C:/Users/郑曾波/Projects/_harness_worktrees/w08/cwp-g2-replay | [卡](cards/W08-CWP-G2-REPLAY.md) |

## 为什么能同时跑

三工作目录不重叠、三项目不同，唯一写集见dispatch.json。CWP包新tools/narrative_g2_replay与新测试，ROOT改W04 src，源码写集不重叠；输入仍固定122bbe3b，不读ROOT新WIP。RF包只扩tool，不动scripts；Audit包只改review_protocol/新evidence helper，不动loop/四review主卡。CWP只消费固定RF8dc26710代码快照，不等待新RF组合工具，Audit也不读另外两包。

## ROOT接线顺序

1. ROOT W04已证实共因修复→集中测试→正常发布，母目标仍暂停时不因发卡自动启动。
2. 接收三个分支和handoff，独立大节点检查；RF闭五组覆盖，Audit由ROOT接入四审/安装，CWP使用已修当前核心重跑同CaseSpec。
3. ROOT真正配置的G2有限付费模型/公开read/RF消费；G4原三家公司/12独审；G5新A/H/US三家及后续循环。工具工程绿不等于研究完成。

workers只在A/B/C三大节点审查；测试与下载资料归独立测试根并恢复原样。缺hash不新增签收，未知不PASS。各包0外网provider/LLM调用，ROOT累计预算仍$20/200万tokens。

完成后给ROOT卡号、workdir/branch/HEAD和docs/handoffs/<plan_id>/handoff.json/md绝对路径；一包不需要等另一包。详各卡和[共用交接接口](HANDOFF_CONTRACT.md)。母当前状态见[ROOT入口](../w06_parallel_verification_2026-10-11/ROOT-reception-status.md)。
